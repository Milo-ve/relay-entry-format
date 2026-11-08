# Relay Method task-layer protocol v1

This is the executable local task layer added in version 0.3.0. It reuses the original CLI's bounded readers, Markdown section selector, knowledge metadata checks, hashing, and workspace lock. The original [stage protocol](PROTOCOL.md) remains available through `okf-icm`.

## Scope

`relay` supports a preferred-assistant handoff flow. It does not invoke a worker model, execute shell commands, enforce model compute, authenticate organizations, or manage distributed collaboration. `relay serve` is loopback-only and intended for a trusted local user.

The task layer provides a compact lifecycle instead of silently creating and completing six legacy stages. Its profiles recommend work appropriate to the task. They do not confer permissions or approve business decisions.

## Commands

`relay --root PROJECT` precedes the operation. Use `relay --help` and operation-specific help for arguments.

| Command                  | Effect                                                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `init PATH`              | Initialize the existing `.context` format without overwriting.                                                |
| `start ID`               | Validate a task, choose an initial route, snapshot controls/selected sources.                                 |
| `list`, `show ID`        | Compute current freshness and review state.                                |
| `context ID`             | Export a current readable work packet. Refuse changed inputs or blockers.                       |
| `submit ID`              | Bind separate result and evidence files to the current packet.                                                |
| `review ID`              | Record a decision for the exact current submission and assigned reviewer name.                                |
| `refresh ID`             | Snapshot current sources and clear the current submission and acceptance; retain history.                     |
| `escalate ID`            | Explicitly increase effort to Investigative, with a reason and a one-escalation limit.                        |
| `serve`                  | Serve the local forms and packet downloads on 127.0.0.1.                                                      |
| `export-html --out FILE` | Write a self-contained, script-free snapshot of the knowledge map and every task's history. Never overwrites. |

## Sources and packets

Every task includes `.context/ENTRY.md`, `policy.md`, `project.md`, and `config.json`. Explicit `--select path` or `path#Exact Heading` selections add data. Selected knowledge retains its metadata signals. Source text cannot elevate its role by containing instructions.

Full-file SHA-256 hashes identify byte versions even for section selections. Selected files are bounded by the existing 1 MB reader and common-secret-path exclusions. The rendered packet has a character budget and fails before task creation if exceeded. No required source is silently omitted. These exclusions are not comprehensive secret detection.

Packets are frozen JSON with a hash over sorted-key JSON excluding `packet_id`. Each packet includes a brief, route, files, task ID, and revision. The Markdown export frames source contents as JSON strings. Hashes detect changes/corruption, not authenticated identity or malicious rewriting of all records together.

## Routing

Policy `relay-effort-v1` uses explicit task kind, consequence level, missing-prerequisite flags, and conservative request-text heuristics. Direct requires an explicitly specified transformation with low consequences. Diagnosis/design and high consequences select Investigative. Otherwise Standard is the default. An explicit blocker selects Clarify.

No automatic classifier discovers every risk, policy conflict, or missing prerequisite. Review the selected route and escalate on evidence. The task's boundaries and host instructions remain applicable regardless of effort.

`--jev shadow` and `--jev route` explicitly authorize a request containing the goal and selected non-control source contents to TypeSafe's documented endpoint. Control files are excluded from the provider request. The adapter asks a Choice about work type and a Noul about conflicting relevant claims. Route mode can raise effort; it cannot lower a rule-selected profile or waive prerequisites/review. The threshold is an initial heuristic, not a measured error bound.

The adapter uses a five-second timeout, no automatic retries, rejects redirects, bounds response size, validates returned choices/probabilities, and does not persist the API key. Failure retains rules with a visible reason. A refresh does not reuse or automatically rerun the old provider judgment.

## Result and acceptance

Submission requires nonempty output and evidence files, a description of actual checks, and a next action. Results cannot be selected inputs or live `.context` controls/state. Intentional canonical-source editing should use a separate integration action or the detailed stage workflow's explicit mutated outputs.

`submission_id` hashes the result/evidence receipts, packet reference, checks, questions, next action, and time. The receipt is preserved independently under `submissions/`. Reviews name a specific current ID and the assigned actor. Reviewer names are self-recorded assertions, not proof of identity. The software checks existence, versions, and metadata, not the truth of claimed evidence.

Workflow/result progress, freshness, and acceptance are separate fields. Changed sources, outputs, or evidence produce `needs_review`; submission alone does not become acceptance. Refresh and escalation remove current acceptance. Review events retain the recorded decision and its version references.

The optional library-level `review_required=False` skips the pending-human-review label but never creates acceptance. The public CLI and UI require an explicit reviewer decision.

## Views

`serve` adds a knowledge map (`/map`) and a history panel on each task page. `export-html` writes the same views as one static file. All are inline SVG and HTML generated by Python: no JavaScript, no external assets, no change to the response CSP.

- The **knowledge map** draws concepts from `.context/knowledge` and the relative Markdown links between them. Shape shows lifecycle, fill shows trust, a dashed outline shows stale. Invalid concepts are listed, not drawn. Unresolved links are counted, not drawn. Beyond 100 concepts the map is truncated with a visible notice, and the table still lists all of them.
- The **task history** separates three things: whether the selected sources are current, whether work was returned with checks the submitter reported (Relay does not verify them), and whether the current version was accepted. A refresh fades earlier events as superseded. If sources change after acceptance, the view says the acceptance no longer applies.
- Trust and freshness are the bundle's own recorded signals. A view is not verification or approval.
- The snapshot contains goals, acceptance state, owners, reviewers, timestamps and event kinds. It omits source, packet, deliverable and free-text note contents. It is a point-in-time copy; treat it as project data and keep it out of public history. Its own style is pinned by hash in a `Content-Security-Policy` meta tag.
- A task that cannot be read (for example a modified packet) appears in the snapshot as an error, not silently omitted.

## Concurrency and local HTTP

CLI/UI writes use the existing cooperative `.context/write.lock`. Browser forms include a task revision and reject stale mutations. Local JSON replacement is atomic; packet creation plus state mutation is not a database transaction. External editors are not locked. After a crash, inspect state and confirm the process stopped before clearing a stale lock.

The UI checks Host and Origin, includes a per-server CSRF token, escapes rendered data, and sets restrictive response headers. It exposes only explicit task operations and packet downloads, not a general file server. It accepts no shell command strings. Keep it on loopback; source confidentiality and authentic review require a future authorization layer.

## Verification limits

Offline tests exercise routing, freshness, receipts, review identity fields, corrupted packets, path boundaries, provider failures, and HTTP forms/CSRF/concurrency. They do not establish actual user savings, broad prompt-injection resistance, live Jev calibration, worker correctness, or enterprise security.
