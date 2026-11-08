# Relay Method development

Read README.md and docs/RELAY.md. The original stage protocol is in docs/PROTOCOL.md.

- Runtime code lives in `src/okf_icm`; retain the `okf-icm` entry point for compatibility.
- Keep the core provider-neutral. Jev is optional, explicit, and cannot grant permission or weaken required review.
- Preserve existing project state. Never silently migrate stage graphs or fabricate checkpoints.
- Distinguish selected source versions, substantive verification, and actual acceptance.
- Run `python -m unittest discover -s tests -v`, `python examples/smoke.py`, and `python examples/relay_smoke.py` for behavior changes.
- Use synthetic fixtures. Live model results and user savings require separate observed evidence.
- Local `.context`, private packets, API keys, virtual environments, and generated deliverables must stay out of public Git history.
- This is a loopback trusted-user prototype; do not claim organizational authorization or managed compute enforcement.
