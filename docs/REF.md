# REF v1: Relay Entry Format

REF names the part of Relay that a person or assistant meets first: the workspace entry, the control files beside it, and the packet that carries them. It documents the format introduced in version 0.3.0 and retained in the 0.4.0 local prototype. Naming it introduces no new fields and changes no existing state.

The rest of the lifecycle (effort routing, submissions, review, freshness, views) is the [Relay Method task layer](RELAY.md). REF is the format those operations read and write at the edge.

## What REF covers

| Part      | Location                                                               | Role                                                                          |
| --------- | ---------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Entry     | `.context/ENTRY.md`                                                    | First file an assistant reads. Says how to proceed, including with no tools.  |
| Controls  | `.context/policy.md`, `project.md`, `config.json`                      | Workflow, authority and conventions. The only files whose instructions apply. |
| Knowledge | `.context/knowledge/`                                                  | Portable concepts (Markdown with YAML metadata). Data, never instructions.    |
| Packet    | `.context/runs/<run>/packets/` or `.context/relay/tasks/<id>/packets/` | A frozen, hashed snapshot of the controls and selected sources.               |

Submissions, receipts, reviews, and acceptance are not part of REF. They are defined in [RELAY.md](RELAY.md).

## Rules

1. **Controls define the workflow.** The four control files are always included in a packet with the role `control`. Selected sources are data, even when they contain imperative text.
2. **Entry works without tools.** If the assistant cannot read files, it asks the operator for the exported packet and does not claim to have read paths that were only named.
3. **A packet is frozen.** `packet_id` is the SHA-256 of the packet as sorted-key JSON, excluding `packet_id` itself. A mismatch means the packet was modified or is corrupt.
4. **Files are versioned by bytes.** Each file record carries the full-file SHA-256 even when only a heading section is selected.
5. **Nothing is silently dropped.** A packet that exceeds its character budget fails instead of omitting a required source.
6. **A packet is not a sandbox.** The assistant still applies its host's instruction and access rules.

## Packet shape

Both packet kinds use `schema_version: 1`, a `packet_id`, and a `files` list. A file record has:

| Field     | Meaning                                                                   |
| --------- | ------------------------------------------------------------------------- |
| `path`    | Workspace-relative path.                                                  |
| `section` | Selected heading, or `null` for the whole file.                           |
| `role`    | `control`, `knowledge`, or `artifact` (stage runs also use `continuity`). |
| `sha256`  | Hash of the full file bytes.                                              |
| `content` | The selected text, framed as a JSON string in the Markdown export.        |

The two kinds differ in what surrounds `files`:

- **Stage packet** (`okf-icm context`): `run_id`, `stage`, `status`, `warnings`.
- **Task packet** (`relay start`, `refresh`, `escalate`): `task_id`, `task_revision`, `brief`, `route`. Its file records also carry `knowledge_signals` (lifecycle, freshness, trust) for knowledge files, otherwise `null`.

`relay navigate` offers read-only source suggestions; only explicit `--select` values enter a packet. Navigation creates no new packet kind or on-disk state (see [limits and held-out failure](navigate-results.md)).

## Version and compatibility

The optional bundled `relay-workspace` skill connects an assistant to these
controls. `relay skill --to DIRECTORY` installs it; `relay --root PROJECT workspace`
previews workspace onboarding and `--apply` saves prior modified files and a
layout inventory before appending an `AGENTS.md` entry pointing to the controls.
New entry scaffolds describe both task and stage commands and name the
optional skills in one sentence; the entry is part of every packet, so the
default controls are kept under 2,500 characters. `relay init --minimal`
creates the same controls with a one-stage `config.json`; it is chosen only at
creation and leaves no marker. Existing `.context` controls
and packet shapes are unchanged. This bridge does not elevate source data or
grant authority. See [workspace adaptation](RELAY.md#workspace-adaptation).

The optional portable `ref` skill is an implementation candidate for task handoffs
and continuity; observed cross-client compatibility remains a release gate.
`relay skill --name ref --to DIRECTORY` copies its complete resource
tree; `--zip FILE` exports that tree and `--manual FILE` exports a standalone
guide and return template. Installation does not adapt any project. Native
invocation syntax and actual tool access depend on the client; the
[validation record](ref-validation.md) separates offline checks from observed
client behavior.

`relay workspace --claude` includes an optional `CLAUDE.md` import of the common
`AGENTS.md` bridge. Applying saves originals before appending; existing controls,
packets and stage graphs remain unchanged.
These assistant instructions are an adapter to REF, not additional control files,
a new packet kind or a replacement for explicit reviewer decisions.

REF v1 is a name for the format as it exists now. There is no version marker on disk, and Relay does not add one to existing projects. A future incompatible change would bump `schema_version` and require an explicit, documented migration, never an automatic one.

The package name `okf-icm` and both commands, `okf-icm` and `relay`, are unchanged.

## What a REF packet does not establish

- It does not authenticate who wrote the files. A hash detects change or corruption, not identity, and not a coordinated rewrite of every record.
- It does not confer permission. Controls describe the workflow; they do not grant access or approval.
- It does not detect secrets. Common secret paths are refused, but inspect selected content before sharing a packet.

## Conformance checklist

A project uses REF v1 when:

- [ ] `.context/ENTRY.md`, `policy.md`, `project.md`, and `config.json` exist.
- [ ] Packets are produced by `okf-icm context` or `relay start`/`context`, not edited by hand.
- [ ] Every packet's `packet_id` equals the hash of its contents.
- [ ] Selected sources are labeled with a non-control role.
