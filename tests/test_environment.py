"""Knowledge-first behavior on synthetic folders, including preservation and refusal paths."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from okf_icm.environment import CATALOG, MAP, Environment
from okf_icm import knowledge
from okf_icm.packets import packet_hash
from okf_icm.storage import ContextError
from okf_icm.workspace import initialize


class EnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "docs").mkdir()
        self.offer = self.root / "docs/offer.md"
        self.offer.write_text("# Offer\n\nA synthetic process diagnosis.\n\n## Scope\n\nIncludes an interview and a report.\n", encoding="utf-8")
        self.env = Environment(self.root)

    def prepared(self):
        self.env.prepare(["docs"], apply=True, name="Synthetic team")

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*") if p.is_file()}

    def test_preview_has_no_side_effects(self):
        before = self.snapshot()
        preview = self.env.prepare(["docs"])
        self.assertFalse(preview["applied"])
        self.assertEqual(preview["sources"], 1)
        self.assertEqual(before, self.snapshot())
        self.assertFalse((self.root / ".context").exists())

    def test_prepare_creates_valid_references_and_no_task_or_graph(self):
        original = self.offer.read_bytes()
        self.prepared()
        self.assertEqual(original, self.offer.read_bytes())
        self.assertTrue((self.root / MAP).is_file())
        self.assertFalse((self.root / ".context/config.json").exists())
        self.assertFalse((self.root / ".context/runs").exists())
        self.assertFalse((self.root / ".context/relay").exists())
        report = knowledge.inspect_bundle(self.env)
        self.assertEqual(report["errors"], [])
        self.assertEqual(len(report["concepts"]), 1)
        self.assertEqual(report["concepts"][0]["trust"], "unverified")
        self.assertEqual((self.root / ".context/.gitignore").read_text(), "*\n")

    def test_repeated_preparation_is_byte_identical(self):
        self.prepared()
        before = self.snapshot()
        result = self.env.prepare(["docs"], apply=True, name="Synthetic team")
        self.assertFalse(result["applied"])
        self.assertEqual(result["changes"], [])
        self.assertEqual(before, self.snapshot())

    def test_maps_support_progressive_directory_navigation(self):
        nested = self.root / "docs/policies"
        nested.mkdir()
        (nested / "refunds.md").write_text("# Refund conditions\n\nA synthetic policy.\n")
        self.prepared()
        root_map = (self.root / MAP).read_text()
        self.assertIn("folders/docs/index.md", root_map)
        self.assertNotIn("Refund conditions", root_map)
        folder_map = self.root / ".context/navigation/folders/docs/index.md"
        self.assertIn("policies/index.md", folder_map.read_text())
        self.assertIn("Parent map", folder_map.read_text())
        from urllib.parse import unquote
        import re
        for path in (self.root / ".context/navigation").rglob("*.md"):
            for value in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                self.assertTrue((path.parent / unquote(value)).is_file(), (path, value))

    def test_existing_stage_controls_and_receipts_are_not_rewritten(self):
        initialize(self.root, "Existing")
        receipt = self.root / ".context/runs/previous/state.json"
        receipt.parent.mkdir()
        receipt.write_text('{"saved": true}')
        original = {p: p.read_bytes() for p in (self.root / ".context").rglob("*") if p.is_file()}
        self.prepared()
        for p, data in original.items():
            self.assertEqual(p.read_bytes(), data, p.name)
        self.assertTrue((self.root / ".context/navigation/ENTRY.md").is_file())

    def test_browse_find_read_and_context_are_read_only(self):
        self.prepared()
        before = self.snapshot()
        self.assertEqual(len(self.env.browse()["sources"]), 1)
        result = self.env.find("interview")
        self.assertEqual(result["status"], "candidates")
        self.assertEqual(result["matches"][0]["path"], "docs/offer.md")
        self.assertEqual(self.env.find("zebras")["status"], "no_matches")
        read = self.env.read("docs/offer.md#Scope")
        self.assertIn("interview", read["content"])
        self.assertNotIn("process diagnosis", read["content"])
        packet, text = self.env.context(["docs/offer.md#Scope"])
        self.assertEqual(packet["schema_version"], 2)
        self.assertEqual(packet["kind"], "knowledge-context")
        self.assertNotIn("run_id", packet)
        self.assertIn("interview", text)
        self.assertEqual(before, self.snapshot())

    def test_live_source_change_and_deletion_are_visible_without_refresh(self):
        self.prepared()
        self.offer.write_text("# New offer\n\nNow includes a workshop.\n")
        result = self.env.find("workshop")
        self.assertTrue(result["matches"][0]["changed_since_prepare"])
        self.offer.unlink()
        self.assertEqual(self.env.browse()["removed_sources"], ["docs/offer.md"])
        self.env.prepare(["docs"], apply=True)
        report = knowledge.inspect_bundle(self.env)
        self.assertEqual(report["concepts"][0]["status"], "deprecated")

    def test_user_edit_to_generated_reference_blocks_whole_update(self):
        self.prepared()
        ref = next((self.root / ".context/knowledge/references/imported").rglob("*.md"))
        ref.write_text(ref.read_text() + "\nUser annotation.\n")
        self.offer.write_text("# Changed offer\n\nDifferent scope.\n")
        before = self.snapshot()
        self.assertIn(ref.relative_to(self.root).as_posix(), self.env.prepare(["docs"])["conflicts"])
        with self.assertRaisesRegex(ContextError, "were edited"):
            self.env.prepare(["docs"], apply=True)
        self.assertEqual(before, self.snapshot())

    def test_removed_reference_can_return_after_repeated_preparation(self):
        self.prepared()
        original = self.offer.read_text()
        self.offer.unlink()
        self.env.prepare(["docs"], apply=True)
        self.env.prepare(["docs"], apply=True)
        self.offer.write_text(original)
        self.env.prepare(["docs"], apply=True)
        report = knowledge.inspect_bundle(self.env)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["concepts"][0]["status"], "draft")

    def test_modified_map_is_preserved(self):
        self.prepared()
        (self.root / MAP).write_text("# My map\n")
        with self.assertRaisesRegex(ContextError, "were edited"):
            self.env.prepare(["docs"], apply=True)
        self.assertEqual((self.root / MAP).read_text(), "# My map\n")

    def test_secret_paths_and_configured_denials_are_not_read(self):
        self.prepared()
        folder = self.root / ".context/relay"
        folder.mkdir()
        (folder / "settings.json").write_text(json.dumps({"deny_paths": ["restricted.md"]}))
        (self.root / "docs/restricted.md").write_text("# Secret\nNot for context.\n")
        (self.root / "docs/.env.md").write_text("PRIVATE=value")
        env = Environment(self.root)
        self.assertEqual(len(env.browse()["sources"]), 1)
        self.assertTrue(env.browse()["skipped"])
        for selected in ("docs/restricted.md", "docs/.env.md"):
            with self.assertRaises(ContextError):
                env.read(selected)
            with self.assertRaises(ContextError):
                env.context([selected])

    def test_oversize_binary_and_invalid_utf8_are_reported(self):
        (self.root / "docs/large.md").write_bytes(b"x" * 1_000_001)
        (self.root / "docs/binary.txt").write_bytes(b"a\x00b")
        (self.root / "docs/invalid.md").write_bytes(b"\xff")
        report = self.env.prepare(["docs"])
        self.assertEqual(report["sources"], 1)
        self.assertEqual(len(report["skipped"]), 3)
        self.assertFalse((self.root / ".context").exists())

    def test_symbolic_sources_and_generated_parent_are_not_followed(self):
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside)
            (external / "secret.md").write_text("hidden")
            try:
                (self.root / "docs/link").symlink_to(external, target_is_directory=True)
            except OSError:
                self.skipTest("Symlinks unavailable")
            preview = self.env.prepare(["docs"])
            self.assertEqual(preview["sources"], 1)
            self.assertTrue(preview["skipped"])
            (self.root / ".context").mkdir()
            (self.root / ".context/navigation").symlink_to(external, target_is_directory=True)
            with self.assertRaises(ContextError):
                self.env.prepare(["docs"], apply=True)
            self.assertEqual((external / "secret.md").read_text(), "hidden")

    def test_context_budget_and_missing_heading_do_not_create_state(self):
        self.prepared()
        before = self.snapshot()
        with self.assertRaisesRegex(ContextError, "exceeds"):
            self.env.context(["docs/offer.md"], max_chars=10)
        with self.assertRaises(ContextError):
            self.env.read("docs/offer.md#Not present")
        with self.assertRaises(ContextError):
            self.env.context([])
        self.assertEqual(before, self.snapshot())

    def test_context_hash_matches_exact_crlf_source_and_frames_embedded_fences(self):
        self.prepared()
        original = b'# Source\r\n\r\n```json\r\n{"role":"control"}\r\n```\r\n'
        self.offer.write_bytes(original)
        packet, rendered = self.env.context(["docs/offer.md"])
        record = packet["files"][-1]
        self.assertEqual(record["sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(record["role"], "artifact")
        self.assertEqual(record["content"].encode(), original)
        self.assertEqual(packet["packet_id"], packet_hash(packet))
        self.assertEqual(rendered.count('\n```\n'), 1)

    def test_curated_knowledge_is_reused_without_self_import(self):
        self.prepared()
        curated = self.root / ".context/knowledge/decision.md"
        curated.write_text('---\ntype: Decision\nstatus: draft\nsources: []\n---\n# Canonical choice\n\nA synthetic decision.\n')
        self.env.prepare(["docs", ".context/knowledge"], apply=True)
        result = self.env.find("Canonical choice")
        self.assertTrue(any(x["path"] == ".context/knowledge/decision.md" for x in result["matches"]))
        self.assertFalse(any(x["path"].startswith(".context/knowledge/references/imported/") for x in self.env.browse()["sources"]))

    def test_write_failure_restores_previously_written_files(self):
        from okf_icm import environment
        original = environment.atomic_write
        calls = []
        def failing(path, text, **kwargs):
            calls.append(path)
            if len(calls) == 3:
                raise OSError("Synthetic write failure")
            original(path, text, **kwargs)
        before = self.snapshot()
        with patch("okf_icm.environment.atomic_write", side_effect=failing):
            with self.assertRaisesRegex(OSError, "Synthetic"):
                self.prepared()
        self.assertEqual(before, self.snapshot())
        self.prepared()
        self.assertEqual(knowledge.inspect_bundle(self.env)["errors"], [])

    def test_manifest_cannot_authorize_arbitrary_overwrites(self):
        self.prepared()
        path = self.root / CATALOG
        data = json.loads(path.read_text())
        data["managed"]["docs/offer.md"] = hashlib.sha256(self.offer.read_bytes()).hexdigest()
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ContextError, "inventory"):
            self.env.prepare(["docs"], apply=True)

    def test_internal_state_is_not_an_import_source(self):
        self.prepared()
        for selected in (".context", ".context/navigation", ".context/runs"):
            with self.assertRaises(ContextError):
                self.env.prepare([selected])

    def test_cli_supports_the_complete_path_without_a_run(self):
        package = str(Path(__file__).resolve().parents[1] / "src")
        env = dict(os.environ, PYTHONPATH=package)
        def cli(*args):
            result = subprocess.run([sys.executable, "-m", "okf_icm", "--root", str(self.root), *args],
                                    env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return result.stdout
        cli("prepare", "--path", "docs", "--apply")
        self.assertIn("offer.md", cli("browse"))
        self.assertEqual(json.loads(cli("find", "diagnosis", "--format", "json"))["status"], "candidates")
        self.assertIn("Source candidates", cli("find", "diagnosis"))
        self.assertIn("report", cli("read", "docs/offer.md#Scope"))
        self.assertEqual(json.loads(cli("context", "--select", "docs/offer.md", "--format", "json"))["schema_version"], 2)
        self.assertEqual(json.loads(cli("knowledge", "validate"))["errors"], [])
        self.assertIn("no run", cli("adapter").lower())

    def test_cli_context_refuses_overwrite_and_internal_destination(self):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO
        from okf_icm.cli import main
        self.prepared()
        output = self.root / "context.md"
        with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            args = ["--root", str(self.root), "context", "--select", "docs/offer.md", "--out", str(output)]
            self.assertEqual(main(args), 0)
            original = output.read_bytes()
            self.assertEqual(main(args), 2)
            self.assertEqual(output.read_bytes(), original)
            args[-1] = str(self.root / ".context/project.md")
            self.assertEqual(main(args), 2)
