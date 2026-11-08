"""Conservative, provider-neutral effort policy. Recommendations never grant permission."""
from __future__ import annotations

import re

from .storage import ContextError

POLICY_VERSION = "relay-effort-v1"
PROFILES = {
    "direct": {"reasoning": "low", "process": ["work", "check"], "max_escalations": 1},
    "standard": {"reasoning": "medium", "process": ["plan", "work", "check", "handoff"], "max_escalations": 1},
    "investigative": {"reasoning": "high", "process": ["investigate", "plan", "work", "validate", "handoff"], "max_escalations": 0},
    "clarify": {"reasoning": None, "process": ["resolve missing prerequisite"], "max_escalations": 0},
}
KINDS = ("auto", "transform", "draft", "diagnose", "design")


def route(goal: str, kind: str = "auto", risk: str = "standard", blockers: list[str] | None = None) -> dict:
    if kind not in KINDS or risk not in {"low", "standard", "high"}:
        raise ContextError("Unknown task kind or consequence level.")
    reasons = []
    if blockers:
        profile = "clarify"
        reasons.append("unresolved-prerequisite")
    elif risk == "high":
        profile = "investigative"
        reasons.append("consequential-task")
    elif kind in {"diagnose", "design"} or (kind == "auto" and re.search(
        r"\b(diagnos\w*|investigat\w*|architect\w*|contradict\w*|conflict\w*|root cause)\b", goal, re.I
    )):
        profile = "investigative"
        reasons.append("investigation-or-design")
    elif risk == "low" and kind == "transform":
        profile = "direct"
        reasons.append("explicit-bounded-low-consequence-transformation")
    else:
        profile = "standard"
        reasons.append("conservative-default")
    return {"policy_version": POLICY_VERSION, "profile": profile, "reason_codes": reasons,
            "settings": PROFILES[profile], "compute_enforcement": "advisory-external-assistant",
            "decision_source": "rules", "jev": {"mode": "off"}}


def apply_jev(decision: dict, observation: dict, mode: str) -> dict:
    """Only raise effort, never waive a blocker or required review."""
    decision["jev"] = {"mode": mode, **observation}
    if mode != "route" or observation.get("status") != "ok" or decision["profile"] == "clarify":
        return decision
    # This is an initial conservative policy threshold, not a calibrated error bound.
    signals = observation["signals"]
    if signals["conflict"] >= 0.7 or signals["approach"] in {"diagnose", "design"}:
        decision["profile"] = "investigative"
        decision["settings"] = PROFILES["investigative"]
        decision["reason_codes"].append("jev-investigation-signal")
        decision["decision_source"] = "rules-and-jev"
    return decision
