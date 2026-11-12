# Jev in Relay

Jev is TypeSafe's [System One](https://docs.typesafe.ai/api/system-one) model: it returns a typed answer with a probability in a fraction of a second and does not generate text. Relay uses it for small judgments that rules cannot make and that are too cheap to deserve a reasoning model. It is optional and off by default. The rules work without it.

## Turning it on

- **For one task:** `relay start ... --jev shadow` or `--jev route`. This always consults Jev for that task.
- **For a workspace:** set `jev_mode` in `.context/relay/settings.json`. Relay then decides, per command, whether a call is worth making.

```json
{ "jev_mode": "shadow", "jev_uses": ["route", "source-scan"], "jev_max_calls": 5 }
```

| `jev_mode` | Effect                                                                    |
| ---------- | ------------------------------------------------------------------------- |
| `off`      | Never called. The default.                                                |
| `shadow`   | Called where useful; the judgment is recorded and changes nothing.        |
| `auto`     | Called where useful; the judgment acts, within the limits on this page.   |

`--jev` on a command overrides the setting in both directions, so `--jev off` keeps one task local. The key is read from `TYPESAFE_API_KEY` in the environment and is never stored.

## When it runs and when it does not

Relay asks Jev only when all of these hold. Otherwise it records a skip with the reason.

| Reason recorded     | Meaning                                                                          |
| ------------------- | -------------------------------------------------------------------------------- |
| `not-enabled`       | `jev_mode` is `off`, or the command said `--jev off`. Nothing is recorded.       |
| `use-not-enabled`   | This use is not listed in `jev_uses`.                                            |
| `rules-decisive`    | The rules already settled the question, so a call would buy nothing.             |
| `nothing-shareable` | There is no content to judge.                                                    |
| `no-key`            | `TYPESAFE_API_KEY` is not set.                                                   |
| `budget-exhausted`  | The command already made `jev_max_calls` requests.                               |
| `call`              | Jev was asked. If the provider fails, the status is `unavailable` and rules stay. |

## Uses

| Use           | Where                  | Question                                                           | What it can change                                                                                              |
| ------------- | ---------------------- | ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| `route`       | `relay start`          | What kind of work is this, and do the sources conflict?            | `auto`: raises to Investigative on a design, diagnosis or conflict signal. May lower to Direct, see below.     |
| `source-scan` | same request as `route` | Does a source address instructions to an assistant?                | Adds the flag `source-instructions` under `route.jev.flags`. A warning only; it also blocks the lowering below. |

**Routing is skipped** when a blocker, high consequences, a stated `--kind` or a keyword already decided the route. A refresh returns to the rules and does not ask again.

**Lowering effort.** In `auto` only, a task started with `--risk low` and no stated kind may go from Standard to Direct when Jev says "bounded transformation" with probability 0.8 or more, conflict 0.3 or less, and no source flag. The operator's low-risk declaration is the precondition, and review stays required. The per-command `--jev route` never lowers.

**Choosing a model.** A route carries `settings.reasoning` (low, medium or high). Relay cannot make an assistant use a given model; the workspace's own instructions can map low or medium to a small or standard model and high to a frontier one.

## What is sent

The task goal and the selected non-control sources, to TypeSafe's endpoint. Control files are never sent. `deny_paths` applies before anything is read, so set it before choosing `shadow` or `auto`: with the setting on, no flag marks the commands that send content.

Requests time out after five seconds, are not retried, reject redirects and bound the response size. Relay validates every probability it uses and records `usage` as reported.

## What it can never do

- Grant permission, accept or reject work, or record a review.
- Clear a blocker or a missing prerequisite.
- Skip or weaken required review.
- Change a file, select a source, or run a command.

## Where not to use it

Relay has no inbox to triage, no latency-sensitive loop and no tool execution to gate, so those uses do not exist here. Do not use a Jev signal as proof that a result is correct or complete: a typed answer guarantees its shape, not its truth.

## Evidence

Offline tests cover the gate, the limits above and provider failures with mocked responses. They say nothing about Jev's quality on your tasks. The thresholds (0.7 to raise or flag, 0.8 and 0.3 to lower) are starting heuristics from the provider's guidance, not calibrated error bounds. Run `shadow` on real work before choosing `auto`. The original design rationale is in [the archive](archive/relay-adaptive-effort-and-jev.md).
