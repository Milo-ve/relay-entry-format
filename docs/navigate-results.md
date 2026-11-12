# Navigate: first implementation evaluation

Evaluated on 2026-11-11, after the user accepted decision 3: 12,000 source packet
characters, 2,000 raw characters per source, no per-type budgets, and `--stage` in v1.
The budget commits d679327 and d67964d remain the pre-implementation record.

**Status: experimental; held-out acceptance failed.** The original synthetic gate
passes, including its gap cases. The independent held-out fixture returns guesses
for all three gap goals. No ranking changes were made after either result was seen.
No fixture or expected set was changed. This is not ready to claim reliable gap detection.
The CLI is available on this branch for inspection; no release/version bump was made.

## Reproduce

With the project dependencies installed:

```sh
python examples/navigation_evaluate.py --fixture navigation
python examples/navigation_evaluate.py --fixture navigation_heldout
python examples/navigation_evaluate.py --fixture both
```

The evaluator copies each fixture to a temporary workspace, compares repeated results,
checks file bytes before and after, scores concept-level precision and recall using the
frozen expected sets, and compares the frozen keyword-top-five baseline. It records
raw source characters separately from framed task-packet characters. It returns **1**
when any requested fixture fails acceptance; the held-out failure is intentional to
retain visibly in this record, not a passing regression test.

The ranking implementation evaluated here is `src/okf_icm/navigation.py`, SHA-256:

```
8436edfe943066ce71e8cb3f1277d4be015860de247abf097364f21f53712100
```

Both fixture evaluations used that same implementation, without intermediate tuning.
The held-out sizes had already informed the budgets, as disclosed in
[navigate-budgets.md](archive/navigate-budgets.md). Held-out retrieval results were not used
to modify the algorithm. Now that these results have been seen, this held-out set
cannot serve as a blind test of a future tuned revision.

## Measurements

Precision and recall are macro means over 17 non-gap goals in each fixture.
Character means include every goal (19 synthetic, 20 held-out). A section counts
as a concept-level hit; these metrics do **not** establish that every returned section
contains the required facts or is sufficient for the goal.

| Metric | Original synthetic | Independent held-out |
| --- | ---: | ---: |
| Navigator precision | 0.391527 | 0.624020 |
| Keyword top-five precision | 0.317647 | 0.317647 |
| Navigator recall | 0.980392 | 1.000000 |
| Keyword top-five recall | 0.852941 | 1.000000 |
| Mean raw source characters per goal | 3,953.58 | 2,714.20 |
| Mean source packet characters per goal | 5,795.63 | 3,965.50 |
| Select-everything raw source characters | 41,683 | 62,498 |
| Silent hazards | 0 | 0 |
| Required stale-only source returned flagged | Yes | Yes |
| Gap goals with an explicit no-coverage result and no guesses | 2 / 2 | 0 / 3 |
| Denied or sensitive paths in any output | 0 | 0 |
| Byte-identical repeated results | Yes | Yes |
| Workspace file bytes unchanged | Yes | Yes |
| Overall acceptance | **Pass** | **Fail** |

The synthetic miss is `g02-refund-annual-enterprise`: `processes/invoicing` is
absent, while the other two expected concepts are returned. Aggregate recall
still exceeds the predeclared baseline gate. Some goals return many extra sources;
a gate pass does not mean minimal or sufficient selection.

The held-out failures are:

| Goal | What was requested | Concepts suggested despite absent coverage |
| --- | --- | --- |
| `h15-extraction-capacity` | Verified airflow capacity and pressure setpoint for a proposed third grinding booth | `bench/tool-cabinet`, `records/received-note` |
| `h16-opalveil-ratios` | Master concentrate ratios for Opalveil | `kilns/calibration`, `materials/amber-finish`, `materials/silver-bloom-finish`, `records/decision-reclaim-split`, `studio/blue-card-artwork` |
| `h18-food-contact-certificate` | Jurisdiction-specific food-contact certificate for Vela cups | `bench/measurement-manual`, `records/vela-cup-drawing` |

Inferred cause: lexical overlap in metadata/headings and links can clear the relevance
threshold without supporting the specific requested claim. The program can report
unmatched terms while still suggesting nearby concepts. Neither returned suggestions
nor the absence of a `no_coverage` code establish coverage. Fixing that would require
a new design decision and an independently frozen evaluation set; this implementation
has been left unchanged in accordance with the stop-on-failure rule.

## Regression checks

- `python -m unittest discover -s tests -v`: **258 passed**, including 13 new navigation
  tests and the existing legacy state/packet compatibility tests. The existing loopback
  HTTP tests required execution outside the restricted network sandbox.
- `python examples/smoke.py`: **passed**, installed CLI, six stages, evidence, promotion,
  source-change invalidation.
- `python examples/relay_smoke.py`: **passed**, task context, submission, version-specific
  review, changed source and refresh.
- `git diff --check`: **passed**. Frozen fixture files unchanged.

The integration rerun exported all committed files with `git archive` to a fresh
temporary directory, then ran the full suite, both smoke examples and both fixture
evaluations there. Checks used the existing local virtual environment's Python,
with the export's absolute `src` on `PYTHONPATH`; the shell did not have a bare
`python` executable. The clean export reproduced the measurements above and the
held-out evaluator's exit code 1.
The integration check also exercises CLI suggestions passed explicitly to `start`
and `context`, then changes text outside the selected section and confirms the
full-file hash still makes the task need review. The CLI prints an experimental
warning on stderr and the bundled REF skill guides this inspection/selection
step; the ranking module and its fingerprint above remain unchanged.

A fresh-checkout check found that the original synthetic sensitive-path decoy,
`tests/fixtures/navigation/context/knowledge/ops/.env-conventions.md`, existed only
as an ignored local file in the design worktree. Its original bytes are now
included explicitly so fixture checks also work from GitHub. It contains only
fictional naming conventions, no environment values or credentials. Frozen goals,
expected sets and existing fixture files were not changed.

No model was called. These are synthetic retrieval and software checks, not observed
user savings, answer-quality measurements, substantive source verification or acceptance
of any project deliverable. Spanish generated sentences have automated catalogue/parity
coverage, not a new human language review.
