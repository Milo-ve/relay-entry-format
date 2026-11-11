"""Phase 3 additions for running many tasks: list --stale and refresh --all-stale. Synthetic fixtures only."""
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
        initialize(self.root, "Operation test")
        self.write("policy.md", "# Current\n149 MXN monthly.\n")
        self.write("other.md", "# Other\nUnrelated.\n")
        self.tasks = Tasks(self.root)

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return path

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        try:
            with redirect_stdout(out), redirect_stderr(err):
                code = main(["--root", str(self.root), *args])
        except SystemExit as exc:  # argparse
            code = exc.code
        return code, out.getvalue(), err.getvalue()

    def start(self, name, source="policy.md", **kwargs):
        defaults = dict(goal=f"Goal of {name}", acceptance=["Cites the source"], selections=[source])
        return self.tasks.start(name, **{**defaults, **kwargs})

    def files(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in sorted(self.root.rglob("*")) if p.is_file()}

    def events(self, task):
        return self.tasks.load(task)["events"]

    def setting(self, **values):
        self.write(".context/relay/settings.json", json.dumps(values))

    def accept(self, task):
        self.write(f"work/{task}-result.md", "Result\n")
        self.write(f"work/{task}-evidence.md", "Checked\n")
        sub = self.tasks.submit(task, [f"work/{task}-result.md"], [f"work/{task}-evidence.md"], "read it", "", "Review")
        return self.tasks.review(task, sub["submission"]["submission_id"], "accept", "local-reviewer", "Fine")


class ListStale(Project):
    def test_only_tasks_with_changed_inputs_are_listed_and_it_combines_with_brief(self):
        self.start("a")
        self.start("b", "other.md")
        self.write("policy.md", "# Current\n159 MXN monthly.\n")
        code, out, err = self.cli("list", "--stale", "--brief")
        self.assertEqual(code, 0)
        self.assertEqual([x["id"] for x in json.loads(out)], ["a"])
        self.assertEqual(set(json.loads(out)[0]), {"id", "status", "freshness", "owner", "reviewer", "revision"})
        self.assertIn("--all-stale", err)
        self.assertNotIn("--all-stale", out)

    def test_full_stale_list_keeps_the_default_shape(self):
        self.start("a")
        self.write("policy.md", "changed\n")
        _, out, _ = self.cli("list", "--stale")
        self.assertEqual(json.loads(out), [x for x in self.tasks.list() if x["freshness"] == "changed"])
        self.assertIn("acceptance", json.loads(out)[0])

    def test_nothing_stale_prints_an_empty_list_and_no_advice(self):
        self.start("a")
        code, out, err = self.cli("list", "--stale")
        self.assertEqual((code, json.loads(out), err), (0, [], ""))

    def test_default_list_prints_no_advice(self):
        self.start("a")
        self.write("policy.md", "changed\n")
        self.assertEqual(self.cli("list")[2], "")


class RefreshAllStalePreview(Project):
    def setUp(self):
        super().setUp()
        self.start("a")
        self.start("b", "other.md")
        self.start("c")
        self.accept("c")
        self.write("policy.md", "# Current\n159 MXN monthly.\n")

    def test_preview_writes_nothing_and_names_what_would_be_cleared(self):
        before = self.files()
        code, out, _ = self.cli("refresh", "--all-stale", "--note", "Price changed")
        self.assertEqual(code, 0)
        self.assertEqual(self.files(), before)
        result = json.loads(out)
        self.assertEqual((result["mode"], result["stale"], result["failed"]), ("preview", 2, []))
        by_id = {x["id"]: x for x in result["tasks"]}
        self.assertEqual(set(by_id), {"a", "c"})
        self.assertEqual(by_id["a"]["changed"], ["policy.md"])
        self.assertEqual((by_id["a"]["clears_submission"], by_id["a"]["clears_acceptance"]), (False, False))
        self.assertEqual((by_id["c"]["clears_submission"], by_id["c"]["clears_acceptance"]), (True, True))
        self.assertIn("--apply", result["next_step"])

    def test_preview_does_not_take_the_writer_lock(self):
        (self.root / ".context" / "write.lock").write_text("held by someone else")
        self.setting(lock_wait_seconds=0)
        code, out, _ = self.cli("refresh", "--all-stale", "--note", "x")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["mode"], "preview")

    def test_a_note_is_required(self):
        before = self.files()
        code, _, err = self.cli("refresh", "--all-stale")
        self.assertEqual(code, 2)
        self.assertIn("--note", err)
        self.assertEqual(self.files(), before)
        code, _, err = self.cli("refresh", "--all-stale", "--note", "   ")
        self.assertEqual(code, 2)
        self.assertIn("note", err.lower())

    def test_preview_reports_a_task_whose_refresh_would_be_refused_and_exits_2(self):
        self.start("big", max_chars=8000)
        self.write("policy.md", "x" * 9000)
        before = self.files()
        code, out, _ = self.cli("refresh", "--all-stale", "--note", "grew")
        self.assertEqual(code, 2)
        self.assertEqual(self.files(), before)
        result = json.loads(out)
        self.assertEqual([x["id"] for x in result["failed"]], ["big"])
        self.assertIn("budget", result["failed"][0]["error"])

    def test_nothing_stale_says_so(self):
        self.cli("refresh", "--all-stale", "--note", "x", "--apply")
        code, out, _ = self.cli("refresh", "--all-stale", "--note", "x")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["tasks"], [])
        self.assertIn("No task has changed", json.loads(out)["next_step"])


