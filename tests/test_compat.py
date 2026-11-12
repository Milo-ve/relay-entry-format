"""Old task state must keep loading, hashing and reporting the same way."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from okf_icm.packets import packet_hash
from okf_icm.relay_cli import main
from okf_icm.tasks import Tasks

FIXTURE = Path(__file__).parent / "fixtures" / "legacy_task"
TASKS = ("legacy-faq", "legacy-escalated")


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


class LegacyTaskCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / "project"
        self.root.mkdir()
        shutil.copytree(FIXTURE / "context", self.root / ".context")
        for name in ("policy.md", "result.md", "checks.md"):
            shutil.copy(FIXTURE / name, self.root / name)
        self.expected = json.loads((FIXTURE / "expected_status.json").read_text(encoding="utf-8"))
        self.tasks = Tasks(self.root)

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--root", str(self.root), *args])
        return code, out.getvalue()

    def test_status_matches_what_the_old_code_recorded(self):
        for task in TASKS:
            status = self.tasks.status(task)
            self.assertTrue(status.pop("next_step"))
            self.assertEqual(status, self.expected[task])

    def test_every_stored_packet_still_hashes_to_its_id(self):
        packets = sorted((self.root / ".context/relay/tasks").glob("*/packets/*.json"))
        self.assertEqual(len(packets), 3)
        for path in packets:
            packet = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(packet_hash(packet), packet["packet_id"])
            self.assertEqual(path.stem, packet["packet_id"])

    def test_acceptance_and_escalation_survive(self):
        faq, escalated = (self.tasks.status(t) for t in TASKS)
        self.assertEqual((faq["status"], faq["review"]["decision"]), ("accepted", "accept"))
        self.assertEqual((escalated["route"]["profile"], escalated["escalations"]), ("investigative", 1))

    def test_read_only_commands_leave_every_byte_alone(self):
        before = snapshot(self.root)
        export = self.base / "snapshot.html"
        for args in (("list",), ("show", "legacy-faq"), ("context", "legacy-escalated"), ("export-html", "--out", str(export))):
            self.assertEqual(self.run_cli(*args)[0], 0, args)
        self.assertEqual(snapshot(self.root), before)

    def test_changed_source_is_still_detected(self):
        (self.root / "policy.md").write_text("# Current\n199 MXN monthly.\n", encoding="utf-8")
        status = self.tasks.status("legacy-faq")
        self.assertEqual(status["status"], "needs_review")
        self.assertEqual(status["changed"], ["policy.md"])


if __name__ == "__main__":
    unittest.main()
