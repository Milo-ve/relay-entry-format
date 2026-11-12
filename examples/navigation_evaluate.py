"""Evaluate the frozen navigator without changing either synthetic fixture.

Usage: python examples/navigation_evaluate.py [--fixture navigation|navigation_heldout|both]
The held-out content/expected sets are evaluation-only: do not tune to this output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from okf_icm import navigation, settings  # noqa: E402
from okf_icm.storage import readable  # noqa: E402
from okf_icm.workspace import Workspace  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def evaluate(fixture):
    source = ROOT / "tests/fixtures" / fixture
    spec = json.loads((source / "goals.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="relay-navigate-eval-") as temp:
        root = Path(temp)
        shutil.copytree(source / "context", root / ".context")
        ws = Workspace(root)
        deny = settings.load(ws.home)["deny_paths"]
        universe = navigation._catalog(ws, deny)
        rows = []
        unchanged = {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}
        for goal in spec["goals"]:
            result = navigation.navigate(ws, goal["goal"], stage=goal.get("stage"))
            repeat = navigation.navigate(ws, goal["goal"], stage=goal.get("stage"))
            returned = {c["select"].partition("#")[0][len(navigation.BUNDLE) + 1:-3] for c in result["candidates"]}
            expected = {e.partition("#")[0] for e in goal["expected"]}
            hit = len(returned & expected)
            stop = set(spec["baselines"]["stopwords"])
            keywords = {word for word in re.findall("[a-z0-9]+", goal["goal"].lower()) if len(word) >= 4 and word not in stop}
            scores = {path: sum(word in item["raw"].lower() for word in keywords) for path, item in universe.items()}
            baseline_paths = sorted((path for path in scores if scores[path]), key=lambda path: (-scores[path], path))[:5]
            baseline = {path[len(navigation.BUNDLE) + 1:-3] for path in baseline_paths}
            baseline_hit = len(expected & baseline)
            silent = 0
            warned = set()
            for candidate in result["candidates"]:
                path = candidate["select"].partition("#")[0]
                if universe[path]["hazard"]:
                    if any(w["code"] == "signals" for w in candidate["warnings"]):
                        warned.add(path[len(navigation.BUNDLE) + 1:-3])
                    else:
                        silent += 1
            # Inspect the *entire* result, including omissions, for disallowed paths.
            output = json.dumps(result, ensure_ascii=False, sort_keys=True)
            leaks = []
            for path in (root / ".context/knowledge").rglob("*.md"):
                value = path.relative_to(root).as_posix()
                try:
                    settings.check_selection(ws.root, value, deny)
                    readable(ws.root, value)
                except (ValueError, OSError):
                    if value in output or path.relative_to(root / ".context/knowledge").as_posix() in output:
                        leaks.append(value)
            rows.append({"goal": goal["id"], "gap": bool(goal.get("gap")),
                         "precision": hit / len(returned) if returned else 0,
                         "recall": hit / len(expected) if expected else None,
                         "baseline_precision": baseline_hit / len(baseline) if baseline else 0,
                         "baseline_recall": baseline_hit / len(expected) if expected else None,
                         "raw_characters": sum(c["raw_characters"] for c in result["candidates"]),
                         "packet_characters": result["budget"]["used"], "returned": sorted(returned),
                         "selections": [c["select"] for c in result["candidates"]],
                         "missing": sorted(expected - returned), "silent_hazards": silent,
                         "must_warn_satisfied": set(goal.get("must_warn", [])) <= warned,
                         "explicit_gap": any(g["code"] == "no_coverage" for g in result["gaps"]),
                         "deterministic": result == repeat, "leaks": leaks})
        normal = [r for r in rows if not r["gap"]]
        gaps = [r for r in rows if r["gap"]]
        average = lambda key: sum(r[key] for r in normal) / len(normal)
        summary = {"precision": average("precision"), "recall": average("recall"),
                   "keyword_top5_precision": average("baseline_precision"), "keyword_top5_recall": average("baseline_recall"),
                   "mean_raw_characters": sum(r["raw_characters"] for r in rows) / len(rows),
                   "mean_packet_characters": sum(r["packet_characters"] for r in rows) / len(rows),
                   "select_everything_raw_characters": sum(len(i["raw"]) for i in universe.values()),
                   "silent_hazards": sum(r["silent_hazards"] for r in rows),
                   "must_warn_satisfied": all(r["must_warn_satisfied"] for r in rows),
                   "gap_goals_no_guess": all(not r["returned"] and r["explicit_gap"] for r in gaps),
                   "deterministic": all(r["deterministic"] for r in rows), "no_leaks": all(not r["leaks"] for r in rows),
                   "workspace_unchanged": unchanged == {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}}
        summary["acceptance_passed"] = (summary["precision"] > summary["keyword_top5_precision"]
                                        and summary["recall"] >= summary["keyword_top5_recall"]
                                        and summary["mean_raw_characters"] < summary["select_everything_raw_characters"]
                                        and summary["silent_hazards"] == 0
                                        and all(summary[k] for k in ("must_warn_satisfied", "gap_goals_no_guess", "deterministic", "no_leaks", "workspace_unchanged")))
        return {"summary": summary, "goals": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("navigation", "navigation_heldout", "both"), default="navigation")
    args = parser.parse_args()
    fixtures = ("navigation", "navigation_heldout") if args.fixture == "both" else (args.fixture,)
    fingerprint = hashlib.sha256((ROOT / "src/okf_icm/navigation.py").read_bytes()).hexdigest()
    out = {"navigator_sha256": fingerprint, "results": {name: evaluate(name) for name in fixtures}}
    print(json.dumps(out, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if all(r["summary"]["acceptance_passed"] for r in out["results"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
