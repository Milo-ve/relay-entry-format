# REF skill validation record

Recorded 2026-11-11 on one machine: macOS ARM64, Python 3.14.5, branch
`feat/phase-0-baseline`. This page separates what was run from what was not.
It is updated only when someone observes something new.

## Offline checks that were run

- `python -m unittest discover -s tests -v`: 106 tests passed. They include
  complete install of the bundled skills into a directory with spaces, refusal of
  differing existing skill contents, ZIP and manual export that never overwrite,
  workspace preview/apply with backups, and refusal of symlinks and incompatible
  workspaces.
- `python examples/smoke.py` and `python examples/relay_smoke.py` passed. Neither
  calls a model.
- `tests/test_skill_distribution.py` runs separate Python processes against one
  workspace and confirms they share the task ID, packet ID and status, and that a
  stale caller is refused. This shows continuity through files. It does not show
  continuity between two assistants.
- `tests/test_compat.py` loads a frozen task written by earlier code and confirms
  its packet hashes, statuses and bytes are unchanged by read-only commands.

## Client versions found on this machine

Claude Code 2.1.316 and Codex CLI 0.163.0 are installed. Their presence says
nothing about how either one discovers or uses the skills.

## Not run

- **Client discovery.** Neither client was started to check that it lists, loads
  or invokes the installed `ref` skill, or which invocation syntax it accepts.
- **Cross-assistant continuity.** No task was started in one assistant and resumed
  in another.
- **Tool access.** Nobody observed what an assistant could read, write or run
  with these instructions loaded.
- **Prompt injection.** No assistant was given a source containing an injected
  instruction to see whether it treated the source as data.
- **Publication.** The skills were not published or distributed outside this
  repository. No MCP server exists.

Until those are observed, the README and REF describe the `ref` skill as an
implementation candidate and make no claim of parity between clients.
