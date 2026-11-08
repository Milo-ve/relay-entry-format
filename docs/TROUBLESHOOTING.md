# Troubleshooting

Relay does not guess. When a command cannot proceed on what is recorded, it says so and stops. The state is the folder, so whatever a refusal depends on can be read: `.context/relay/tasks/TASK/state.json` and the files the task points at.

A task tracks three things separately: progress (what has been returned), currency (whether anything the work depends on has changed) and acceptance (which exact version a reviewer accepted). Nearly every refusal means one of the three is out of date. Find which one, bring that one up to date, and leave the other two as they are.

## Reading a task

```sh
relay show TASK        # status, what changed, and a plain-language next_step
```

`next_step` is advice for the operator. It is not written into packets and it grants no permission. When a command is refused because inputs changed or prerequisites are open, the CLI prints the same advice after the error. Put `--root PROJECT` before the operation when you are not inside the project folder.

| `status`            | What it tells you                                                     | Next command                                                                 |
| ------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `ready`             | Snapshot is current; nothing returned yet                             | `relay context TASK --out FILE`, work in your assistant, then `relay submit` |
| `awaiting_review`   | Work returned; no decision on this version                            | The assigned reviewer runs `relay review` with the current `submission_id`   |
| `changes_requested` | The reviewer asked for changes                                        | Revise, then `relay refresh`, then `relay submit` again                      |
| `accepted`          | The reviewer accepted this exact version                              | None. Folding the result into a canonical source is a separate step          |
| `needs_review`      | A source, control, result or evidence file changed after the snapshot | `relay refresh TASK --note "what changed"`, then reassess the work           |
| `blocked`           | A prerequisite was recorded as open                                   | Resolve it, then `relay refresh TASK --resolve --note "..."`                 |

## Questions, by command

### Why can't I start the task?

Nothing is created when `start` fails.

**`Task exists. Choose another ID; existing work is never overwritten.`**
Task IDs are never reused. Pick a new one.

**`IDs must contain 1-80 lowercase letters, digits or hyphens.`**
Rename the task, for example `pricing-faq`.

**`Sensitive/internal path is not exportable: PATH`**
Paths under `.git`, `.ssh`, `.aws`, `.venv`, or starting with `.env`, are never selected, so nothing from them is sent or snapshotted. Copy the content you need, minus the secrets, into a file you have reviewed, and select that.

**`[Errno 2] No such file or directory: PATH`**
A `--select` path does not exist. Paths are relative to the project root, which is `--root`. Check the spelling and the root. The same message appears when a `--output` path given to `submit` does not exist.

**`Markdown heading not found: NAME`**
`path#Heading` must match a heading in the file exactly. Copy the heading text from the file.

**`Context needs N characters; budget is M. Nothing was silently omitted.`**
The selected sources do not fit in the packet, and Relay will not drop part of one. Select fewer files or narrower headings, or raise `--max-chars` on purpose.

### Why can't I export the context?

`relay context` exports only a packet that matches what is on disk and has no open prerequisites. The message names the cause.

**`Cannot export context. Changed since the snapshot: FILES. Refresh the context first.`**
A selected source, a control file, or a submitted result or evidence file no longer matches its recorded hash. Run `relay refresh TASK --note "what changed"`, then export again. The current submission and acceptance are cleared. Earlier packets, receipts and review events stay as history.

**`Cannot export context. Open prerequisites: .... Resolve them, then refresh with the resolved flag.`**
A `--blocker` was recorded at `start`. Resolve it outside Relay, then run `relay refresh TASK --resolve --note "..."`. The flag records that you resolved it. Relay does not check.

### Why can't I submit?

**`Inputs changed or prerequisites unresolved. Refresh or resolve before submitting.`**
The same two causes as above, so refresh first. This is also what you see after a reviewer asks for changes and you edit the result or evidence: editing changes the version that was submitted. Refresh, then run `relay submit` again.

**`Write results/evidence to separate non-control files; do not overwrite task inputs.`**
A result or evidence path is one of the selected inputs, or is under `.context`. Save the deliverable and its evidence as new files elsewhere in the project and submit those paths. The inputs stay untouched.

