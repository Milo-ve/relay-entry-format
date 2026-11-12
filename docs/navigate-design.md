# Relay navigate: evaluation and proposal

**Status: initial implementation on this branch, experimental. Decision 3 accepted on 2026-11-11 (12,000 / 2,000, no per-type budgets, `--stage` in v1). Original synthetic acceptance passed; held-out gap acceptance failed. Ranking is frozen pending a new decision; see [the evaluation record](navigate-results.md). The proposal and repository snapshot below remain as historical design context.** Written on branch `feat/navigate-design`, stacked on `feat/phase-2-savings-and-practicality`. The original proposal changed no behaviour, REF, packets or existing state; the implementation now adds a read-only CLI operation.

Goal: today Relay freezes what a person selects and reports when it goes stale. That is verification. This asks whether Relay can also help find the smallest well-justified set of sources, by walking the structure that OKF and ICM already give it, without a model call.

## Repository state when this was written

| Item | Observed |
|---|---|
| Branches | `feat/phase-0-baseline` (11 commits ahead of `main`), `feat/phase-1-collaboration` (16), `feat/phase-2-savings-and-practicality` (21, last commit `88bb6b6`). Each stacked on the previous. |
| Phase 3 (R10 batch refresh, R9 Spanish UI, 0.4.0) | Not started: no commit mentions it on any branch, `grep` finds no `all-stale`, `--stale` or `language` setting in `src/`, version is still 0.3.0 and there are no tags. |
| Working tree | Clean, single worktree, no stash. |
| Other sessions | Other Claude sessions had this folder as their working directory while this was written. One received this same prompt, stopped at the sequencing gate and changed nothing. This work was done in a separate worktree so the shared one was not touched. |

## Part 1: Evaluation

### 1. What already exists for goal-to-sources navigation

Nothing that chooses sources from a goal. Evidence:

- **Selection is explicit and manual.** `relay start --select` (`relay_cli.py:42`, passed at `:180`), `okf-icm context --select` (`cli.py:49`, used at `packets.py:78-80`), and the web form ("Use paths relative to this project", `web.py:90`). `Tasks.start` stores the list (`tasks.py:127,140`); `files()` reads exactly that list (`tasks.py:88-114`) and `refresh` re-reads it (`tasks.py:117`).
- **The protocol says so.** "No recursive link traversal occurs" (`PROTOCOL.md:53`); sources are chosen with `--select path#Heading`.
- **The goal only drives effort.** `routing.route` reads the goal text to pick Direct, Standard or Investigative with one regex (`routing.py:28-30`). It never touches sources.
- **Jev works after selection.** It asks whether the already selected sources conflict (`jev.py:33-36`), and the task's selected non-control sources are what it is sent (`tasks.py:148`).
- **The only catalog is generated and unread.** `knowledge.reindex` writes `index.md` files with a title and description per concept (`knowledge.py:167-184`). `inspect_bundle` skips them (`knowledge.py:143`) and nothing parses them back. `add` does not reindex (`knowledge.py:198`), so the index lags new concepts.
- **The link graph is built for display only.** `viz.bundle_model` (`viz.py:62-84`) gives nodes and edges with lifecycle, trust and freshness. It feeds the map and table (`viz.py:149-162`), not selection.
- **Skills tell the assistant to choose by hand.** `ref/references/workflow.md:37-39`: "Choose sources explicitly... Do not select entire trees." The `relay-workspace` skill says nothing about finding sources. The scaffolded `ENTRY.md` routes to commands, not to knowledge (`scaffold.py:33-47`).
- **The method exists only as guidance, outside this repo.** `icm-architect` describes the librarian that walks the catalog (`SKILL.md:10`, walk test `:87-100`), and `references/forms.md:109` says "navigation is link-following, not folder-crawling". It builds workspaces; it is not a tool that finds sources for a goal. Its own warning (`forms.md:114`): a bundle read as a search index misses what it is for.
- No test exercises anything like navigation.

### 2. What a goal-driven walk can use

