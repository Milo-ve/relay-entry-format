"""Measure the two navigation baselines on the synthetic fixture, exactly as defined in goals.json.

Read-only: it copies the fixture to a temporary folder and never writes inside the repository.
It makes no model call. Usage: python examples/navigation_baselines.py [--json]
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from okf_icm import knowledge, settings  # noqa: E402
from okf_icm.packets import section  # noqa: E402
from okf_icm.workspace import Workspace  # noqa: E402

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "navigation"
DEFAULT_BUDGET = 32000  # tasks.start max_chars default


def load():
    temp = Path(tempfile.mkdtemp(prefix="nav-baseline-"))
    shutil.copytree(FIXTURE / "context", temp / ".context")
    ws = Workspace(temp)
    report = knowledge.inspect_bundle(ws)
    deny = settings.load(ws.home)["deny_paths"]
    universe, denied = {}, []
    for concept in report["concepts"]:
        spelled = f".context/knowledge/{concept['id']}.md"
        if settings.denied_by(deny, spelled):
            denied.append(concept["id"])
            continue
        text = (ws.root / spelled).read_text(encoding="utf-8")
        hazard = concept["status"] != "stable" or concept["freshness"] == "stale" or concept["trust"] == "unverified"
        universe[concept["id"]] = {"text": text, "hazard": hazard, **concept}
    return temp, ws, universe, denied, report


def keywords(goal: str, stopwords: set[str]) -> list[str]:
    return sorted({t for t in re.findall(r"[a-z0-9]+", goal.lower()) if len(t) >= 4 and t not in stopwords})


def keyword_scores(goal: str, universe: dict, stopwords: set[str]) -> dict[str, int]:
    words = keywords(goal, stopwords)
    lowered = {cid: item["text"].lower() for cid, item in universe.items()}
    return {cid: sum(1 for w in words if w in text) for cid, text in lowered.items()}


def loaded_chars(selection: list[str], universe: dict) -> int:
    total = 0
    for item in selection:
        cid, _, slug = item.partition("#")
        text = universe[cid]["text"]
        if slug:
            title = next(h[3:].strip() for h in text.splitlines() if h.startswith("## ") and h[3:].strip().lower().replace(" ", "-") == slug)
            text = section(text, title)
        total += len(text)
    return total


def score(returned: set[str], expected: set[str]):
    hit = len(returned & expected)
    return (hit / len(returned) if returned else 0.0), (hit / len(expected) if expected else None)


def evaluate(name: str, picks: dict[str, list[str]], goals: list[dict], universe: dict) -> dict:
    rows, gap_rows = [], []
    for goal in goals:
        selection = picks[goal["id"]]  # "id" loads the whole file, "id#slug" only that section
        returned = list(dict.fromkeys(item.partition("#")[0] for item in selection))
        expected = {e.partition("#")[0] for e in goal["expected"]}
        hazards = [c for c in returned if universe[c]["hazard"]]
        chars = loaded_chars(selection, universe)
        if goal.get("gap"):
            gap_rows.append({"goal": goal["id"], "returned": len(returned), "chars": chars, "silent_hazards": len(hazards),
                             "said_gap": False})
            continue
        precision, recall = score(set(returned), expected)
        rows.append({"goal": goal["id"], "returned": len(returned), "precision": precision, "recall": recall, "chars": chars,
                     "silent_hazards": len(hazards), "must_warn_returned": all(m in returned for m in goal.get("must_warn", []))})
    n = len(rows)
    return {"method": name, "goals": rows, "gap_goals": gap_rows,
            "mean_precision": sum(r["precision"] for r in rows) / n, "mean_recall": sum(r["recall"] for r in rows) / n,
            "mean_chars_all_goals": (sum(r["chars"] for r in rows) + sum(r["chars"] for r in gap_rows)) / (n + len(gap_rows)),
            "silent_hazards_total": sum(r["silent_hazards"] for r in rows) + sum(r["silent_hazards"] for r in gap_rows),
            "returned_for_gap_goals": sum(r["returned"] for r in gap_rows)}


def main() -> int:
    spec = json.loads((FIXTURE / "goals.json").read_text(encoding="utf-8"))
    goals, stop = spec["goals"], set(spec["baselines"]["stopwords"])
    temp, ws, universe, denied, report = load()
    try:
        everything = sorted(universe)
        picks = {"select_everything": {g["id"]: everything for g in goals}, "keyword_any": {}, "keyword_top5": {}}
        for g in goals:
            scores = keyword_scores(g["goal"], universe, stop)
            hits = sorted((cid for cid, s in scores.items() if s >= 1), key=lambda c: (-scores[c], c))
            picks["keyword_any"][g["id"]] = hits
            picks["keyword_top5"][g["id"]] = hits[:5]
        # Reference only, not a method: the expected sets themselves.
        picks["expected_reference"] = {g["id"]: list(g["expected"]) for g in goals}
        results = {name: evaluate(name, p, goals, universe) for name, p in picks.items()}
        whole = sum(len(i["text"]) for i in universe.values())
        out = {"universe_concepts": len(universe), "denied_concepts_excluded": len(denied), "invalid_or_sensitive_excluded": len(report["errors"]),
               "universe_chars": whole, "default_budget": DEFAULT_BUDGET, "hazard_concepts_in_universe": sum(1 for i in universe.values() if i["hazard"]),
               "results": results}
        if "--json" in sys.argv:
            print(json.dumps(out, indent=2))
            return 0
        print(f"Permitted universe: {len(universe)} concepts, {whole} characters "
              f"({len(denied)} denied and {len(report['errors'])} sensitive/invalid excluded). Default packet budget: {DEFAULT_BUDGET}.")
        print(f"Hazard concepts (deprecated, draft, stale or unverified) in the universe: {out['hazard_concepts_in_universe']}\n")
        print("| method | mean precision | mean recall | mean chars/goal | silent hazards (all goals) | returned on 2 gap goals |")
        print("|---|---|---|---|---|---|")
        for name, r in results.items():
            print(f"| {name} | {r['mean_precision']:.3f} | {r['mean_recall']:.3f} | {r['mean_chars_all_goals']:.0f} | {r['silent_hazards_total']} | {r['returned_for_gap_goals']} |")
        for name in ("keyword_any", "keyword_top5"):
            print(f"\n{name}, per goal:\n\n| goal | returned | precision | recall | chars | hazards |\n|---|---|---|---|---|---|")
            for r in results[name]["goals"]:
                print(f"| {r['goal']} | {r['returned']} | {r['precision']:.2f} | {r['recall']:.2f} | {r['chars']} | {r['silent_hazards']} |")
            for r in results[name]["gap_goals"]:
                print(f"| {r['goal']} (gap) | {r['returned']} | n/a | n/a | {r['chars']} | {r['silent_hazards']} |")
        return 0
    finally:
        shutil.rmtree(temp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