### Why can't I record a review?

**`Actor must match the assigned reviewer. This is a local assertion, not authenticated identity.`**
`--actor` differs from the reviewer set at `start`. Use the assigned name. There is no command to change reviewers; start a new task if the reviewer must change.

**`Review must identify the current submission and a valid decision.`**
The `--submission` value is not the current `submission_id`, for example after a resubmit. Copy it from `relay show TASK`. The earlier receipt remains under `submissions/`.

Once a version is accepted, editing its result, its evidence or a source returns the task to `needs_review`, and the earlier acceptance no longer applies to what is on disk.

### Why can't I refresh or escalate?

**`Escalation unavailable. Reassess scope or resolve the missing prerequisite.`**
A task allows one escalation, to Investigative. Either it is already used, or the route is Clarify or Investigative. Reassess the scope, or start a new task with the right route.

### Why does any command stop?

**`Task changed. Reload its current version before submitting this action.`**
`--expected-revision` is older than the task, so another action ran first. Run `relay show TASK` and repeat the action if it still applies. Nothing was overwritten.

**`Workspace writer is busy (write.lock).`**
Another Relay command or `relay serve` holds the lock, or a crashed one left it. See [A stuck lock](#a-stuck-lock).

**`Task packet is modified or corrupt.`**
A packet no longer matches its hash. See [A corrupt packet](#a-corrupt-packet).

## A stuck lock

`.context/write.lock` holds the PID and time of the writer. Remove it only after you have confirmed that no `relay` process and no `relay serve` is running. Packet creation and the state update are not a single transaction, so after a crash, run `relay show TASK` for the task that was being written before you continue. Do not delete the lock to get past a command that is still running.

## A corrupt packet

Packets and submission receipts under `.context/relay/tasks/TASK/` are checked against their hashes. If one fails:

1. Do not edit it to make the hash pass, and do not delete it. A hash detects change. It does not tell you who changed it or why.
2. Restore the file from version control or a backup. If the file is intact and the hash fails, the change is the finding. Decide whether to trust the task.
3. If no good copy exists, keep the folder as a record and start a new task with a new ID.

While any one task is unreadable, `relay list` stops with this error. `relay show` on the other task IDs still works, and `relay export-html` lists the unreadable task as an error instead of omitting it.

## In the browser interface

| You see                                                                  | What to do                                                                                                                         |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `Form expired or invalid. Reload the page.`                              | The page is older than the running server, for example after a restart. Reload and submit again.                                   |
| `Request origin not allowed.`                                            | Open the interface at `http://127.0.0.1:PORT` itself. Do not use a proxy, a tunnel or another host name.                           |
| `Task changed...`                                                        | Someone else acted on the task after the page loaded. Reload to see the current version.                                           |
| `Result path exists. Use CLI with new output paths or refresh the task.` | The browser form writes versioned deliverables and will not overwrite one. Refresh the task, or use `relay submit` with new paths. |

## If Jev is unavailable

Jev is optional. On any failure, such as a missing `TYPESAFE_API_KEY`, a timeout or a rejected response, Relay keeps the rules-only route and records the reason in the route (`relay show TASK`, under `route.jev`). Nothing is retried and nothing blocks. Start the task without `--jev` if you do not want the provider call.

## What the record can and cannot vouch for

The task folder is Relay's record of the work. Hashes show that a packet or receipt changed. They do not show who changed it, so a task moves forward only through `relay` commands. Editing `state.json`, a packet or a receipt by hand produces a record that no longer means what it says.

Some entries are statements made by the operator, and Relay stores them as given. `--resolve` says a prerequisite was resolved. The checks text and the evidence file say what was checked. The reviewer name says who reviewed. Relay confirms that the files exist and which version they are. It does not confirm that the checks were run, so an evidence file should describe only checks that were.

`relay serve` is for one trusted user on loopback. To let someone else see a task, share the project folder or an `export-html` snapshot. A tunnel or shared server would put a page with no authentication in front of other people.
