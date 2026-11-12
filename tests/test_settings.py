from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest

from okf_icm import settings
from okf_icm.relay_cli import main
from okf_icm.storage import ContextError, lock
from okf_icm.tasks import Tasks
from okf_icm.workspace import initialize


class WorkspaceFixture(object):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        initialize(self.root, "Settings test")
        self.home = self.root / ".context"
        (self.root / "a.md").write_text("Source.\n", encoding="utf-8")

    def write_settings(self, value):
        path = self.home / "relay" / "settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()


class SettingsCase(WorkspaceFixture, unittest.TestCase):
    def test_absent_file_gives_defaults_and_loading_never_writes(self):
        before = sorted(p.name for p in self.home.rglob("*"))
        self.assertEqual(settings.load(self.home), settings.DEFAULTS)
        self.assertEqual(sorted(p.name for p in self.home.rglob("*")), before)
        self.assertFalse((self.home / "relay" / "settings.json").exists())

    def test_defaults_are_not_shared_between_loads(self):
        settings.load(self.home)["deny_paths"].append("x")
        self.assertEqual(settings.load(self.home)["deny_paths"], [])

    def test_valid_values_override_only_what_is_given(self):
        self.write_settings({"lock_wait_seconds": 0, "deny_paths": [" secrets/* "]})
        loaded = settings.load(self.home)
        self.assertEqual((loaded["lock_wait_seconds"], loaded["deny_paths"], loaded["require_expected_revision"]),
                         (0.0, ["secrets/*"], False))

    def test_unknown_keys_and_wrong_types_are_refused(self):
        for bad in ({"lock_wait": 1}, {"lock_wait_seconds": "5"}, {"lock_wait_seconds": True}, {"lock_wait_seconds": -1},
                    {"lock_wait_seconds": 301}, {"require_expected_revision": "yes"}, {"deny_paths": "secrets"},
                    {"deny_paths": [""]}, {"deny_paths": [1]}, {"deny_paths": ["x"] * 101}, "[]", "not json"):
            self.write_settings(bad)
            with self.assertRaises((ContextError, ValueError), msg=bad):
                settings.load(self.home)

    def test_a_symlinked_settings_file_is_refused(self):
        target = self.root / "elsewhere.json"
        target.write_text("{}", encoding="utf-8")
        (self.home / "relay").mkdir()
        (self.home / "relay" / "settings.json").symlink_to(target)
        with self.assertRaises(ContextError):
            settings.load(self.home)

    def test_settings_are_not_part_of_any_packet_or_freshness(self):
        tasks = Tasks(self.root)
        tasks.start("t", "Goal", ["Criterion"], ["a.md"])
        before = tasks.status("t")["packet_id"]
        self.write_settings({"lock_wait_seconds": 1})
        status = tasks.status("t")
        self.assertEqual((status["packet_id"], status["freshness"]), (before, "current"))
        self.assertNotIn("settings.json", json.dumps(tasks.packet(tasks.load("t"))))


class LockWaitCase(WorkspaceFixture, unittest.TestCase):
    def test_second_writer_waits_and_then_succeeds(self):
        held, release = threading.Event(), threading.Event()

        def hold():
            with lock(self.home):
                held.set()
                release.wait(5)

        thread = threading.Thread(target=hold)
        thread.start()
        self.assertTrue(held.wait(5))
        threading.Timer(0.3, release.set).start()
        started = time.monotonic()
        with lock(self.home, wait=5):
            waited = time.monotonic() - started
        thread.join()
        self.assertGreaterEqual(waited, 0.2)
        self.assertFalse((self.home / "write.lock").exists())

    def test_zero_wait_fails_at_once_and_names_the_holder(self):
        with lock(self.home):
            started = time.monotonic()
            with self.assertRaises(ContextError) as caught:
                with lock(self.home, wait=0):
                    pass
        self.assertLess(time.monotonic() - started, 0.5)
        message = str(caught.exception)
        self.assertIn("Workspace writer is busy", message)
        self.assertIn("held by process", message)
        self.assertNotIn("after waiting", message)

    def test_timeout_reports_the_wait(self):
        with lock(self.home):
            started = time.monotonic()
            with self.assertRaises(ContextError) as caught:
                with lock(self.home, wait=0.3):
                    pass
        self.assertGreaterEqual(time.monotonic() - started, 0.25)
        self.assertIn("after waiting 0.3s", str(caught.exception))

    def test_the_setting_controls_the_cli_wait(self):
        self.write_settings({"lock_wait_seconds": 0})
        with lock(self.home):
            started = time.monotonic()
            code, _, err = self.cli("start", "t", "--goal", "G", "--accept", "A")
        self.assertEqual(code, 2)
        self.assertLess(time.monotonic() - started, 1)
        self.assertIn("Workspace writer is busy", err)


class RequireRevisionCase(WorkspaceFixture, unittest.TestCase):
    def test_missing_revision_is_refused_only_when_required(self):
        tasks = Tasks(self.root)
        tasks.start("t", "Goal", ["Criterion"], ["a.md"])
        tasks.refresh("t", "No revision given")
        self.write_settings({"require_expected_revision": True})
        with self.assertRaisesRegex(ContextError, "requires the expected revision"):
            tasks.refresh("t", "Still none")
        revision = tasks.status("t")["revision"]
        self.assertEqual(tasks.refresh("t", "With revision", expected=revision)["revision"], revision + 1)

    def test_cli_refuses_and_names_the_next_step(self):
        self.cli("start", "t", "--goal", "G", "--accept", "A")
        self.write_settings({"require_expected_revision": True})
        code, _, err = self.cli("refresh", "t", "--note", "n")
        self.assertEqual(code, 2)
        self.assertIn("--expected-revision", err)


if __name__ == "__main__":
    unittest.main()
