# Try Relay on a project

A 20-minute guide for a colleague trying Relay on a real folder for the first time. Relay does not call a model. It prepares a packet for the assistant you already use and records what comes back.

This is a single-user prototype that runs on your machine. Nothing is uploaded unless you turn on Jev, which is off by default.

## 1. Install (3 minutes)

Requires Python 3.11+ and Git.

```sh
git clone https://github.com/Milo-ve/relay-entry-format.git
cd relay-entry-format
python3 -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e .
relay --version
```

Confirm the install on synthetic data first:

```sh
python examples/relay_smoke.py
```

It should end with `PASS`. If not, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) and tell the author.

## 2. Pick a project (2 minutes)

Choose a folder where one small, real piece of work is coming up, such as a draft, a summary or a review of a document. Avoid anything with secrets: Relay copies the sources you select into a task snapshot inside the project.

Commit the folder or make a backup before you start. `workspace --apply` also backs up what it changes, under `.relay-backups/`.

## 3. Set up the workspace (3 minutes)

For an existing folder, preview first. This writes nothing:

```sh
relay --root ./my-project workspace
```

If the preview looks right:

```sh
relay --root ./my-project workspace --apply --name "My project"
```

For an empty folder use `relay init ./my-project --name "My project" --minimal` instead. Then open `.context/policy.md` and `.context/project.md` and write who decides what. Relay does not discover business authority, so an empty policy means the packet carries none.

## 4. Run one task (10 minutes)

```sh
relay --root ./my-project start first --goal "Summarise the open risks" \
  --accept "Every risk cites the file it came from" \
  --select path/to/source.md --kind draft \
  --owner you --reviewer colleague
relay --root ./my-project context first --out first-context.md
```

Paste `first-context.md` into your assistant (Claude, Codex, ChatGPT, anything). Save its answer and a separate file listing the checks that were really done. Put both files inside the project folder, outside `.context/` and not among the selected sources; `submit` reads them relative to `--root`:

```sh
relay --root ./my-project submit first --output first-result.md --evidence first-evidence.md \
  --checks "What I actually compared" --questions "What is still unclear" \
  --next "Who does what next"
relay --root ./my-project show first
```

A reviewer then accepts a specific version, using the `submission_id` printed by `show`:

```sh
relay --root ./my-project review first --submission ACTUAL_SUBMISSION_ID \
  --decision accept --actor colleague --note "Checked against the source"
```

Prefer a screen? `relay --root ./my-project serve` opens the same flow at <http://127.0.0.1:8765>.

Now edit the source file and run `relay --root ./my-project list`: the task shows `freshness: changed` and `needs_review`, because the acceptance covered only the old version. `relay refresh first --note "what changed"` takes a new snapshot and clears the submission and acceptance, keeping the history. That separation is the point of Relay.

## 5. Optional extras

- **Find sources for a goal:** `relay --root ./my-project navigate "your goal"`. It is experimental: it suggests sources, shows what it left out, and may refuse on a very small folder. Check the omissions before selecting. See [navigate-results.md](navigate-results.md) for what was measured.
- **Check for clutter:** `relay --root ./my-project tidy` reports duplicates, unlinked old files and broken links, and writes nothing. `tidy --apply --dry-run` shows the safe cleanups; `tidy --apply` runs them with a backup, and `tidy --undo latest` reverses them.
- **Skill for your assistant:** `relay skill --to <your assistant's skills directory>` installs `relay-workspace`; add `--name ref` for the handoff skill. See [ADOPTION.md](ADOPTION.md#install-the-assistant-skills).
- **Jev:** leave it off for a first trial. If you enable it, content it judges is sent to TypeSafe. See [JEV.md](JEV.md).

## What to tell the author

Short answers are enough:

1. Did the install and `workspace` preview work first time? Paste any refusal message.
2. Was the context packet smaller or larger than what you would normally paste? Roughly how many characters?
3. Did the assistant use the sources and boundaries correctly, or did you fix something by hand?
4. Did the stale and acceptance states match what you expected?
5. What did you have to read in the docs that should have been in the command output?

Please do not send private project files. Share the command, the message Relay gave, and a description.

## What this does not show

One person trying it on one task is an observation, not evidence of time or cost savings. Relay records self-attributed decisions on a local machine; it does not authenticate people or enforce organizational permissions. The Spanish interface (`language` setting) has not been reviewed by a native speaker.
