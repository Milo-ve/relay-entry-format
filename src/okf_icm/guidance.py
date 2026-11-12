"""Plain-language next steps for a task, derived only from its computed status.

Guidance is advice for the operator. It is never written into a packet, never
grants permission, and never changes a task's state. The text follows the `language`
setting (see i18n.py); the commands inside it keep their English words.
"""
from __future__ import annotations

from pathlib import Path
import shlex

from .i18n import translator

_MAX_LISTED = 5


def command_prefix(root: Path) -> str:
    """`relay`, plus `--root PATH` when the project is not the current directory."""
    try:
        here = root.resolve() == Path.cwd().resolve()
    except OSError:
        here = False
    return "relay" if here else f"relay --root {shlex.quote(str(root))}"


def listed(items: list[str], language: str | None = None) -> str:
    shown = ", ".join(items[:_MAX_LISTED])
    extra = len(items) - _MAX_LISTED
    return shown + (" " + translator(language)("guide.more", n=extra) if extra > 0 else "")


def _submit(relay: str, task: str) -> str:
    return f'`{relay} submit {task} --output RESULT --evidence EVIDENCE --checks "..." --next "..."`'


def next_step(status: dict, relay: str = "relay", language: str | None = None) -> str:
    t = translator(language)
    task, state = status["id"], status["status"]
    blockers = status.get("blockers") or []
    if state == "needs_review":
        text = t("guide.needs_review", changed=listed(status["changed"], language), relay=relay, task=task)
        if blockers:
            text += t("guide.also_open", blockers=listed(blockers, language))
        return text
    if state == "blocked":
        return t("guide.blocked", blockers=listed(blockers, language), relay=relay, task=task)
    if state == "ready":
        return t("guide.ready", relay=relay, task=task, submit=_submit(relay, task))
    if state == "awaiting_review":
        return t("guide.awaiting", reviewer=status["reviewer"], sid=status["submission"]["submission_id"], relay=relay, task=task)
    if state == "changes_requested":
        return t("guide.changes_requested", relay=relay, task=task, submit=_submit(relay, task))
    if state == "accepted":
        review = status["review"]
        reference = t("guide.reference", ref=review["external_ref"]) if review.get("external_ref") else ""
        return t("guide.accepted", actor=review["actor"], sid=review["submission_id"][:12], reference=reference)
    if state == "submitted":
        return t("guide.submitted")
    return ""


def stale_step(count: int, relay: str = "relay", language: str | None = None) -> str:
    """Advice after `list --stale`. Printed on stderr so the JSON list on stdout stays clean."""
    return translator(language)("guide.stale", count=count, relay=relay)


def batch_preview_step(has_tasks: bool, anything_found: bool, language: str | None = None) -> str:
    """The `next_step` of `refresh --all-stale` without --apply."""
    t = translator(language)
    if has_tasks:
        return t("guide.batch_apply")
    return t("guide.batch_nothing") if anything_found else t("guide.batch_none")


def after_context(task: str, relay: str = "relay", language: str | None = None) -> str:
    return translator(language)("guide.after_context", submit=_submit(relay, task))
