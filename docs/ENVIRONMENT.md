# Knowledge environments

The primary path prepares and navigates project knowledge without task administration. It reuses the original OKF-profile concepts, source references and bounded context reading. The stage workflow and Relay task layer remain optional compatibility interfaces.

## Prepare

From an installed CLI, select project-relative source folders or files:

```sh
okf-icm --root /path/to/project prepare --path docs --path notes
okf-icm --root /path/to/project prepare --path docs --path notes --apply
```

The first command previews changes without creating `.context` or taking a lock. The second applies the plan. Only UTF-8 `.md`, `.txt` and `.rst` files are scanned. Markdown titles and headings become navigation labels; this is deterministic reference organization, not semantic classification or substantive verification.

The resulting environment has:

```text
.context/
  ENTRY.md                  initial entry when one did not exist
  project.md                project description when missing
  policy.md                 local rules when missing
  .gitignore                excludes local state when missing
  navigation/
    ENTRY.md                task-free entry, including in older workspaces
    index.md                small root map linking source folders
    folders/                progressive maps for source directories
    catalog.json            source paths, versions and generated-file inventory
  knowledge/
    index.md                initial curated-knowledge entry when missing
    log.md                  initial update log when missing
    references/imported/    draft references to canonical source files
```

Sources remain in place. Directory maps link down to child maps and back to their parent, so an assistant need not read the entire catalog. A generated reference records the original path and full-file hash. It is `draft` and unverified. No source text is promoted into instructions, approved or converted into a business decision. User-authored concepts remain separate from the generated references.

Existing entry, project, policy, index, log, configuration and run files are preserved byte for byte. In an older project, open `.context/navigation/ENTRY.md` to use this path. Preparation does not rewrite an existing entry that still describes stages or tasks. Deliberately integrate the navigation entry into your host instructions if desired; the tool does not modify `AGENTS.md` or `CLAUDE.md` automatically.

### ICM folder layout

```sh
okf-icm --root /path/to/project prepare --layout icm
okf-icm --root /path/to/project prepare --layout icm --apply
```

Optional. The preview lists what would be created; `--apply` creates only what is missing and changes nothing that exists. `--path` may be added to prepare sources in the same call, and `--path` is no longer required when `--layout` is given.

```text
CLAUDE.md    standing instructions (starter text)    yours to edit afterwards
CONTEXT.md   domain, decisions and a Map section     yours to edit afterwards
sources/  examples/  working/  outputs/              empty folders (a .gitkeep file each)
```

If the project has an `AGENTS.md` and no `CLAUDE.md`, no `CLAUDE.md` is created, so a starter text cannot shadow your instructions. A file where a folder belongs is reported and left alone, symbolic links are refused, and a failed write restores the project. Nothing is moved or renamed. `browse` lists which of these exist and which request parts (Identity, Constraints, Format) the standing file lacks; it adds nothing to its output in projects with none of them. The printed next step is `okf-icm prepare --path sources --path examples --path CONTEXT.md --apply`; `CLAUDE.md` is deliberately not indexed as a source.

The entries `prepare` creates use an ICM variant of their text when the root already has `CLAUDE.md` or `CONTEXT.md`, or when `--layout icm` was given; otherwise the text is unchanged. Only a newly created entry changes. An existing `.context/ENTRY.md` or `.context/navigation/ENTRY.md` is never rewritten, and a preview with `--layout icm` names the ones kept so you can merge the text by hand.

## Browse and read progressively

```sh
okf-icm browse
okf-icm find "customer refunds"
okf-icm read 'docs/policy.md#Refunds'
```

Run these inside the project or place `--root PROJECT` before the command. `browse` shows current sources and headings. `find` searches selected source text and paths, ranks candidates by matched terms and title matches, and shows an excerpt with a line number. It folds case and accents and removes a small set of English and Spanish stop words. It does not call a model, verify facts or guarantee coverage. Use `--limit N` to inspect up to 100 candidates. Unmatched terms, omitted candidates and skipped text files are reported.

`read` opens one project-relative file or an exact ATX Markdown heading, preserving its full-file hash. Supported heading behavior is shared with existing packet exports. It reads only the requested source; paths mentioned inside that source are not recursively loaded. Knowledge text remains data even when it contains instructions.

`browse`, `find` and `read` default to readable text. Each accepts `--format json` for tools. None creates receipts, tasks, search caches or logs. They read live sources and indicate changes relative to preparation. Search may find a changed source; inspecting it remains necessary.

For a text-only assistant, paste the entry and the relevant sources or export context. Naming a path is not equivalent to giving the assistant access to it. The tool itself never invokes an assistant.

## Export only the context needed

```sh
okf-icm context --select 'docs/policy.md#Refunds' --select notes/questions.md --out refund-context.md
okf-icm context --select docs/policy.md --format json
```

