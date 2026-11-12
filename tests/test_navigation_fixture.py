"""The synthetic navigation fixture stays valid and agrees with its frozen expected sets.

This tests the fixture, not any navigator. Dates in the fixture are far in the past or far in the
future, so freshness does not depend on when the test runs.
"""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from okf_icm import knowledge, settings
from okf_icm.packets import section
from okf_icm.workspace import Workspace

FIXTURE = Path(__file__).parent / "fixtures" / "navigation"


class NavigationFixtureCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        shutil.copytree(FIXTURE / "context", Path(temp.name) / ".context")
        self.ws = Workspace(Path(temp.name))
        self.report = knowledge.inspect_bundle(self.ws)
        self.goals = json.loads((FIXTURE / "goals.json").read_text(encoding="utf-8"))["goals"]

    def test_size_and_the_one_sensitive_file(self):
        self.assertEqual(len(self.report["concepts"]), 50)
        self.assertEqual([e["path"] for e in self.report["errors"]], ["ops/.env-conventions.md"])

    def test_contains_each_kind_of_trap(self):
        concepts = {c["id"]: c for c in self.report["concepts"]}
        self.assertTrue(any(c["status"] == "deprecated" for c in concepts.values()))
        self.assertTrue(any(c["freshness"] == "stale" for c in concepts.values()))
        self.assertTrue(any(c["trust"] == "unverified" for c in concepts.values()))
        self.assertEqual(settings.load(self.ws.home)["deny_paths"], ["hr"])
        self.assertTrue(any("chargeback-policy" in w["message"] for w in self.report["warnings"]))

    def test_expected_sources_exist_and_sections_resolve(self):
        ids = {c["id"] for c in self.report["concepts"]}
        self.assertGreaterEqual(len(self.goals), 10)
        for goal in self.goals:
            for item in goal["expected"]:
                cid, _, slug = item.partition("#")
                self.assertIn(cid, ids, goal["id"])
                if slug:
                    text = (self.ws.home / "knowledge" / f"{cid}.md").read_text(encoding="utf-8")
                    headings = [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]
                    title = next((h for h in headings if h.lower().replace(" ", "-") == slug), None)
                    self.assertIsNotNone(title, f"{goal['id']}: {item}")
                    self.assertTrue(section(text, title))

    def test_expected_sets_never_include_denied_or_hazard_concepts_except_declared(self):
        hazards = {c["id"] for c in self.report["concepts"]
                   if c["status"] != "stable" or c["freshness"] == "stale" or c["trust"] == "unverified"}
        for goal in self.goals:
            expected = {item.partition("#")[0] for item in goal["expected"]}
            self.assertFalse(any(i.startswith("hr/") for i in expected), goal["id"])
            self.assertEqual(expected & hazards, set(goal.get("must_warn", [])), goal["id"])


if __name__ == "__main__":
    unittest.main()