class RefreshAllStaleApply(Project):
    def setUp(self):
        super().setUp()
        self.start("a")
        self.start("b", "other.md")
        self.start("c")
        self.accept("c")
        self.write("policy.md", "# Current\n159 MXN monthly.\n")

    def apply(self, *extra, note="Price changed"):
        return self.cli("refresh", "--all-stale", "--note", note, "--apply", *extra)

    def test_refreshes_only_stale_tasks_with_one_marked_event_each(self):
        revisions = {t: self.tasks.load(t)["revision"] for t in "abc"}
        code, out, _ = self.apply("--actor", "Ana")
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual((result["mode"], result["stale"], result["failed"]), ("apply", 2, []))
        self.assertEqual({x["id"] for x in result["refreshed"]}, {"a", "c"})
        self.assertEqual(self.tasks.load("b")["revision"], revisions["b"])
        for task in "ac":
            state = self.tasks.load(task)
            self.assertEqual(state["revision"], revisions[task] + 1)
            event = state["events"][-1]
            self.assertEqual((event["action"], event["note"], event["batch"], event["actor"]), ("refresh", "Price changed", True, "Ana"))
            self.assertEqual(event["changed"], ["policy.md"])
            self.assertFalse(event["resolved_by_operator"])
            self.assertEqual(self.tasks.status(task)["status"], "ready")

    def test_clears_submission_and_acceptance_but_creates_no_review_and_keeps_history(self):
        reviews = [e for e in self.events("c") if e["action"] == "review"]
        self.assertEqual(len(reviews), 1)
        self.apply()
        state = self.tasks.load("c")
        self.assertEqual((state["submission"], state["review"]), (None, None))
        self.assertEqual([e for e in state["events"] if e["action"] == "review"], reviews)
        self.assertEqual(len(state["packets"]), 2)
        self.assertNotIn("accepted", {self.tasks.status(t)["status"] for t in "abc"})

    def test_a_second_run_finds_nothing_to_do(self):
        self.apply()
        before = self.files()
        code, out, _ = self.apply()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["refreshed"], [])
        self.assertEqual(self.files(), before)

    def test_one_failure_is_reported_and_does_not_stop_the_others(self):
        self.start("big", max_chars=8000)
        self.write("policy.md", "x" * 9000)
        # a and c now exceed no budget (default 32000) but `big` does.
        big_before = self.tasks.load("big")["revision"]
        code, out, err = self.apply()
        self.assertEqual(code, 2)
        result = json.loads(out)
        self.assertEqual({x["id"] for x in result["refreshed"]}, {"a", "c"})
        self.assertEqual([x["id"] for x in result["failed"]], ["big"])
        self.assertEqual(self.tasks.load("big")["revision"], big_before)
        self.assertEqual(self.tasks.status("big")["freshness"], "changed")
        self.assertEqual(self.tasks.status("a")["freshness"], "current")

    def test_a_deleted_source_fails_only_that_task(self):
        self.start("gone", "other.md")
        (self.root / "other.md").unlink()
        code, out, _ = self.apply()
        self.assertEqual(code, 2)
        result = json.loads(out)
        self.assertEqual({x["id"] for x in result["refreshed"]}, {"a", "c"})
        self.assertEqual({x["id"] for x in result["failed"]}, {"b", "gone"})

    def test_an_unreadable_task_is_reported_and_hides_nothing(self):
        (self.tasks.home("b") / "state.json").write_text("{not json")
        code, out, _ = self.apply()
        self.assertEqual(code, 2)
        result = json.loads(out)
        self.assertEqual({x["id"] for x in result["refreshed"]}, {"a", "c"})
        self.assertEqual([x["id"] for x in result["failed"]], ["b"])

    def test_open_prerequisites_stay_open(self):
        self.start("blocked", blockers=["Need legal text"])
        self.write("policy.md", "again\n")
        self.apply()
        status = self.tasks.status("blocked")
        self.assertEqual((status["status"], status["blockers"]), ("blocked", ["Need legal text"]))

    def test_an_escalated_task_stays_investigative(self):
        self.tasks.refresh("a", "Failed a check", escalate=True)
        self.write("policy.md", "again\n")
        self.apply()
        self.assertEqual(self.tasks.status("a")["route"]["profile"], "investigative")

    def test_the_writer_lock_is_released(self):
        self.apply()
        self.assertFalse((self.root / ".context" / "write.lock").exists())

    def test_apply_waits_for_the_writer_lock_and_fails_clearly_when_it_stays_busy(self):
        (self.root / ".context" / "write.lock").write_text("held by someone else")
        self.setting(lock_wait_seconds=0)
        before = self.files()
        code, _, err = self.apply()
        self.assertEqual(code, 2)
        self.assertIn("busy", err)
        self.assertEqual(self.files(), before)


