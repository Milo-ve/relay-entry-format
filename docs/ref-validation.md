# REF skill validation record

Updated 2026-11-11 on one machine: macOS ARM64, Python 3.14.5, PyYAML 6.0.3.
The 0.4.0 implementation baseline is commit `60e0049`; the publication branch is
`publish/relay-0.4.0-prototype`. This page separates reproducible software checks
from observed client behavior. No client compatibility result is inferred from
the version number or from opening a pull request.

## Offline checks that were run

- The original `feat/phase-0-baseline` record reported 106 passing tests. The
  0.4.0 suite now has **241 passing tests**. Coverage includes complete bundled
  skill installation into a directory with spaces, refusal of differing existing
  resources, ZIP/manual export without overwrites, workspace preview/apply with
  backups, symlink boundaries, and refusal of incompatible workspaces.
- The suite also covers writer lock waiting, optional revision requirements,
  reassignment, recorded external review references, denied source paths, compact
  listings, minimal initialization, snapshot submissions, delivery cards, batch
  refresh, and English/Spanish views and catalogue parity.
- `python examples/smoke.py` and `python examples/relay_smoke.py` passed. They
  exercise the installed CLI's stage and task workflows without calling a model.
- `tests/test_skill_distribution.py` runs separate Python processes against one
  workspace and confirms shared task ID, packet ID and status, and refusal of a
  stale caller. This establishes continuity through files, not between assistants.
- `tests/test_compat.py` loads a frozen task written by earlier code and confirms
  its packet hashes, statuses and bytes survive read-only commands unchanged.
- The first publication CI run passed on Linux/macOS but exposed a Windows
  dangling-symlink export failure. Exclusive writes now explicitly refuse links;
  a storage regression test checks that neither the link nor its absent target is
  changed. CI outcomes are available on the PR alongside the local test record.

The shell has no bare `python` executable. The publication check uses the existing
virtual environment's Python with the publication worktree's absolute `src` path
on `PYTHONPATH`, so subprocesses in temporary workspaces use the code under review:

```sh
export PYTHONPATH="$PWD/src"
/path/to/venv/bin/python -m unittest discover -s tests -v
/path/to/venv/bin/python examples/smoke.py
/path/to/venv/bin/python examples/relay_smoke.py
```

The restricted sandbox prevents loopback socket binding in 13 existing HTTP
tests. The complete passing run uses local loopback access. These are synthetic
software checks, not live model results, user savings, substantive verification
of a real deliverable, or reviewer acceptance.

## Client inventory recorded earlier

The initial record found Claude Code 2.1.316 and Codex CLI 0.163.0 installed.
Their presence alone says nothing about skill discovery or invocation. No new
client discovery or cross-assistant observation was performed for publication.

## Observed gates still pending

| Gate | Evidence required before claiming compatibility | Status |
| --- | --- | --- |
| Client discovery and access | In clean sessions of both clients, observe the installed skill being found/invoked and record actual read/write/CLI access. | Not run |
| Claude → Codex continuity | Start in Claude, resume the same task in a fresh Codex session without chat history; check IDs, sources, hashes, evidence and review state. | Not run |
| Codex → Claude continuity | Repeat in the opposite direction with the same state guarantees. | Not run |
| Manual text-only handoff | Export a packet, obtain separate result/evidence text, and observe the operator recording its return against the correct current packet. | Not run |
| Instruction boundary | Observe an assistant handling a synthetic injected source as data, recording client/version/tools and behavior. | Not run |

An observed collaboration with a second human reviewer and a timing record is
also pending. No time-saving or broad prompt-injection-resistance claim follows
from the offline suite. Spanish wording remains without a recorded human language
review; library errors remain English as documented in [RELAY.md](RELAY.md#language).

## Publication boundary

The 0.4.0 code and bundled skill are being submitted for repository review as a
local prototype and implementation candidate. A PR is not a compatibility release.
Do not publish that release until the client discovery, bidirectional continuity,
manual handoff and instruction-boundary observations above have been recorded and
reviewed. Installation from the exact distributed artifacts must then be checked
in clean client environments, with complete references and no private state.

Navigation implementation and its synthetic evaluations are reviewed separately;
they do not satisfy these client gates. No MCP server is included.
