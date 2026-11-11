"""Phase 2 additions that reduce what a person or assistant must read. Synthetic fixtures only."""
from contextlib import redirect_stdout, redirect_stderr
import base64
import hashlib
import io
import json
import re
from pathlib import Path
import tempfile
import unittest
from unittest import mock

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


class SubmitSnapshot(Project):
    def setUp(self):
        super().setUp()
        self.write("work/report.md", "Result v1\n")
        self.write("work/evidence.md", "Checked against policy.\n")
        self.start()

    def submit(self, *extra, outputs=("work/report.md",), evidence=("work/evidence.md",)):
        args = ["submit", "t1", "--checks", "read the policy", "--next", "Review it"]
        for path in outputs:
            args += ["--output", path]
        for path in evidence:
            args += ["--evidence", path]
        return self.cli(*args, *extra)

    def snapshot_files(self):
        base = self.root / "deliverables"
        return sorted(p.relative_to(self.root).as_posix() for p in base.rglob("*")) if base.exists() else []

    def test_snapshot_copies_byte_for_byte_and_keeps_source_path(self):
        data = b"line one\r\nline two\n"
        (self.root / "work/report.md").write_bytes(data)
        code, out, err = self.submit("--snapshot")
        self.assertEqual(code, 0, err)
        submission = json.loads(out)["submission"]
        record = submission["outputs"][0]
        self.assertEqual(record["path"], "deliverables/t1/r1/work/report.md")
        self.assertEqual(record["source_path"], "work/report.md")
        self.assertEqual((self.root / record["path"]).read_bytes(), data)
        self.assertEqual(record["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(submission["evidence"][0]["source_path"], "work/evidence.md")
        self.assertTrue(submission["snapshot"])

    def test_editing_the_original_leaves_the_task_awaiting_review(self):
        self.submit("--snapshot")
        self.write("work/report.md", "Result v2, edited later\n")
        self.write("work/evidence.md", "Different evidence\n")
        _, out, _ = self.cli("show", "t1")
        shown = json.loads(out)
        self.assertEqual(shown["status"], "awaiting_review")
        self.assertEqual(shown["freshness"], "current")

    def test_editing_the_copy_returns_the_task_to_needs_review(self):
        self.submit("--snapshot")
        (self.root / "deliverables/t1/r1/work/report.md").write_text("tampered\n", encoding="utf-8")
        _, out, _ = self.cli("show", "t1")
        self.assertEqual(json.loads(out)["status"], "needs_review")

    def test_without_the_flag_nothing_is_copied_and_originals_are_signed(self):
        code, out, _ = self.submit()
        self.assertEqual(code, 0)
        submission = json.loads(out)["submission"]
        self.assertEqual(submission["outputs"][0]["path"], "work/report.md")
        self.assertNotIn("source_path", submission["outputs"][0])
        self.assertNotIn("snapshot", submission)
        self.assertEqual(self.snapshot_files(), [])
        self.write("work/report.md", "edited\n")
        self.assertEqual(json.loads(self.cli("show", "t1")[1])["status"], "needs_review")

    def test_same_file_name_in_different_folders_does_not_collide(self):
        self.write("a/notes.md", "from a\n")
        self.write("b/notes.md", "from b\n")
        code, out, err = self.submit("--snapshot", outputs=("a/notes.md", "b/notes.md"))
        self.assertEqual(code, 0, err)
        paths = [x["path"] for x in json.loads(out)["submission"]["outputs"]]
        self.assertEqual(paths, ["deliverables/t1/r1/a/notes.md", "deliverables/t1/r1/b/notes.md"])
        self.assertEqual((self.root / paths[1]).read_text(encoding="utf-8"), "from b\n")

    def test_a_file_listed_as_output_and_evidence_is_copied_once(self):
        code, out, err = self.submit("--snapshot", outputs=("work/report.md",), evidence=("work/report.md",))
        self.assertEqual(code, 0, err)
        submission = json.loads(out)["submission"]
        self.assertEqual(submission["outputs"][0]["path"], submission["evidence"][0]["path"])

    def test_invalid_submission_copies_nothing(self):
        self.write("work/empty.md", "  \n")
        code, _, err = self.submit("--snapshot", evidence=("work/empty.md",))
        self.assertEqual(code, 2)
        self.assertIn("Empty output/evidence", err)
        self.assertFalse((self.root / "deliverables").exists())
        code, _, _ = self.submit("--snapshot", evidence=("work/missing.md",))
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "deliverables").exists())

    def test_existing_target_is_refused_and_never_overwritten_and_partial_copies_are_removed(self):
        self.write("deliverables/t1/r1/work/evidence.md", "someone else's file\n")
        code, _, err = self.submit("--snapshot")
        self.assertEqual(code, 2)
        self.assertIn("never overwritten", err)
        self.assertEqual((self.root / "deliverables/t1/r1/work/evidence.md").read_text(encoding="utf-8"), "someone else's file\n")
        # The output copy made before the conflict was removed; the pre-existing file and its folders remain.
        self.assertEqual(self.snapshot_files(), ["deliverables/t1", "deliverables/t1/r1", "deliverables/t1/r1/work",
                                                 "deliverables/t1/r1/work/evidence.md"])
        self.assertIsNone(self.tasks.load("t1")["submission"])
        self.assertEqual(self.tasks.load("t1")["revision"], 1)

    def test_failure_after_copying_removes_the_copies_and_their_new_folders(self):
        with mock.patch.object(Tasks, "save", side_effect=OSError("disk full")):
            code, _, err = self.submit("--snapshot")
        self.assertEqual(code, 2)
        self.assertIn("disk full", err)
        self.assertEqual(self.snapshot_files(), [])
        self.assertIsNone(self.tasks.load("t1")["submission"])

    def test_resubmitting_after_a_later_revision_uses_a_new_folder(self):
        self.submit("--snapshot")
        self.cli("refresh", "t1", "--note", "edit")
        code, out, err = self.submit("--snapshot")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["submission"]["outputs"][0]["path"], "deliverables/t1/r3/work/report.md")
        self.assertTrue((self.root / "deliverables/t1/r1/work/report.md").is_file())

    def test_review_accepts_the_snapshot_and_later_original_edits_do_not_revoke_it(self):
        _, out, _ = self.submit("--snapshot")
        sid = json.loads(out)["submission"]["submission_id"]
        code, out, err = self.cli("review", "t1", "--submission", sid, "--decision", "accept",
                                  "--actor", "local-reviewer", "--note", "Checked the copy")
        self.assertEqual(code, 0, err)
        self.write("work/report.md", "edited after acceptance\n")
        self.assertEqual(json.loads(self.cli("show", "t1")[1])["status"], "accepted")

    def test_symlinked_source_outside_the_project_is_refused(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        (outside / "secret.md").write_text("outside\n", encoding="utf-8")
        (self.root / "work/link.md").symlink_to(outside / "secret.md")
        code, _, _ = self.submit("--snapshot", outputs=("work/link.md",))
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "deliverables").exists())


