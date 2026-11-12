# Relay Method development

Start here. Do not read `README.md` or whole documents by default: open `docs/INDEX.md`, then only the section the task needs. `docs/archive/` is history; read it only when asked.

- Entry, controls, packet shape: `docs/REF.md`. Change it in the same commit.
- `relay` commands, tasks, review: the matching section of `docs/RELAY.md`.
- `okf-icm` stage runs: `docs/PROTOCOL.md`.
- A refused command: the matching entry of `docs/TROUBLESHOOTING.md`.

Sessions: one task each. Ongoing work is a Relay task in the local `.context`: `relay list --brief` shows it and `relay context TASK` exports its bounded packet. End by recording the result or a short note.

Effort: a route with `reasoning` low or medium suits a small or standard model, high a frontier model. With no task, use a standard model. This is advice; nothing enforces it.

Rules:

- Runtime code lives in `src/okf_icm`; retain the `okf-icm` entry point for compatibility.
- REF v1 adds no on-disk version marker; do not add one to existing projects.
- Keep the core provider-neutral. Jev is optional, explicit, and cannot grant permission or weaken required review.
- Preserve existing project state. Never silently migrate stage graphs or fabricate checkpoints.
- Distinguish selected source versions, substantive verification, and actual acceptance.
- Run `python -m unittest discover -s tests -v`, `python examples/smoke.py`, and `python examples/relay_smoke.py` for behavior changes.
- Use synthetic fixtures. Live model results and user savings require separate observed evidence.
- Local `.context`, private packets, API keys, virtual environments, and generated deliverables must stay out of public Git history.
- This is a loopback trusted-user prototype; do not claim organizational authorization or managed compute enforcement.
- A new file in `docs/` needs a line in `docs/INDEX.md`; `tests/test_docs_index.py` enforces it and this file's size.
