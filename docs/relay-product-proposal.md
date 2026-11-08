# Relay: shared work that survives handoffs

**Working name:** Relay. Branding and trademark availability have not been checked.

**Date:** November 7, 2026, America/Mexico_City.

**Status:** Product proposal and test plan. This is not an approved roadmap, an implemented application, or evidence of product-market fit.

**Implementation update (0.3.0):** a local CLI and browser prototype now implement the task-to-review loop and effort recommendations, with optional Jev judgments. This proposal retains its planning history. See [README](../README.md) and [the task protocol](RELAY.md) for current features and limitations. Organizational access, managed worker execution, and measured savings remain future work.

## 1. The recommendation

**User experience:**

> **Open the task. Understand its boundaries. Continue with your preferred assistant. Return reviewable work.**

**Operating principle:**

> Use the least total effort that satisfies the task’s requirements, and increase effort when evidence shows it is needed.

Build a small front door to shared work on top of OKF + ICM. Start with one useful action: **hand a bounded task to another person or assistant and get back a result that someone can review without reconstructing the conversation.**

The product's core object is a **work brief**: the outcome, relevant sources, responsibilities, boundaries, acceptance criteria, and current next step. A brief links to the actual work; it does not duplicate every source or turn an entire company into a prompt.

The experience has four steps:

1. **Open the task.** Find the outcome and current next action in the work brief.
2. **Understand its boundaries.** Identify authoritative sources, responsibilities, permissions, and acceptance criteria.
3. **Continue with your preferred assistant.** Use the selected context and an appropriate level of effort.
4. **Return reviewable work.** Submit the deliverable, actual checks, uncertainties, and next action.

When a recorded dependency changes, the result displays **Review needed** with a reason. That label means the basis changed; it does not mean the result is wrong.

**Positioning hypothesis:** For small teams that repeatedly explain the same project to collaborators and AI tools, Relay makes ongoing work easier to pick up, check, and maintain across people, sessions, and providers.

The broad company workspace remains a possible destination. The entry point is a recurring handoff that can be improved and measured now.

Apply the operating principle across context, reasoning, workflow, and verification. Routine work should take a short path; uncertainty and consequential changes should trigger appropriate investigation or review. The controller, execution profiles, and optional role of Jev are specified in [Adaptive effort and Jev](relay-adaptive-effort-and-jev.md). These mechanisms are proposed, not implemented by the current CLI.

The [operational backcast](relay-operational-backcast.md) works backward from dependable daily use to the capability gates, operating responsibilities, and first seven working days needed to get there.

## 2. What problem is worth solving?

### The problem expressed by the founder

Milo wants an organization context that collaborators can navigate, edit according to responsibility, and use with different agents. Installation should be straightforward and collaboration should not require rebuilding context each time.

That conversation is direct input from one prospective user. It is not a representative market study. No collaborator interviews or live usability sessions have been conducted for this proposal.

### The working problem statement

> When work crosses a person, session, or tool boundary, the receiver struggles to determine what is current, what is allowed, what has already been established, and what to do next.

Our hypothesis is that repeated explanation, stale assumptions, and unclear review responsibility are more urgent initial problems than acquiring additional model capacity. The pilot must test that priority.

### Jobs to be done

| Person | Situation | Desired progress |
|---|---|---|
| Founder or project lead | A collaborator joins an active task. | Delegate useful work without writing a long private explanation. |
| Collaborator | Receives a project with unfamiliar files. | Find the relevant sources, boundaries, and next action. |
| Reviewer | Receives an AI-assisted deliverable. | Understand its basis, inspect the changes, and decide whether to accept it. |
| Returning contributor | Comes back after a gap or switches assistants. | Continue from current evidence rather than repeat the diagnosis. |

The first customer hypothesis is an owner-led team of roughly 2–10 people doing product, agency, consulting, or internal operations work. This is a targeting choice, not measured demand. The earliest users should be comfortable sharing a project folder or repository and already experience recurring handoffs.

