"""Measure source sizes for choosing navigate budgets, on both navigation fixtures.

Read-only: copies each fixture to a temporary folder and never writes inside the repository.
It makes no model call and runs no navigator. It reads each goals.json `expected` list only (never
baselines, metrics or any precision/recall). "framed" is the number of characters a selection adds
to a real rendered Relay packet (the unit `start --max-chars` already counts).
Usage: python examples/navigation_sizes.py
"""
from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from okf_icm import knowledge, settings  # noqa: E402
from okf_icm.packets import section  # noqa: E402
from okf_icm.tasks import Tasks  # noqa: E402
from okf_icm.workspace import Workspace  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
STATE = dict(id="t", revision=1, goal="g", kind="auto", risk="standard", blockers=[], acceptance=["a"], owner="o",
             reviewer="r", review_required=True, boundaries="b", jev_mode="off", escalations=0, selections=[])


def pct(values, p):
    values = sorted(values)
    k = (len(values) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(values) - 1)
    return round(values[lo] + (values[hi] - values[lo]) * (k - lo))


def headings(text):
    """Heading titles outside code fences, by the same rule as packets.section."""
    titles, fence = [], None
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("```", "~~~")):
            marker = stripped[:3]
            fence = marker if fence is None else (None if fence == marker else fence)
            continue
        match = None if fence else re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line.rstrip())
        if match:
            titles.append(match[2])
    return titles


def measure(name):
    fixture = FIXTURES / name
    temp = Path(tempfile.mkdtemp(prefix="nav-sizes-"))
    shutil.copytree(fixture / "context", temp / ".context")
    ws, tasks = Workspace(temp), Tasks(temp)
    deny = settings.load(ws.home)["deny_paths"]
    universe = {}
    for concept in knowledge.inspect_bundle(ws)["concepts"]:
        spelled = f".context/knowledge/{concept['id']}.md"
        if not settings.denied_by(deny, spelled):
            universe[concept["id"]] = {"text": (ws.root / spelled).read_text(encoding="utf-8"), **concept}
    base = len(Tasks.render_packet(tasks.snapshot(STATE)))

    def framed(selection):
        return len(Tasks.render_packet(tasks.snapshot({**STATE, "selections": [selection]}))) - base

    print(f"\n=== {name} ===")
    sizes = [len(u["text"]) for u in universe.values()]
    whole_framed = [framed(f".context/knowledge/{cid}.md") for cid in universe]
    extra = [f - s for f, s in zip(whole_framed, sizes)]
    print(f"permitted concepts {len(universe)}; raw chars {sum(sizes)}; framed chars if all selected {sum(whole_framed)}")
    print(f"packet overhead with controls and no sources: {base}")
    print(f"framed minus raw per source: min {min(extra)} median {pct(extra, .5)} max {max(extra)}")
    print(f"files over 1,500 / 2,000 / 3,000 raw chars: " + " / ".join(str(sum(s > t for s in sizes)) for t in (1500, 2000, 3000)))
    by_type = defaultdict(list)
    for cid, u in universe.items():
        by_type[u["type"]].append(len(u["text"]))
    print("per type: files, median, max raw chars")
    for kind, values in sorted(by_type.items(), key=lambda kv: -sum(kv[1])):
        print(f"  {kind:12} {len(values):>3} {pct(values, .5):>6} {max(values):>6}")

    asw_totals, whole_totals, kind_goal = [], [], defaultdict(lambda: defaultdict(int))
    taken_whole, taken_section = [], []
    for goal in json.loads((fixture / "goals.json").read_text(encoding="utf-8"))["goals"]:
        if not goal["expected"]:
            continue
        asw = whl = 0
        for item in goal["expected"]:
            cid, _, slug = item.partition("#")
            u = universe[cid]
            whole = framed(f".context/knowledge/{cid}.md")
            whl += whole
            if slug:
                title = next(t for t in headings(u["text"]) if t.strip().lower().replace(" ", "-") == slug)
                cost = framed(f".context/knowledge/{cid}.md#{title}")
                taken_section.append((len(section(u["text"], title)), len(u["text"])))
            else:
                cost = whole
                taken_whole.append(len(u["text"]))
            asw += cost
            kind_goal[u["type"]][goal["id"]] += cost
        asw_totals.append(asw)
        whole_totals.append(whl)
    print(f"expected items taken whole: {len(taken_whole)} (largest file {max(taken_whole)} chars)")
    print(f"expected items taken as a section: {len(taken_section)} (largest section {max(s for s, _ in taken_section)}, "
          f"largest containing file {max(f for _, f in taken_section)})")
    print(f"expected sets, framed, as written: max {max(asw_totals)}, median {pct(asw_totals, .5)}")
    print(f"expected sets, framed, if every source were whole: max {max(whole_totals)}, median {pct(whole_totals, .5)}")
    print("largest single-type total in one expected set (framed): " +
          ", ".join(f"{k} {max(v.values())}" for k, v in sorted(kind_goal.items())))
    for budget in (4000, 6000, 8000, 12000):
        print(f"  budget {budget:>6}: as written {sum(t <= budget for t in asw_totals)}/{len(asw_totals)}, "
              f"whole files {sum(t <= budget for t in whole_totals)}/{len(whole_totals)}")


if __name__ == "__main__":
    for fixture_name in ("navigation", "navigation_heldout"):
        measure(fixture_name)
