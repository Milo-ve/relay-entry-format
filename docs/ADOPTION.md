# Adopting Relay

Practices for setting Relay up in a project and for choosing who sees what. They are recommendations, not requirements: nothing here is enforced by the software, and none of it is a measured saving in cost, time or quality. Claims that are deductions, or that nobody has checked, carry a mark:

- **[Inference]** deduced, not measured.
- **[Not verified]** not checked in this project.

Sizes quoted below were measured with synthetic fixtures (see [Verification limits](RELAY.md#verification-limits)). They show how large the tool's own output is, not what anyone saved.

## Keep the footprint small

- **One shared install, one `.context/` per project.** Install the tool once (see the [README](../README.md)) and run `relay --root PROJECT ...` against each project. Copying the tool into every project duplicates code, creates a nested repository, and means updating it N times.
- **Keep the controls under 2,500 characters in total.** `ENTRY.md`, `policy.md`, `project.md` and `config.json` are in every task packet, so every task pays for them. A default scaffold stays under that bound (a test enforces it); a project that adds to its controls should not add pointers most tasks never use. For task-only projects, `relay init --minimal` writes a one-stage `config.json` (see [Minimal workspace](RELAY.md#minimal-workspace)). Editing a control makes every task stale, which is why the controls should change rarely.
- **Select by heading, and keep one reviewable result per task.** `--select policy.md#Current` puts one section in the packet instead of the whole file. A task that returns one result is one decision for the reviewer.
- **Resume with `show` and `context`, not `list`.** `relay show ID` and `relay context ID` give an assistant what it needs for one task. Pasting the whole `list` output grows with every task: on seven synthetic tasks it was 10,685 characters, and `relay list --brief` was 1,144. Use `list --brief` to find a task, then `show`.
- **Do not compact the packet JSON.** The packet shape is frozen and its hashes depend on it; the saving was judged too small to justify the risk.

## Hand in copies, not live files

- **Submit dated copies.** A submission signs the files it names. If those files keep changing, the task keeps returning to `needs_review`. `relay submit --snapshot` validates the submission and then signs byte-for-byte copies under `deliverables/TASK/rREV/`, so later edits to the originals leave the submitted version alone. See [Result and acceptance](RELAY.md#result-and-acceptance).
- **For code tasks, deliver a patch or a report.** A file that is a selected source cannot also be the submitted output. Put the change in a separate file (a patch, or a report that lists the changed paths) and submit that.

## Keep conversations and tools lean

- **One task per conversation.** Start a fresh conversation for each task and bring in its packet, rather than carrying earlier tasks along.
- **Turn off what the project does not use.** **[Inference]** Plugins, skills and MCP servers load their descriptions into each turn, so unused ones cost context on every message. Their weight has not been measured here.
- **Match the model to the effort profile in the project policy.** For example a lighter model for `transform` and `draft` tasks, and the most capable one only for `investigative` tasks. The profile is a recommendation to the assistant; Relay does not enforce which model runs.
- **Measure before claiming an improvement.** Look at what occupies the context before and after a change, and say what you observed. **[Inference]** Open-ended reading of many files costs more than loading an ordinary packet, so the expense is in how much a task makes an assistant read, not in the method.

## Choose the interface for the audience

Do not put Relay in front of people who do not need it. A client or a non-technical colleague should receive the deliverable and a short card, not the method.

| Audience | Suggested surface | What it covers |
|---|---|---|
| Colleagues with some technical skill | A private Git repository, with one branch or pull request per task. | Attributable history and approval, using Git's own accounts. Relay's names stay self-recorded; `--actor` and `review --external-ref` only record who says they acted and where the approval lives. For the pilot rules (one writer per run, no automatic merging of conflicting receipts, everyone can read everything cloned) see the [proposal](archive/relay-product-proposal.md#phase-2-trusted-team-pilot). |
| Clients and non-technical colleagues | Their usual tool (comments in a shared document, or an issue tracker) plus the [delivery card](RELAY.md#delivery-card). Relay stays the evidence ledger: paste the `submission_id` and the hash into their tool. | Assignment, notifications and identity, which Relay does not provide. |
| Review with a platform identity | A private page on a platform the reviewer already signs in to. **[Not verified]** whether an external reviewer can open it without an account. It creates a second source of truth beside `.context`. | Sign-in, if the platform provides it. |
| A web platform with its own login and permissions | Only after one full cycle with a second human reviewer has been observed. | High effort. Not recommended before that evidence exists. |

- **Never expose `relay serve` to a network.** It listens on loopback and is for one trusted user. It has no sign-in and no per-user permissions; a tunnel or shared server would put an unauthenticated page in front of other people.
- **`review --external-ref` is a pointer, not a transfer.** It stores text that says where an approval was given. Whether an approval made elsewhere may be copied into Relay as a review is a project decision; the software records the reference and does not check it.
- **A card contains free text.** The goal, criteria, reported checks, open questions and review note appear on it. Read it before sending it outside the project.

## What this guide does not establish

No collaboration, cross-assistant handoff or time saving with real users has been observed; the [operational backcast](archive/relay-operational-backcast.md) lists the evidence still required. The practices above are a starting point to test, not a result.
