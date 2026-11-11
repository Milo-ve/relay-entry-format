"""Synthetic workspace onboarding and distribution checks."""
import json
from pathlib import Path
import tempfile
import unittest

from okf_icm.onboarding import adapt_workspace, install_skill
from okf_icm.storage import ContextError, lock
from okf_icm.workspace import initialize


class OnboardingTests(unittest.TestCase):
    def test_optional_claude_bridge_preserves_crlf_and_backs_up(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = b"# Local Claude guidance\r\nKeep existing rules.\r\n"
            (root / "CLAUDE.md").write_bytes(original)
            preview = adapt_workspace(root, "Synthetic", claude=True)
            self.assertIn("CLAUDE.md", preview["update"])
            self.assertFalse((root / ".relay-backups").exists())
            result = adapt_workspace(root, "Synthetic", apply=True, claude=True)
            self.assertEqual((Path(result["backup"]) / "CLAUDE.md").read_bytes(), original)
            content = (root / "CLAUDE.md").read_bytes()
            self.assertTrue(content.startswith(original))
            self.assertIn(b"@AGENTS.md", content)
            # A checkout converted to CRLF must remain repeatable too.
            for filename in ("AGENTS.md", "CLAUDE.md"):
                path = root / filename
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
            self.assertFalse(adapt_workspace(root, "Synthetic", apply=True, claude=True)["applied"])

    def test_claude_is_opt_in_and_existing_import_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            adapt_workspace(root, "Synthetic", apply=True)
            self.assertFalse((root / "CLAUDE.md").exists())
            original = b"# Shared guidance\r\n@AGENTS.md\r\n"
            (root / "CLAUDE.md").write_bytes(original)
            self.assertFalse(adapt_workspace(root, "Synthetic", apply=True, claude=True)["applied"])
            self.assertEqual((root / "CLAUDE.md").read_bytes(), original)

    def test_existing_workspace_lock_prevents_adaptation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize(root, "Synthetic")
            with lock(root / ".context"):
                with self.assertRaises(ContextError):
                    adapt_workspace(root, "Synthetic", apply=True, claude=True)
                self.assertFalse((root / ".relay-backups").exists())
            self.assertFalse((root / "CLAUDE.md").exists())

    def test_preview_backup_preservation_and_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = b"# Existing instructions\r\nKeep source in lib/.\r\n"
            (root / "AGENTS.md").write_bytes(original)
            (root / "lib").mkdir()
            (root / "lib/source.py").write_text("value = 1\n")
            before = set(root.iterdir())
            preview = adapt_workspace(root, "Synthetic")
            self.assertFalse(preview["applied"])
            self.assertEqual(before, set(root.iterdir()))
            result = adapt_workspace(root, "Synthetic", apply=True)
            backup = Path(result["backup"])
            self.assertEqual((backup / "AGENTS.md").read_bytes(), original)
            manifest = json.loads((backup / "manifest.json").read_text())
            self.assertFalse(manifest["files"][".gitignore"]["existed"])
            self.assertIn({"path": "lib/source.py", "kind": "file"}, manifest["layout"])
            self.assertTrue((root / "AGENTS.md").read_bytes().startswith(original))
            self.assertEqual((root / "lib/source.py").read_text(), "value = 1\n")
            self.assertTrue((root / ".context/ENTRY.md").is_file())
            self.assertFalse(adapt_workspace(root, "Synthetic", apply=True)["applied"])
            self.assertEqual(len(list((root / ".relay-backups").iterdir())), 1)

    def test_existing_state_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initialize(root, "Existing")
            state = root / ".context/runs/previous/state.json"
            state.parent.mkdir()
            state.write_text('{"not_a_checkpoint": true}')
            originals = {p: p.read_bytes() for p in (root / ".context").rglob("*") if p.is_file()}
            adapt_workspace(root, "Do not replace", apply=True)
            self.assertEqual(originals, {p: p.read_bytes() for p in originals})

    def test_incompatible_context_and_symlinks_refused_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".context").mkdir()
            with self.assertRaises(OSError):
                adapt_workspace(root, "Synthetic", apply=True)
            self.assertFalse((root / ".relay-backups").exists())
            (root / ".context").rmdir()
            (root / "target").write_text("untouched")
            try:
                (root / "AGENTS.md").symlink_to(root / "target")
            except OSError:
                self.skipTest("Symlinks unavailable")
            with self.assertRaises(ContextError):
                adapt_workspace(root, "Synthetic", apply=True)
            self.assertEqual((root / "target").read_text(), "untouched")

    def test_install_preserves_existing_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = install_skill(root)
            self.assertTrue(result["changed"])
            self.assertFalse(install_skill(root)["changed"])
            path = Path(result["skill"])
            path.write_text("custom skill")
            with self.assertRaises(ContextError):
                install_skill(root)
            self.assertEqual(path.read_text(), "custom skill")
