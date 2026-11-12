# Legacy task fixture

Synthetic workspace produced by the Relay code at commit `3ad37aa` (before any
Relay-brief change). It is frozen: do not regenerate it with newer code, because
its purpose is to prove that newer code still reads state written by older code.

- `context/` is the `.context` folder (stored without the dot so it is not gitignored).
- `legacy-faq`: started, submitted, accepted.
- `legacy-escalated`: started, then refreshed with escalation.
- `expected_status.json`: `status()` output recorded at generation, without `next_step`
  (it embeds the project path).

All content is invented. `tests/test_compat.py` copies this folder to a temporary
directory and never writes to it.
