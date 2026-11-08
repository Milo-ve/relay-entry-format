# CLI reference

`--root PATH` goes before the command. Task paths are project-relative. `--out`
is relative to the shell working directory, may be outside the project and never
overwrites an existing file.

```bash
okf-icm init ./project --name "Example"
okf-icm --root ./project run start test-a --goal "Write a specification" --accept "Has testable criteria"
okf-icm --root ./project status --run test-a
okf-icm --root ./project context --run test-a --format json
```

## Context and checkpoints

```bash
okf-icm context --run test-a --stage 01-define --select 'notes.md#Requirements' --out define-packet.md
# Write the actual report first, then use the exported packet ID:
okf-icm run checkpoint --run test-a --stage 01-define --packet PACKET_ID --output .context/runs/test-a/outputs/01-define/scope.md
okf-icm run skip --run test-a --stage 02-research --reason "Operator supplied complete authoritative source"
# The default validation stage requires evidence:
okf-icm run checkpoint --run test-a --stage 05-validate --packet PACKET_ID --output validation-report.md --evidence observed-results.txt
okf-icm verify --run test-a
okf-icm run handoff --run test-a --file next-session.md
```

Repeat `--select`, `--output` and `--evidence` as needed. Declare edited selected
sources as outputs. The tool calculates real hashes and IDs.

## Knowledge

```bash
okf-icm knowledge add decisions/local-first --title "Use local files" --type Decision --body decision-body.md --source 'https://example.org/design'
okf-icm knowledge validate
# Only after checking content against evidence:
okf-icm knowledge promote decisions/local-first --evidence review-evidence.md --reviewer process:design-review --note "Compared decision with requirements" --confirmed-content
okf-icm knowledge index
okf-icm knowledge list
```

Index regeneration is explicit and preserves concept bodies. The reserved log
may be maintained manually. Promotion preserves evidence inside the bundle even
if the originating run is archived.

## Entry snippets

```bash
okf-icm adapter --kind generic
okf-icm adapter --kind agents --out AGENTS.snippet.md
okf-icm adapter --kind claude --out CLAUDE.snippet.md
```

Merge snippets deliberately. No command assumes automatic loading of Markdown
by a harness or silently changes existing harness instructions.
