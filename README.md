# OKF + ICM knowledge environments

Organize a project's knowledge and give people and assistants a small entry point, a source map, and a way to read only what they need.

```text
Prepare the environment → Browse the map → Find and read sources → Reuse the knowledge
```

The main interface is `okf-icm`. It works locally with ordinary text files and the assistant you already use. Reading, searching and exporting knowledge context require no task, stage, submission or reviewer. No model API is required.

This recovery restores the original knowledge and context purpose while retaining the old stage and Relay commands for existing projects. It does not rewrite their state. The implemented knowledge-first path is described in [REF](docs/REF.md#knowledge-environments-ref-v2) and the [environment guide](docs/ENVIRONMENT.md).

## Getting started

Requires Python 3.11+. PyYAML is the only runtime dependency.

```sh
git clone https://github.com/Milo-ve/relay-entry-format.git
cd relay-entry-format
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`.

Select an existing folder containing Markdown, UTF-8 text or reStructuredText. Preview first, then apply:

```sh
okf-icm --root /path/to/project prepare --path docs
okf-icm --root /path/to/project prepare --path docs --apply
okf-icm --root /path/to/project browse
okf-icm --root /path/to/project find "refund policy"
okf-icm --root /path/to/project read 'docs/policy.md#Refunds'
```

Replace the example query, file and heading with your own. Open `.context/navigation/ENTRY.md` in your editor to follow the generated links. Repeat `--path` to include more folders. Use `--path .context/knowledge` to include an existing curated knowledge bundle.

Preparation keeps source files in place, generates a map and draft OKF-profile references, and preserves existing controls and stage graphs. It refuses to overwrite generated maps or references you edited by hand. It organizes references structurally; it does not automatically extract verified concepts or infer business decisions.

For optional portable context:

```sh
okf-icm --root /path/to/project context --select 'docs/policy.md#Refunds' --out policy-context.md
```

The export contains the controls, explicit selections and their full-file hashes. It creates no task or receipt. Review the selected content before sharing it with an assistant or another person.

## Keeping knowledge useful

Use `find` to locate candidates, `read` to inspect them, and their references to check claims. Search is lexical; a match does not prove that a document answers the question. Missing matches do not prove that information is absent.

Keep facts, interpretations and gaps distinct. Existing `knowledge add`, `validate`, `index` and `promote` commands remain available for curated concepts. Regenerate navigation with `prepare --path ... --apply` after source changes. Missing sources remain visible and generated references are retained as deprecated.

## Try the synthetic demo

```sh
python examples/environment_smoke.py
```

This temporary-folder example exercises preparation, search, section reading, task-free context, source updates and preservation. It calls no model. The older task demo is still available with `python examples/relay_demo.py ./relay-demo` and `relay --root ./relay-demo serve`; it is a compatibility workflow, not the default way to navigate knowledge.

## Existing projects

`okf-icm init` continues creating the legacy six-stage workspace. `context --run RUN`, checkpoints and the `relay` task commands retain their contracts. Existing assistant skills remain compatible with those workflows; `okf-icm adapter` exports a navigation-first entry snippet for deliberate integration into your assistant instructions.

No automatic graph migration, acceptance or on-disk v1 version marker is introduced. Historical features remain documented in the [stage protocol](docs/PROTOCOL.md) and [Relay reference](docs/RELAY.md).

## Limits and evidence

This is a local trusted-user implementation. It does not provide organization accounts, permission enforcement, managed compute or automatic content verification. Recognizable private paths and configured exclusions are filtered; that is not comprehensive secret detection.

The environment accepts text files up to 1 MB and at most 2,000 selected files. Binary documents need an explicit text extraction step outside the tool. Local `.context` data and exports must stay out of public Git history.

Synthetic tests establish software behavior, not user savings, semantic retrieval quality, cross-assistant compatibility or business results. See the [environment guide](docs/ENVIRONMENT.md#validation) for what is and is not checked.

## Development

```sh
python -m unittest discover -s tests -v
python examples/smoke.py
python examples/relay_smoke.py
python examples/environment_smoke.py
```

Start with [docs/INDEX.md](docs/INDEX.md) for focused documentation. The package remains `okf-icm`; the repository URL is retained for compatibility.

## License

MIT. See [LICENSE](LICENSE) and [ATTRIBUTION.md](ATTRIBUTION.md). The implementation does not claim official endorsement or full conformance to every OKF or ICM feature.
