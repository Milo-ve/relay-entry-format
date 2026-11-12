"""deny_paths: sources that may never enter a packet (Relay brief R4)."""
import json
from pathlib import Path
import tempfile
import unittest

from okf_icm import settings
from okf_icm.packets import export
from okf_icm.storage import ContextError
from okf_icm.tasks import Tasks
from okf_icm.workspace import Workspace, initialize


class MatcherCase(unittest.TestCase):
    def test_component_patterns_match_any_level_and_any_case(self):
        self.assertEqual(settings.denied_by(["*.pem"], "a/b/Key.PEM"), "*.pem")
        self.assertTrue(settings.denied_by(["secrets"], "secrets/x.md"))
        self.assertTrue(settings.denied_by(["secrets"], "a/Secrets/x.md"))
        self.assertIsNone(settings.denied_by(["secrets"], "notsecrets/x.md"))
        self.assertIsNone(settings.denied_by(["secrets"], "secrets.md"))

    def test_path_patterns_match_the_path_and_every_parent_directory(self):
        self.assertTrue(settings.denied_by(["finance/payroll*"], "finance/payroll-2026/x.csv"))
        self.assertTrue(settings.denied_by(["finance/payroll*"], "FINANCE/Payroll.xlsx"))
        self.assertIsNone(settings.denied_by(["finance/payroll*"], "finance/other/x.csv"))
        self.assertIsNone(settings.denied_by(["finance/payroll*"], "other/finance/payroll.csv"))
        self.assertTrue(settings.denied_by(["secrets/*"], "secrets/a/b.md"))
        self.assertIsNone(settings.denied_by(["secrets/*"], "secrets"))

    def test_spelling_variants_of_the_pattern_are_normalised(self):
        for pattern in ("./private/", "/private", "private/", "PRIVATE\\"):
            self.assertTrue(settings.denied_by([pattern], "private/x.md"), pattern)

    def test_patterns_that_match_nothing_by_construction_are_refused_at_load(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            (home / "relay").mkdir()
            for bad in ("/", "./", "//"):
                (home / "relay" / "settings.json").write_text(json.dumps({"deny_paths": [bad]}))
                with self.assertRaises(ContextError, msg=bad):
                    settings.load(home)


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        initialize(self.root, "Deny test")
        for name, text in {"policy.md": "# Current\n149 MXN.\n", "secrets/pay.md": "salary table\n",
                           "notes/ok.md": "fine\n", "notes/KEY.PEM": "key\n"}.items():
            (self.root / name).parent.mkdir(parents=True, exist_ok=True)
            (self.root / name).write_text(text, encoding="utf-8")
        self.tasks = Tasks(self.root)

    def deny(self, *patterns):
        path = self.root / ".context/relay/settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"deny_paths": list(patterns)}), encoding="utf-8")


class TaskCase(Base):
    def test_start_with_a_denied_path_fails_and_creates_no_task_folder(self):
        self.deny("secrets", "*.pem")
        for selection in ("secrets/pay.md", "secrets/pay.md#Current", "notes/KEY.PEM"):
            with self.assertRaisesRegex(ContextError, "deny_paths"):
                self.tasks.start("t", "Goal", ["Criterion"], [selection])
            self.assertFalse(self.tasks.home("t").exists(), selection)
        self.assertFalse((self.root / ".context/relay/tasks/t").exists())

    def test_other_sources_and_controls_still_work_under_a_broad_rule(self):
        self.deny("*.md")
        self.tasks.start("t", "Goal", ["Criterion"], [])  # controls are .md but are not selections
        with self.assertRaisesRegex(ContextError, "deny_paths"):
            self.tasks.start("u", "Goal", ["Criterion"], ["notes/ok.md"])

    def test_a_link_to_a_denied_target_is_refused_whatever_its_name(self):
        self.deny("secrets")
        (self.root / "notes/harmless.md").symlink_to(self.root / "secrets/pay.md")
        (self.root / "docs").symlink_to(self.root / "secrets", target_is_directory=True)
        for selection in ("notes/harmless.md", "docs/pay.md"):
            with self.assertRaisesRegex(ContextError, "through a link"):
                self.tasks.start("t", "Goal", ["Criterion"], [selection])
            self.assertFalse(self.tasks.home("t").exists())

    def test_the_message_names_the_pattern_and_not_the_target(self):
        self.deny("secrets")
        (self.root / "notes/harmless.md").symlink_to(self.root / "secrets/pay.md")
        with self.assertRaises(ContextError) as caught:
            self.tasks.start("t", "Goal", ["Criterion"], ["notes/harmless.md"])
        self.assertIn("'secrets'", str(caught.exception))
        self.assertNotIn("pay.md", str(caught.exception))

    def test_refresh_fails_clearly_when_a_source_became_denied(self):
        self.tasks.start("t", "Goal", ["Criterion"], ["secrets/pay.md"])
        before = self.tasks.load("t")["revision"]
        self.deny("secrets")
        with self.assertRaisesRegex(ContextError, "cannot be selected as a source"):
            self.tasks.refresh("t", "Re-read")
        self.assertEqual(self.tasks.load("t")["revision"], before)

    def test_an_older_packet_cannot_be_exported_once_its_source_is_denied(self):
        self.tasks.start("t", "Goal", ["Criterion"], ["secrets/pay.md", "notes/ok.md"])
        self.assertIn("salary table", self.tasks.context("t"))
        self.deny("secrets")
        with self.assertRaisesRegex(ContextError, "before the rule"):
            self.tasks.context("t")
        self.assertEqual(self.tasks.status("t")["status"], "ready")  # reading state is unaffected

    def test_without_the_setting_nothing_changes(self):
        self.tasks.start("t", "Goal", ["Criterion"], ["secrets/pay.md"])
        self.assertIn("salary table", self.tasks.context("t"))


class StageCase(Base):
    def test_stage_packets_apply_the_same_rule(self):
        ws = Workspace(self.root)
        ws.start("run-a", "Goal", ["Acceptance"])
        allowed = export(ws, "run-a", "01-define", ["secrets/pay.md"], "json", 100_000)[0]
        self.assertIn("secrets/pay.md", [item["path"] for item in allowed["files"]])
        self.deny("secrets")
        with self.assertRaisesRegex(ContextError, "deny_paths"):
            export(ws, "run-a", "01-define", ["secrets/pay.md#Current"], "json", 100_000)
        self.assertEqual(export(ws, "run-a", "01-define", ["notes/ok.md"], "json", 100_000)[0]["files"][-1]["path"], "notes/ok.md")


if __name__ == "__main__":
    unittest.main()