| Signal | Where | State today |
|---|---|---|
| Concept metadata: `type`, `status`, `tags`, `sources`, `description`, `title` | `knowledge.py:65-103` validates all but `description` | Available. **`inspect_bundle` drops `tags` and `description`** from its per-concept record (`knowledge.py:152-153`), so a walk must re-read the files. |
| Lifecycle, freshness, trust | `status`, `freshness()` (`:106`), `trust()` (`:112`) | Available and already the words packets use (`packets.py:100-101`). Freshness reads the clock, so it can change between two runs. |
| Relative links, with `#fragment` | `local_links` (`knowledge.py:127-134`) yields the full target | Fragments are ignored today (`viz.py:76-82`). Links to missing files are legal and only warned about (`:160-161`). |
| Section headings | `packets.section` selects by exact ATX title outside fences (`packets.py:13-38`) | **No function lists headings.** Duplicate titles: first match wins, and `PROTOCOL.md:55` says disambiguation is not implemented. |
| Generated `index.md` | `reindex` (`knowledge.py:167-184`) | Derived from the same metadata the concepts already hold, so it adds no information, and it can lag. |
| Stage contract inputs | `workspace.py:43-47` parses `id`, `needs`, `contract` only; `needs` outputs enter packets automatically (`packets.py:74-76`) | The `## Inputs` table is prose (`scaffold.py:64-72`) and **nothing parses it**. The default rows name no sources, so a default project gives no signal; a contract that names paths gives some. |
| `ENTRY.md`, `project.md` | `scaffold.py:33-47,59` | Free text. The default entry has no routing table. A custom one with links is a weak, optional signal. |
| Knowledge only | `.context/knowledge/` | Selection accepts any readable file (`tasks.py:88-114`); a walk by OKF structure only reaches the bundle. |

Two constraints found while testing, both measured on the fixture below:

- **The existing views leak what a navigator must hide.** On the fixture, `bundle_section`, `inspect_bundle` and the generated `index.md` files all name the denied `hr/` concepts and the sensitive `ops/.env-conventions.md` path (the latter as an error entry). `deny_paths` applies only when a path is selected (`tasks.py:95-96`, `packets.py:77-79`). A navigator therefore cannot reuse their output.
- **A hub link is noise.** In the fixture `glossary/terms` is linked from every one of the other 49 concepts. Following links without discounting hubs would pull it into every answer.

### 3. Where the path is chosen today, and by whom

By the operator, or the assistant acting for them, typing paths into `--select` or the web form. Relay then validates the choice and freezes it: `deny_paths` (`tasks.py:95-96`), sensitive paths and size (`storage.py:39-47`), concept validity (`tasks.py:103-110`), the character budget, default 32,000 (`relay_cli.py:51`, `tasks.py:157-161`), and later staleness (`tasks.py:182-190`). Relay checks that a choice is safe and current. It does not help make it.

### 4. Measurement on a synthetic knowledge base

**Fixture** (`tests/fixtures/navigation/`, fictional company, nothing real): 50 valid concepts plus one sensitive-path file; 48 of the 50 are permitted (two are under the denied `hr` folder), with 41,683 characters and 115 `##` sections. It contains 8 stale, 3 deprecated, 4 draft and 7 unverified concepts (13 concepts carry at least one of those flags), near-duplicates (current/2023/summary refund policies, retention policy/FAQ/privacy notice, export/old limits, onboarding/legacy), a hub (`glossary/terms`, in-degree 49) and other heavily linked concepts (`plan-tiers` 12, `refund-policy` 8, `data-retention` 8), an unresolved link (`chargeback-policy`), a generated index that lags two concepts, a denied folder (`hr`, via `deny_paths`), a note containing an injected instruction, and one stage contract that names its inputs.

**Goals:** 19, each with a hand-written expected set (33 expected items, 1 to 3 per goal), including 2 gap goals (no concept covers it; the only concepts are denied) and 1 goal whose only source is stale and must be returned flagged.

**Order of work, checkable in git:** expected sets and the exact baseline definitions were committed first (`47170dd`), before the knowledge base content existed. The knowledge base (`c782ee3`) and the script (`30ab651`) came after. `goals.json` has not changed since `47170dd`.

