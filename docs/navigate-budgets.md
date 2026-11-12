# Navigate budgets (accepted)

Status: decision 3 accepted by the user on 2026-11-11: 12,000 source packet characters,
2,000 raw characters per source, no per-type budgets; `--stage` ships in v1.
The measurements and proposal were committed before implementation (d679327, d67964d),
so the budgets were not tuned to navigator results.

## What this is based on

Only sizes measured in this repository, reproduced by `python examples/navigation_sizes.py`
(read-only, no model, no navigator):

- every permitted concept in the synthetic knowledge base (48) and the held-out one (44);
- the `expected` lists in both `goals.json` files (17 source-backed goals each);
- the existing defaults: `--max-chars` 32,000 for `start` and `context` (`relay_cli.py`, `cli.py`),
  the 1,000 to 1,000,000 range (`tasks.py`), the 2,500-character control bound
  ([ADOPTION.md](ADOPTION.md)), and "budgets count rendered Unicode characters, not tokens"
  ([PROTOCOL.md](PROTOCOL.md)).

No precision, recall or navigator output was used. The held-out sizes were used, so that
fixture no longer tests the budgets blind. They are recorded here before any navigator code.

Estimates, not measurements, are marked **(est.)**. There is no tokenizer in the repo, so every
token figure is an estimate. Judgment calls are marked **(judgment)**.

## Measurements

**The unit.** `start` counts the whole rendered packet, so a selected source costs more than its
text. Measured on real packets (`Tasks.render_packet`), the cost added by one source is its raw
characters plus 376 to 433 (median 395 synthetic, 398 held-out), about 366 fixed plus one per
newline. Over a whole base, framed/raw is 1.46 (synthetic) and 1.28 (held-out), because the fixed part
weighs most on small files.

| | Synthetic | Held-out |
|---|---|---|
| Permitted concepts | 48 | 44 |
| Raw characters, everything | 41,683 | 62,498 |
| Framed characters, everything | 60,649 | 80,022 |
| Packet overhead with controls, no sources | 5,373 | 3,576 |
| Controls, raw (`ENTRY`, `policy`, `project`, `config`) | 2,873 | 1,210 |

Select-everything exceeds the 32,000 default in both, as the design doc says.

**Whole file or section.** A `#` title section spans the whole file, and every section over
1,500 characters in either knowledge base is such a title section (0 in the synthetic base, 4 in
the held-out one).

| | Synthetic | Held-out |
|---|---|---|
| Files over 1,500 / 2,000 / 3,000 raw characters | 2 / 0 / 0 | 6 / 4 / 3 |
| Expected items taken whole (count, largest file) | 16, 1,530 | 8, 1,416 |
| Expected items taken as a section (count, largest section) | 17, 401 | 19, 682 |
| Largest file an expected set takes only a section of | 1,669 | 5,126 |

The four held-out files over 2,000 characters are all type `Standard`. No expected set takes any
of them whole; the sections they take from them are at most 682 characters.

**Expected sets (framed, sources only).**

| | Synthetic | Held-out |
|---|---|---|
| Largest set, sections where the set says so | 4,517 | 4,754 |
| Largest set, if every source were taken whole | 5,087 | 5,703 |
| Median set, as written / all whole | 1,771 / 3,224 | 1,362 / 3,611 |
| Items per set (median, max) | 2, 3 | 1, 3 |
| Sets that fit 4,000 as written / whole | 16 / 13 of 17 | 16 / 12 of 17 |
| Sets that fit 6,000 (either way) | 17 of 17 | 17 of 17 |

**By concept `type`.** The type is a free-form string (`validate_meta` requires only a nonempty
string), and the same type has different sizes in the two bases (`Reference`: median 841 synthetic,
1,163 held-out). Types with at least one expected item:

| Type (base) | Files | Median / max file | Expected items | Largest one-goal total, framed |
|---|---|---|---|---|
| Policy (S) | 10 | 1,041 / 1,669 | 12 | 1,769 |
| Reference (S) | 10 | 841 / 1,530 | 8 | 3,185 |
| Process (S) | 9 | 1,051 / 1,236 | 6 | 1,483 |
| Decision (S) | 6 | 740 / 914 | 2 | 1,317 |
| Feature (S) | 5 | 683 / 1,328 | 4 | 1,721 |
| Glossary (S) | 3 | 712 / 1,328 | 1 | 1,109 |
| Procedure (H) | 17 | 1,248 / 1,477 | 12 | 3,221 |
| Standard (H) | 5 | 3,337 / 5,126 | 7 | 1,066 |
| Reference (H) | 7 | 1,163 / 1,629 | 1 | 779 |
| Schema (H) | 2 | 1,581 / 1,739 | 3 | 863 |
| Glossary, Register, Directory, Decision (H) | 1 to 3 | 1,139 to 1,416 | 1 each | 650 to 1,818 |

No type needs more than 3,221 framed characters in one goal, and none has more than 2 items in one
goal. Types with no expected item (Note, Report, FAQ, Plan, Drawing, Proposal) have no evidence for
any budget.

## Proposal

Budgets are in packet characters (the unit `start` counts). Tokens are **(est.)** at 4 characters
per token, a common rule of thumb for English prose, not measured here; JSON framing and markdown
could move it between about 3 and 4.

| Budget | Proposed | Basis | Tokens (est.) |
|---|---|---|---|
| Sources per goal, `--max-chars` default | **12,000** | All 34 expected sets fit 6,000 even taken whole. 12,000 is 2.1x the largest whole-file set (5,703) and 2.5x the largest as-written set (4,754), **(judgment)** as headroom for near-neighbors. It holds about 7 to 9 median whole files, against sets of median 1 to 2 and maximum 3. | ~3,000 |
| Per-source cap | **2,000 raw characters**, for whole files and sections alike | 1.3x the largest file an expected set takes whole (1,530); no expected set takes a larger file whole. Files above it are offered only by sub-section: 0 files synthetic, 4 held-out. **(judgment)** on the 1.3x. | ~500 |
| Section cap | none separate | Sections over 1,500 characters are title sections that equal the file, so the per-source cap covers them. | |
| Per-type budget | **none in v1** | Sizes for one type differ between bases, and no type has more than 2 items or 3,221 characters in a goal. A table keyed on free-form type names would fit these two bases and nothing else. | |
| Controls | not charged to navigate; reported separately | Measured 1,210 and 2,873 raw (5,373 and 3,576 packet overhead); the documented bound is 2,500. | ~1,300 to 1,800 for 5,373 |
| Ceiling for `--max-chars` | note above **26,000** | 32,000 minus the largest measured overhead (5,373) is 26,627; above that a packet may not fit `start`'s default. | ~6,500 |
| Non-knowledge artifacts | not navigated, no budget | Navigate selects concepts; nothing here measures other files. | |

If the budget is counted in raw source characters as the design doc first wrote it, add about 400
per source: 12,000 raw characters over 8 sources frames to about 15,200, plus the overhead, still
under 32,000 but no longer the number the user reads.

## Limits

- Two small synthetic knowledge bases, each written by one author. Expected sets are judgment
  calls and say what a careful person would select, not what is enough.
- Nothing here measures answer quality or real savings.
- The headroom factors (2.1x to 2.5x, 1.3x) are choices, not measurements.
- Characters per token is an estimate and was not measured.
