"""Synthetic distribution checks; no claims about live client discovery."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

from okf_icm.relay_cli import main
from okf_icm.skill_distribution import export_skill, install_skill, skill_files
from okf_icm.storage import ContextError


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


class SkillDistributionTests(unittest.TestCase):
    def test_complete_install_with_spaces_and_repeat(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "client with spaces" / "skills"
            self.assertTrue(install_skill(destination, "ref")["changed"])
            self.assertEqual(tree(destination / "ref"), skill_files("ref"))
            self.assertFalse(install_skill(destination, "ref")["changed"])
            self.assertFalse((destination / ".context").exists())

    def test_conflicting_resource_refuses_entire_install(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            install_skill(destination, "ref")
            reference = destination / "ref/references/workflow.md"
            reference.write_bytes(b"Customized resource\r\n")
            before = tree(destination)
            with self.assertRaises(ContextError):
                install_skill(destination, "ref")
            self.assertEqual(tree(destination), before)
            reference.unlink()
            before = tree(destination)
            with self.assertRaises(ContextError):
                install_skill(destination, "ref")
            self.assertEqual(tree(destination), before)

    def test_unknown_skill_and_symlinks_do_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ContextError):
                install_skill(root / "absent", "../ref")
            self.assertFalse((root / "absent").exists())
            install_skill(root, "ref")
            path = root / "ref/assets/return.md"
            original = path.read_bytes()
            path.unlink()
            external = root / "custom.md"
            external.write_bytes(original)
            try:
                path.symlink_to(external)
            except OSError:
                self.skipTest("Symlinks unavailable")
            with self.assertRaises(ContextError):
                install_skill(root, "ref")
            self.assertEqual(external.read_bytes(), original)

    def test_zip_and_manual_are_complete_and_never_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "ref.zip"
            export_skill(archive, "ref")
            with ZipFile(archive) as bundle:
                self.assertEqual({name.removeprefix("ref/"): bundle.read(name) for name in bundle.namelist()},
                                 skill_files("ref"))
                bundle.extractall(root / "clean client")
            self.assertEqual(tree(root / "clean client/ref"), skill_files("ref"))
            with self.assertRaises(FileExistsError):
                export_skill(archive, "ref")
            manual = root / "manual.md"
            export_skill(manual, "ref", manual=True)
            body = manual.read_bytes()
            for resource in skill_files("ref").values():
                self.assertIn(resource, body)
            with self.assertRaises(FileExistsError):
                export_skill(manual, "ref", manual=True)
            with self.assertRaises(ContextError):
                export_skill(root / "invalid.md", manual=True)
            self.assertFalse((root / "invalid.md").exists())

    def test_cli_default_selection_exports_and_refusal(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            root = Path(directory)
            self.assertEqual(main(["skill", "--to", str(root)]), 0)
            self.assertEqual(tree(root / "relay-workspace"), skill_files("relay-workspace"))
            self.assertEqual(main(["skill", "--name", "ref", "--to", str(root)]), 0)
            self.assertEqual(main(["skill", "--name", "ref", "--zip", str(root / "ref.zip")]), 0)
            self.assertEqual(main(["skill", "--name", "ref", "--manual", str(root / "manual.md")]), 0)
            self.assertEqual(main(["skill", "--name", "ref", "--zip", str(root / "ref.zip")]), 2)

    def test_new_processes_share_task_identity_without_chat(self):
        # Process boundaries exercise file continuity, not model/client behavior.
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "workspace with spaces"
            root.mkdir()

            def command(*args, code=0):
                result = subprocess.run([sys.executable, "-m", "okf_icm.relay_cli", "--root", str(root), *args],
                                        capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, code, result.stderr)
                return json.loads(result.stdout) if code == 0 else result

            command("workspace", "--apply", "--claude")
            # Both installation targets get the identical host-neutral skill.
            command("skill", "--name", "ref", "--to", str(root / ".claude/skills"))
            command("skill", "--name", "ref", "--to", str(root / ".agents/skills"))
            self.assertEqual(tree(root / ".claude/skills/ref"), tree(root / ".agents/skills/ref"))
            (root / "source.md").write_bytes(b"Synthetic source\r\n")
            command("start", "handoff", "--goal", "Summarize source", "--accept", "Matches source",
                    "--select", "source.md", "--owner", "synthetic-owner", "--reviewer", "synthetic-reviewer")
            state = command("show", "handoff")
            command("context", "handoff", "--out", str(root / "packet.md"))
            (root / "result.md").write_text("Synthetic source summary\n", encoding="utf-8")
            (root / "evidence.md").write_text("Synthetic fixture; no live assistant check.\n", encoding="utf-8")
            command("submit", "handoff", "--output", "result.md", "--evidence", "evidence.md",
                    "--checks", "Fixture file check only", "--next", "Reviewer assesses",
                    "--expected-revision", str(state["revision"]))
            submitted = command("show", "handoff")
            self.assertEqual(submitted["packet_id"], state["packet_id"])
            self.assertEqual(submitted["status"], "awaiting_review")
            self.assertIsNone(submitted["review"])
            command("refresh", "handoff", "--note", "Stale caller", "--expected-revision", str(state["revision"]), code=2)
            (root / "source.md").write_text("Changed synthetic source\n", encoding="utf-8")
            self.assertEqual(command("show", "handoff")["freshness"], "changed")
            command("context", "handoff", code=2)
            self.assertEqual([t["id"] for t in command("list")], ["handoff"])
