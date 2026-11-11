"""Phase 2 additions that reduce what a person or assistant must read. Synthetic fixtures only."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest

from okf_icm.relay_cli import main
from okf_icm.tasks import Tasks
from okf_icm.workspace import Workspace, initialize


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


class MinimalInit(unittest.TestCase):
    def fresh(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return Path(temp.name)

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def packet_size(self, root):
        # Fixed small fixture (one one-line source, short goal) so sizes are comparable between runs.
        (root / "source.md").write_text("x\n", encoding="utf-8")
        tasks = Tasks(root)
        tasks.start("t1", "Goal", ["Done"], ["source.md"])
        return len(tasks.context("t1"))

    def test_minimal_workspace_loads_with_one_stage_and_one_contract(self):
        root = self.fresh()
        code, out, _ = self.cli("init", str(root), "--minimal")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["minimal"])
        ws = Workspace(root)
        self.assertEqual([s["id"] for s in ws.stages], ["01-work"])
        contracts = sorted(p.parent.name for p in (root / ".context/stages").glob("*/CONTEXT.md"))
        self.assertEqual(contracts, ["01-work"])

    def test_minimal_packet_is_at_most_4300_characters_and_smaller_than_default(self):
        small, default = self.fresh(), self.fresh()
        initialize(small, "Packet size", minimal=True)
        initialize(default, "Packet size")
        small_size, default_size = self.packet_size(small), self.packet_size(default)
        self.assertLessEqual(small_size, 4300)
        self.assertLess(small_size, default_size)

    def test_minimal_workspace_runs_the_stage_cli(self):
        root = self.fresh()
        initialize(root, "Stage run", minimal=True)
        ws = Workspace(root)
        started = ws.start("r1", "Do it", ["Done"])
        self.assertEqual(started["current_stage"], "01-work")

    def test_default_init_is_unchanged(self):
        root = self.fresh()
        code, out, _ = self.cli("init", str(root))
        self.assertEqual(code, 0)
        self.assertNotIn("minimal", json.loads(out))
        self.assertEqual(len(Workspace(root).stages), 6)

    def test_workspace_apply_initialises_minimal_and_never_rewrites_existing(self):
        root = self.fresh()
        code, out, _ = self.cli("--root", str(root), "workspace", "--apply", "--minimal")
        self.assertEqual(code, 0, out)
        self.assertEqual(len(Workspace(root).stages), 1)
        before = (root / ".context/config.json").read_bytes()
        code, _, err = self.cli("--root", str(root), "workspace", "--apply", "--minimal")
        self.assertEqual(code, 2)
        self.assertIn("never rewritten", err)
        self.assertEqual((root / ".context/config.json").read_bytes(), before)

    def test_workspace_preview_says_minimal(self):
        root = self.fresh()
        _, out, _ = self.cli("--root", str(root), "workspace", "--minimal")
        self.assertTrue(json.loads(out)["minimal"])
        self.assertFalse((root / ".context").exists())


if __name__ == "__main__":
    unittest.main()
