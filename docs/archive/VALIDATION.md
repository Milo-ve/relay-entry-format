# Validation record

Local environment: macOS ARM64, Python 3.11.15, PyYAML 6.0.3.

## Performed

- 43 unit tests passed with `python -m unittest discover -s tests -v`.
- The offline CLI smoke example passed across all six stages, evidence recording,
  knowledge promotion and source-change invalidation.
- Built `okf_icm-0.2.0-py3-none-any.whl` with pip without build isolation.
- Installed that wheel into a temporary target outside the source tree,
  confirmed the imported module came from that target and reran the smoke
  example successfully with that installation.
- Prepared a separate fresh synthetic evaluation workspace for manual assistant
  testing; no task stage in that workspace was marked complete by the preparation.

## Not established

- No model-provider comparison or live LLM evaluation was performed.
- No reduction in token usage or improvement in reasoning quality was measured.
- No Windows or Linux job was executed locally; CI definitions are provided.
- The OKF validator covers the documented core profile, not every v0.2 feature.
- Prompt-injection resistance is not proven by role labels or unit tests.

The evaluation scorecard should be filled with observed behavior after trying
the same task in selected assistants. No test result establishes compatibility
with every harness or equivalent results across LLMs.