SECRET_SOURCE = "CONFIDENTIAL-SOURCE-BODY-9f3a"
SECRET_RESULT = "CONFIDENTIAL-RESULT-BODY-77c1"


class DeliveryCard(Project):
    def setUp(self):
        super().setUp()
        self.write("policy.md", f"# Current\n149 MXN monthly. {SECRET_SOURCE}\n# History\nold\n")
        self.write("work/report.md", f"Report. {SECRET_RESULT}\n")
        self.write("work/evidence.md", "Evidence file.\n")
        self.tasks.start("t1", "Draft the FAQ | with <b>markup</b>", ["Cites policy", "Unknowns stay explicit"],
                         ["policy.md#Current"], owner="ana", reviewer="luis")

    def contents(self):
        return {p.relative_to(self.root / ".context").as_posix(): p.read_bytes()
                for p in sorted((self.root / ".context").rglob("*")) if p.is_file()}

    def submit(self, *extra):
        return self.cli("submit", "t1", "--output", "work/report.md", "--evidence", "work/evidence.md",
                        "--checks", "Read the policy.\n\n# Not a heading\nCompared prices.", "--questions", "Is 149 final?",
                        "--next", "Review please", *extra)

    def accept(self):
        sid = self.tasks.load("t1")["submission"]["submission_id"]
        return self.cli("review", "t1", "--submission", sid, "--decision", "accept", "--actor", "luis",
                        "--note", "Looks right", "--external-ref", "TICKET-42")

    def test_card_is_read_only_and_leaves_every_file_byte_identical(self):
        self.submit()
        before = self.contents()
        for args in (("card", "t1"), ("card", "t1", "--format", "html")):
            code, out, err = self.cli(*args)
            self.assertEqual(code, 0, err)
            self.assertTrue(out.strip())
        self.assertEqual(self.contents(), before)
        self.assertFalse((self.root / "deliverables").exists())

    def test_card_has_no_local_paths_or_operator_commands(self):
        self.submit()
        for fmt in ("md", "html"):
            _, out, _ = self.cli("card", "t1", "--format", fmt)
            self.assertNotIn(str(self.root), out)
            self.assertNotIn("relay --root", out)

    def test_line_start_markup_in_user_text_is_neutralised(self):
        from okf_icm.card import _md, _quote
        for raw in ("# H", "- item", "+ item", "1. one", "2) two", "=== ", "~~~", "> quote", "```", "* x"):
            self.assertNotRegex(_md(raw), r"^(#|[-+=~>`*]|\d+[.)])", raw)
        self.assertEqual(_quote("a\n\n  # b\n    code").splitlines(), ["> a", ">", "> \\# b", "> code"])

    def test_card_before_submission_says_nothing_was_returned(self):
        code, out, _ = self.cli("card", "t1")
        self.assertEqual(code, 0)
        self.assertIn("Nothing has been returned", out)
        self.assertIn("Not accepted", out)
        self.assertIn("Submission: none", out)

    def test_markdown_has_the_fields_and_keeps_the_three_states_separate(self):
        self.submit("--snapshot")
        self.accept()
        _, out, _ = self.cli("card", "t1")
        packet_id = self.tasks.status("t1")["packet_id"]
        submission_id = self.tasks.load("t1")["submission"]["submission_id"]
        for expected in ("Cites policy", "Unknowns stay explicit", "ana", "luis", "policy.md", "Current", "revision 3",
                         packet_id, submission_id, "Read the policy.", "Is 149 final?", "Review please", "TICKET-42",
                         "recorded, not verified", "self-recorded", "copy of `work/report.md`"):
            self.assertIn(expected, out)
        self.assertIn("**Selected sources:** Current", out)
        self.assertIn("**Work returned:** Returned for this version", out)
        self.assertIn("**Acceptance:** Accepted by luis (self-recorded)", out)
        digest = hashlib.sha256((self.root / "policy.md").read_bytes()).hexdigest()
        self.assertIn(digest[:12], out)
        self.assertNotIn(digest, out)

    def test_no_source_or_deliverable_contents_in_either_format(self):
        self.submit()
        for fmt in ("md", "html"):
            _, out, _ = self.cli("card", "t1", "--format", fmt)
            self.assertNotIn(SECRET_SOURCE, out)
            self.assertNotIn(SECRET_RESULT, out)
            self.assertNotIn("Evidence file.", out)

    def test_user_text_cannot_inject_markup_into_markdown(self):
        self.submit()
        _, out, _ = self.cli("card", "t1")
        self.assertNotIn("<b>", out)
        self.assertIn("\\<b\\>markup\\</b\\>", out)
        self.assertIn("> \\# Not a heading", out)
        self.assertNotRegex(out, r"(?m)^> #")

    def test_html_has_no_script_pins_style_by_hash_and_escapes_text(self):
        self.submit()
        _, out, _ = self.cli("card", "t1", "--format", "html")
        self.assertNotIn("<script", out.lower())
        self.assertNotRegex(out, r"(?i)\son[a-z]+=")
        self.assertNotIn(" style=", out)
        self.assertNotIn("<b>markup</b>", out)
        self.assertIn("&lt;b&gt;markup&lt;/b&gt;", out)
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', out).group(1)
        self.assertIn("default-src &#x27;none&#x27;", csp)
        css = re.search(r"<style>(.*?)</style>", out, re.S).group(1)
        expected = base64.b64encode(hashlib.sha256(css.encode()).digest()).decode()
        self.assertIn(f"sha256-{expected}", csp)
        self.assertNotIn("http://", out)
        self.assertNotIn("https://", out)

    def test_changed_source_and_changed_acceptance_are_reported_separately(self):
        self.submit()
        self.accept()
        self.write("policy.md", "# Current\n159 MXN monthly.\n# History\nold\n")
        _, out, _ = self.cli("card", "t1")
        self.assertIn("**Selected sources:** Changed since selected: policy.md", out)
        self.assertIn("**Work returned:** Returned for this version", out)
        self.assertIn("Earlier acceptance no longer applies", out)
        self.assertIn("**changed**", out)

    def test_changes_requested_is_not_shown_as_accepted(self):
        self.submit()
        sid = self.tasks.load("t1")["submission"]["submission_id"]
        self.cli("review", "t1", "--submission", sid, "--decision", "request_changes", "--actor", "luis", "--note", "Fix the price")
        _, out, _ = self.cli("card", "t1")
        self.assertIn("**Acceptance:** Changes requested", out)
        self.assertIn("Changes requested by luis", out)
        self.assertNotIn("Accepted by", out)

    def test_out_never_overwrites_and_is_refused_inside_context(self):
        self.submit()
        target = self.root / "card.md"
        code, out, err = self.cli("card", "t1", "--out", str(target))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["written"], str(target))
        first = target.read_bytes()
        code, _, err = self.cli("card", "t1", "--out", str(target))
        self.assertEqual(code, 2)
        self.assertEqual(target.read_bytes(), first)
        before = self.contents()
        code, _, err = self.cli("card", "t1", "--out", str(self.root / ".context" / "card.md"))
        self.assertEqual(code, 2)
        self.assertIn("outside .context", err)
        self.assertEqual(self.contents(), before)
        link = self.root / "link.md"
        link.symlink_to(self.root / "elsewhere.md")
        code, _, _ = self.cli("card", "t1", "--out", str(link))
        self.assertEqual(code, 2)
        self.assertFalse((self.root / "elsewhere.md").exists())

    def test_unknown_task_and_corrupt_packet_fail_without_a_card(self):
        code, out, err = self.cli("card", "missing")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        packet = next((self.root / ".context/relay/tasks/t1/packets").glob("*.json"))
        packet.write_text(packet.read_text(encoding="utf-8").replace("Draft the FAQ", "Draft the faq"), encoding="utf-8")
        code, out, err = self.cli("card", "t1")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("modified or corrupt", err)


if __name__ == "__main__":
    unittest.main()
