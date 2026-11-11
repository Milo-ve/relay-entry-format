"""Bounded reads, contained paths, atomic writes and cooperative writer locking."""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time


class ContextError(ValueError):
    pass


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def identifier(value: str) -> str:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", value):
        raise ContextError("IDs must contain 1-80 lowercase letters, digits or hyphens.")
    return value


def contained(root: Path, value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ContextError(f"Use a contained relative path: {value}")
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ContextError(f"Path escapes the workspace: {value}")
    return target


def readable(root: Path, value: str | Path) -> Path:
    target = contained(root, value)
    # Check both spelling and resolved target, including symlinks inside root.
    parts = (*Path(value).parts, *target.relative_to(root.resolve()).parts)
    if any(p.casefold() in {".git", ".ssh", ".aws", ".venv"} or p.casefold().startswith(".env") for p in parts):
        raise ContextError(f"Sensitive/internal path is not exportable: {value}")
    if target.stat().st_size > 1_000_000:
        raise ContextError(f"File exceeds 1 MB: {value}")
    return target


def read_text(root: Path, value: str | Path) -> str:
    text = readable(root, value).read_text(encoding="utf-8")
    if "\x00" in text:
        raise ContextError(f"Binary file is not context: {value}")
    return text


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_text(data: object) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n"


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContextError(f"Expected a JSON object: {path.name}")
    return value


def atomic_write(path: Path, text: str, *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        # O_EXCL refuses existing files, including symlinks.
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        return
    fd, name = tempfile.mkstemp(prefix=".ctx-", dir=path.parent)
    try:
        # Write LF on every platform so identical content has identical bytes
        # (and hashes) on Windows, macOS and Linux.
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _holder(path: Path) -> str:
    """Describe who holds the lock, or an empty string if the file is not readable yet."""
    try:
        held = json.loads(path.read_text(encoding="utf-8"))
        return f", held by process {held['pid']} since {held['at']}"
    except (OSError, ValueError, KeyError, TypeError):
        return ""


@contextmanager
def lock(workspace: Path, wait: float = 0.0):
    """Cooperative writer lock. Poll for up to `wait` seconds; 0 fails at once."""
    path = workspace / "write.lock"
    deadline = time.monotonic() + wait
    while True:
        try:
            handle = path.open("x", encoding="utf-8")
            break
        except FileExistsError as exc:
            if time.monotonic() >= deadline:
                waited = f" after waiting {wait:g}s" if wait else ""
                raise ContextError(f"Workspace writer is busy (write.lock{_holder(path)}){waited}. "
                                   "If a process crashed, confirm it stopped before removing the lock.") from exc
            time.sleep(0.05)
    try:
        with handle:
            handle.write(json_text({"pid": os.getpid(), "at": now()}))
        yield
    finally:
        path.unlink(missing_ok=True)
