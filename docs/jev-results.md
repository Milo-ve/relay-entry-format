# Jev: first live shadow run

Run on 2026-11-12 with `python examples/jev_shadow_report.py --live-synthetic`, model alias `jev-latest`, one machine, one run. Twelve requests went to the provider. All content was invented for the run; nothing came from a real project.

This is an integration check with a handful of cases. It shows that the requests are accepted, that the answers parse, and what the signals looked like once. It is not a benchmark and does not calibrate any threshold.

## Limits of this evidence

- **Small.** Eight routing cases, two results, two navigation candidates, two section pairs.
- **One author.** The expected labels were written by the same author as the cases, before the run.
- **One sample each.** Nothing was repeated, so variability is unknown.
- **Easy cases.** Each was built to have a clear answer. Ambiguous and adversarial cases were not included.
- **Shadow only.** No route was changed, so no cost, time or quality effect was measured.

## Routing

Every goal was written so the rules ended on the conservative default, which is the only case where the gate asks Jev. "auto would" is what `auto` mode would have done with the same judgment.

| Task     | Risk     | Expected            | Jev kind  | p    | Conflict | Source instructions | `auto` would              |
| -------- | -------- | ------------------- | --------- | ---- | -------- | ------------------- | ------------------------- |
| spelling | low      | transform           | transform | 0.97 | 0.03     | 0.18                | Standard to Direct        |
| table    | low      | transform           | transform | 0.99 | 0.04     | 0.50                | Standard to Direct        |
| faq      | standard | draft               | draft     | 1.00 | 0.03     | 0.15                | keep                      |
| summary  | standard | draft               | draft     | 0.91 | 0.04     | 0.15                | keep                      |
| invoice  | standard | diagnose            | diagnose  | 1.00 | 0.13     | 0.07                | Standard to Investigative |
| plans    | standard | design              | design    | 0.99 | 0.04     | 0.07                | Standard to Investigative |
| price    | standard | draft, conflict     | draft     | 0.53 | 0.98     | 0.03                | Standard to Investigative |
| note     | standard | draft, instructions | draft     | 1.00 | 0.97     | 0.99                | Standard to Investigative |

- The kind of work matched the expected label in 8 of 8 cases.
- The two planted signals were found: conflicting prices (0.98) and a note addressing instructions to the assistant (0.99). The note also scored 0.97 for conflict, which is fair: it contradicts the pricing page.
- **Watch item:** `table` scored 0.50 for source instructions on a source that contains none. It is under the 0.7 flag threshold, so nothing was flagged, but it is the one value in this run that sits in the uncertain middle.

## Result signals at submit

| Task    | Result                                                    | Unsupported claim | Criteria met | Flags                                |
| ------- | --------------------------------------------------------- | ----------------- | ------------ | ------------------------------------ |
| faq     | Correct price plus an invented lifetime guarantee         | 0.99              | 0.99, 0.01   | `unsupported-claim`, `criterion-unmet` |
| summary | Three bullets that restate the page                       | 0.04              | 0.97         | none                                 |

The `faq` result was written to state the price (criterion one) and omit the annual offer (criterion two).

## Navigate relevance

Goal: "How long should the kiln soak at peak, and how fast should it ramp, in the studio?" The request used 597 input tokens.

| Candidate       | Lexical score | Jev relevance |
| --------------- | ------------- | ------------- |
| kiln-firing.md  | 35            | 0.98          |
| kiln-loading.md | 29            | 0.04          |

The lexical scores are close because both notes share "kiln" and the tag. Jev separated the note that answers the goal from the one that does not.

## Tidy same-content judgments

No pair shared 80% of its words, so nothing was reported without Jev. Two pairs fell in the 50% to 80% band and were sent in one request.

| Pair                                        | Word overlap | Same content |
| ------------------------------------------- | ------------ | ------------ |
| Same refund policy, reworded                | 0.67         | 0.98         |
| Same wording, different terms (5 days and original method, against 30 days and store credit) | 0.65 | 0.01 |

Word overlap could not tell these two apart. This is the case the `dedupe` use exists for.

## What this does and does not support

- **Supported:** the integration works end to end against the live endpoint for all five uses.
- **Not supported:** that `auto` is safe to enable, that any threshold is right, or that Jev saves cost or time. Those need shadow records from real tasks. `python examples/jev_shadow_report.py --root PROJECT` tabulates them without sending anything.
