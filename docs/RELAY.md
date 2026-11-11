# Relay Method task-layer protocol v1

This is the executable local task layer added in version 0.3.0. It reuses the original CLI's bounded readers, Markdown section selector, knowledge metadata checks, hashing, and workspace lock. The original [stage protocol](PROTOCOL.md) remains available through `okf-icm`.

## Scope

`relay` supports a preferred-assistant handoff flow. It does not invoke a worker model, execute shell commands, enforce model compute, authenticate organizations, or manage distributed collaboration. `relay serve` is loopback-only and intended for a trusted local user.

The task layer provides a compact lifecycle instead of silently creating and completing six legacy stages. Its profiles recommend work appropriate to the task. They do not confer permissions or approve business decisions.

## Commands

`relay --root PROJECT` precedes the operation. Use `relay --help` and operation-specific help for arguments.

| Command                  | Effect                                                                                                        |
| ------------------------ | ------------------------------------------------------------------------------------------------------------- |
| `init PATH [--minimal]`  | Initialize the existing `.context` format without overwriting. `--minimal` writes a one-stage `config.json` (stage `01-work`) and one stage contract instead of six; see [Minimal workspace](#minimal-workspace). |
| `skill [--name ref] --to DIRECTORY` | Install a complete bundled skill tree; default remains `relay-workspace`; refuse different contents. |
| `skill [--name ref] --zip FILE` | Export the complete skill folder as a new ZIP; never overwrite. |
| `skill --name ref --manual FILE` | Export a standalone manual guide and separate-result/evidence return template. |
| `workspace [--apply] [--claude] [--minimal]` | Preview additive onboarding; save originals and layout before applying; optionally add the Claude bridge. `--minimal` applies only when this creates the workspace; an existing one is refused, never rewritten. |
| `start ID`               | Validate a task, choose an initial route, snapshot controls/selected sources.                                 |
| `list`, `show ID`        | Compute current freshness and review state, with a plain-language `next_step`. `list --brief` prints only id, status, freshness, owner, reviewer and revision for each task; use `show ID` for detail. `list --stale` keeps only tasks whose inputs changed since their snapshot and combines with `--brief`; it adds a one-line hint on stderr, so the JSON on stdout is unchanged. |
| `context ID`             | Export a current readable work packet. Refuse changed inputs or blockers, naming which.                       |
| `submit ID [--snapshot]` | Bind separate result and evidence files to the current packet. `--snapshot` first validates, then signs byte-for-byte copies under `deliverables/ID/rREV/`; see [Result and acceptance](#result-and-acceptance). |
| `review ID`              | Record a decision for the exact current submission and assigned reviewer name.                                |
| `refresh ID`             | Snapshot current sources and clear the current submission and acceptance; retain history.                     |
| `refresh --all-stale --note N [--apply]` | After a shared source changed: preview, or with `--apply` perform, a refresh of every task whose inputs changed; see [Refreshing many tasks](#refreshing-many-tasks). |
| `escalate ID`            | Explicitly increase effort to Investigative, with a reason and a one-escalation limit.                        |
| `reassign ID`            | Change the owner and/or reviewer with a note. Owner and reviewer are part of the frozen packet brief, so this takes a new snapshot and clears the current submission and review; history is kept. Refused while inputs are changed or if nothing would change. |
| `serve`                  | Serve the local forms and packet downloads on 127.0.0.1.                                                      |
| `card ID [--format md\|html] [--out FILE]` | Read-only delivery card for someone who will not open Relay; see [Delivery card](#delivery-card). |
| `export-html --out FILE` | Write a self-contained, script-free snapshot of the knowledge map and every task's history. Never overwrites. |

`start`, `submit`, `refresh`, `escalate` and `reassign` accept an optional `--actor NAME`, stored on the event only when given (at most 80 characters, no control characters). It is a self-recorded label for the history, like the reviewer name: it is not authentication and is never required. Events written before it existed load and display unchanged.

### Refreshing many tasks

When one shared source changes, every task that selected it becomes `needs_review`. `relay list --stale --brief` shows them. `relay refresh --all-stale --note "what changed"` then **previews and writes nothing**: for each stale task it lists the changed paths and whether its current submission or acceptance would be cleared, and it names any task whose refresh would be refused (for example, a source that now exceeds the task's character budget or matches `deny_paths`). Run the same command with `--apply` to perform it.

- Applying is an ordinary refresh per task: one event each, carrying your note, `batch: true` and the changed paths, under one writer lock. Each task loses its current submission and acceptance and keeps its history, exactly as a single `refresh` does. **Read the preview first**: an accepted task that depended on the changed source stops being accepted.
- It never creates a review, never resolves open prerequisites (`--resolve` is refused here, so a prerequisite is cleared only deliberately, one task at a time) and never accepts anything on a reviewer's behalf.
- A task that cannot be read or refreshed is reported under `failed` with its error and left unchanged; the other tasks are still processed. The command then exits with code 2 so a script cannot miss it, and the same applies to a preview that finds such a task.
- `--note` is required. `--expected-revision` is refused, because each task has its own revision; and when `require_expected_revision` is on, `--all-stale` is refused entirely. Refresh those tasks one at a time.
- `--actor NAME` is recorded on every event, as for a single refresh.

### Operator guidance

`next_step` in `show`/`list` output is derived only from the computed status. It is advice for the operator: it is never written into a packet, grants no permission, and does not change task state. `context` prints its guidance on stderr, so stdout stays a clean packet; with `--out` it appears as `next_step` in the JSON result. When another task command is refused because inputs changed or prerequisites are open, the CLI prints the same advice after the error. Refusal messages raised by the library name the cause but not CLI commands, because the browser interface shows them too. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Workspace adaptation

`relay --root PROJECT workspace` previews changes without writing. `--apply`
records original bytes of affected `AGENTS.md` and `.gitignore` files (or their
absence) and a path/type inventory in `.relay-backups/workspace-*/manifest.json`
before the first workspace change. Inventory omits `.git`, `.context`, backups,
virtual environments and Python caches; it does not copy source contents or
follow directory symlinks. Managed paths cannot be symlinks. Existing `.context`
must be compatible and is never rewritten; otherwise the usual initializer runs.
Existing instructions remain before the appended Relay guidance. Ignore rules
cover local context, backups, deliverables, virtual environments and `.env*`.
The command never moves sources, creates tasks, migrates graphs or records acceptance.

`--claude` explicitly includes `CLAUDE.md` in preview and backup and appends a
small `@AGENTS.md` import. Existing instructions and original line-ending bytes
are preserved; an existing import is left alone. Without the flag, `CLAUDE.md`
is untouched. A different existing managed bridge is refused for reconciliation.
For compatible existing workspaces, application also respects the cooperative
`.context/write.lock`; preview does not create a lock or any files.

The backup is local and may contain private instructions and filenames. Ignore
rules do not remove already tracked files from Git. Do not publish backups or
private packets. A failed multi-file operation can leave partial changes; inspect
the backup and workspace before retrying. Avoid concurrent external edits.

To undo, compare current files with saved originals, then restore files listed
as previously present and remove newly created files only if subsequent work
will not be lost. If the manifest says `context_existed: false`, a newly created
`.context` may be removed only after checking that no later task, run or knowledge
work needs retaining. Never remove a pre-existing `.context`. No automatic
destructive rollback is provided.

### Portable skill and manual return

`ref` is a shared instruction tree for preparation, task administration and
continuity. Its entry routes to operation-specific references and a return
template, all included in both directory and ZIP distribution. The installer
uses package resources, so an installed wheel does not need the source checkout.
It refuses different existing trees rather than merging customized resources.
An identical tree is a no-op. Destinations are explicit; no global client
configuration is discovered or changed automatically.

The same content is intended for Codex `.agents/skills/ref` and Claude Code
`.claude/skills/ref`. Invocation syntax belongs to the host; installing a folder
does not prove discovery. The skill requires checking visible duplicate copies
and actual file/CLI/write access. No-tool use asks an operator for an exported
packet and returns separate result and evidence bodies without claiming writes.
The operator checks packet identity and freshness before recording the return;
review remains an explicit separate decision. See [validation](ref-validation.md)
for observed checks and outstanding client gates. No MCP server is included.

## Minimal workspace

`config.json` is a control, so every task packet carries it. The default six-stage graph is only useful if you run the stage protocol; for task-only use, `relay init PATH --minimal` (or `workspace --apply --minimal` when it creates the workspace) writes a one-stage workflow, `01-work`, with one contract. It is a smaller `config.json`, nothing more: tasks, review and packets work the same, and `okf-icm` can still run its single stage.

Measured with the offline test fixture (one one-line source, goal `Goal`), the rendered task packet is 4,268 characters with `--minimal` and 5,276 with the default scaffold. Other fixtures give other totals; the saving is about the size of the six-stage `config.json`. This is a size measurement, not a measured saving in model cost or time.

Default `init` is unchanged. `--minimal` never changes an existing `.context`, and adds no version marker to a project; to shrink an existing project, edit its controls yourself, knowing that every task then needs a refresh (see [REF](REF.md)).

## Sources and packets

Entry, controls and packets follow [REF v1](REF.md). Every task includes `.context/ENTRY.md`, `policy.md`, `project.md`, and `config.json`. Explicit `--select path` or `path#Exact Heading` selections add data. Selected knowledge retains its metadata signals. Source text cannot elevate its role by containing instructions.

Full-file SHA-256 hashes identify byte versions even for section selections. Selected files are bounded by the existing 1 MB reader and common-secret-path exclusions. The rendered packet has a character budget and fails before task creation if exceeded. No required source is silently omitted. These exclusions are not comprehensive secret detection.

Packets are frozen JSON with a hash over sorted-key JSON excluding `packet_id`. Each packet includes a brief, route, files, task ID, and revision. The Markdown export frames source contents as JSON strings. Hashes detect changes/corruption, not authenticated identity or malicious rewriting of all records together.

## Routing

Policy `relay-effort-v1` uses explicit task kind, consequence level, missing-prerequisite flags, and conservative request-text heuristics. Direct requires an explicitly specified transformation with low consequences. Diagnosis/design and high consequences select Investigative. Otherwise Standard is the default. An explicit blocker selects Clarify.

No automatic classifier discovers every risk, policy conflict, or missing prerequisite. Review the selected route and escalate on evidence. The task's boundaries and host instructions remain applicable regardless of effort.

`--jev shadow` and `--jev route` explicitly authorize a request containing the goal and selected non-control source contents to TypeSafe's documented endpoint. Control files are excluded from the provider request. The adapter asks a Choice about work type and a Noul about conflicting relevant claims. Route mode can raise effort; it cannot lower a rule-selected profile or waive prerequisites/review. The threshold is an initial heuristic, not a measured error bound.

The adapter uses a five-second timeout, no automatic retries, rejects redirects, bounds response size, validates returned choices/probabilities, and does not persist the API key. Failure retains rules with a visible reason. A refresh does not reuse or automatically rerun the old provider judgment.

## Result and acceptance

Submission requires nonempty output and evidence files, a description of actual checks, and a next action. Results cannot be selected inputs or live `.context` controls/state. Intentional canonical-source editing should use a separate integration action or the detailed stage workflow's explicit mutated outputs.

`submission_id` hashes the result/evidence receipts, packet reference, checks, questions, next action, and time. The receipt is preserved independently under `submissions/`. Reviews name a specific current ID and the assigned actor. Reviewer names are self-recorded assertions, not proof of identity. `review --external-ref TEXT` may add a pointer to an approval kept elsewhere (a ticket, message or link; at most 200 characters, no control characters). It is stored with the review as `external_ref` with `external_ref_assurance: recorded-not-verified`, is shown as "recorded, not verified", and is never fetched or checked. It does not change `identity_assurance` and is not authentication. The software checks existence, versions, and metadata, not the truth of claimed evidence.

By default a submission signs the files where they are, so editing a result or its evidence afterwards returns the task to `needs_review`. `submit --snapshot` is for work that keeps changing in place: after all the checks above pass, each output and evidence file is copied byte for byte to `deliverables/ID/rREV/ORIGINAL-PATH` (REV is the task revision at submission, and the original folder structure is kept, so equal file names in different folders do not collide) and the copies are what is signed. Each record keeps `source_path`, and the submission carries `snapshot: true`. Later edits to the originals leave the submitted version, and any acceptance of it, untouched; editing a copy returns the task to `needs_review`. Copies are opened exclusively: an existing target is refused and never overwritten, and copies and folders created by a submission that then fails are removed. `deliverables/` is in the `.gitignore` lines that `workspace --apply` adds. The copy proves which bytes were submitted, not that they are correct; reviewing the original after it changed again is still a separate decision. Without `--snapshot` nothing is copied and behaviour is as before.

Workflow/result progress, freshness, and acceptance are separate fields. Changed sources, outputs, or evidence produce `needs_review`; submission alone does not become acceptance. Refresh and escalation remove current acceptance. Review events retain the recorded decision and its version references.

The optional library-level `review_required=False` skips the pending-human-review label but never creates acceptance. The public CLI and UI require an explicit reviewer decision.

## Views

`serve` adds a knowledge map (`/map`) and a history panel on each task page. `export-html` writes the same views as one static file. All are inline SVG and HTML generated by Python: no JavaScript, no external assets, no change to the response CSP.

- The **knowledge map** draws concepts from `.context/knowledge` and the relative Markdown links between them. Shape shows lifecycle, fill shows trust, a dashed outline shows stale. Invalid concepts are listed, not drawn. Unresolved links are counted, not drawn. Beyond 100 concepts the map is truncated with a visible notice, and the table still lists all of them.
- The **task history** separates three things: whether the selected sources are current, whether work was returned with checks the submitter reported (Relay does not verify them), and whether the current version was accepted. A refresh fades earlier events as superseded. If sources change after acceptance, the view says the acceptance no longer applies.
- Trust and freshness are the bundle's own recorded signals. A view is not verification or approval.
- The snapshot contains goals, acceptance state, owners, reviewers, timestamps and event kinds. It omits source, packet, deliverable and free-text note contents. It is a point-in-time copy; treat it as project data and keep it out of public history. Its own style is pinned by hash in a `Content-Security-Policy` meta tag.
- A task that cannot be read (for example a modified packet) appears in the snapshot as an error, not silently omitted.

## Delivery card

`relay card ID` prints a one-page summary of a task to stdout; `--format html` writes the same content as a self-contained, script-free page (style pinned by hash in a `Content-Security-Policy` meta tag, no external assets), and `--out FILE` writes a new file instead of printing. It never overwrites a file and refuses a path inside `.context`.

It is read-only: it changes no task state, takes no lock, and leaves every file under `.context` byte-identical. It shows the goal and acceptance criteria; owner and reviewer (self-recorded); each selected source with its section, role, first 12 hex characters of its hash, and the packet's snapshot date, marking any source that changed since; the outputs and evidence files with their short hashes (and the original path when `submit --snapshot` made copies); the checks, open questions and next action as the submitter reported them; the review decision, its note, and any `--external-ref` (recorded, not verified); revision; and the full `packet_id` and `submission_id`. The three states stay separate: whether the sources are current, whether work was returned, and whether it was accepted.

It does not include source, packet or deliverable contents, and it omits the operator's next-step commands, so it carries no local paths. It does include free text that people wrote into Relay: goal, criteria, checks, open questions and the review note. Unlike the `export-html` snapshot, which omits notes, the card's purpose is to show them, so read it before sharing it outside the project. In Markdown, that text is escaped so it cannot start headings, lists or links of its own.

Nothing on the card is verified: names are self-recorded, checks are as reported, and a hash shows which bytes were recorded, not that they are correct. The card describes one moment (it states when it was generated); it is not a live view and not an approval.

## Concurrency and local HTTP

CLI/UI writes use the existing cooperative `.context/write.lock`. A writer that finds it held waits up to 5 seconds, then stops with the holder's process ID and start time. Set `lock_wait_seconds` to `0` for the earlier fail-at-once behaviour. Browser forms include a task revision and reject stale mutations. Local JSON replacement is atomic; packet creation plus state mutation is not a database transaction. External editors are not locked. After a crash, inspect state and confirm the process stopped before clearing a stale lock.

The UI checks Host and Origin, includes a per-server CSRF token, escapes rendered data, and sets restrictive response headers. It exposes only explicit task operations and packet downloads, not a general file server. It accepts no shell command strings. Keep it on loopback; source confidentiality and authentic review require a future authorization layer.

## Settings

Optional tool settings live in `.context/relay/settings.json`. Relay never creates the file; without it every default applies. Settings are not controls: they are not part of any packet, so editing them does not make a task stale, and existing projects gain no marker. An unknown key or a wrong type is refused with the key's name, so a typo cannot silently disable a rule.

| Key | Default | Effect |
| --- | --- | --- |
| `lock_wait_seconds` | `5` | How long a writer waits for `write.lock`, 0 to 300. `0` fails at once. |
| `require_expected_revision` | `false` | When `true`, `refresh`, `escalate`, `reassign`, `submit` and `review` are refused without `--expected-revision`. |
| `deny_paths` | `[]` | Names that may never be selected as a source, in task and stage packets. See below. |
| `language` | `"en"` | `"en"` or `"es"`: the language of the people-facing views. See [Language](#language). |

`deny_paths` patterns are matched case-insensitively against the spelled path and against the path it resolves to through links, and against every parent directory. A pattern without a slash matches any one path component (`secrets`, `*.pem`). A pattern with a slash matches the whole path or any parent directory of it (`finance/payroll*`); `*` also crosses slashes. The check runs before a file is read, so a refused `start` creates no task folder, and a `refresh` whose source became denied is refused with nothing changed. A packet taken before the rule is also refused at `context` export. Project controls are not subject to it. This applies only the names you list; it is not a secret scanner, and a denied file can still be pasted into an assistant by hand.

### Language

`"language": "es"` in `settings.json` shows Spanish in the places people read: the local interface (pages, forms, buttons, status and effort labels), the knowledge map and task history, the `export-html` snapshot, the delivery card (`card`, Markdown and HTML), and the plain-language `next_step` guidance, including the `relay: next:` hints on stderr. The `lang` attribute of every page and export follows the setting. English is the default; a value other than `en` or `es` is refused, naming the allowed values.

**What stays English, on purpose:**

- Library error messages (`Cannot export context ...`, `Task exists ...`) and the `relay:` prefix. A refused action in the interface therefore shows a Spanish page title around an English reason. **The "fully Spanish" criterion is not met** until those messages are localised; this is the stated limit of this release.
- CLI option names, command names, JSON keys, and the status and effort codes inside JSON (`needs_review`, `standard`). The commands quoted inside Spanish guidance keep their English words, because that is what the person types.
- The work packet, the packet scaffold and everything written to `.context`: events, receipts, `ENTRY.md`. Language is not a control, so it is never in a packet and changing it makes no task stale. Packets are read by assistants, and a translation would change the hashes that identify them.
- Anything people typed: goals, criteria, notes, reviewer and owner names, checks. Relay shows these as written.
- Values recorded by a knowledge bundle (type, lifecycle, trust, freshness) are shown as the bundle recorded them; only the labels around them are translated.

The Spanish text was written by Claude, the assistant that made this change, and has been read by no one else. It has not been reviewed by a native speaker or by the first non-technical reviewer it is meant for; treat wording as unreviewed until someone has done that. Each message is one entry in `src/okf_icm/i18n.py`, a table of English and Spanish pairs, so a correction is a one-line edit. A test checks that both languages have the same entries and placeholders.

## Verification limits

Offline tests exercise routing, freshness, receipts, review identity fields, corrupted packets, path boundaries, provider failures, and HTTP forms/CSRF/concurrency. They do not establish actual user savings, broad prompt-injection resistance, live Jev calibration, worker correctness, or enterprise security.