class RefreshAllStaleRefusals(Project):
    def setUp(self):
        super().setUp()
        self.start("a")
        self.write("policy.md", "changed\n")
        self.before = self.files()

    def refused(self, *args, needle):
        code, out, err = self.cli(*args)
        self.assertEqual(code, 2, err)
        self.assertEqual(out, "")
        self.assertIn(needle, err)
        self.assertEqual(self.files(), self.before)

    def test_a_task_and_all_stale_together(self):
        self.refused("refresh", "a", "--all-stale", "--note", "x", needle="not both")

    def test_resolve_is_never_batched(self):
        self.refused("refresh", "--all-stale", "--resolve", "--note", "x", "--apply", needle="--resolve")

    def test_expected_revision_is_not_combined(self):
        self.refused("refresh", "--all-stale", "--expected-revision", "1", "--note", "x", "--apply", needle="--expected-revision")

    def test_apply_needs_all_stale(self):
        self.refused("refresh", "a", "--note", "x", "--apply", needle="--all-stale")

    def test_refresh_needs_a_task_or_all_stale(self):
        self.refused("refresh", "--note", "x", needle="--all-stale")

    def test_escalate_has_no_batch_form(self):
        code, _, _ = self.cli("escalate", "--all-stale", "--note", "x")
        self.assertEqual(code, 2)
        self.assertEqual(self.files(), self.before)

    def test_required_expected_revision_refuses_preview_and_apply(self):
        self.setting(require_expected_revision=True)
        self.before = self.files()
        self.refused("refresh", "--all-stale", "--note", "x", needle="expected revision")
        self.refused("refresh", "--all-stale", "--note", "x", "--apply", needle="expected revision")

    def test_single_task_refresh_is_unchanged(self):
        code, out, _ = self.cli("refresh", "a", "--note", "Price changed")
        self.assertEqual(code, 0)
        event = self.events("a")[-1]
        self.assertNotIn("batch", event)
        self.assertNotIn("changed", event)
        self.assertEqual(json.loads(out)["status"], "ready")


class BatchInTheHistory(Project):
    def test_history_labels_a_batch_refresh(self):
        from okf_icm.viz import timeline_model
        self.start("a")
        self.write("policy.md", "changed\n")
        self.cli("refresh", "--all-stale", "--note", "x", "--apply")
        labels = [e["label"] for e in timeline_model(self.tasks, "a")["events"]]
        self.assertEqual(labels[-1], "Context refreshed · batch refresh")


if __name__ == "__main__":
    unittest.main()
