"""Optional actor names and reassignment (Relay brief R1)."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest

from okf_icm.relay_cli import main
from okf_icm.storage import ContextError
from okf_icm.tasks import Tasks
from okf_icm.viz import timeline_model
from okf_icm.workspace import initialize


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        initialize(self.root, "Collab test")
        (self.root / "policy.md").write_text("# Current\n149 MXN monthly.\n", encoding="utf-8")
        (self.root / "result.md").write_text("149 MXN monthly.\n", encoding="utf-8")
        (self.root / "checks.md").write_text("Compared with policy.md: matches.\n", encoding="utf-8")
        self.tasks = Tasks(self.root)

    def start(self, **kwargs):
        return self.tasks.start("t", "Draft an FAQ", ["Use current source"], ["policy.md#Current"],
                                owner="ana", reviewer="bea", **kwargs)

    def submit(self, **kwargs):
        return self.tasks.submit("t", ["result.md"], ["checks.md"], "Compared source", "None", "Review", **kwargs)

    def events(self):
        return self.tasks.load("t")["events"]

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()


class ActorCase(Base):
    def test_actor_is_stored_only_when_given(self):
        self.start()
        self.submit()
        self.tasks.refresh("t", "No name")
        self.assertTrue(all("actor" not in e for e in self.events()))

    def test_actor_is_recorded_on_start_submit_refresh_and_escalate(self):
        self.start(actor="ana")
        self.submit(actor="ana")
        self.tasks.refresh("t", "Re-read", actor="ana")
        self.tasks.refresh("t", "More effort", escalate=True, actor="cy")
        self.assertEqual([(e["action"], e.get("actor")) for e in self.events()],
                         [("start", "ana"), ("submit", "ana"), ("refresh", "ana"), ("escalate", "cy")])

    def test_invalid_actors_are_refused_before_anything_is_written(self):
        for bad in ("", "   ", "x" * 81, "a\nb", "a\x00b"):
            with self.assertRaises(ContextError, msg=repr(bad)):
                self.tasks.start("t", "G", ["A"], ["policy.md"], actor=bad)
            self.assertFalse(self.tasks.home("t").exists())
        self.start()
        revision = self.tasks.load("t")["revision"]
        with self.assertRaises(ContextError):
            self.tasks.refresh("t", "n", actor="a\tb")
        self.assertEqual(self.tasks.load("t")["revision"], revision)

    def test_cli_accepts_actor_and_the_history_shows_it_as_self_recorded(self):
        self.assertEqual(self.cli("start", "t", "--goal", "G", "--accept", "A", "--select", "policy.md", "--actor", "ana")[0], 0)
        self.assertEqual(self.cli("refresh", "t", "--note", "n", "--actor", "ana")[0], 0)
        labels = [row["label"] for row in timeline_model(self.tasks, "t")["events"]]
        self.assertTrue(all("ana (self-recorded)" in label for label in labels), labels)

    def test_events_without_actor_still_render(self):
        self.start()
        self.assertNotIn("self-recorded", timeline_model(self.tasks, "t")["events"][0]["label"])


class ReassignCase(Base):
    def accepted(self):
        self.start()
        s = self.submit()
        return self.tasks.review("t", s["submission"]["submission_id"], "accept", "bea", "Matches")

    def test_reassign_takes_a_new_snapshot_and_clears_the_acceptance(self):
        old = self.accepted()
        status = self.tasks.reassign("t", "Bea is away", reviewer="dan", actor="ana")
        self.assertNotEqual(status["packet_id"], old["packet_id"])
        self.assertEqual((status["status"], status["reviewer"], status["owner"]), ("ready", "dan", "ana"))
        self.assertIsNone(status["submission"])
        self.assertIsNone(status["review"])
        brief = self.tasks.packet(self.tasks.load("t"))["brief"]
        self.assertEqual((brief["reviewer"], brief["owner"]), ("dan", "ana"))

    def test_old_reviewer_cannot_review_and_history_is_kept(self):
        self.accepted()
        self.tasks.reassign("t", "Bea is away", reviewer="dan")
        s = self.submit()
        with self.assertRaisesRegex(ContextError, "assigned reviewer"):
            self.tasks.review("t", s["submission"]["submission_id"], "accept", "bea", "Still me")
        self.assertEqual(self.tasks.review("t", s["submission"]["submission_id"], "accept", "dan", "Ok")["status"], "accepted")
        actions = [e["action"] for e in self.events()]
        self.assertEqual(actions, ["start", "submit", "review", "reassign", "submit", "review"])
        event = self.events()[3]
        self.assertEqual((event["previous"], event["current"]), ({"owner": "ana", "reviewer": "bea"}, {"owner": "ana", "reviewer": "dan"}))
        self.assertEqual(len(self.tasks.load("t")["packets"]), 2)

    def test_an_escalated_task_stays_investigative(self):
        self.start()
        self.tasks.refresh("t", "More effort", escalate=True)
        status = self.tasks.reassign("t", "New owner", owner="cy")
        self.assertEqual(status["route"]["profile"], "investigative")
        self.assertEqual(status["escalations"], 1)

    def test_blockers_are_not_resolved_by_reassigning(self):
        self.start(blockers=["Policy missing"])
        status = self.tasks.reassign("t", "New owner", owner="cy")
        self.assertEqual((status["status"], status["blockers"]), ("blocked", ["Policy missing"]))

    def test_refused_while_inputs_are_changed_and_nothing_is_written(self):
        self.start()
        (self.root / "policy.md").write_text("# Current\n199 MXN monthly.\n", encoding="utf-8")
        before = self.tasks.load("t")["revision"]
        with self.assertRaisesRegex(ContextError, "Refresh the task"):
            self.tasks.reassign("t", "n", reviewer="dan")
        self.assertEqual(self.tasks.load("t")["revision"], before)

    def test_refused_without_a_change_or_a_name_or_a_note(self):
        self.start()
        for kwargs in ({}, {"reviewer": "bea"}, {"owner": "ana", "reviewer": "bea"}, {"reviewer": "  "}):
            with self.assertRaises(ContextError, msg=kwargs):
                self.tasks.reassign("t", "n", **kwargs)
        with self.assertRaises(ContextError):
            self.tasks.reassign("t", "  ", reviewer="dan")

    def test_stale_expected_revision_is_refused(self):
        self.start()
        with self.assertRaisesRegex(ContextError, "Task changed"):
            self.tasks.reassign("t", "n", reviewer="dan", expected=99)

    def test_cli_and_history_label(self):
        self.start()
        code, out, _ = self.cli("reassign", "t", "--reviewer", "dan", "--note", "Bea is away", "--actor", "ana")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["reviewer"], "dan")
        label = timeline_model(self.tasks, "t")["events"][-1]["label"]
        self.assertIn("reassigned", label)
        self.assertIn("reviewer dan", label)
        self.assertEqual(self.cli("reassign", "t", "--note", "n")[0], 2)


if __name__ == "__main__":
    unittest.main()
