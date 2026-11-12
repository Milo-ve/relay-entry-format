# Adaptive effort in OKF + ICM, and where Jev fits

**Date:** November 7, 2026, America/Mexico_City.

**Status:** Architecture proposal and literature investigation. No model routing, Jev integration, or live benchmark was implemented or executed.

**Implementation update (0.3.0):** the local task layer now implements effort recommendations, optional Jev shadow/raise-only routing, context export, result/evidence submission, and version-specific local review. The original proposal below records the design; use [the executable protocol](../RELAY.md) and [README](../../README.md) for current behavior. Worker execution, compute enforcement, and live Jev benchmarking remain unimplemented or unperformed.

## 1. The clarified design intent

**User experience:**

> **Open the task. Understand its boundaries. Continue with your preferred assistant. Return reviewable work.**

**Operating principle:**

> Use the least total effort that satisfies the task’s requirements, and increase effort when evidence shows it is needed.

The structure should allocate effort in proportion to a task's demands. Small, well-understood work should use little context, reasoning, ceremony, and coordination. Broad, uncertain work should receive investigation, planning, appropriate computation, and stronger checks.

This refines the [Relay proposal](relay-product-proposal.md): adaptive effort is part of the operating design, while a work brief is the user-facing way to expose the task and its boundaries.

For the sequence from current artifacts to daily team operation, see the [operational backcast](relay-operational-backcast.md).

Total effort includes context gathering, computation, retries, coordination, and human review. Task requirements include quality and operating constraints. Minimizing the first model call can increase total work through retries and review. Always using maximum effort can waste resources on routine work.

This is a proposed behavior of the combined application. OKF stores structured knowledge and provenance; the local ICM-inspired workflow supplies contracts and execution records. Neither format, by itself, chooses compute or guarantees speed. A controller and a compatible execution runtime must implement that choice.

## 2. Separate the responsibilities

| Layer | Responsibility |
|---|---|
| OKF knowledge | Reusable sources, decisions, procedures, provenance, and lifecycle signals. |
| Context selection | Fetch the permitted, relevant information needed for this task or decision. |
| Effort controller | Select a permitted execution profile using explicit facts, narrow model judgments where useful, and measured policy. |
| ICM-inspired execution | Apply relevant contracts, carry work through dependencies, record actual outputs, and preserve continuity. |
| Model/tool runtime | Perform generation, reasoning, retrieval, or deterministic operations under the chosen limits. |
| Verification and review | Check observable requirements and obtain any required human acceptance. |

Jev is a candidate component in the controller or a narrow semantic-checking step. Keep the controller replaceable and the core provider-independent.

## 3. Effort has several dimensions

Do not reduce effort to one model name or token limit:

| Dimension | Small end | Larger end |
|---|---|---|
| Context | One relevant source or section | Several sources and necessary dependencies |
| Reasoning | Direct transformation | Planning, reconciliation, diagnosis, or exploration |
| Tools | None or one deterministic operation | Research, execution, and appropriate tests |
| Workflow | Short task/result record | Explicit intermediate decisions and checkpoints |
| Verification | Targeted observable check | Multiple relevant checks and independent review where justified |
| Coordination | One worker | Bounded independent contributions plus integration |

These dimensions need not rise together. A one-line change to a commercial term can require little generation and strict review. A long mechanical conversion can require substantial output but little reasoning. Missing authorization or an absent commercial decision requires resolution, not more tokens.

## 4. Three execution profiles, with an explicit pause outcome

| Profile | Conditions | Proposed behavior |
|---|---|---|
| Direct | Clear, reversible, bounded transformation with sufficient current evidence. | Minimal context, deterministic tool when possible or a short model call, relevant check, concise result. |
| Standard | Several related steps with clear scope and ordinary uncertainty. | Brief plan, selected sources, appropriate model, output validation, and handoff when work crosses a boundary. |
| Investigative | Substantial ambiguity, conflicting evidence, significant dependencies, or complex diagnosis. | Establish sources, investigate, plan, execute with checkpoints, and apply stronger validation. Consider parallel work only for independent contributions. |
| Clarify or pause | Missing prerequisite, authorization, critical evidence, or approved budget. | Identify what is missing and request resolution. Continue independent permitted work when possible. |

