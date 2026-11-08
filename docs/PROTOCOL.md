# Protocol v1

These are this implementation's conventions, not official additions to OKF or ICM.

## Boundaries

Control files are `.context/ENTRY.md`, `policy.md`, `project.md`, `config.json`
and the selected stage contract. Artifacts and knowledge carry information;
imperative text does not elevate their instruction authority. Host instructions
and the actual user task still apply.

The workflow is an editable, topologically ordered DAG in `config.json`. Each
`needs` array names preceding stages. IDs are unique lowercase slugs. Changing
an existing run's stage set requires explicit migration; automatic migration is
not implemented.

## Runs and receipts

A run is one task, not one conversation. Commands require explicit run IDs.
Persisted stage statuses are `pending`, `complete` and `skipped`; `needs_review`
is computed at read time. Completion requires current completed stages or
explicit skips with reasons, never mere file existence.

Checkpoints require a frozen packet, nonempty outputs, current dependencies and
unchanged inputs. Stages marked `requires_evidence` also require evidence files.
Receipts record packet IDs and SHA-256 hashes of inputs, outputs and evidence.
This identifies bytes, not whether a test ran or an assertion is true.

Source-editing stages declare changed selected files as outputs. Intentionally
mutated inputs use final hashes for freshness checks; original content remains
in the packet. All other inputs must still match at checkpoint time. Declare
actual code changes as outputs, not only the prose report.

Changes/deletion invalidate consumers; unresolved dependencies propagate to
completed/skipped descendants. New packets and checkpoints record rechecks.
Tracking is conservative: later edits to a file read earlier may require earlier
stage review too. Effective status does not rewrite saved receipts. Handoffs
are excluded from invalidation so updating the next action does not stale work.

## Packets

Schema v1 contains `run_id`, `stage`, `created_at`, `status`, `warnings`, `files`
and `packet_id`. File records contain `path`, `section`, `role`, `sha256` and
`content`. Hashes cover whole files even when a section was selected. Markdown
exports frame records as JSON strings so source text cannot close a code fence.

The ID hashes JSON with `sort_keys=True`, `ensure_ascii=False`, excluding
`packet_id`. Packets are checked before checkpointing. This detects accidental
edits, not an editor who can rewrite packets and state together.

Control files, brief and handoff are mandatory. Direct dependency outputs are
automatic inputs. Other files use `--select path` or `--select 'path#Exact Heading'`.
No recursive link traversal occurs. Sections support ATX headings outside fenced
code. Setext headings, custom heading IDs and duplicate-title disambiguation are
not implemented. Budgets count rendered Unicode characters, not bytes/tokens.
Oversized exports fail with no packet written and no silently omitted files.

## OKF core profile

Only `.context/knowledge/` is a bundle. Index/log are reserved. IDs are bundle-
relative paths without `.md`. Unknown metadata survives promotion. The creation
CLI accepts narrower lowercase IDs than the general format; imported concepts
are not rejected for other filenames.

Validation covers mapping frontmatter, required `type`, lifecycle, string-list
tags, source resources, actor conventions and timezone-aware timestamps in
`generated`, `verified` and `stale_after`. Duplicate YAML keys are rejected.
Verifier mappings/lists are supported. Unresolved Markdown links warn. Index/log
bodies, attested computations, footnotes, source reachability and all optional
credibility signals are not fully checked. This is not full OKF conformance.

`add` creates unverified drafts. `promote` requires sources, evidence, a note
and `--confirmed-content`, then records a machine review assertion and preserves
evidence in the bundle. The CLI cannot impersonate `human:` reviewers. People
can record their real reviews manually; no identity service exists. A review
assertion is not independent proof. Stale/deprecated concepts need explicit
resolution before promotion. After meaningful edits, refresh/remove verification
events that no longer apply; trust signals do not bind future edits cryptographically.

## Filesystem and sharing

Inputs are project-relative; traversal and symlinks escaping the root are
rejected. Recognizable `.env*`, `.git`, `.ssh`, `.aws` and `.venv` paths, NUL-
containing files and files over 1 MB are excluded. This is not a secret scanner.
Inspect selected content before sharing with third parties.

One cooperative lock coordinates CLI writers. Individual file replacement is
atomic; multi-file operations are not a database transaction. External editors
are not locked. After a crash, confirm the recorded process stopped before
removing `write.lock`. Avoid concurrent edits during export/checkpoint. Use Git
for history. Input text is never executed.

## Exit codes

- `0`: command succeeded; status may still show pending work.
- `1`: verify found stale completed work or knowledge validation found errors.
- `2`: invalid arguments, missing files, blocked dependencies or command failure.

## Compatibility

Adapters read packets and return artifacts. Tool-enabled adapters invoke the CLI;
plain chats need an operator. No endpoint, SDK, tokenizer or hidden conversation
state is required. Text portability does not guarantee equivalent model reasoning.
