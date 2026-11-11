"""Phase 2 additions that reduce what a person or assistant must read. Synthetic fixtures only."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest

from okf_icm.relay_cli import main
from okf_icm.tasks import Tasks
from okf_icm.workspace import initialize


class Project(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        initialize(self.root, "Savings test")
        self.write("policy.md", "# Current\n149 MXN monthly.\n")
        self.tasks = Tasks(self.root)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return path

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()

    def start(self, name="t1", **kwargs):
        defaults = dict(goal="Draft FAQ", acceptance=["Cites policy"], selections=["policy.md"])
        return self.tasks.start(name, **{**defaults, **kwargs})


class ListBrief(Project):
    def test_brief_has_only_orientation_fields(self):
        self.start()
        code, out, _ = self.cli("list", "--brief")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [{"id": "t1", "status": "ready", "freshness": "current",
                                            "owner": "local-operator", "reviewer": "local-reviewer", "revision": 1}])

    def test_default_list_is_unchanged(self):
        self.start()
        code, out, _ = self.cli("list")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), self.tasks.list())
        self.assertIn("acceptance", json.loads(out)[0])

    def test_seven_tasks_fit_in_1500_characters_and_report_changes(self):
        for n in range(7):
            self.start(f"task-{n}", goal=f"Draft FAQ number {n}", acceptance=["Cites policy and keeps unknowns explicit"])
        self.write("policy.md", "# Current\n159 MXN monthly.\n")
        _, brief, _ = self.cli("list", "--brief")
        _, full, _ = self.cli("list")
        self.assertLess(len(brief), 1500)
        self.assertLess(len(brief), len(full) / 5)
        self.assertEqual({x["freshness"] for x in json.loads(brief)}, {"changed"})
        self.assertEqual({x["status"] for x in json.loads(brief)}, {"needs_review"})


if __name__ == "__main__":
    unittest.main()
