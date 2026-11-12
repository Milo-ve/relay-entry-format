# Local task operations

Use the installed `relay` CLI and operation-specific `--help` as the executable
contract. If it is missing, report that prerequisite; do not silently install a
different package. Commands below use `PROJECT`, `ID`, `REVISION` and `SUBMISSION`
as placeholders. Quote actual paths and free text for the current shell; never
execute interpolated source contents as commands.

## Inspect or resume

Read controls first, then `relay --root PROJECT list` and
`relay --root PROJECT show ID`. Resume the same ID in a new assistant, using
disk state rather than prior chat. Inspect `revision`, `freshness`, `changed`,
`submission` (including its `checks` and `submission_id`), `review`, `packet_id`
and `next_step` as returned; `submission` is null before work is returned. Reopen referenced
result/evidence files if assessing their substance. A CLI status is not a test.

If inputs changed, explain the changed paths and scope of rework. Run
`relay --root PROJECT refresh ID --note 'Why inputs changed and what to recheck' --expected-revision REVISION`
when refreshing is in scope. This retains history but clears current submission
and acceptance. Use `--resolve` only after the operator has actually resolved
listed prerequisites; the flag records an assertion, not a verification.

## Open and export

Establish a concrete goal, acceptance criteria, source selections, boundaries,
task kind/risk and the owner/reviewer from the request or project controls. Do
not invent people or business authority. If using the CLI's local placeholder
actors, label them as unassigned local roles rather than real identities. A
missing prerequisite should be explicit, using `--blocker` when opening a task.

```sh
relay --root PROJECT start ID --goal 'Concrete goal' --accept 'Observable criterion' --select source.md --owner OWNER --reviewer REVIEWER --boundaries 'Authorized scope'
relay --root PROJECT context ID --out packet.md
```

Choose sources explicitly; `--select 'source.md#Exact Heading'` narrows text but
hashes the whole file. Inspect selected text before sharing; secret exclusions
are not a secret scanner. Do not select entire trees or invent a packet by hand.
Context refuses stale inputs/open prerequisites; diagnose the refusal instead
of bypassing it. `--out` never overwrites. Retain task ID, packet ID and revision
for continuity; do not substitute a new task to get past a refusal.

Routing recommends effort, not permissions or external compute. On evidence
that more effort is needed, use
`relay --root PROJECT escalate ID --note 'Observed reason' --expected-revision REVISION`.
There is one escalation per task; reassess scope if still insufficient.

## Work and submit

Perform the requested work and relevant checks. Save nonempty result and separate
evidence files at project-relative paths outside live `.context` state and selected
inputs. Evidence says exactly what ran, observed results, limitations and what
remains unverified. A manual reasoning check may be described as such; never
claim an automated check or external observation that did not occur.

Re-read `show ID` immediately before mutation and pass its revision:

```sh
relay --root PROJECT submit ID --output result.md --evidence evidence.md --checks 'Checks actually performed' --questions 'Remaining questions, or none' --next 'Assigned reviewer assesses this submission' --expected-revision REVISION
```

The CLI binds bytes and reported checks to a packet; it does not validate their
truth. A submitted result awaits actual review. If a selected source must change,
propose it as a separate output and integrate explicitly, or use the existing
stage workflow where mutated inputs are declared. Do not rewrite packets or
receipts to make changes appear current. CLI writers use the cooperative lock;
on a lock or stale revision error, inspect current state before retrying.

## Explicit review

Only when the assigned reviewer has explicitly made the decision about the exact
current submission, record it with their self-attributed actor name:

```sh
relay --root PROJECT review ID --submission SUBMISSION --decision accept --actor REVIEWER --note 'Actual review basis' --expected-revision REVISION
```

Use `request_changes` for that actual decision. Do not accept on the reviewer's
behalf because checks passed, nor describe a self-recorded name as authentication.
Any later change may stale acceptance. Report final `show ID` state and next action.