These are proposed application profiles, not existing CLI modes. Human-review requirements and permission boundaries apply across profiles. Task length alone must not determine the route.

## 5. The smallest useful control loop

```text
Task + relevant current state
            |
            v
Deterministic permission, freshness, requirement, and budget checks
            |
            v
Obvious permitted route? -------- yes --------> Execute selected profile
            |                                          |
            no                                         v
            |                                  Check actual result
            v                                          |
Narrow judgment, optionally Jev                         v
            |                                Done / revise / escalate / pause
            v
Code applies policy and selects an allowed profile
```

Use rules for what code can establish: permitted paths, configured budget, changed hashes, required approvals, missing files, and failed schema checks. Optional semantic judgments help where rules are awkward, such as distinguishing a straightforward rewrite from a request requiring synthesis across contradictory statements.

Start routing at task entry. Reassess at meaningful events: conflicting evidence, failed validation, an unanticipated dependency, or a scope change. Avoid a controller call before every trivial operation.

A proposed escalation policy allows one profile escalation per subtask before reassessing the plan or asking for the missing input. It includes a task-wide cost/time ceiling and cancellation. Exhausting the ceiling produces a visible pause, not a success claim. Exact limits depend on observed work and user preferences.

## 6. What the research establishes about Jev

### Official product fit

