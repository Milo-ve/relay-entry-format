"""ICM workspace layer on synthetic folders: exclusions, scaffold, budget headings and the request."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from okf_icm import icm
from okf_icm.cli import main
from okf_icm.environment import Environment
from okf_icm.storage import ContextError

CLAUDE = "# Rules\n\n## Identity\nYou are a careful engineer.\n\n## Constraints\n- No network.\n\n## Format\nA patch and three lines.\n\n## Paths\nRead docs.\n"


class IcmBase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = Environment(self.root)

    def write(self, relative, text="# Title\n\nBody.\n"):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}


class ExclusionTests(IcmBase):
    def test_folder_scans_skip_working_and_outputs_but_explicit_paths_do_not(self):
        for name in ("docs/a.md", "docs/working/draft.md", "docs/outputs/final.md", "outputs/top.md"):
            self.write(name)
        items, _ = self.env.scan(["docs"])
        self.assertEqual([i["path"] for i in items], ["docs/a.md"])
        items, _ = self.env.scan(["outputs"])
        self.assertEqual([i["path"] for i in items], ["outputs/top.md"])


class ExportBase(IcmBase):
    def setUp(self):
        super().setUp()
        self.write("docs/offer.md", "# Offer\n\n## Scope\n\nInterview and report.\n")
        self.write("examples/good.md", "# Good\n\nA sample.\n")
        self.env.prepare(["docs"], apply=True, name="Synthetic")

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--root", str(self.root), *args])
        return code, out.getvalue(), err.getvalue()


class BudgetTests(ExportBase):
    def test_plain_export_is_not_changed_by_the_layer(self):
        code, out, _ = self.run_cli("context", "--select", "docs/offer.md")
        _, expected = self.env.context(["docs/offer.md"])
        self.assertEqual((code, out), (0, expected))
        self.assertNotIn("Context budget", out)

    def test_budget_keeps_the_same_packet_as_plain_selection(self):
        packet, _, _ = icm.export(self.env, ["docs/offer.md#Scope"])
        plain, _ = self.env.context(["docs/offer.md#Scope"])
        self.assertEqual(packet["packet_id"], plain["packet_id"])
        self.assertEqual([f["role"] for f in packet["files"]], [f["role"] for f in plain["files"]])

    def test_each_file_names_its_heading_and_the_rule(self):
        self.write("history/2026-10.md", "# Earlier\n\nNotes.\n")
        self.write("docs/examples/bad.md", "# Bad\n\nA miss.\n")
        _, text, _ = icm.export(self.env, ["docs/offer.md", "docs/examples/bad.md"], examples=["examples/good.md"],
                                history=["history/2026-10.md"])
        self.assertIn("### .context/policy.md (role control; placed by role control)", text)
        self.assertIn("### docs/offer.md (role artifact; placed by --select)", text)
        self.assertIn("### docs/examples/bad.md (role artifact; placed by path segment examples/)", text)
        self.assertIn("### examples/good.md (role artifact; placed by --example)", text)
        self.assertIn("### history/2026-10.md (role artifact; placed by --history)", text)
        self.assertLess(text.index("## History"), text.index("## Material"))
        self.assertLess(text.index("## Material"), text.index("## Examples"))

    def test_explicit_flag_beats_path_segment_and_select(self):
        _, text, _ = icm.export(self.env, ["examples/good.md"], history=["examples/good.md"])
        self.assertIn("### examples/good.md (role artifact; placed by --history)", text)
        self.assertEqual(text.count("### examples/good.md"), 1)

    def test_size_table_matches_the_rendered_export(self):
        _, text, _ = icm.export(self.env, ["docs/offer.md"])
        total = int(text.split("| Total | | ")[1].split(" of ")[0].replace(",", ""))
        self.assertEqual(total, len(text))
        self.assertIn("of 32,000", text)

    def test_oversize_export_fails_without_dropping_anything(self):
        with self.assertRaisesRegex(ContextError, "exceeds 500 characters"):
            icm.export(self.env, ["docs/offer.md"], max_chars=500)

    def test_selection_is_required(self):
        with self.assertRaisesRegex(ContextError, "explicit --select"):
            icm.export(self.env, [])

    def test_export_writes_nothing(self):
        before = self.snapshot()
        icm.export(self.env, ["docs/offer.md"], with_prompt=True, task="x")
        self.assertEqual(before, self.snapshot())


class PromptTests(ExportBase):
    def test_parts_are_copied_verbatim_and_files_are_added(self):
        self.write("CLAUDE.md", CLAUDE)
        self.write("CONTEXT.md", "# Context\n\nDomain.\n")
        packet, text, unfilled = icm.export(self.env, ["docs/offer.md"], with_prompt=True, task="Draft the scope.")
        self.assertEqual(unfilled, [])
        self.assertIn("## 1. Identity\nYou are a careful engineer.\n", text)
        self.assertIn("## 2. Task\nDraft the scope.\n", text)
        self.assertIn("## 4. Constraints\n- No network.\n", text)
        self.assertIn("## 5. Format\nA patch and three lines.\n", text)
        roles = {f["path"]: f["role"] for f in packet["files"]}
        self.assertEqual((roles["CLAUDE.md"], roles["CONTEXT.md"]), ("control", "artifact"))
        self.assertIn("### CLAUDE.md (role control; placed by role control, added by --with-prompt)", text)
        self.assertIn("### CONTEXT.md (role artifact; placed by --with-prompt, project context file)", text)
        self.assertIn("policy.md wins", text)
        self.assertIn("also counted under Standing instructions", text)

    def test_missing_parts_become_todo_and_are_reported(self):
        self.write("CLAUDE.md", "# Rules\n\n## Identity\nYou are an engineer.\n")
        _, text, unfilled = icm.export(self.env, ["docs/offer.md"], with_prompt=True)
        self.assertEqual(unfilled, ["2 Task", "4 Constraints", "5 Format"])
        self.assertIn("TODO: state the task", text)
        self.assertIn("TODO: CLAUDE.md has no `## Constraints` section", text)

    def test_spanish_headings_are_accepted(self):
        self.write("CLAUDE.md", "# Reglas\n\n## Identidad\nEres ingeniera.\n\n## Restricciones\nSin red.\n\n## Formato\nUn parche.\n")
        _, text, unfilled = icm.export(self.env, ["docs/offer.md"], with_prompt=True, task="t")
        self.assertEqual(unfilled, [])
        self.assertIn("Eres ingeniera.", text)

    def test_agents_file_is_used_when_claude_only_imports_it(self):
        self.write("CLAUDE.md", "<!-- relay-claude -->\n@AGENTS.md\n<!-- /relay-claude -->\n")
        self.write("AGENTS.md", CLAUDE)
        packet, text, unfilled = icm.export(self.env, ["docs/offer.md"], with_prompt=True, task="t")
        paths = [f["path"] for f in packet["files"]]
        self.assertIn("AGENTS.md", paths)
        self.assertNotIn("CLAUDE.md", paths)
        self.assertIn("only imports AGENTS.md", text)
        self.assertEqual(unfilled, [])

    def test_agents_file_alone_is_the_fallback(self):
        self.write("AGENTS.md", CLAUDE)
        packet, _, _ = icm.export(self.env, ["docs/offer.md"], with_prompt=True, task="t")
        self.assertIn("AGENTS.md", [f["path"] for f in packet["files"]])

    def test_no_standing_file_still_exports_with_a_note(self):
        _, text, unfilled = icm.export(self.env, ["docs/offer.md"], with_prompt=True, task="t")
        self.assertIn("No CLAUDE.md or AGENTS.md in the project root", text)
        self.assertEqual(unfilled, ["1 Identity", "4 Constraints", "5 Format"])
        self.assertNotIn("policy.md wins", text)

    def test_denied_standing_file_is_reported_not_dropped_silently(self):
        self.write("CLAUDE.md", CLAUDE)
        (self.root / ".context/relay").mkdir(parents=True, exist_ok=True)
        (self.root / ".context/relay/settings.json").write_text(json.dumps({"deny_paths": ["CLAUDE.md"]}))
        env = Environment(self.root)
        packet, text, _ = icm.export(env, ["docs/offer.md"], with_prompt=True, task="t")
        self.assertNotIn("CLAUDE.md", [f["path"] for f in packet["files"]])
        self.assertIn("Not included: CLAUDE.md", text)

    def test_prompt_packet_differs_from_plain_only_by_added_files(self):
        self.write("CLAUDE.md", CLAUDE)
        plain, _ = self.env.context(["docs/offer.md"])
        packet, _, _ = icm.export(self.env, ["docs/offer.md"], with_prompt=True, task="t")
        extra = [f["path"] for f in packet["files"] if f["path"] not in {x["path"] for x in plain["files"]}]
        self.assertEqual(extra, ["CLAUDE.md"])


class CliTests(ExportBase):
    def test_task_free_prompt_end_to_end_reports_unfilled_on_stderr(self):
        self.write("CLAUDE.md", CLAUDE)
        code, out, err = self.run_cli("context", "--select", "docs/offer.md", "--with-prompt")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("# Request"))
        self.assertIn("Request parts still to fill: 2 Task", err)

    def test_out_file_is_new_and_outside_context(self):
        target = self.root / "task.md"
        code, out, _ = self.run_cli("context", "--select", "docs/offer.md", "--budget", "--out", str(target))
        self.assertEqual(code, 0)
        self.assertIn("# Context budget", target.read_text())
        self.assertEqual(self.run_cli("context", "--select", "docs/offer.md", "--budget", "--out", str(target))[0], 2)

    def test_refusals(self):
        cases = [("--run", "r", "--budget"), ("--format", "json", "--budget"), ("--with-prompt", "--format", "json"),
                 ("--task", "x"), ("--example", "examples/good.md"), ("--history", "docs/offer.md")]
        for extra in cases:
            with self.subTest(extra=extra):
                self.assertEqual(self.run_cli("context", "--select", "docs/offer.md", *extra)[0], 2)


if __name__ == "__main__":
    unittest.main()
