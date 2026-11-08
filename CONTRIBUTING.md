# Contributing

Install from source and run `python -m unittest discover -s tests -v` and
`python examples/smoke.py` and `python examples/relay_smoke.py`. Keep the core independent of provider APIs and
harness-specific state. New integrations should adapt the packet protocol.

Add tests for behavioral changes, particularly source invalidation, honest
review signals and safe path handling. Update the protocol for schema changes, and `docs/REF.md` when the entry, controls or packet shape change.
Do not silently migrate or overwrite existing project state.

Use synthetic fixtures. Do not submit credentials, private packets or user data.
Report model behavior separately from deterministic CLI results. Include model,
harness, tool access and observed evidence when discussing live evaluations.