TypeSafe describes Jev as a decision model: state and typed questions go in; structured answers come out. Choice selects among supplied options, Score uses an ordered rubric, and Noul estimates whether a statement is true. TypeSafe recommends atomic questions with their results combined in application code. This makes Jev a plausible source of bounded routing signals. See [TypeSafe's introduction](https://docs.typesafe.ai/introduction).

The vendor explicitly distinguishes Jev from the generative model powering a coding assistant. Jev does not replace the worker that writes code or carries a conversation. See [Jev with coding agents](https://docs.typesafe.ai/introduction/coding-agents).

TypeSafe also publishes a [cascade recipe](https://docs.typesafe.ai/cookbooks/sde_cascade): a small model produces structured output, narrow Jev checks flag possible violations, and a stronger model handles flagged cases. That is an implementation example, not evidence that every Relay task benefits from such a cascade. Prefer exact code checks when requirements can be checked deterministically.

### Important probability distinction

The vendor's [confidence documentation](https://docs.typesafe.ai/confidence) distinguishes its confidence summary from a selected option's probability. In a fixed Choice schema, these are related summaries of the same distribution, not independent confirmations. A routing probability also does not measure the chance that the eventual worker will complete the task correctly.

Set thresholds on local held-out outcomes and inspect failures, especially underestimated effort. Do not interpret a generic confidence cutoff as a validated error bound for business work.

### Independent evidence and its limits

Two recent research preprints materially qualify the proposal:

- [Good Judgment, Bad Advice](https://arxiv.org/abs/2610.24649) reports that a Jev 1.13 controller increased cost per attempt by 19% at the same 73% pass rate in a terminal-agent experiment with 21 held-out tasks and 315 trials. Its narrow setup does not settle other use cases; it shows that informative decisions can still cause unhelpful extra verification.
- [What Can't Jev Decide?](https://arxiv.org/abs/2610.24929) reports weaknesses on reasoning-dependent decisions and stale state. In those experiments, confidence did not reliably expose errors inherited from stale summaries. This supports checking the underlying state rather than relying on the router's confidence.

These papers were read as published research reports, not reproduced locally. They concern particular models and experiments; do not generalize their results to every version or workflow.

## 7. How Jev would participate in this project

Use a few bounded judgments against relevant current state, for example:

- Does the requested outcome require reconciling conflicting claims in the supplied sources?
- Is the request an explicitly specified transformation, a diagnosis, or open-ended design?
- Does the returned answer introduce a commercial promise absent from the supplied authoritative source?

The last check is only a signal for review. It does not certify absence of unsupported claims. A broad “is the whole answer correct?” question is a poor substitute for task-specific evidence.

Keep these decisions in deterministic policy:

- Which files and tools are accessible.
- Which source is designated authoritative.
- Whether recorded bytes changed.
- Whether required human approval exists for the exact version.
- Maximum spend, retry count, deadline, and permitted escalation.

Jev may identify ambiguity or suggest a route. Its output cannot grant authority, waive policy, authorize publication, or promote proposed knowledge into approved policy.

## 8. Compact routing record

An illustrative application record, not a current CLI or Jev API schema:

```json
{
  "task_id": "faq-draft",
  "policy_version": "effort-policy-v1",
  "input_snapshot": "actual-packet-id-if-generated",
  "selected_profile": "standard",
  "decision_source": "rules-and-optional-model-signals",
  "reason_codes": ["bounded-draft", "current-source-available"],
  "review_required": true,
  "escalations_remaining": 1
}
```

Keep model version, question-schema version, measured signals, allowed actions, and observed resource use in the detailed record when available. Reason codes describe the policy branch; do not invent a natural-language rationale and attribute it to a model that returned only typed answers.

Reuse a routing decision only while its relevant task, source snapshot, policy, schema, and runtime assumptions remain valid. Any cache is an optimization; it does not replace source freshness checks. Routing state sent to an external service must be permitted for that service and audience.

## 9. What this means for the current CLI

The [CLI reference](../CLI.md) and implementation support `run skip --reason`. The [protocol](../PROTOCOL.md) also supports an editable dependency graph, with explicit migration required when an existing run's stage set changes.

Therefore the six-stage example need not imply that every task must perform six stages of substantive work. An operator can explicitly skip an unnecessary stage with a real reason, subject to the task contract. Skipping validation that policy requires is not a valid optimization.

However, skip bookkeeping still incurs work, and changing a model's effort is a different operation from skipping a stage. Current limitations remain: no automatic profile selector, compute allocation, model invocation, native per-run profile creation, or Jev controller. An adapter must supply them. A future profile mechanism should be selected and versioned at run creation rather than silently rewriting an in-progress graph.

For trivial tasks, the proposed application can use a compact task/result record without initializing the full workflow, provided project policy permits it. A result reused downstream should retain enough provenance to become a tracked dependency. This lightweight record is proposed functionality, not something the current CLI already implements.

## 10. A pilot that answers whether Jev earns its place

Start with simple rules and a conservative default. Then compare four configurations on representative tasks:

1. A fixed capable worker with the same required checks.
2. Rules-only routing with permitted profiles.
3. Rules plus Jev routing signals.
4. A small generative model answering equivalent routing questions, if a model baseline is warranted.

Include easy, ambiguous, stale-source, multi-step, and short-but-high-consequence examples. Split development cases from held-out cases. Repeat enough cases to observe variability; use the first sample diagnostically rather than as a statistical guarantee.

Start Jev in **shadow mode**: record its recommendation without letting it change execution. This tests agreement and highlights mistakes, but cannot prove cost savings. To estimate actual savings, run controlled executions under the alternative routes, including downstream validation, rework, and reviewer effort.

Measure quality and serious misses, total task cost, wall-clock time, context volume, escalation frequency, false escalations, human overhead, and cost per accepted result. Keep identities, tools, policies, and quality rubrics comparable.

For a simple small-worker-first cascade, its average compute cost is approximately:

```text
C_small + C_router + C_checks + escalation_rate * C_strong
```

That must improve on a relevant fixed-worker baseline at the required quality. Direct-to-strong routing has a different cost shape; include every call actually made. Human review and expected rework belong in the overall decision even when absent from the compute equation.

Adopt Jev only if it improves the quality/cost/latency tradeoff over the rules-only baseline for the target tasks. Retain a deterministic fallback for unavailability. If the needed route is uncertain, code should select a bounded stronger assessment or request clarification according to policy; it should not quietly assume the cheapest path is adequate.

## 11. First development slice

Implement a provider-neutral profile selector, a compact route record, and visible escalation reasons. Begin with rules. Connect only to worker controls that the runtime actually exposes; a copied prompt cannot guarantee a compute ceiling in another assistant's subscription.

Add optional Jev judgments after collecting representative cases, initially in shadow mode. Add further agents only when their independent contribution beats the extra coordination and review cost.

The central product promise becomes: **the work gets the effort it needs, and the record explains what was done and why it was escalated.** Savings and accuracy remain empirical questions.
