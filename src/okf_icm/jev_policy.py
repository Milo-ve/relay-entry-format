"""When Jev is worth calling. A deterministic rule whose every answer is recorded.

Rules come first: Jev is asked only where they leave a real question open, where the
workspace enabled that use, and where there is something to send. It adds a signal for a
person or raises effort; within one stated limit it may lower effort. It never grants
permission, accepts work, clears a prerequisite or skips review.
"""
from __future__ import annotations

import os

from .settings import JEV_USES

__all__ = ["JEV_USES", "mode", "decide", "skipped"]


def mode(flag: str | None, configured: dict) -> tuple[str, str]:
    """Effective mode (`off`, `shadow` or `route`) and what chose it (`flag` or `setting`).

    A flag given on the command always wins, including `off`.
    """
    if flag is not None:
        return flag, "flag"
    return {"off": "off", "shadow": "shadow", "auto": "route"}[configured["jev_mode"]], "setting"


def decide(use: str, configured: dict, *, flag: str | None = None, decisive: bool = False,
           shareable: bool = True, calls: int = 0) -> dict:
    """Should this use call Jev now? Returns the answer and a reason code to record.

    `decisive`: the rules already settled the question, so a call would buy nothing.
    `shareable`: there is content to judge that may leave the machine.
    `calls`: provider requests already made by this command.
    """
    if use not in JEV_USES:
        raise ValueError(f"Unknown Jev use: {use}")
    effective, trigger = mode(flag, configured)

    def answer(call: bool, reason: str) -> dict:
        return {"use": use, "call": call, "reason": reason, "mode": effective, "trigger": trigger}

    if effective == "off":
        return answer(False, "not-enabled")
    if trigger == "setting":
        if use not in configured["jev_uses"]:
            return answer(False, "use-not-enabled")
        if decisive:
            return answer(False, "rules-decisive")
    if not shareable:
        return answer(False, "nothing-shareable")
    if not os.environ.get("TYPESAFE_API_KEY"):
        return answer(False, "no-key")
    if calls >= configured["jev_max_calls"]:
        return answer(False, "budget-exhausted")
    return answer(True, "call")


def skipped(plan: dict) -> dict:
    """The record left on a task or report when the gate said no."""
    return {"mode": plan["mode"], "trigger": plan["trigger"], "use": plan["use"], "status": "skipped", "reason": plan["reason"]}
