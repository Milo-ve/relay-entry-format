"""`relay tidy --apply` and `--undo`. Synthetic fixtures only."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from okf_icm import relay_cli, settings, tidy, tidy_apply
from okf_icm.storage import ContextError
from okf_icm.workspace import initialize

LONG = ("Kiln firing schedules depend on clay body thickness glaze chemistry cone rating "
        "ramp speed soak duration cooling curve ventilation shelf spacing and witness placement.")
OTHER = ("Invoice reconciliation compares ledger entries against bank statements, flags unmatched "
         "amounts, and routes exceptions to the approver named in the close calendar every month.")
OLD = time.time() - 90 * 86400


class ApplyCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()

    def write(self, relative: str, text: str, *, old: bool = True) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        if old:
            os.utime(path, (OLD, OLD))
        return path

    def read(self, relative: str) -> str:
        return (self.root / relative).read_bytes().decode("utf-8")

    def exists(self, relative: str) -> bool:
        return (self.root / relative).exists()

    def snapshot(self, skip: str = ".relay-backups") -> dict:
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob("*")
                if p.is_file() and skip not in p.relative_to(self.root).parts}

    def apply(self, **kwargs) -> dict:
        return tidy_apply.apply(self.root, ["docs"], **kwargs)

    def cli(self, *args: str) -> tuple[int, dict | str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = relay_cli.main(["--root", str(self.root), "tidy", *args])
        try:
            return code, json.loads(out.getvalue()), err.getvalue()
        except ValueError:
            return code, out.getvalue(), err.getvalue()


class Duplicates(ApplyCase):
    def setUp(self):
        super().setUp()
        self.write("docs/index.md", "# Index\n\n- [Firing](firing-copy.md)\n- [Other](other.md)\n")
        self.write("docs/firing.md", f"# Firing\n\n{LONG}\n")
        self.write("docs/firing-copy.md", f"# Firing\r\n\r\n{LONG}   \r\n")
        self.write("docs/other.md", f"# Other\n\nSee [firing](firing.md#top) and [again](firing.md).\n\n```\n[x](firing.md)\n```\n")

    def test_the_copy_is_removed_and_every_link_follows_the_kept_file(self):
        result = self.apply()
        self.assertEqual(result["mode"], "applied")
        keep = result["removed"][0]["same_as"]
        gone = result["removed"][0]["path"]
        self.assertNotEqual(keep, gone)
        self.assertFalse(self.exists(gone))
        self.assertTrue(self.exists(keep))
        name = Path(keep).name
        self.assertIn(f"({name})", self.read("docs/index.md"))
        self.assertNotIn(Path(gone).name, self.read("docs/index.md"))
        self.assertIn(f"({name}#top)", self.read("docs/other.md"))  # already pointed at the kept file
        self.assertIn("```\n[x](firing.md)\n```", self.read("docs/other.md"))  # code fences are never rewritten
        self.assertEqual(tidy.scan(self.root, ["docs"])["counts"].get("broken-link", 0), 0)

    def test_undo_restores_every_byte_and_a_second_apply_has_nothing_to_do(self):
        before = self.snapshot()
        done = self.apply()
        self.assertNotEqual(self.snapshot(), before)
        self.assertEqual(self.apply()["mode"], "unchanged")
        undone = tidy_apply.undo(self.root, done["run"])
        self.assertEqual(undone["conflicts"], [])
        self.assertEqual(self.snapshot(), before)
        with self.assertRaises(ContextError):
            tidy_apply.undo(self.root, done["run"])  # a run is undone once

    def test_dry_run_changes_nothing_and_writes_no_backup(self):
        before = self.snapshot(skip="nothing")
        result = self.apply(dry_run=True)
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(len(result["removed"]), 1)
        self.assertEqual(self.snapshot(skip="nothing"), before)
        self.assertFalse(self.exists(".relay-backups"))

    def test_undo_leaves_a_file_edited_since_instead_of_overwriting_it(self):
        done = self.apply()
        edited = self.root / "docs/index.md"
        edited.write_text(edited.read_text(encoding="utf-8") + "\nA new line.\n", encoding="utf-8")
        undone = tidy_apply.undo(self.root, "latest")
        self.assertEqual(undone["conflicts"], ["docs/index.md"])
        self.assertIn("A new line.", self.read("docs/index.md"))
        self.assertTrue(self.exists(done["removed"][0]["path"]))  # the removed file did come back

    def test_a_file_changed_after_it_was_read_stops_the_whole_run(self):
        real = tidy_apply._plan

        def plan_then_edit(*args, **kwargs):
            plan = real(*args, **kwargs)
            self.write("docs/index.md", "# Index\n\nEdited meanwhile.\n")
            return plan
        before = self.snapshot()
        with patch.object(tidy_apply, "_plan", plan_then_edit), self.assertRaises(ContextError):
            self.apply()
        after = self.snapshot()
        self.assertEqual({k: v for k, v in after.items() if k != "docs/index.md"},
                         {k: v for k, v in before.items() if k != "docs/index.md"})

    def test_a_run_that_would_add_broken_links_undoes_itself(self):
        before = self.snapshot()
        with patch.object(tidy_apply, "_broken", side_effect=[0, 3]):
            result = self.apply()
        self.assertEqual(result["mode"], "rolled-back")
        self.assertEqual(self.snapshot(), before)

    def test_a_file_that_project_state_names_is_never_removed(self):
        initialize(self.root, "Test")
        self.write(".context/notes.txt", "Selected source: docs/firing-copy.md and docs/firing.md\n")
        result = self.apply()
        self.assertEqual(result["mode"], "unchanged")
        self.assertEqual(result["skipped"][0]["reason"], "named-by-project-state")
        self.assertTrue(self.exists("docs/firing-copy.md") and self.exists("docs/firing.md"))


class Orphans(ApplyCase):
    def setUp(self):
        super().setUp()
        self.write("README.md", "# Project\n\n- [Docs](docs/index.md)\n")
        self.write("docs/index.md", "# Index\n\n- [Kept](kept.md)\n")
        self.write("docs/kept.md", f"# Kept\n\n{LONG}\n")
        self.write("docs/lost.md", f"# Lost\n\n{OTHER}\n\nBack to [readme](../README.md) and [kept](kept.md) and [pic](../img/a%20b.png).\n")
        self.write("docs/recent.md", f"# Recent\n\nA note written today.\n", old=False)

    def test_an_old_unlinked_file_is_archived_with_its_own_links_re_spelled(self):
        result = self.apply()
        self.assertEqual([a["to"] for a in result["archived"]], ["docs/archive/lost.md"])
        self.assertFalse(self.exists("docs/lost.md"))
        moved = self.read("docs/archive/lost.md")
        self.assertIn("(../../README.md)", moved)
        self.assertIn("(../kept.md)", moved)
        self.assertIn("(../../img/a%20b.png)", moved)
        self.assertTrue(self.exists("docs/recent.md"))
        self.assertIn({"kind": "orphan", "paths": ["docs/recent.md"], "reason": "changed-in-last-30-days"}, result["skipped"])

    def test_undo_puts_it_back_and_removes_the_archive_folder_it_made(self):
        before = self.snapshot()
        done = self.apply()
        tidy_apply.undo(self.root, done["run"])
        self.assertEqual(self.snapshot(), before)
        self.assertFalse(self.exists("docs/archive"))

    def test_a_taken_archive_name_is_a_skip_not_an_overwrite(self):
        self.write("docs/archive/LOST.md", "# Older\n")
        result = self.apply()
        self.assertTrue(self.exists("docs/lost.md"))
        self.assertIn("archive-name-taken", [s["reason"] for s in result["skipped"]])

    def test_settings_can_turn_orphans_off_or_restrict_the_actions(self):
        initialize(self.root, "Test")
        (self.root / ".context/relay").mkdir(exist_ok=True)
        (self.root / ".context/relay/settings.json").write_text(json.dumps({"tidy_orphan_days": 0}), encoding="utf-8")
        self.assertEqual(self.apply()["mode"], "unchanged")
        (self.root / ".context/relay/settings.json").write_text(json.dumps({"tidy_actions": ["broken-link"]}), encoding="utf-8")
        self.assertEqual(self.apply()["mode"], "unchanged")
        self.assertTrue(self.exists("docs/lost.md"))

    def test_uncommitted_files_in_git_are_left_alone(self):
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        run = lambda *a: subprocess.run(["git", "-C", str(self.root), *a], check=True, capture_output=True)
        run("init", "-q")
        run("add", "docs/index.md", "docs/kept.md", "README.md")
        run("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "x")
        result = self.apply()
        self.assertTrue(self.exists("docs/lost.md"))  # untracked: someone is still working on it
        self.assertIn("uncommitted-changes", [s["reason"] for s in result["skipped"]])

    def test_entry_files_indexes_controls_and_knowledge_are_never_moved(self):
        initialize(self.root, "Test")
        self.write("AGENTS.md", "# Rules\n")
        self.write("docs/log.md", "# Log\n")
        result = tidy_apply.apply(self.root, [".", ".context/knowledge"])
        moved = {a["path"] for a in result["archived"]}
        self.assertFalse(moved & {"AGENTS.md", "docs/log.md", ".context/ENTRY.md", ".context/policy.md", ".context/project.md"})
        self.assertTrue(all(not p.startswith(".context/") for p in moved))


class Links(ApplyCase):
    def test_a_broken_link_with_one_match_is_repaired_and_an_ambiguous_one_is_not(self):
        self.write("docs/index.md", "# Index\n\n- [A](gone/alpha.md#top)\n- [B](gone/beta.md)\n- [C](gone/gamma.md)\n")
        self.write("docs/guides/alpha.md", f"# Alpha\n\n{LONG}\n")
        self.write("docs/guides/beta.md", f"# Beta\n\n{OTHER}\n")
        self.write("docs/more/beta.md", "# Beta again\n\nDifferent words entirely about pottery wheels and trimming tools.\n")
        result = self.apply()
        text = self.read("docs/index.md")
        self.assertIn("(guides/alpha.md#top)", text)
        self.assertIn("(gone/beta.md)", text)
        self.assertIn("(gone/gamma.md)", text)
        reasons = {tuple(s["paths"]): s["reason"] for s in result["skipped"] if s["kind"] == "broken-link"}
        self.assertEqual(reasons[("docs/index.md",)], "no-single-match")

    def test_a_denied_file_is_neither_read_nor_moved_nor_named(self):
        initialize(self.root, "Test")
        (self.root / ".context/relay").mkdir(exist_ok=True)
        (self.root / ".context/relay/settings.json").write_text(json.dumps({"deny_paths": ["docs/private/*"]}), encoding="utf-8")
        self.write("docs/index.md", "# Index\n")
        self.write("docs/private/secret.md", f"# Secret\n\n{LONG}\n")
        self.write("docs/private/secret-copy.md", f"# Secret\n\n{LONG}\n")
        result = self.apply()
        self.assertTrue(self.exists("docs/private/secret.md") and self.exists("docs/private/secret-copy.md"))
        self.assertNotIn("secret", json.dumps(result))


class Command(ApplyCase):
    def test_apply_dry_run_and_undo_through_the_command_line(self):
        self.write("docs/index.md", "# Index\n\n- [One](one.md)\n")
        self.write("docs/one.md", f"# One\n\n{LONG}\n")
        self.write("docs/two.md", f"# One\n\n{LONG}\n")
        code, dry, _ = self.cli("--path", "docs", "--apply", "--dry-run")
        self.assertEqual((code, dry["mode"]), (0, "dry-run"))
        self.assertTrue(self.exists("docs/two.md"))
        code, done, _ = self.cli("--path", "docs", "--apply")
        self.assertEqual((code, done["mode"]), (0, "applied"))
        self.assertFalse(self.exists("docs/two.md"))
        self.assertIn(done["run"], done["undo"])
        code, undone, _ = self.cli("--undo", "latest")
        self.assertEqual((code, undone["restored"]), (0, 1))
        self.assertTrue(self.exists("docs/two.md"))

    def test_flags_that_do_not_belong_together_are_refused(self):
        self.write("docs/index.md", "# Index\n")
        for args in (["--dry-run"], ["--apply", "--brief"], ["--apply", "--undo", "latest"]):
            self.assertNotEqual(self.cli("--path", "docs", *args)[0], 0, args)

    def test_a_run_id_cannot_name_a_path(self):
        with self.assertRaises(ContextError):
            tidy_apply.undo(self.root, "../../etc")

    def test_plain_report_still_changes_nothing(self):
        self.write("docs/index.md", "# Index\n")
        self.write("docs/a.md", f"# A\n\n{LONG}\n")
        self.write("docs/b.md", f"# A\n\n{LONG}\n")
        before = self.snapshot(skip="nothing")
        self.cli("--path", "docs")
        self.assertEqual(self.snapshot(skip="nothing"), before)


class Settings(unittest.TestCase):
    def test_values_are_validated(self):
        for key, bad in (("tidy_orphan_days", -1), ("tidy_orphan_days", True), ("tidy_orphan_days", 99999),
                         ("tidy_actions", ["delete-everything"]), ("tidy_actions", ["orphan", "orphan"])):
            with self.assertRaises(ContextError, msg=f"{key}={bad}"):
                settings._check(key, bad)
        self.assertEqual(settings._check("tidy_actions", []), [])
        self.assertEqual(settings.DEFAULTS["tidy_orphan_days"], 30)


if __name__ == "__main__":
    unittest.main()
