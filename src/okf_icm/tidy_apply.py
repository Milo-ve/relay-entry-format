"""`relay tidy --apply` and `--undo`: carry out the cleanups that need no judgment, and take them back.

A single run, with no per-file approval, does three things a person would otherwise do by hand:

* remove a file whose content is identical to another, and point its links at the one kept;
* archive a file nothing links to, once it has sat untouched for `tidy_orphan_days`;
* repair a broken link when exactly one scanned file has that name.

Everything else the report finds (overlapping sections, oversized entry files, invalid or stale
concepts) needs a reader, so it is left in the report. No model is contacted here, and Jev has no
part in it: nothing in this module is decided by a score.

Safety is by construction, not by asking. Before any change every original is copied to
`.relay-backups/tidy-*/files` and a manifest is written. Nothing is touched if any file changed
since it was read. Files that project controls or task state name by path, files with uncommitted
Git changes, entry files and indexes are never moved. If the run would leave more broken links than
it found, it undoes itself. `--undo` restores the whole run, and skips any file edited since.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import settings, tidy
from .i18n import translator
from .navigation import LINK
from .storage import ContextError, atomic_write, json_text, lock, read_json

BACKUPS = ".relay-backups"
RUN_ID = re.compile(r"^tidy-\d{8}T\d{6}Z-[0-9a-f]{4}$")
AUTO = ("duplicate-file", "broken-link", "orphan")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _put(path: Path, data: bytes, *, exclusive: bool = False) -> None:
    if path.is_symlink() or (exclusive and os.path.lexists(path)):
        raise FileExistsError(f"Refusing to write over: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".ctx-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _spell(relative: str) -> str:
    """A path as a Markdown link target: no spaces or parentheses, which end the target."""
    return relative.replace("%", "%25").replace(" ", "%20").replace("(", "%28").replace(")", "%29")


def _inside(root: Path, path: Path) -> str | None:
    return path.relative_to(root).as_posix() if path.is_relative_to(root) else None


def _taken(destination: Path) -> bool:
    """True when the name is in use, including by a name that differs only in case."""
    if os.path.lexists(destination):
        return True
    try:
        return destination.name.casefold() in {name.casefold() for name in os.listdir(destination.parent)}
    except OSError:
        return False


def _dirty(root: Path) -> set[str] | None:
    """Paths with uncommitted or untracked changes, relative to `root`; None when not a Git checkout."""
    try:
        prefix = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-prefix"], capture_output=True, text=True, timeout=20)
        status = subprocess.run(["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"],
                                capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    if prefix.returncode or status.returncode:
        return None
    base, dirty, parts, index = prefix.stdout.strip(), set(), status.stdout.split("\0"), 0
    while index < len(parts):
        entry, index = parts[index], index + 1
        if len(entry) < 4:
            continue
        code, path = entry[:2], entry[3:]
        if "R" in code or "C" in code:
            index += 1  # a rename lists its old path next
        dirty.add(path[len(base):] if base and path.startswith(base) else path)
    return dirty


def _state_text(root: Path) -> str:
    """Project controls and task state outside the knowledge bundle, which may name files by path."""
    home, parts = root / ".context", []
    if not home.is_dir() or home.is_symlink():
        return ""
    for folder, dirs, names in os.walk(home, followlinks=False):
        here = Path(folder)
        dirs[:] = [d for d in dirs if not (here / d).is_symlink() and (here / d) != root / tidy.BUNDLE]
        for name in names:
            path = here / name
            try:
                if not path.is_symlink() and path.stat().st_size <= 1_000_000:
                    parts.append(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError):
                continue
    return "\n".join(parts)


def _protected(relative: str) -> str | None:
    path = Path(relative)
    if relative in tidy.LINK_SOURCES:
        return "entry-file"
    if path.name.casefold() in tidy.INDEX_NAMES:
        return "index"
    if relative.startswith(".context/") and not relative.startswith(tidy.BUNDLE + "/"):
        return "project-control-or-state"
    return None


def _relink(root: Path, text: str, old: str, new: str, redirect) -> tuple[str, int]:
    """Rewrite local links outside code fences. `redirect(target, destination)` names a new destination or None.

    Every local link is also re-spelled when the file itself moves to another folder.
    """
    before, after, count, fence, out = (root / old).parent, (root / new).parent, 0, None, []

    def swap(match):
        nonlocal count
        label, target = match.group(1), match.group(2)
        url = urlsplit(target)
        if url.scheme or not url.path:
            return match.group(0)
        destination = (before / unquote(url.path)).resolve()
        changed = redirect(target, destination)
        if changed is None and before == after:
            return match.group(0)
        spelled = _spell(os.path.relpath(changed or destination, after).replace(os.sep, "/"))
        spelled += (f"?{url.query}" if url.query else "") + (f"#{url.fragment}" if url.fragment else "")
        if spelled == target:
            return match.group(0)
        count += 1
        return f"[{label}]({spelled})"

    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            fence = marker if fence is None else (None if marker == fence else fence)
            out.append(line)
        else:
            out.append(LINK.sub(swap, line) if fence is None else line)
    return "".join(out), count


def _plan(root: Path, scope: list[str] | None, loaded: dict) -> dict:
    deny, enabled, days = loaded["deny_paths"], set(loaded["tidy_actions"]), loaded["tidy_orphan_days"]
    result = tidy.scan(root, scope, deny=deny, language=loaded["language"], configured=None)
    scanned = tidy._markdown_files(root, result["scope"], deny)
    holders: dict[str, tuple[bytes, str]] = {}
    for relative in [*scanned, *(n for n in tidy.LINK_SOURCES if tidy._allowed(root, n, deny) is not None)]:
        if relative in holders:
            continue
        try:
            raw = (root / relative).read_bytes()
            holders[relative] = (raw, raw.decode("utf-8"))
        except (OSError, UnicodeError):
            continue
    findings = result["findings"]
    skipped: list[dict] = []
    remap: dict[str, str] = {}       # a removed or archived file -> where its links should point now
    removals: dict[str, str] = {}    # removed duplicate -> the file kept
    archives: dict[str, str] = {}    # archived orphan -> its new path
    pinned: set[str] = set()         # files that will have inbound links after this run
    state, dirty = None, _dirty(root)

    def named(relative: str) -> bool:
        nonlocal state
        if state is None:
            state = _state_text(root)
        names = [relative] + ([relative[len(tidy.BUNDLE) + 1:]] if relative.startswith(tidy.BUNDLE + "/") else [])
        return any(name in state for name in names)

    def refuse(relative: str) -> str | None:
        if relative not in holders:
            return "not-readable"
        return _protected(relative) or ("named-by-project-state" if named(relative) else None)

    if "duplicate-file" in enabled:
        for finding in (f for f in findings if f["kind"] == "duplicate-file"):
            keep = finding["evidence"]["keep"]
            pinned.add(keep)
            for relative in finding["paths"]:
                if relative == keep:
                    continue
                reason = refuse(relative) or (None if keep in holders else "kept-copy-not-readable")
                if reason:
                    skipped.append({"kind": "duplicate-file", "paths": [relative], "reason": reason})
                else:
                    removals[relative] = remap[relative] = keep

    by_name: dict[str, list[str]] = {}
    for relative in scanned:
        by_name.setdefault(Path(relative).name.casefold(), []).append(relative)
    fixable: dict[tuple[str, str], str] = {}
    if "broken-link" in enabled:
        for finding in (f for f in findings if f["kind"] == "broken-link"):
            holder, target = finding["paths"][0], finding["evidence"]["target"]
            name = Path(unquote(urlsplit(target).path)).name.casefold()
            found = [c for c in by_name.get(name, []) if c != holder]
            if len(found) == 1 and holder in holders and holder not in removals:
                fixable[(holder, target)] = remap.get(found[0], found[0])
                pinned.add(fixable[(holder, target)])
            else:
                skipped.append({"kind": "broken-link", "paths": [holder], "reason": "no-single-match", "target": target})

    if "orphan" in enabled and days:
        for finding in (f for f in findings if f["kind"] == "orphan"):
            relative = finding["paths"][0]
            if relative in pinned or relative in removals or "archive" in Path(relative).parts:
                continue
            path = root / relative
            reason = refuse(relative)
            if not reason and relative.startswith(tidy.BUNDLE + "/"):
                reason = "knowledge-concept"  # found by search, not by links
            if not reason and time.time() - path.stat().st_mtime < days * 86400:
                reason = f"changed-in-last-{days}-days"
            if not reason and dirty is not None and relative in dirty:
                reason = "uncommitted-changes"
            destination = path.parent / "archive" / path.name
            if not reason and _taken(destination):
                reason = "archive-name-taken"
            if reason:
                skipped.append({"kind": "orphan", "paths": [relative], "reason": reason})
            else:
                archives[relative] = remap[relative] = _inside(root, destination)

    rewrites: dict[str, tuple[str, int]] = {}
    for relative, (_, text) in holders.items():
        if relative in removals:
            continue

        def redirect(target, destination, holder=relative):
            inside = _inside(root, destination)
            if inside in remap:
                return root / remap[inside]
            if not destination.exists() and (holder, target) in fixable:
                return root / fixable[(holder, target)]
            return None
        rewritten, count = _relink(root, text, relative, archives.get(relative, relative), redirect)
        if count or relative in archives:
            rewrites[relative] = (rewritten, count)
    return {"scan": result, "holders": holders, "removals": removals, "archives": archives, "rewrites": rewrites,
            "skipped": skipped}


def _summary(plan: dict) -> dict:
    changed = {relative: count for relative, (_, count) in plan["rewrites"].items() if count}
    return {"removed": [{"path": p, "same_as": k} for p, k in sorted(plan["removals"].items())],
            "archived": [{"path": p, "to": d} for p, d in sorted(plan["archives"].items())],
            "links_updated": [{"path": p, "links": c} for p, c in sorted(changed.items())],
            "skipped": plan["skipped"]}


def _broken(result: dict) -> int:
    return result["counts"].get("broken-link", 0)


def apply(root: Path, scope: list[str] | None = None, *, dry_run: bool = False) -> dict:
    root = root.resolve()
    home = root / ".context"
    loaded = settings.load(home) if home.is_dir() and not home.is_symlink() else dict(settings.DEFAULTS)
    t = translator(loaded["language"])
    if not root.is_dir():
        raise ContextError("The project root must be an existing folder.")
    if (root / BACKUPS).is_symlink():
        raise ContextError(f"{BACKUPS} must not be a symbolic link.")
    if home.is_dir() and not home.is_symlink():
        with lock(home, wait=loaded["lock_wait_seconds"]):
            return _apply(root, scope, loaded, t, dry_run)
    return _apply(root, scope, loaded, t, dry_run)


def _apply(root: Path, scope, loaded: dict, t, dry_run: bool) -> dict:
    plan = _plan(root, scope, loaded)
    summary, holders = _summary(plan), plan["holders"]
    kept = {k: v for k, v in plan["scan"]["counts"].items() if k not in AUTO}
    changes = bool(plan["removals"] or plan["archives"] or any(count for _, count in plan["rewrites"].values()))
    base = {**summary, "left_for_review": kept, "note": t("tidy.left")}
    if dry_run:
        return {"mode": "dry-run", **base, "summary": t("tidy.dry_run")}
    if not changes:
        return {"mode": "unchanged", "run": None, **base, "summary": t("tidy.nothing_to_apply")}

    entries: list[dict] = []
    for relative, (text, count) in plan["rewrites"].items():
        raw = holders[relative][0]
        data = text.encode("utf-8")
        if relative in plan["archives"]:
            entries.append({"kind": "move", "path": relative, "to": plan["archives"][relative], "before": _sha(raw),
                            "after": _sha(data), "links": count, "_data": data})
        else:
            entries.append({"kind": "rewrite", "path": relative, "before": _sha(raw), "after": _sha(data),
                            "links": count, "_data": data})
    for relative, keep in plan["removals"].items():
        entries.append({"kind": "remove", "path": relative, "same_as": keep, "before": _sha(holders[relative][0])})

    # Nothing is touched unless every file is still exactly what was read.
    for entry in entries:
        if _sha((root / entry["path"]).read_bytes()) != entry["before"]:
            raise ContextError(f"{entry['path']} changed while tidying; nothing was changed. Run again.")
    for entry in entries:
        if entry["kind"] == "remove":
            kept_path = root / entry["same_as"]
            if tidy._normal(kept_path.read_text(encoding="utf-8")) != tidy._normal(holders[entry["path"]][1]):
                raise ContextError(f"{entry['same_as']} no longer matches {entry['path']}; nothing was changed. Run again.")
        if entry["kind"] == "move" and _taken(root / entry["to"]):
            raise ContextError(f"{entry['to']} appeared while tidying; nothing was changed. Run again.")

    run = "tidy-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(2)
    folder = root / BACKUPS / run
    for entry in entries:
        _put(folder / "files" / entry["path"], holders[entry["path"]][0], exclusive=True)
    manifest = {"id": run, "status": "applying", "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "scope": plan["scan"]["scope"], "entries": [{k: v for k, v in e.items() if k != "_data"} for e in entries]}
    atomic_write(folder / "manifest.json", json_text(manifest))
    before = _broken(plan["scan"])
    try:
        for entry in entries:
            if entry["kind"] == "rewrite":
                _put(root / entry["path"], entry["_data"])
        for entry in entries:
            if entry["kind"] == "move":
                _put(root / entry["to"], entry["_data"], exclusive=True)
                (root / entry["path"]).unlink()
        for entry in entries:
            if entry["kind"] == "remove":
                (root / entry["path"]).unlink()
        after = tidy.scan(root, scope, deny=loaded["deny_paths"], language=loaded["language"], configured=None)
    except Exception as exc:
        _restore(root, folder, manifest, t)
        raise ContextError(f"Tidy failed and was undone ({exc}).") from exc
    if _broken(after) > before:
        _restore(root, folder, manifest, t)
        return {"mode": "rolled-back", "run": run, **base, "summary": t("tidy.rolled_back")}
    manifest["status"] = "complete"
    atomic_write(folder / "manifest.json", json_text(manifest))
    counts = {"removed": len(plan["removals"]), "archived": len(plan["archives"]),
              "links": sum(c for _, c in plan["rewrites"].values()), "rewritten": len(summary["links_updated"])}
    return {"mode": "applied", "run": run, **{**base, "left_for_review": {k: v for k, v in after["counts"].items()}},
            "summary": t("tidy.applied", run=run, **counts), "undo": f"relay tidy --undo {run}"}


def _restore(root: Path, folder: Path, manifest: dict, t) -> dict:
    restored, conflicts = 0, []
    for entry in reversed(manifest["entries"]):
        original, path = (folder / "files" / entry["path"]).read_bytes(), root / entry["path"]
        here = _sha(path.read_bytes()) if path.is_file() else None
        if entry["kind"] == "rewrite":
            if here == entry["after"]:
                _put(path, original)
                restored += 1
            elif here != entry["before"]:
                conflicts.append(entry["path"])
        elif entry["kind"] == "move":
            moved = root / entry["to"]
            there = _sha(moved.read_bytes()) if moved.is_file() else None
            if here is None and there == entry["after"]:
                _put(path, original, exclusive=True)
                moved.unlink()
                restored += 1
                try:
                    moved.parent.rmdir()  # the archive folder this run created, if it is now empty
                except OSError:
                    pass
            elif not (there is None and here == entry["before"]):
                conflicts.append(entry["path"])
        elif entry["kind"] == "remove":
            if here is None and not os.path.lexists(path):
                _put(path, original, exclusive=True)
                restored += 1
            elif here != entry["before"]:
                conflicts.append(entry["path"])
    manifest["status"] = "undone"
    atomic_write(folder / "manifest.json", json_text(manifest))
    return {"mode": "undone", "run": manifest["id"], "restored": restored, "conflicts": conflicts,
            "summary": t("tidy.undone", run=manifest["id"], restored=restored, conflicts=len(conflicts))}


def undo(root: Path, run: str = "latest") -> dict:
    root = root.resolve()
    home = root / ".context"
    loaded = settings.load(home) if home.is_dir() and not home.is_symlink() else dict(settings.DEFAULTS)
    t = translator(loaded["language"])
    backups = root / BACKUPS
    if backups.is_symlink():
        raise ContextError(f"{BACKUPS} must not be a symbolic link.")

    def go():
        if run == "latest":
            found = sorted(p.name for p in backups.glob("tidy-*") if RUN_ID.match(p.name) and (p / "manifest.json").is_file()
                           and read_json(p / "manifest.json").get("status") == "complete") if backups.is_dir() else []
            if not found:
                raise ContextError("No tidy run to undo.")
            name = found[-1]
        elif RUN_ID.match(run):
            name = run
        else:
            raise ContextError("Name a run as printed by `tidy --apply`, or use `latest`.")
        folder = backups / name
        if not (folder / "manifest.json").is_file():
            raise ContextError(f"No such tidy run: {name}")
        manifest = read_json(folder / "manifest.json")
        if manifest.get("status") == "undone":
            raise ContextError(f"{name} was already undone.")
        return _restore(root, folder, manifest, t)
    if home.is_dir() and not home.is_symlink():
        with lock(home, wait=loaded["lock_wait_seconds"]):
            return go()
    return go()