**Definitions** (frozen in `goals.json`): *select everything* is every permitted concept, whole files. *Keyword* tokenises the goal (tokens of 4+ characters, minus a fixed stopword list), matches by case-insensitive substring in the whole concept file, and scores by distinct matches; `keyword_any` takes every concept with a match, `keyword_top5` the five best. Precision and recall are at concept level, macro-averaged over the 17 non-gap goals. A hazard is a concept the existing code already warns about (`status != stable`, stale, or unverified); it is *silent* when the method says nothing about it.

**Results** (`python examples/navigation_baselines.py`):

| Method | Mean precision | Mean recall | Mean characters per goal | Hazard concepts returned, none flagged (19 goals) | Concepts returned on the 2 gap goals |
|---|---|---|---|---|---|
| Select everything | 0.040 | 1.000 | 41,683 | 247 | 96 |
| Keyword, any match | 0.106 | 1.000 | 19,562 | 104 | 3 |
| Keyword, top 5 | 0.318 | 0.853 | 4,850 | 9 | 3 |
| *Reference: the expected sets themselves, with sections* | 1.000 | 1.000 | 1,204 | | 0 |

Reading these:

- Select everything is 41,683 characters, **above the default 32,000 packet budget**, so `start` would refuse it. Keyword-any also exceeds 32,000 on three goals.
- The best baseline, keyword top 5, misses at least one expected source on 5 of the 17 goals (recall 0.853), and about 68% of what it returns is not in the expected set (precision 0.318).
- **No baseline can say a goal has no answer.** Both keyword variants returned something for both gap goals, and none flags a stale, deprecated or unverified concept.
- The reference row is a floor for this fixture, not a prediction: with sections it loads 1,204 characters per goal averaged over all 19 goals (about 2,100 with whole files).

**Limits of this measurement**

- One author wrote the knowledge base and the expected sets, so they are judgment calls and have not been reviewed by anyone else.
- The fixture is small and synthetic. It says nothing about real projects, real users or real savings.
- Whoever designs a navigator after reading these results has seen the test. The proposal below was written after the fixture existed, so any result on this fixture will be optimistic. See "Held-out set" below.
- No model ran. Nothing here measures answer quality.

## Part 2: Proposal

**`relay navigate GOAL [--stage ID] [--max-chars N] [--limit N]`**, read-only and deterministic, with no model call.

**Output** (JSON like the other commands; a stable code plus rendered text for each sentence):

| Field | Content |
|---|---|
| `candidates` | Ranked. Each has `select` (a ready `--select` value, `path` or `path#Exact Heading`), characters, and `why`: which tags, headings, title words, link (and its source concept) or contract led to it. |
| `warnings` | Per candidate, the same lifecycle, freshness and trust words the packet already uses (`packets.py:100-101`). |
| `left_out` | The next best candidates not selected, each with the reason: below the bar, over budget, a deprecated or unverified near-duplicate whose matched terms a stable concept already covers, or a hub link not supported by the goal. Bounded by `--limit`; the rest are counted. |
| `budget` | Characters used of `--max-chars` (default 12,000 for sources; the project controls are not counted and add roughly 2,400 to 2,900 characters). |
| `gaps` | Goal terms no permitted concept mentions, an overall "no concept covers this" when nothing reaches the bar, and links from selected concepts to concepts that do not exist but whose anchor matches the goal. |
| `notes` | A fixed sentence: candidates, not a complete or verified set; read them before selecting. |

**Walk, in order**

