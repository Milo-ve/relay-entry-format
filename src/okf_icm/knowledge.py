"""OKF core-profile validation and explicit evidence-backed knowledge promotion.

Unknown metadata is retained. This is not a complete OKF v0.2 validator:
attested computations and resource reachability are outside this profile.
"""
from __future__ import annotations

from datetime import datetime, timezone
import re
from urllib.parse import unquote, urlsplit

import yaml

from .storage import ContextError, atomic_write, contained, digest, json_text, now, read_text


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in mapping:
            raise ContextError("YAML mapping keys must be unique strings.")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def parse_concept(text: str) -> tuple[dict, str]:
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)(.*)\Z", text, flags=re.S)
    if not match:
        raise ContextError("Concept needs YAML frontmatter delimited by ---.")
    try:
        meta = yaml.load(match[1], Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise ContextError(f"Invalid YAML: {exc}") from exc
    if not isinstance(meta, dict):
        raise ContextError("Frontmatter must be a mapping.")
    return meta, match[2]


def serialize(meta: dict, body: str) -> str:
    return "---\n" + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True) + "---\n" + body


def timestamp(value) -> datetime:
    try:
        result = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContextError("Timestamp must be an ISO 8601 datetime with timezone.") from exc
    if result.tzinfo is None:
        raise ContextError("Timestamp must include a timezone.")
    return result


def actor(value) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"(?:human:|process:)[^\s]+|[^\s/]+/[^\s]+", value))


def validate_meta(meta: dict) -> list[str]:
    errors = []
    if not isinstance(meta.get("type"), str) or not meta["type"].strip():
        errors.append("type is required and must be a nonempty string")
    if not isinstance(meta.get("status", "stable"), str) or meta.get("status", "stable") not in {"draft", "stable", "deprecated"}:
        errors.append("status must be draft, stable or deprecated")
    if "tags" in meta and (not isinstance(meta["tags"], list) or any(not isinstance(x, str) for x in meta["tags"])):
        errors.append("tags must be a list of strings")
    if "sources" in meta:
        sources = meta["sources"]
        if not isinstance(sources, list) or any(not isinstance(s, dict) or not isinstance(s.get("resource"), str) or not s["resource"].strip() for s in sources):
            errors.append("sources must be a list of mappings containing resource")
    events = []
    if "generated" in meta:
        events.append(("generated", meta["generated"], False))
    if "verified" in meta:
        verified = meta["verified"]
        verified = [verified] if isinstance(verified, dict) else verified
        if not isinstance(verified, list):
            errors.append("verified must be a mapping or list")
        else:
            events.extend(("verified", event, True) for event in verified)
    for label, event, required_time in events:
        if not isinstance(event, dict) or not actor(event.get("by")):
            errors.append(f"{label}.by must identify a human, process or producer/version")
            continue
        if required_time and "at" not in event:
            errors.append(f"{label}.at is required")
        elif "at" in event:
            try:
                timestamp(event["at"])
            except ContextError as exc:
                errors.append(f"{label}.at: {exc}")
    if "stale_after" in meta:
        try:
            timestamp(meta["stale_after"])
        except ContextError as exc:
            errors.append(f"stale_after: {exc}")
    return errors


def freshness(meta: dict) -> str:
    if "stale_after" not in meta:
        return "unspecified"
    return "stale" if datetime.now(timezone.utc) >= timestamp(meta["stale_after"]) else "current"


def trust(meta: dict) -> str:
    events = meta.get("verified", [])
    events = [events] if isinstance(events, dict) else events
    if not events:
        return "unverified"
    return "human-reviewed" if any(str(e.get("by", "")).startswith("human:") for e in events) else "machine-confirmed"


def concept_path(ws, cid: str):
    # An OKF concept ID is its bundle-relative path without .md.
    if not re.fullmatch(r"[a-z0-9][a-z0-9_/-]*", cid) or any(p in {"index", "log", ""} for p in cid.split("/")):
        raise ContextError("Use a lowercase concept path without .md; index/log are reserved.")
    return contained(ws.path(".context/knowledge"), cid + ".md")


def local_links(bundle, path, body: str):
    """Yield (target, destination) for each relative Markdown link outside code fences."""
    plain = re.sub(r"```.*?```", "", body, flags=re.S)
    for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", plain):
        url = urlsplit(target)
        if url.scheme or not url.path:
            continue
        yield target, (bundle / unquote(url.path).lstrip("/")) if url.path.startswith("/") else (path.parent / unquote(url.path))


