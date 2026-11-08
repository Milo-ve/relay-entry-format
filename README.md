# Relay Method

**Open the task. Understand its boundaries. Continue with your preferred assistant. Return reviewable work.**

Use the least total effort that satisfies the task’s requirements, and increase effort when evidence shows it is needed.

Relay Method combines portable knowledge inspired by [OKF](https://github.com/GoogleCloudPlatform/open-knowledge-format), staged work inspired by [ICM](https://github.com/RinDig/Interpretable-Context-Methodology), and a lightweight task-to-review flow. It works offline with your existing assistant. Jev judgments are optional.

**Status: local prototype 0.3.0.** The CLI and loopback browser interface implement task creation, adaptive effort recommendations, selected context export, evidence submission, version-specific local review, freshness checks, and bounded escalation. Organizational authentication, managed model execution, compute enforcement, and cross-run dependency graphs remain future work. Savings and live Jev performance have not been established.

## Install

Requires Python 3.11+.

```sh
git clone https://github.com/milo-ve/relay-okf-icm.git
cd relay-okf-icm
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows use `python -m venv .venv` and `.venv\Scripts\Activate.ps1` in PowerShell. Installation uses PyYAML; no model API is required for the default workflow.

## Try the local application

Create a new synthetic project; use a destination that does not exist:

```sh
python examples/relay_demo.py ./relay-demo
relay --root ./relay-demo serve
```

Open **http://127.0.0.1:8765**. Select the sample FAQ task, download its context for your preferred assistant, paste the result and actual evidence, and record a review. You can also open a new task from the home page.

For a real project:

```sh
relay init ./my-project --name "My project"
relay --root ./my-project serve
```

If the project already has `.context/`, initialization refuses to overwrite it. Use `relay --root ./existing-project serve` to work with a compatible existing workspace. Read and deliberately configure `.context/policy.md` and `.context/project.md` before delegating real work. Relay does not discover business authority automatically.

## Use the CLI

From an initialized project, with the CLI on PATH:

```sh
relay start faq --goal "Draft a source-backed pricing FAQ" \
  --accept "Each commercial statement cites the current policy" \
  --select inputs/pricing-current.md --kind draft \
  --owner collaborator --reviewer milo
relay context faq --out faq-context.md
```

Work in your assistant and save separate deliverable and evidence files. Then:

```sh
relay submit faq --output faq.md --evidence observed-checks.md \
  --checks "Compared each commercial answer with the policy" \
  --questions "Cancellation terms remain unspecified" \
  --next "Milo reviews the draft against the acceptance criteria"
relay show faq
```

Use the actual `submission_id` from that output:

```sh
relay review faq --submission ACTUAL_SUBMISSION_ID --decision accept \
  --actor milo --note "Reviewed this version against the designated source"
```

The named actor is a local, self-recorded assertion, not authenticated identity. The files and checks must exist; the CLI does not decide that their claims are true.

## Proportional effort

| Profile | Rule | Expected work |
|---|---|---|
| Direct | Explicit transformation + low consequences | Work and a relevant check. |
| Standard | Conservative default | Plan, work, check, handoff where needed. |
| Investigative | Diagnosis, design, conflict signal, or high consequences | Investigation and stronger validation. |
| Clarify | An explicit missing prerequisite | Resolve what is missing before continuing. |

Profiles recommend reasoning and process to the participant's assistant. They do not control an external model's internal compute. Explicit inputs and conservative request-text rules are heuristics; automated classification has limitations. A short consequential task still gets strict attention.

```sh
relay start heading --goal "Fix the heading spelling" --accept "Spelling corrected" \
  --kind transform --risk low --select draft.md
relay escalate heading --note "The change revealed conflicting terminology"
```

One escalation is permitted per task; it moves to Investigative. Further effort requires reassessing the scope. Source refresh preserves an already recorded escalation.

## When inputs change

```sh
relay show faq
relay refresh faq --note "The designated policy changed; reassess affected answers"
relay context faq --out faq-context-v2.md
```

Freshness covers selected inputs, controls, submitted outputs, and evidence. Changes make acceptance due for review. Refresh creates a new input snapshot and clears the current submission/review; frozen packets, submission receipts, and review events remain. Rework and resubmit against the new snapshot. Refresh does not mean the changed facts were semantically validated.

Task outputs must be separate from selected inputs and control files. This first release supports proposal handoffs; integrating edits into canonical sources is a separate action. The browser writes versioned files under `deliverables/`.

## Optional Jev

Relay calls the official [TypeSafe System One endpoint](https://docs.typesafe.ai/api/system-one) only when explicitly requested. It reads `TYPESAFE_API_KEY` from the process environment. Do not put the key into project files or Git.

```sh
relay start assessment --goal "Investigate conflicting product claims" \
  --accept "Resolve conflicts with evidence" --select sources.md --jev shadow
```

`shadow` records judgments without affecting the route. `--jev route` can raise effort; it cannot lower a rule-selected profile or bypass blockers or review. The goal and selected non-control source contents are sent to TypeSafe, so select only information authorized for that provider. Missing credentials, timeouts, malformed responses, and provider errors retain the rules-only route and are visible in the record. No requests are retried automatically. Refresh does not reuse old Jev signals.

The initial semantic threshold is a policy starting point, not a calibrated error bound. The adapter has offline mocked-response coverage; a live provider evaluation requires your own approved credentials and test cases. See [adaptive effort and Jev](docs/relay-adaptive-effort-and-jev.md).

## Storage and boundaries

```text
.context/
  policy.md / project.md       Project control and authority
  knowledge/                  Portable concepts
  runs/                       Existing six-stage CLI runs
  relay/tasks/<id>/
    state.json                Current task, route and review events
    packets/<sha256>.json     Frozen input snapshots
    submissions/<sha256>.json Result/evidence receipts
deliverables/                 Browser-submitted result/evidence versions
```

The `okf-icm` command remains available for the existing detailed stage workflow. Relay tasks share its path readers, hashing, section selection, knowledge validation, and cooperative lock. They do not silently complete legacy stages or rewrite the project graph. See [the task-layer protocol](docs/RELAY.md) and [original protocol](docs/PROTOCOL.md).

The browser binds only to loopback, checks Host/Origin, uses CSRF tokens, escapes rendered content, and uses version checks for mutations. It serves no arbitrary files or shell commands. This is a trusted-user local tool, not an enterprise authorization boundary. Do not expose it through a public tunnel or shared server. A repository clone cannot hide confidential subfolders from its reader.

Exports are explicit; common secret paths are refused, but this is not a secret scanner. Inspect content before sending it to a person or model provider.

## Development and verification

```sh
python -m unittest discover -s tests -v
python examples/smoke.py
python examples/relay_smoke.py
```

CI runs the suite and smoke examples on Linux, macOS, and Windows. Live model quality and customer savings are separate evaluations.

## Design documents

- [Product proposition and strategy](docs/relay-product-proposal.md)
- [Adaptive effort and Jev](docs/relay-adaptive-effort-and-jev.md)
- [Operational backcast](docs/relay-operational-backcast.md)
- [First collaborator experiment](docs/relay-first-work-brief.md)

The strategy documents retain their proposal history; current implemented behavior is described here and in [RELAY.md](docs/RELAY.md). Generate the synthetic example before following local `.context/` links; private execution history and machine-specific packets are not distributed with the repository.

Independent implementation. See [attribution](ATTRIBUTION.md) and [MIT license](LICENSE). Naming does not imply endorsement by OKF, ICM, or TypeSafe.