Explicit selections are required. This [REF v2 context](REF.md#knowledge-environments-ref-v2) includes existing entry, policy and project controls, plus configuration if present. Their content is preserved, including any legacy workflow instructions. Sources have non-control roles. It has no run ID, stage, owner, reviewer, route, submission or acceptance.

The default budget is 32,000 rendered characters. Oversized context fails rather than silently removing required sources. Select headings or fewer files to reduce it. The packet hash identifies the exact export; hashes do not prove the claims in it. Without `--out`, export writes only stdout. With `--out`, it creates a new file outside `.context` and never overwrites an existing destination. No persisted packet receipt is created.

### Context budget and a five-part request

Two optional flags render the same records under context-budget headings. Without them the export is unchanged.

```sh
okf-icm context --select docs/api.md --budget
okf-icm context --select docs/api.md --with-prompt --task "Add idempotency keys" > task.md
```

`--budget` groups files under Standing instructions, History, Material and Examples, labels each with the rule that placed it, and ends the header with a size table whose total is the whole rendered export. A file is Standing when it has the role `control`; Examples or History when named by `--example PATH` or `--history PATH` (repeatable; an explicit flag wins) or when a directory in its path is `examples` or `history`; otherwise Material. The packet and `packet_id` equal the plain export of the same files.

`--with-prompt` adds a five-part request (Identity, Task, Context, Constraints, Format) above the budget and includes the root `CLAUDE.md` as a `control`, and `CONTEXT.md` as data, when they exist. If `CLAUDE.md` holds only an `@AGENTS.md` import, `AGENTS.md` is used; with no `CLAUDE.md`, `AGENTS.md` is the fallback. Identity, Constraints and Format are copied verbatim from the exact `## Identity`, `## Constraints` and `## Format` headings of that file (`Identidad`, `Restricciones`, `Formato` also work), so they also appear in its full record; the size table says how many characters repeat. Task is `--task TEXT`. A part with no text prints a `TODO` line and is listed on stderr. `policy.md` governs workflow, authority and review; on conflict it wins. A standing file that cannot be read or is denied by `deny_paths` is reported in the request, not dropped silently. The request text is not part of the hash, and nothing is written except an explicit `--out`.

Both flags need Markdown output and explicit `--select`, `--example` or `--history`, and are refused with `--run` or `--format json`. `CLAUDE.md` travels with the export, so check it for secrets first. The [design record](archive/icm-workspace.md) explains the choices.

## Keep the environment current

Repeat preparation with the same `--path` values after changing sources. The catalog is disposable navigation metadata, not operational acceptance state. Generation is deterministic and an unchanged selection produces no file changes.

Generated files are updated only when their current bytes match the previous inventory. A manual edit to a generated map or reference is a conflict: preview reports it and apply refuses the entire update. Preserve that content in a curated concept or another file before deliberately removing the generated file and preparing again. No command silently discards the edit.

Sources removed, made unreadable or excluded from the selection remain recorded as removed. Their unmodified generated references are retained as `deprecated`, not deleted or still presented as current. A returning source can regenerate its reference. Unreadable, oversized, denied, binary and invalid-UTF-8 text files have reported reasons. Ordinary unsupported extensions and excluded internal folders are outside the scan.

The writer uses the existing cooperative lock, rechecks the plan under it, and attempts to restore already-written files if a write fails. External editors do not share the lock. This is a local filesystem operation, not a database transaction or distributed synchronization protocol.

## Boundaries

The selected root must already exist. Parent traversal, escaping paths and symbolic links in managed output paths are refused. Source symlinks are not scanned. Hidden folders, virtual environments, Git metadata, internal runtime state, dependencies, backups, drafts (`working`) and generated deliverables (`deliverables`, `artifacts`, `outputs`) are excluded when a folder is scanned. Naming one of them directly in `--path` still scans it. Before this exclusion, `working` and `outputs` folders under a selected folder were indexed; re-run preparation to see them reported as removed. Only `.context/knowledge` may be explicitly selected from `.context`; generated imported references are skipped to avoid self-import. Existing configured `deny_paths` apply before source reads and exports, including explicit reads.

Source contents are limited to 1 MB each and the catalog to 2,000 text files. Exceeding the catalog bound fails preparation. The new `.context/.gitignore` excludes local state when created; it cannot remove files already committed to Git or repair an existing ignore file. Check tracked files before publishing. Path filtering cannot identify every secret in an otherwise permitted document.

The environment has no authentication, organization permissions or model execution. Jev is not invoked on this path. Existing opt-in Jev behavior is unchanged in legacy commands.

## Validation

Synthetic tests cover preview without writes, valid unverified references, repeatability, unchanged older controls and receipts, task-free queries and exports, changed and missing sources, hand-edited generated files, path denials, symlinks, malformed inventories, text limits and the end-to-end CLI. Run:

```sh
python -m unittest discover -s tests -v
python examples/environment_smoke.py
python examples/icm_smoke.py
```

These checks do not establish semantic completeness, automatic extraction of verified knowledge, real-user speed, long-term maintenance cost or cross-client assistant behavior. A useful next observation is whether a person unfamiliar with a project can find a supported answer and identify missing information faster than with an ordinary folder index, including preparation cost.