def inspect_bundle(ws) -> dict:
    bundle = ws.path(".context/knowledge")
    concepts, errors, warnings = [], [], []
    for path in sorted(bundle.rglob("*.md")):
        rel = path.relative_to(bundle).as_posix()
        # Reserved index/log files are not concept documents.
        if path.name in {"index.md", "log.md"}:
            continue
        try:
            text = read_text(ws.root, path.relative_to(ws.root).as_posix())
            meta, body = parse_concept(text)
            problems = validate_meta(meta)
            if problems:
                errors.extend({"path": rel, "message": e} for e in problems)
                continue
            item = {"id": rel[:-3], "title": meta.get("title", path.stem), "type": meta["type"],
                    "status": meta.get("status", "stable"), "trust": trust(meta), "freshness": freshness(meta)}
            concepts.append(item)
            if item["status"] != "stable" or item["freshness"] == "stale" or item["trust"] == "unverified":
                warnings.append({"path": rel, "message": "Review advisory lifecycle/trust/freshness signals", "signals": item})
            for target, dest in local_links(bundle, path, body):
                if not dest.resolve().is_relative_to(bundle.resolve()):
                    warnings.append({"path": rel, "message": f"Link leaves bundle: {target}"})
                elif not dest.exists():
                    warnings.append({"path": rel, "message": f"Unresolved link (allowed by OKF): {target}"})
        except (ValueError, OSError, UnicodeError) as exc:
            errors.append({"path": rel, "message": str(exc)})
    return {"profile": "okf-0.2-core", "concepts": concepts, "errors": errors, "warnings": warnings}


def reindex(ws) -> None:
    report = inspect_bundle(ws)
    if report["errors"]:
        raise ContextError("Cannot index invalid concepts: " + json_text(report["errors"]))
    bundle = ws.path(".context/knowledge")
    folders = {bundle}
    for path in bundle.rglob("*.md"):
        folders.update(p for p in path.parents if p == bundle or p.is_relative_to(bundle))
    for folder in sorted(folders):
        header = '---\nokf_version: "0.2"\n---\n' if folder == bundle else ""
        lines = [header + "# Knowledge index\n"]
        for path in sorted(folder.iterdir()):
            if path.is_dir() and path in folders:
                lines.append(f"- [{path.name}]({path.name}/index.md)\n")
            elif path.suffix == ".md" and path.name not in {"index.md", "log.md"}:
                meta, _ = parse_concept(path.read_text(encoding="utf-8"))
                lines.append(f"- [{meta.get('title', path.stem)}]({path.name}) — {meta.get('description', meta['type'])}\n")
        atomic_write(folder / "index.md", "".join(lines))


def add(ws, cid: str, title: str, kind: str, body_path: str, sources: list[str]) -> dict:
    path = concept_path(ws, cid)
    body = read_text(ws.root, body_path)
    if not body.strip() or not title.strip() or not kind.strip():
        raise ContextError("Concept title, type and body must be nonempty.")
    meta = {"type": kind, "title": title, "status": "draft",
            "generated": {"by": "process:okf-icm", "at": now()},
            "sources": [{"resource": s} for s in sources]}
    if any(not s.strip() for s in sources):
        raise ContextError("Source resources cannot be empty.")
    atomic_write(path, serialize(meta, body), exclusive=True)
    # Indexing is explicit; an unrelated invalid concept cannot leave add half-failed.
    return {"id": cid, "status": "draft", "trust": "unverified", "path": str(path.relative_to(ws.root))}


def promote(ws, cid: str, evidence_path: str, reviewer: str, note: str, confirmed: bool) -> dict:
    if not confirmed or not note.strip():
        raise ContextError("Promotion requires --confirmed-content and a note explaining the actual content check.")
    if not actor(reviewer) or reviewer.startswith("human:"):
        raise ContextError("CLI reviewers must be process:name or producer/version. Human review must be recorded explicitly by the person, not impersonated by this command.")
    path = concept_path(ws, cid)
    meta, body = parse_concept(path.read_text(encoding="utf-8"))
    errors = validate_meta(meta)
    if errors:
        raise ContextError("Invalid concept: " + "; ".join(errors))
    if meta.get("status") == "deprecated" or freshness(meta) == "stale":
        raise ContextError("Resolve deprecation/freshness explicitly before promotion.")
    if not meta.get("sources"):
        raise ContextError("Promotion requires at least one source.")
    if not isinstance(meta.get("icm_reviews", []), list):
        raise ContextError("icm_reviews extension must be a list before appending a review.")
    evidence = read_text(ws.root, evidence_path)
    if not evidence.strip():
        raise ContextError("Review evidence is empty.")
    evidence_hash = digest(ws.path(evidence_path))
    refid = f"references/review-{evidence_hash}"
    refpath = concept_path(ws, refid)
    if refpath == path:
        raise ContextError("Review evidence must be separate from the reviewed concept.")
    refmeta = {"type": "Reference", "title": f"Review evidence for {cid}", "status": "stable",
               "generated": {"by": "process:okf-icm", "at": now()}, "evidence_sha256": evidence_hash}
    if not refpath.exists():
        atomic_write(refpath, serialize(refmeta, evidence), exclusive=True)
    meta["status"] = "stable"
    verified = meta.get("verified", [])
    if isinstance(verified, dict):
        verified = [verified]
    meta["verified"] = [*verified, {"by": reviewer, "at": now()}]
    meta.setdefault("icm_reviews", []).append({"by": reviewer, "at": now(), "note": note,
                                               "evidence": f"/{refid}.md", "sha256": evidence_hash})
    body += f"\nReview evidence: [{refid}](/{refid}.md).\n"
    atomic_write(path, serialize(meta, body))
    return {"id": cid, "status": "stable", "trust": trust(meta), "evidence": refid,
            "note": "Reviewer assertion recorded; the CLI does not independently establish truth."}
