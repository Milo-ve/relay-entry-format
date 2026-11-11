"""Optional tool settings in `.context/relay/settings.json`.

Settings are not controls: they are never put in packets, editing them does not make
tasks stale, and the file is never created automatically. An absent file means defaults.
Unknown keys and wrong types are refused so a typo cannot silently disable a rule.
"""
from __future__ import annotations

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