## 3. Applying Blue Ocean Strategy

We apply the [Four Actions Framework](https://www.blueoceanstrategy.com/tools/four-actions-framework/) to change the basis of the offering. An ERRC exercise does not establish an uncontested market; it produces a proposition to test.

### Eliminate, reduce, raise, create

| Action | Product decision | Expected effect to test |
|---|---|---|
| Eliminate | No mandatory new chat interface or automatic whole-company ingestion in the first release. | Lower migration, setup, and disclosure burden. |
| Eliminate | No autonomous agent swarm or subscription pooling in the first release. | Keep the first build small and its operating behavior understandable. |
| Reduce | Hide workflow administration behind a task-oriented view; prefill reports from actual artifacts where possible. | Less methodology training and clerical work. |
| Reduce | Limit each pilot task to one accountable owner, one reviewer, and explicit sources. | Fewer coordination conflicts. |
| Raise | Make source authority, next action, review responsibility, and dependency changes visible. | Faster and more accurate continuation. |
| Raise | Make an export inspectable and useful without Relay. | Lower switching risk and support existing assistants. |
| Create | A short handoff-to-review loop with an input snapshot, result, and specific reasons for re-review. | Make continuity a repeatable product behavior. |

“Create” describes the proposed offering. It is not a claim that these mechanisms are new inventions.

### Noncustomers to investigate

Using the [three tiers of noncustomers](https://www.blueoceanstrategy.com/tools/three-tiers-of-noncustomers/) as a discovery lens:

- **Near adopters:** small teams using AI but still forwarding chat excerpts and rewriting explanations.
- **Reluctant adopters:** teams that tried agent platforms and stopped because setup or supervision outweighed the benefit.
- **Overlooked users:** non-engineering collaborators who can edit a brief but will not operate a developer workflow.

Interview the first two groups first. A plain-language brief may attract the third group, but a terminal-based pilot does not yet serve them adequately.

### Proposed value profile

These are design priorities, not scored competitor benchmarks:

| Dimension | Relay's initial target |
|---|---|
| Time to a useful first task | Low, using an existing project and assistant. |
| Company-wide search breadth | Deliberately limited. |
| Workflow configuration | Minimal for the participant. |
| Source and result traceability | Explicit and inspectable. |
| Change awareness | Deterministic for declared dependencies. |
| Autonomous execution | Absent in the first release. |
| Portability | Plain-text artifacts and exportable state. |

### Competitive honesty

The adjacent market is substantial:

- [Open WebUI](https://docs.openwebui.com/getting-started/sharing/) already documents a shared instance, browser access, groups, models, and knowledge access.
- [GitHub Spec Kit](https://github.github.com/spec-kit/) already offers structured agent processes, evidence-oriented work, and customization beyond a single fixed workflow.
- [OpenSpec](https://github.com/Fission-AI/OpenSpec) organizes specification-driven changes around proposals, specifications, designs, and tasks.
- [LiteLLM](https://docs.litellm.ai/docs/proxy/users) already provides shared team budgets and individual or agent limits for model consumption.

Therefore “Markdown + stages + agents” is an insufficient differentiation claim. Relay earns a place only if its complete handoff experience is simpler and more useful for the chosen users than a good shared document or an existing workflow tool. If a configured existing tool produces the same benefit with less work, adopt it or build a narrow adapter.

## 4. Applying systems thinking

The system boundary is one shared project, its contributors, their assistants, selected sources, deliverables, and reviews. The first release does not attempt to model an entire enterprise.

### Stocks, flows, and delays

| System element | Interpretation |
|---|---|
| Stock: usable shared understanding | Current decisions and source relationships that a receiver can recover. |
| Stock: review backlog | Results awaiting meaningful acceptance or re-review. |
| Stock: stale assumptions | Previously useful claims whose basis changed or is unknown. |
| Inflows | New tasks, source changes, proposals, and results. |
| Outflows | Accepted work, resolved uncertainties, and retired knowledge. |
| Delays | Time between a source change and discovery; between submission and review. |

The failure mechanism hypothesized here is a reinforcing loop:

```text
More switching and delegation
  -> more context reconstruction
  -> less time to preserve evidence
  -> more ambiguity for the next receiver
  -> more context reconstruction
```

A second loop is a risk of AI adoption:

```text
More generated output
  -> more review work
  -> review delays and shallow checking
  -> more unresolved defects
  -> more rework and review work
```

Relay's proposed balancing loop is:

```text
Handoff exposes missing sources or acceptance criteria
  -> targeted clarification
  -> more bounded work
  -> easier review
  -> accepted result and reusable next step
```

These are causal hypotheses, not observed system measurements. Validate them by observing actual handoffs.

### The intervention

Following the emphasis on information flows and rules in [Meadows's leverage-points essay](https://donellameadows.org/archives/leverage-points-places-to-intervene-in-a-system/), intervene at the boundary where work changes hands: what information is available and what must be established before a result can be accepted.

The proposed rule is small: a returned result identifies its inputs, deliverable, checks, unresolved questions, and next step. Acceptance belongs to a named reviewer and a particular version.

### Unintended effects and countermeasures

| Risk | Countermeasure |
|---|---|
| Recording everything becomes bureaucracy. | One short brief, progressive disclosure, and a measured overhead limit. |
| A green status is mistaken for truth. | Label freshness, workflow completion, and human acceptance separately. |
| Every source edit creates review noise. | Initially use conservative hashes; explain exactly which recorded input changed. Measure false alarms before designing finer granularity. |
| Faster output overwhelms reviewers. | Limit active work per reviewer; optimize accepted outcomes, not agent activity. |
| Sensitive facts spread through summaries. | Treat exported and derived content as a new disclosure requiring an authorized audience. |

## 5. Applying design thinking

The [Stanford process](https://web.stanford.edu/class/me113/d_thinking.html) provides the sequence of empathy, definition, ideation, prototyping, and testing. The user conversation informs this proposal, but empathy research remains incomplete.

### Empathize: investigate behavior

Observe Milo and one collaborator doing an actual handoff. Ask them to show the last instance, including the files and messages used. Record where they searched, what they re-explained, and what they could not determine.

Use questions such as: “What did you need before you could start?” and “What made you trust this version?” Avoid asking whether they like an abstract AI operating system.

### Define

> How might we let a collaborator complete a small useful task with their existing assistant, while making its scope, authority, and review basis obvious?

### Ideate and choose

| Candidate | Immediate benefit | Complexity or weakness | Decision |
|---|---|---|---|
| Whole-company AI workspace | Broad access and navigation. | Identity, synchronization, connectors, and substantial overlap with existing platforms. | Defer. |
| Shared model-budget portal | Central cost control. | Existing infrastructure addresses much of it; weak connection to the current core. | Integrate later if needed. |
| Automated multi-agent dispatcher | More parallel execution. | Adds scheduling, sandboxing, retries, cost control, and review load. | Defer. |
| Shared briefing template | Useful immediately. | Manual freshness and limited repeatability. | Use as the baseline. |
| Work brief plus reproducible handoff and change-aware review | Uses the existing core and addresses continuation. | Must beat the briefing baseline in actual use. | Recommended experiment. |

### Prototype the smallest experience

Start with the companion [first work brief](relay-first-work-brief.md). It can be used today without a new app, model API, or shared account.

The software prototype then presents only three views: **My work**, **Work brief**, and **Review**. A project sidebar provides familiar navigation to permitted projects, sources, and decisions. Folder browsing supports a task; it is not the central promise.

Conceptual interface, not implemented software:

```text
Project: Pricing demo

MY WORK                        WORK BRIEF: Pricing FAQ
Pricing FAQ                    Outcome: a source-backed FAQ proposal
                               Owner: collaborator
READY FOR REVIEW               Reviewer: Milo
No submissions yet             Inputs: current policy + existing specification
                               Unknowns: payment, cancellation, trial, SLA
REVIEW NEEDED                  Next: draft supported answers
No recorded changes
                               [Prepare handoff] [Return result]
```

The return form has four fields: **Deliverable**, **What I checked**, **Open questions**, and **Next step**. Paths and evidence are shown in the review view; the UI must not hide a missing check behind a summary.

### Test before expanding

Watch a collaborator use the brief without a founder explanation. A useful outcome is a supported FAQ draft that the reviewer can assess. Producing more documentation is not itself a success measure.

## 6. Applying strategic foresight

Use an 18–36 month exploratory horizon. Following [OECD's treatment of foresight](https://www.oecd.org/en/about/programmes/strategic-foresight.html), these are plausible scenarios for stress-testing choices, not forecasts or assigned probabilities.

Two uncertainties matter: whether work concentrates in a few integrated suites or remains spread across tools, and whether teams delegate substantial execution or keep AI primarily advisory.

| Scenario | Implication | Robust response |
|---|---|---|
| Integrated suites + mostly advisory AI | Suites make document collaboration and memory easy. | Offer an adapter or method only if cross-tool handoffs still improve outcomes. Stop a redundant standalone UI. |
| Integrated suites + extensive delegation | Suites own execution; review and accountability remain important. | Attach briefs and version-specific result evidence to suite workflows. |
| Fragmented tools + mostly advisory AI | Manual context transfer persists. | Prioritize readable exports, small setup, and assistant independence. |
| Fragmented tools + extensive delegation | Transfers between systems become frequent. | Add interoperable task/result interfaces and narrowly delegated permissions after proving the human flow. |

### No-regret choices

Keep canonical artifacts exportable, make dependencies explicit, separate execution from acceptance, and avoid binding the core to one model provider. Preserve a useful manual mode so an integration outage does not erase the work.

### Signals and options

| Signal to monitor | Decision it informs |
|---|---|
| Teams can already resume across their preferred tools with negligible explanation. | Narrow, integrate, or stop the handoff product. |
| Users repeatedly request a browser flow because the operator step fails. | Prioritize the web adapter. |
| Stale-input mistakes recur despite existing tools. | Prioritize visible dependency impact and re-review. |
| More than one real pilot requires confidential subproject access. | Build authorization before adding broader navigation or exports. |
| Direct agent execution is repeatedly requested and paid for. | Consider a bounded runtime integration. |

## 7. What exists, what is proposed, and what is deliberately deferred

The [original stage protocol](PROTOCOL.md) describes the inherited CLI. The [Relay task protocol](RELAY.md) describes the local task layer added in 0.3.0.

| Capability | Current basis | Work needed |
|---|---|---|
| Explicit files/sections in context | Implemented CLI exports. | Friendly selection and preview. |
| Input/output/evidence hashes | Implemented checkpoints. | Plain-language display and attachment workflow. |
| Dependency freshness | Implemented within a run. | UI and, later, explicit cross-run dependencies. |
| Stage workflow and handoff | Existing `.context` files. | Brief editor and participant-oriented navigation. |
| Owner and reviewer assignments | Proposed metadata. | Schema, editing, and display. |
| Authenticated, version-specific acceptance | Not implemented by the CLI. | Use repository review in a trusted pilot; design an authenticated review layer for hosted use. |
| Multiple simultaneous writers | One cooperative CLI lock only. | Separate task runs and serialized integration initially. |
| Organization sign-in and confidential project access | Not implemented. | Identity integration and server-side authorization. |
| Agent execution and pooled budgets | Not implemented. | Optional external integrations after validation. |

The existing core should remain responsible for packets, checkpoints, and computed freshness. Avoid inventing a second conflicting workflow engine. It supports explicit stage skips with reasons; an automatic effort controller and runtime compute allocation remain additional functionality.

## 8. A feasible implementation architecture

### Phase 0: useful today

Use the brief, existing project files, an existing assistant, and a human reviewer. The operator manages the current six-stage CLI workflow when using full receipts. The collaborator sees the small task and its deliverable. Manual support cost is recorded rather than hidden.

No new task was started and no policy was changed by creating this proposal. The FAQ brief is ready for a future pilot; its execution remains pending.

### Phase 1: local prototype

Extend the existing Python project with a thin local adapter. A server-rendered interface is sufficient; a separate frontend stack is optional. Use a small web framework, templates, and the existing CLI or a narrowly tested application interface. Reuse dependencies where practical.

Responsibilities:

- Read a project catalog containing only explicitly selected project roots.
- Display current CLI status and dependency reasons.
- Edit the designated brief through a version check.
- Preview and export selected context through the core.
- Attach existing result and evidence files.
- Record checkpoints only when core requirements are satisfied.

Local-only operation binds to loopback. Validate requests, use CSRF protection for writes, restrict paths to the selected project, and never accept arbitrary shell command strings from the browser. Invoke CLI operations with argument arrays and validated parameters. Failed commands must not produce a success badge.

Keep owner/reviewer assignments in a small, versioned metadata sidecar. Treat any search index as a disposable projection. Canonical source text stays in its source file, stage state stays in the core receipts, and a displayed summary is not a second source of truth.

### Phase 2: trusted team pilot

Use a private repository or an explicitly shared sanitized folder. A repository has not been created or configured in this demo. If Git is used, create distinct task branches, require review before integration, and keep one writer responsible for each run's state. Do not merge conflicting receipts automatically; regenerate and recheck against the integrated files.

All pilot participants must be allowed to read the entire distributed project. The pilot may constrain integration through review; it cannot promise folder-level confidentiality inside a cloned repository.

### Phase 3: institutional access, only after demand

Use individual identities under an organization account, an existing OIDC identity provider, and a central service that enforces project access on every request. Start with project-level isolation. Users navigate only projects they may access.

Readable exports must apply the same authorization as direct reads. If a contributor cannot access a required source, do not silently omit it and claim a complete packet. Stop the export and identify the missing authorization, or obtain an authorized, deliberately sanitized source.

A cloned repository distributes its contents and potentially its history. Hiding a folder in a UI, setting CODEOWNERS, or protecting a branch does not revoke those bytes. Confidential work needs a different repository/security boundary or mediated server access. Previously downloaded exports cannot be recalled by changing a permission.

Derived summaries and results also need audience control. A future system must constrain them to the permitted audience of their sources unless an authorized person explicitly releases a sanitized version. Logging the disclosure is not a substitute for preventing unauthorized access.

This hosted phase is substantially more demanding than the local prototype. It should not be described as a weekend enterprise product.

### Later: optional operating capacity

Connect approved runtimes and an existing model gateway when execution is justified. Each agent needs a specific identity or service principal, an allowed project, allowed tools, a bounded budget, timeout/cancellation, and attributable actions. Agents should return proposals through the same review boundary.

Use provider-supported organizational licensing or API budgets. A gateway can distribute allowed consumption; it does not imply that personal subscriptions are freely transferable or that pooling makes a model more capable. This proposal does not depend on subscription pooling.

## 9. Data and state rules

Minimal proposed concepts:

| Object | Required meaning |
|---|---|
| Project | Canonical sources, policy, selected root, and audience. |
| Work brief | Goal, task owner, reviewer, source references, boundaries, acceptance, and next action. |
| Packet | Existing frozen context export and its identifier. |
| Submission | Deliverable references, actual checks, open questions, and the packet used. |
| Review | Reviewer, result version, decision, rationale, and time; identity strength shown honestly. |

Do not collapse these three dimensions into a single “done” flag:

1. **Workflow:** what stages are recorded as completed or pending.
2. **Freshness:** whether recorded inputs and evidence still match.
3. **Acceptance:** whether the designated reviewer accepted the particular result.

For the future review layer, an acceptance binds to the relevant result, brief/criteria, and source snapshot. Meaningful changes trigger review of that acceptance. A hash proves byte identity, not truth, test execution, reviewer identity, or immunity to tampering.

Permissions also have distinct meanings: read, propose edits, integrate changes, administer policy, execute a tool, and approve an outcome. A brief documents the boundary; filesystem, repository, and service controls enforce it where available. A prompt alone does not enforce permission.

## 10. Acceptance criteria for the first software slice

These are requirements, not checks already passed:

1. A new participant finds the outcome, source authority, owner, reviewer, and next action without reading a chat transcript.
2. Export shows the exact included files, roles, sections, and packet identifier. The receiver can read it without Relay.
3. The export fits the configured character budget or fails visibly; it never silently drops a required policy.
4. Unsupported file types, missing paths, and changed sources produce specific errors.
5. Returning a draft does not mark it accepted or fabricate a successful test.
6. The core refuses a checkpoint with stale selected inputs or missing required evidence.
7. A changed declared source produces a review-needed reason for its consumers in the supported dependency scope.
8. An unchanged-byte check is labeled as freshness, not semantic verification.
9. Two edits based on the same old version cannot silently overwrite each other; one must reload or resolve the conflict.
10. Deleting or altering an accepted output triggers review of the corresponding acceptance in the new layer.
11. The local adapter cannot read outside the selected root or run arbitrary submitted shell commands.
12. In hosted mode, an unauthorized user cannot access a project through navigation, direct API calls, search, export, attachments, or derived summaries. Hosted mode must not ship before these paths are verified.

## 11. The first experiment for Milo

Use [the companion work brief](relay-first-work-brief.md) to hand a pricing FAQ proposal to one collaborator. The pricing project is synthetic, has designated current and historical sources, and already contains a completed specification and validation records.

Run three small scenarios:

1. **Initial handoff:** collaborator prepares the proposal using an existing assistant; Milo reviews it.
2. **Interruption:** another session or contributor identifies the current next step and continues.
3. **Changed input:** in a separate disposable copy, change a selected source, observe freshness detection, and repair affected work.

The existing source and historical run should remain intact for comparison. Do not treat the old final-audit file as a fresh check.

### Compare against a serious baseline

Baseline: a well-written shared brief, links to the same sources, and an ordinary checklist. Treatment: the same quality of brief plus frozen packets, receipts, and dependency feedback. This isolates whether the additional machinery helps.

For an initial diagnostic, use paired comparable tasks and alternate order where possible. For a stronger directional test, recruit three small teams and observe at least two handoffs per team, including a resumption or source-change case. This is still a small, potentially biased sample, not proof of market demand.

### Measures and decision thresholds

All thresholds below are proposed gates, not measured results:

| Measure | Definition | Initial gate |
|---|---|---|
| Time to useful continuation | Receiver starts until they correctly identify a supported next action. | Under 10 minutes and meaningfully lower than baseline. |
| Founder explanation | Minutes of extra private clarification after the brief. | At least 30% lower than baseline. |
| Required dependency detection | Seeded changes to explicitly recorded inputs that are flagged. | Every seeded declared change flagged in the pilot. |
| Content quality | Source fidelity, uncertainty handling, and acceptance criteria scored using the same rubric. | No regression against baseline. |
| Process overhead | Recording and operating the workflow, excluding actual task work. | Under 5 minutes per small handoff after setup. |
| Net benefit | (Baseline coordination + administration + rework) minus (treatment coordination + administration + rework). | Positive for the team, not just the receiver. |
| Voluntary reuse | Participants use the flow on a subsequent real task without prompting. | At least 2 of 3 teams in the expanded pilot. |

If setup is excluded from a per-handoff metric, report it separately and calculate how many handoffs would recover it. Never present labor or token savings without the actual records. Avoid measuring agent-message counts as a proxy for team value.

### Kill or pivot conditions

If the simple brief provides almost all the benefit, keep the templates and discontinue the extra UI. If conservative invalidation creates more checking than it saves, narrow the dependency model before expanding. If users want one vendor's built-in workspace and do not need portability, become an adapter or stop the standalone product. If every customer needs a bespoke process, this may be a service rather than scalable software.

## 12. How to build it with AI without expanding the scope

Treat AI as an implementation assistant for a small series of reviewable changes. Human review remains necessary, particularly for authorization and disclosure paths.

| Increment | Deliverable | Meaningful verification |
|---|---|---|
| A: reader | Local project/task view backed by actual core status. | Compare the display with CLI results on current and stale fixtures. |
| B: handoff | Source selector, preview, and export using core packet generation. | Check budget failures, path boundaries, and source selection. |
| C: return | Attach result/evidence and surface actual checkpoint errors. | Check missing evidence and changed input failure paths. |
| D: review | Version-specific proposed/accepted/review-needed display. | Change the result or criteria and confirm acceptance is not reused. |
| E: onboarding | A participant completes the task without terminal work. | Observe a live handoff; do not infer usability from unit tests. |

For each increment, give the coding assistant the intended behavior, relevant source files, boundaries, and an observable check. Require actual modified code as an output, not only a completion report. Do not ask one prompt to build an entire agent operating system.

A planning allowance of roughly 8–15 focused developer-days for a local prototype is a rough hypothesis, contingent on the existing core being easy to integrate. Validate it with increment A. The human pilot can begin before that work. Authentication, hosted isolation, runtime execution, operations, and production hardening are outside this allowance.

## 13. Why this could become a business

The buyer hypothesis is the person paying the coordination cost: a founder, agency lead, or team manager. The user is anyone doing or reviewing the work. The initial distribution path is a reusable briefing kit in an existing project, followed by a small-team pilot.

Keep the local format and export useful without a paid account. A possible paid offering is hosted team access, identity integration, review history, source-change notifications, and maintained integrations. This is a business-model hypothesis; license choices and willingness to pay have not been validated.

Test a paid pilot only after demonstrating a net benefit. Ask for commitment to a repeat use case and an actual purchase decision, not a positive response to a feature list. Set pricing after learning value and support cost; do not invent a market price in this document.

The file format and ERRC grid are readily copied. Any durable advantage would need to come from excellent onboarding, reliable integrations, a proven review experience, and evidence that the workflow helps the chosen users. Portability can be a reason to adopt; it does not guarantee a moat.

## 14. What to do next

1. Use the companion brief with one collaborator and record the baseline.
2. Observe the handoff and review before writing a web application.
3. Improve or remove fields that do not help continuation.
4. Build increment A only if current manual status checking is a demonstrated obstacle.
5. Expand to three teams only after the founder pilot produces positive net benefit.
6. Add hosted identity, confidential project boundaries, and optional model capacity in response to real demand.

The immediate deliverable is a usable collaboration experiment. The product decision is whether to turn that experiment into a small, interoperable front door to shared work.

## 15. Evidence and limitations

This proposal uses the user's stated needs, the local protocol and demo records, and official sources linked alongside the relevant claims. It applies the four strategic lenses to generate and stress-test a product hypothesis.

It does not report customer interviews, a completed collaborator onboarding, a live cross-model comparison, measured savings, authenticated approvals, an implemented UI, or an exhaustive competitive/patent search. The synthetic pricing exercise is evidence about a local workflow, not evidence that a market will buy Relay.

The companion brief is an actionable first test. Its outcome should determine what gets built.

### Document and command verification

Both Markdown documents were checked for existing local link targets and balanced fenced blocks. The companion's `run start`, initial context export, `status`, and `verify` sequence was exercised successfully in a disposable copy using the installed CLI. A Markdown packet was created there. The temporary copy was removed; no `relay-faq-pilot` run or initial export was retained in the original project.

This verifies the documented starting commands, not collaborator usability, task completion, source-change repair, semantic correctness, or any product success threshold.
