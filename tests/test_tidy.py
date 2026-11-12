"""`relay tidy`: a read-only report. Synthetic fixtures only."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from okf_icm import knowledge, relay_cli, tidy
from okf_icm.storage import ContextError
from okf_icm.workspace import initialize

LONG = ("Kiln firing schedules depend on clay body thickness glaze chemistry cone rating "
        "ramp speed soak duration cooling curve ventilation shelf spacing and witness placement.")


class TidyCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def kinds(self, result: dict, kind: str) -> list[dict]:
        return [item for item in result["findings"] if item["kind"] == kind]

    def snapshot(self) -> dict:
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def cli(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = relay_cli.main(["--root", str(self.root), "tidy", *args])
        return code, out.getvalue(), err.getvalue()


class PlainFolder(TidyCase):
    """No workspace is needed: any folder of Markdown can be inspected."""

    def test_identical_files_are_grouped_and_the_linked_one_is_kept(self):
        self.write("notes/index.md", "# Index\n\n- [Firing](firing-copy.md)\n")
        self.write("notes/firing.md", f"# Firing\n\n{LONG}\n")
        self.write("notes/firing-copy.md", f"# Firing\r\n\r\n{LONG}   \r\n\r\n")  # line endings and trailing space only
        found = self.kinds(tidy.scan(self.root, ["notes"]), "duplicate-file")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["paths"], ["notes/firing-copy.md", "notes/firing.md"])
        self.assertEqual(found[0]["evidence"]["keep"], "notes/firing-copy.md")
        self.assertIn("notes/firing-copy.md", found[0]["suggestion"])

    def test_near_identical_sections_are_reported_and_unrelated_ones_are_not(self):
        self.write("a.md", f"# A\n\n## Firing\n\n{LONG}\n\n## Glazing\n\nDip the bisque piece briefly, wipe the foot ring, "
                           "let the coat dry fully, then check thickness against a scratched test tile before loading.\n")
        self.write("b.md", f"# B\n\n## Schedule\n\n{LONG} Always.\n")
        found = self.kinds(tidy.scan(self.root, ["."]), "duplicate-section")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["paths"], ["a.md", "b.md"])
        self.assertEqual(found[0]["evidence"]["sections"], ["a.md#Firing", "b.md#Schedule"])
        self.assertGreaterEqual(found[0]["evidence"]["similarity"], tidy.SIMILARITY)

    def test_short_sections_never_match(self):
        self.write("a.md", "# A\n\n## Note\n\nSee the firing guide.\n")
        self.write("b.md", "# B\n\n## Note\n\nSee the firing guide.\n\nExtra line so the files differ.\n")
        self.assertEqual(self.kinds(tidy.scan(self.root, ["."]), "duplicate-section"), [])

    def test_orphans_and_folder_links(self):
        self.write("docs/INDEX.md", "# Index\n\n- [Guide](guide.md)\n- [History](archive/)\n")
        self.write("docs/guide.md", "# Guide\n\nText.\n")
        self.write("docs/lost.md", "# Lost\n\nNobody links here.\n")
        self.write("docs/archive/old.md", "# Old\n\nCovered by the folder link.\n")
        self.write("README.md", "# Project\n\nSee [the front page note](docs/front.md).\n")
        self.write("docs/front.md", "# Front\n\nLinked from the root README, which is outside the scan.\n")
        found = self.kinds(tidy.scan(self.root, ["docs"]), "orphan")
        self.assertEqual([item["paths"] for item in found], [["docs/lost.md"]])

    def test_broken_links_ignore_code_fences_external_targets_and_repeats(self):
        self.write("a.md", "# A\n\n[gone](missing.md) and again [gone](missing.md).\n[web](https://example.invalid/x.md) [top](#a)\n"
                           "```\n[not a link](also-missing.md)\n```\n")
        found = self.kinds(tidy.scan(self.root, ["a.md"]), "broken-link")
        self.assertEqual([item["evidence"]["target"] for item in found], ["missing.md"])

    def test_entry_file_over_budget_is_reported(self):
        self.write("AGENTS.md", "# Rules\n\n" + "x" * tidy.ENTRY_BUDGET)
        self.write("CLAUDE.md", "@AGENTS.md\n")
        self.write("notes/a.md", "# A\n")
        found = self.kinds(tidy.scan(self.root, ["notes"]), "oversize-entry")
        self.assertEqual([item["paths"] for item in found], [["AGENTS.md"]])
        self.assertEqual(found[0]["evidence"]["budget"], tidy.ENTRY_BUDGET)

    def test_section_comparison_bound_is_reported_not_silent(self):
        for index in range(4):
            self.write(f"n{index}.md", f"# N{index}\n\n## Part\n\n{LONG} Variant {index} alpha{index} beta{index} gamma{index}.\n")
        with patch.object(tidy, "MAX_SECTIONS", 2):
            result = tidy.scan(self.root, ["."])
        self.assertIn("2", result["truncated"])

    def test_scan_changes_nothing_and_default_scope_needs_a_bundle(self):
        self.write("notes/a.md", f"# A\n\n{LONG}\n")
        before = self.snapshot()
        code, out, _ = self.cli("--path", "notes")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["scanned"]["files"], 1)
        self.assertEqual(self.snapshot(), before)
        code, _, err = self.cli()
        self.assertEqual(code, 2)
        self.assertIn("--path", err)
        code, _, err = self.cli("--path", "nowhere")
        self.assertEqual(code, 2)
        self.assertIn("nowhere", err)
        with self.assertRaises(ContextError):
            tidy.scan(self.root, ["../outside"])

    def test_note_is_written_once_outside_the_scan_and_never_overwritten(self):
        self.write("notes/a.md", "# A\n\n[gone](missing.md)\n")
        note = self.root / "tidy-report.md"
        code, out, _ = self.cli("--path", "notes", "--out", str(note))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["counts"], {"broken-link": 1, "orphan": 1})
        text = note.read_text(encoding="utf-8")
        self.assertIn("# Tidy report", text)
        self.assertIn("- [ ] `notes/a.md`: ", text)
        code, _, _ = self.cli("--path", "notes", "--out", str(note))
        self.assertEqual(code, 2)
        self.assertEqual(note.read_text(encoding="utf-8"), text)

    def test_brief_keeps_only_kind_paths_and_suggestion(self):
        self.write("notes/a.md", "# A\n\n[gone](missing.md)\n")
        code, out, _ = self.cli("--path", "notes", "--brief")
        self.assertEqual(code, 0)
        for item in json.loads(out)["findings"]:
            self.assertEqual(set(item), {"kind", "paths", "suggestion"})


class InWorkspace(TidyCase):
    def setUp(self):
        super().setUp()
        initialize(self.root, "Synthetic tidy checks", minimal=True)
        self.bundle = self.root / ".context/knowledge"

    def concept(self, name: str, body: str, **extra) -> None:
        meta = {"type": "Reference", "title": name, "tags": [], "status": "stable",
                "verified": {"by": "human:fixture", "at": "2020-01-01T00:00:00Z"},
                "stale_after": "2099-01-01T00:00:00Z", **extra}
        self.write(f".context/knowledge/{name}.md", knowledge.serialize(meta, body))

    def settings(self, **values) -> None:
        self.write(".context/relay/settings.json", json.dumps(values))

    def test_default_scope_is_the_knowledge_bundle_with_its_recorded_signals(self):
        self.concept("current", f"# Current\n\n{LONG}\n")
        self.concept("draft", "# Draft\n\nUnfinished thought about slip casting moulds.\n", status="draft")
        self.write(".context/knowledge/broken.md", "no metadata here\n")
        result = tidy.scan(self.root)
        self.assertEqual(result["scope"], [tidy.BUNDLE])
        self.assertEqual([item["paths"] for item in self.kinds(result, "review-signal")], [[".context/knowledge/draft.md"]])
        self.assertEqual([item["paths"] for item in self.kinds(result, "invalid-concept")], [[".context/knowledge/broken.md"]])

    def test_controls_over_budget_are_reported_together(self):
        self.assertEqual(self.kinds(tidy.scan(self.root), "oversize-entry"), [])
        project = self.root / ".context/project.md"
        project.write_text(project.read_text(encoding="utf-8") + "\n" + "detail " * 500, encoding="utf-8")
        found = self.kinds(tidy.scan(self.root), "oversize-entry")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["paths"], list(tidy.CONTROLS))

    def test_denied_and_secret_paths_are_never_read_or_named(self):
        self.settings(deny_paths=["private"])
        self.write("notes/open.md", f"# Open\n\n{LONG}\n\n[a](private/secret.md) [b](../.env.md)\n")
        self.write("notes/private/secret.md", f"# Secret\n\n{LONG}\n")
        self.write(".env.md", f"# Env\n\n{LONG}\n")
        code, out, err = self.cli("--path", "notes")
        self.assertEqual(code, 0)
        self.assertNotIn("secret", out + err)
        self.assertEqual(json.loads(out)["scanned"]["files"], 1)
        code, out, err = self.cli("--path", "notes/private")
        self.assertEqual(code, 2)
        self.assertEqual(out, "")

    def test_workspace_is_untouched_and_the_note_cannot_go_inside_it(self):
        self.concept("current", f"# Current\n\n{LONG}\n")
        before = self.snapshot()
        code, _, _ = self.cli()
        self.assertEqual(code, 0)
        code, _, err = self.cli("--out", str(self.root / ".context/tidy.md"))
        self.assertEqual(code, 2)
        self.assertIn("outside .context", err)
        self.assertEqual(self.snapshot(), before)

    def test_suggestions_follow_the_language_setting_and_keys_stay_english(self):
        self.settings(language="es")
        self.write("notes/a.md", "# A\n\n[gone](missing.md)\n")
        code, out, _ = self.cli("--path", "notes")
        result = json.loads(out)
        self.assertIn("Solo sugerencias", result["note"])
        self.assertEqual(result["findings"][0]["kind"], "broken-link")
        self.assertIn("vínculo", result["findings"][0]["suggestion"])


if __name__ == "__main__":
    unittest.main()
