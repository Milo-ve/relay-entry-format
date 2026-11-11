"""Plain-language next steps for a task, derived only from its computed status.

Guidance is advice for the operator. It is never written into a packet, never
grants permission, and never changes a task's state.
"""
from __future__ import annotations

from pathlib import Path
import shlex

_MAX_LISTED = 5


def command_prefix(root: Path) -> str:
    """`relay`, plus `--root PATH` when the project is not the current directory."""
    try:
        here = root.resolve() == Path.cwd().resolve()
    except OSError:
        here = False
    return "relay" if here else f"relay --root {shlex.quote(str(root))}"


def listed(items: list[str]) -> str:
    shown = ", ".join(items[:_MAX_LISTED])
    extra = len(items) - _MAX_LISTED
    return shown + (f" (+{extra} more)" if extra > 0 else "")


def _submit(relay: str, task: str) -> str:
    return f'`{relay} submit {task} --output RESULT --evidence EVIDENCE --checks "..." --next "..."`'


def next_step(status: dict, relay: str = "relay") -> str:
    task, state = status["id"], status["status"]
    blockers = status.get("blockers") or []
    if state == "needs_review":
        text = (f"Changed since the snapshot: {listed(status['changed'])}. "
                f'Run `{relay} refresh {task} --note "what changed"` to take a new snapshot. '
                "That clears the current submission and acceptance and keeps the history. "
                "Then reassess the work the change affects.")
        if blockers:
            text += f" Prerequisites are also still open: {listed(blockers)}."
        return text
    if state == "blocked":
        return (f"Open prerequisites: {listed(blockers)}. Resolve them outside Relay, then run "
                f'`{relay} refresh {task} --resolve --note "what was resolved"`. '
                "--resolve records that you resolved them; Relay does not check.")
    if state == "ready":
        return (f"Export the packet with `{relay} context {task} --out {task}-context.md` and work in your assistant. "
                "Save the result and the checks you actually ran as separate files, then run "
                f"{_submit(relay, task)}.")
    if state == "awaiting_review":
        reviewer, sid = status["reviewer"], status["submission"]["submission_id"]
        return (f"Waiting for {reviewer} to review this exact version: "
                f'`{relay} review {task} --submission {sid} --decision accept|request_changes --actor {reviewer} --note "..."`. '
                "Editing the result, the evidence or a source before then returns the task to needs_review.")
    if state == "changes_requested":
        return ("Changes were requested; read the review note in this output. Revise the result and evidence, "
                f'then run `{relay} refresh {task} --note "what you revised"` (editing the files changes the submitted version) '
                f"and {_submit(relay, task)} again.")
    if state == "accepted":
        review = status["review"]
        reference = f" Reference: {review['external_ref']} (recorded, not verified)." if review.get("external_ref") else ""
        return (f"Accepted by {review['actor']} (self-recorded) for submission {review['submission_id'][:12]}.{reference} "
                "The acceptance covers only this version: if a source, the result or the evidence changes, the task returns to needs_review. "
                "Folding the result into a canonical source is a separate step that Relay does not perform.")
    if state == "submitted":
        return "Submitted. This task does not require review, so nothing here records acceptance."
    return ""


def after_context(task: str, relay: str = "relay") -> str:
    return ("Packet exported. Work in your assistant. Save the result and the checks you actually ran as separate files, "
            "outside .context and not among the selected inputs, then run " + _submit(relay, task) + ".")
