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


def apply_jev(decision: dict, observation: dict, mode: str, *, may_lower: bool = False) -> dict:
    """Record the judgment. In route mode it may raise effort; it never waives a blocker or required review.

    `may_lower` is set by the caller only when the workspace enabled automatic use and the
    operator declared the task low-consequence without naming its kind. Then, and only from
    the conservative default, a confident "bounded transformation" may select Direct.
    """
    decision["jev"] = {"mode": mode, **observation}
    if observation.get("status") != "ok":
        return decision
    # These are initial conservative policy thresholds, not calibrated error bounds.
    signals = observation["signals"]
    if signals.get("source_instructions", 0) >= 0.7:
        # A warning for the person and assistant. It changes no route and permits nothing.
        decision["jev"]["flags"] = ["source-instructions"]
    if mode != "route" or decision["profile"] == "clarify":
        return decision
    if signals["conflict"] >= 0.7 or signals["approach"] in {"diagnose", "design"}:
        decision["profile"] = "investigative"
        decision["settings"] = PROFILES["investigative"]
        decision["reason_codes"].append("jev-investigation-signal")
        decision["decision_source"] = "rules-and-jev"
    elif (may_lower and decision["reason_codes"] == ["conservative-default"] and signals["approach"] == "transform"
          and signals["probabilities"]["transform"] >= 0.8 and signals["conflict"] <= 0.3
          and "flags" not in decision["jev"]):
        decision["profile"] = "direct"
        decision["settings"] = PROFILES["direct"]
        decision["reason_codes"].append("jev-bounded-transformation")
        decision["decision_source"] = "rules-and-jev"
    return decision
