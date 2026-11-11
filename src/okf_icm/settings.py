"""Optional tool settings in `.context/relay/settings.json`.

Settings are not controls: they are never put in packets, editing them does not make
tasks stale, and the file is never created automatically. An absent file means defaults.
Unknown keys and wrong types are refused so a typo cannot silently disable a rule.
"""
from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path

from .storage import ContextError, read_json

RELATIVE = ".context/relay/settings.json"
DEFAULTS = {"lock_wait_seconds": 5.0, "require_expected_revision": False, "deny_paths": []}
MAX_WAIT = 300.0
MAX_PATTERNS = 100
MAX_PATTERN_LENGTH = 200


def _check(key: str, value):
    if key == "lock_wait_seconds":
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= MAX_WAIT:
            raise ContextError(f"{RELATIVE}: lock_wait_seconds must be a number from 0 to {MAX_WAIT:g}.")
        return float(value)
    if key == "require_expected_revision":
        if not isinstance(value, bool):
            raise ContextError(f"{RELATIVE}: require_expected_revision must be true or false.")
        return value
    if key == "deny_paths":
        if not isinstance(value, list) or len(value) > MAX_PATTERNS or not all(
                isinstance(x, str) and x.strip() and len(x) <= MAX_PATTERN_LENGTH and "\x00" not in x for x in value):
            raise ContextError(f"{RELATIVE}: deny_paths must be a list of at most {MAX_PATTERNS} non-empty "
                               f"strings of at most {MAX_PATTERN_LENGTH} characters.")
        if any(not _normal(x) for x in value):
            raise ContextError(f"{RELATIVE}: a deny_paths pattern cannot be only slashes or dots.")
        return [x.strip() for x in value]
    raise ContextError(f"{RELATIVE}: unknown setting '{key}'. Known settings: {', '.join(DEFAULTS)}.")


def load(home: Path) -> dict:
    """Return validated settings for the `.context` folder `home`. Reads only; never writes."""
    path = home / "relay" / "settings.json"
    result = {key: (list(value) if isinstance(value, list) else value) for key, value in DEFAULTS.items()}
    if not path.exists() and not path.is_symlink():
        return result
    if path.is_symlink() or not path.is_file():
        raise ContextError(f"{RELATIVE} must be a regular file.")
    for key, value in read_json(path).items():
        result[key] = _check(key, value)
    return result


def _normal(pattern: str) -> str:
    value = pattern.strip().casefold().replace("\\", "/")
    while value.startswith("./"):
        value = value[2:]
    return value.strip("/")


def denied_by(patterns: list[str], relative: str) -> str | None:
    """Return the first deny_paths pattern that matches `relative`, or None.

    Case-insensitive. A pattern without a slash matches any one path component (`*.pem`, `secrets`);
    a pattern with a slash matches the whole path or any parent directory of it (`finance/payroll*`).
    """
    parts = [c for c in relative.casefold().replace("\\", "/").split("/") if c not in ("", ".")]
    prefixes = ["/".join(parts[:i]) for i in range(1, len(parts) + 1)]
    for pattern in patterns:
        normal = _normal(pattern)
        if normal and any(fnmatchcase(candidate, normal) for candidate in (prefixes if "/" in normal else parts)):
            return pattern
    return None


def check_selection(root: Path, spelled: str, patterns: list[str]) -> None:
    """Refuse a selected source whose spelled path, or the path it resolves to, is denied.

    Run before the file is read. Not a secret scanner: it only applies the names the operator listed.
    """
    if not patterns:
        return
    names = [Path(spelled).as_posix()]
    try:
        names.append((root / spelled).resolve().relative_to(root.resolve()).as_posix())
    except (OSError, ValueError):
        pass  # an escaping or unreadable path is refused by the normal readers
    for name in names:
        hit = denied_by(patterns, name)
        if hit:
            via = "" if name == names[0] else " (through a link)"
            raise ContextError(f"'{spelled}' matches the deny_paths pattern '{hit}'{via} in {RELATIVE} and cannot be selected "
                               "as a source. Choose other sources, or change the setting deliberately.")