1. **Enumerate permitted concepts first.** Apply `deny_paths` to the spelled and resolved path (`settings.denied_by`, as `check_selection` does) and `storage.readable` before reading or parsing. A file that fails either is dropped from every later structure: seeds, link edges, hub counts, gaps and `left_out`. It is not named, not counted, and not shown as an error. A constant line says that excluded paths are never read or listed, whether or not any exist.
2. **Score seeds** from goal tokens against concept fields with fixed integer weights: tags and title highest, then description and headings, then body. Unicode-aware with accents folded; a goal in another language than the concepts finds nothing and falls to a gap rather than a guess.
3. **Add named sources.** With `--stage`, backticked paths in the contract's `## Inputs` section that resolve to permitted files are added first ("contract-named"); the same extraction on `ENTRY.md` and `project.md` is a weak signal ("entry-named"). Only paths are extracted; instruction-like text there is not followed.
4. **Follow links one hop** from strong seeds. A link to a concept linked from more than a fixed share of the bundle (a hub) is followed only when its anchor text or fragment matches the goal. A fragment narrows the candidate to that section.
5. **Apply lifecycle.** A deprecated, draft, stale or unverified concept ranks below stable ones and is returned, flagged, only if it matches a goal term that no stable candidate matches. That keeps a stale-but-only source (contact list) and drops a stale near-duplicate (summary of the old policy).
6. **Choose sections.** For each concept, the headings whose text matches better than the rest; the whole file when matches are spread or there are no headings. Emit exact titles, because `section()` needs them. A duplicate title falls back to the whole file with a note.
7. **Fill the budget** greedily by rank; the rest go to `left_out` with their size.

**It never** creates a task or any file, takes the writer lock, selects silently, grants permission, or says the set is complete. `.context` is byte-identical afterwards (a test will assert it). Output has no timestamp, keys are sorted, and ties break by path, so the same files give the same bytes; because freshness reads the clock, "same" means the same files at the same side of every `stale_after`.

**Interactions**

- **`deny_paths` and sensitive paths:** step 1. This is why it cannot reuse `inspect_bundle` or `bundle_model` output (see Part 1, section 2): it needs its own enumerator that takes the filter before reading, built from the existing `parse_concept`, `validate_meta`, `freshness`, `trust`, `local_links` and `section`. One new helper is needed beside `section` to list headings with the same fence rules, with a test that `section` accepts every title it returns.
- **Existing packet shape and state:** unchanged. The output is not a packet and is not stored. Selecting still goes through `start --select` and `tasks.files()`, so hashes, `packet_id` and the legacy fixture are unaffected. No on-disk marker records that navigate was used. REF's entry, controls and packet shape do not change; `docs/RELAY.md` gets the command row and `docs/REF.md` one sentence under source selection. The scaffolded `ENTRY.md` is left alone (every packet pays for it; the 2,500-character control budget).
- **Index:** read-only use. The walk enumerates concept files directly, and only reports "N concepts are not in the index" (names filtered by the deny rule).
- **Jev:** not in v1. If wanted later, `--jev rank` could reorder the deterministic candidates only. It could not add a concept, hide a warning or see anything step 1 removed.
- **Language (R9):** generated sentences are `(code, params)` pairs from the start. *If R9 lands first:* add each code to both catalogues and the placeholder-parity test covers it. *If after:* ship one English table keyed by the same codes and move it into the catalogue mechanically; the JSON schema does not change. Keys and codes stay English, as the plan already says for CLI JSON.

**Acceptance** is fixed in `goals.json` before any navigator exists: on non-gap goals recall at least keyword top 5 (0.853) and precision above it (0.318); mean characters below select everything; no silent hazard, and the stale-only goal returned flagged; both gap goals return an explicit gap and no guess; no denied or sensitive path anywhere in the output; byte-identical reruns. **If it does not beat keyword top 5, I report that and stop, without touching the fixture or expected sets.**

**Held-out set (recommended before any code is called a result).** Because the author of this proposal has seen the fixture, tune only on it and report on a second knowledge base and goal set written by someone else, or at least by a later session that does not see the algorithm, and frozen first. Without that, a pass here shows the code works on the cases it was designed against.

**What this does not claim:** real-world savings, better answers from any model, or that navigating replaces reviewing what the assistant actually read.

## Decisions needed

1. Order relative to Phase 3. My recommendation: finish Phase 3 first (R10 does not overlap; R9 then gives navigate its catalogue and parity test for free), then build navigate on its own branch stacked on Phase 3, with its own version number chosen by you. Navigate may fail its acceptance, and Phase 3 should not wait on that.
2. Who writes the held-out set.
3. Default `--max-chars` (12,000 proposed) and whether `--stage` ships in the first version.
