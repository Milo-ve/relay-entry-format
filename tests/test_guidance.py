from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest

from okf_icm import guidance
from okf_icm.relay_cli import main
from okf_icm.storage import ContextError
from okf_icm.tasks import Tasks
from okf_icm.workspace import initialize


class GuidanceCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        initialize(self.root, "Guidance test")
        self.tasks = Tasks(self.root)
        self.write("policy.md", "# Current\n149 MXN monthly.\n")

    def write(self, path, text):
        (self.root / path).write_text(text, encoding="utf-8")

    def start(self, **kwargs):
        return self.tasks.start("faq", "Draft an FAQ", ["Use current source"], ["policy.md#Current"], **kwargs)

    def submit(self):
        self.write("result.md", "149 MXN monthly.\n")
        self.write("checks.md", "Compared with policy.md.\n")
        return self.tasks.submit("faq", ["result.md"], ["checks.md"], "Compared source", "", "Review FAQ")

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(["--root", str(self.root), *argv])
        return code, out.getvalue(), err.getvalue()

    def test_every_status_has_an_actionable_next_step(self):
        ready = self.start()
        self.assertEqual(ready["status"], "ready")
        self.assertIn("relay --root", ready["next_step"])  # root differs from the working directory
        self.assertIn("faq-context.md", ready["next_step"])

        submitted = self.submit()
        self.assertEqual(submitted["status"], "awaiting_review")
        self.assertIn(submitted["submission"]["submission_id"], submitted["next_step"])
        self.assertIn("local-reviewer", submitted["next_step"])

        sid = submitted["submission"]["submission_id"]
        changes = self.tasks.review("faq", sid, "request_changes", "local-reviewer", "Add cancellation")
        self.assertEqual(changes["status"], "changes_requested")
        self.assertIn("refresh", changes["next_step"])

        self.tasks.refresh("faq", "Revised")
        sid = self.submit()["submission"]["submission_id"]
        accepted = self.tasks.review("faq", sid, "accept", "local-reviewer", "Matches source")
        self.assertEqual(accepted["status"], "accepted")
        self.assertIn("only this version", accepted["next_step"])

        self.write("policy.md", "# Current\n179 MXN monthly.\n")
        stale = self.tasks.status("faq")
        self.assertEqual(stale["status"], "needs_review")
        self.assertIn("policy.md", stale["next_step"])
        self.assertIn("refresh faq", stale["next_step"])

    def test_blocked_task_says_resolution_is_asserted_not_checked(self):
        blocked = self.start(blockers=["Missing authoritative source"])
        self.assertEqual(blocked["status"], "blocked")
        self.assertIn("Missing authoritative source", blocked["next_step"])
        self.assertIn("--resolve", blocked["next_step"])
        self.assertIn("does not check", blocked["next_step"])

    def test_context_refusal_names_the_cause_without_cli_commands(self):
        self.start()
        self.write("policy.md", "# Current\n179 MXN monthly.\n")
        with self.assertRaises(ContextError) as caught:
            self.tasks.context("faq")
        self.assertIn("policy.md", str(caught.exception))
        self.assertNotIn("`relay", str(caught.exception))  # the browser UI shows this message too

    def test_cli_context_keeps_stdout_a_clean_packet(self):
        self.start()
        code, out, err = self.cli("context", "faq")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("# Relay work packet"))
        self.assertNotIn("relay: next", out)
        self.assertIn("relay: next: Packet exported", err)

        code, out, err = self.cli("context", "faq", "--out", str(self.root / "ctx.md"))
        self.assertEqual(code, 0)
        self.assertIn("submit faq", json.loads(out)["next_step"])

    def test_cli_failure_adds_next_step_after_the_original_error(self):
        self.start()
        self.write("policy.md", "# Current\n179 MXN monthly.\n")
        code, out, err = self.cli("context", "faq")
        self.assertEqual(code, 2)
        lines = err.splitlines()
        self.assertTrue(lines[0].startswith("relay: Cannot export context."))
        self.assertTrue(lines[1].startswith("relay: next: Changed since the snapshot: policy.md"))
        self.assertEqual(out, "")

    def test_failure_hint_is_skipped_when_state_does_not_explain_the_error(self):
        self.start()
        self.write("checks.md", "x\n")
        code, out, err = self.cli("submit", "faq", "--output", "policy.md", "--evidence", "checks.md",
                                  "--checks", "c", "--next", "n")
        self.assertEqual(code, 2)
        self.assertEqual(len(err.splitlines()), 1)

    def test_failure_hint_is_skipped_for_unknown_tasks(self):
        code, out, err = self.cli("context", "missing")
        self.assertEqual(code, 2)
        self.assertEqual(len(err.splitlines()), 1)

    def test_long_lists_are_truncated(self):
        self.assertEqual(guidance.listed(["a", "b", "c", "d", "e", "f", "g"]), "a, b, c, d, e (+2 more)")

    def test_prefix_omits_root_inside_the_project(self):
        import os
        previous = Path.cwd()
        os.chdir(self.root)
        try:
            self.assertEqual(guidance.command_prefix(self.root), "relay")
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
