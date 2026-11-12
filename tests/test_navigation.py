"""Safety, determinism, budget accounting and explicit stage navigation."""
from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from okf_icm import knowledge, navigation, relay_cli
from okf_icm.packets import headings, section
from okf_icm.storage import ContextError
from okf_icm.tasks import Tasks
from okf_icm.workspace import Workspace, initialize


class NavigateCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        initialize(self.root, "Synthetic navigation checks", minimal=True)
        self.ws = Workspace(self.root)
        self.bundle = self.root / ".context/knowledge"

    def concept(self, name, title, body, **extra):
        meta = {"type": "Reference", "title": title, "tags": [], "status": "stable",
                "verified": {"by": "human:fixture", "at": "2020-01-01T00:00:00Z"},
                "stale_after": "2099-01-01T00:00:00Z", **extra}
        path = self.bundle / (name + ".md")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(knowledge.serialize(meta, body), encoding="utf-8")
        return path

    def settings(self, **values):
        path = self.root / ".context/relay/settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(values))

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file()}

    def test_heading_listing_matches_selector_and_existing_fence_rules(self):
        text = "# Title\n~~~\n## Hidden\n~~~\n## Real ###\nx\n```py\n## Hidden too\n```\n## Real\ny\n"
        self.assertEqual(headings(text), ["Title", "Real", "Real"])
        for title in headings(text):
            self.assertTrue(section(text, title))
        self.assertEqual(section(text, "Real"), "## Real ###\nx\n```py\n## Hidden too\n```\n")

    def test_read_only_deterministic_even_when_writer_lock_is_held(self):
        self.concept("orchard", "Orchard", "# Orchard\nAn orchard pruning guide.\n")
        (self.root / ".context/write.lock").write_text("held")
        before = self.snapshot()
        first = navigation.navigate(self.ws, "orchard pruning")
        second = navigation.navigate(self.ws, "orchard pruning")
        self.assertEqual(first, second)
        self.assertTrue(first["candidates"])
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.root / ".context/relay/tasks").exists())

    def test_filters_before_reads_and_hides_excluded_targets_and_indexes(self):
        self.settings(deny_paths=["private", "vault"])
        self.concept("orchard", "Orchard", "# Orchard\n[private orchard](private/secret.md) "
                     "[sensitive orchard](.env-record.md) [vault orchard](vault/missing.md)\n")
        private = self.concept("private/secret", "Orchard secrets", "# Orchard secrets\n")
        self.concept(".env-record", "Orchard secret environment", "# Orchard\n")
        (self.bundle / "alias.md").symlink_to(private)
        (self.bundle / "index.md").write_text("[Orchard private secret](private/secret.md)\n")
        real_read = Path.read_text
        real_bytes = Path.read_bytes
        touched = []

        def check(path, *args, **kwargs):
            touched.append(path)
            self.assertNotIn("private", path.relative_to(self.root).parts)
            self.assertFalse(path.name.startswith(".env"))
            self.assertNotEqual(path.name, "alias.md")
            return real_read(path, *args, **kwargs)

        def check_bytes(path, *args, **kwargs):
            self.assertNotIn("private", path.relative_to(self.root).parts)
            self.assertFalse(path.name.startswith(".env"))
            self.assertNotEqual(path.name, "alias.md")
            return real_bytes(path, *args, **kwargs)

        with patch.object(Path, "read_text", check), patch.object(Path, "read_bytes", check_bytes):
            result = navigation.navigate(self.ws, "orchard")
        text = json.dumps(result)
        self.assertNotIn("private", text)
        self.assertNotIn("vault", text)
        self.assertNotIn(".env-record", text)
        self.assertNotIn("alias.md", text)
        self.assertTrue(touched)

    def test_escaping_links_and_symlinks_are_not_followed(self):
        outside = self.root / "outside.md"
        outside.write_text("not a concept")
        self.concept("orchard", "Orchard", "# Orchard\n[orchard outside](../../../../outside.md)\n")
        (self.bundle / "escape.md").symlink_to(outside)
        result = navigation.navigate(self.ws, "orchard")
        self.assertNotIn("outside.md", json.dumps(result))
        self.assertNotIn("escape.md", json.dumps(result))

    def test_stage_inputs_are_first_and_slugs_become_exact_titles(self):
        self.concept("orchard", "Orchard", "# Orchard\n## Pruning season\nWinter pruning.\n## Harvest\nFall.\n")
        self.concept("recipe", "Recipe", "# Recipe\n## Jam recipe\nFruit and sugar.\n")
        contract = self.ws.path(self.ws.stage("01-work")["contract"])
        contract.write_text("# Work\n## Inputs\n`.context/knowledge/recipe.md#jam-recipe`\n"
                            "## Process\n`.context/knowledge/absent.md`\n")
        before = self.snapshot()
        result = navigation.navigate(self.ws, "orchard pruning", stage="01-work")
        first = result["candidates"][0]
        self.assertEqual(first["select"], ".context/knowledge/recipe.md#Jam recipe")
        self.assertTrue(any(w["code"] == "contract_named" for w in first["why"]))
        self.assertEqual(self.snapshot(), before)
        with self.assertRaises(ContextError):
            navigation.navigate(self.ws, "orchard", stage="unknown")

    def test_budget_is_exact_task_packet_delta_and_never_overflows(self):
        self.concept("orchard", "Orchard", "# Orchard\nUnicode café \"fruit\" \\ branches.\n")
        result = navigation.navigate(self.ws, "orchard")
        candidate = result["candidates"][0]
        tasks = Tasks(self.root)
        base = {"files": tasks.files([])}
        full = {"files": tasks.files([candidate["select"]])}
        delta = len(Tasks.render_packet(full)) - len(Tasks.render_packet(base))
        self.assertEqual(candidate["characters"], delta)
        exact = navigation.navigate(self.ws, "orchard", max_chars=delta)
        self.assertEqual(exact["budget"]["used"], delta)
        small = navigation.navigate(self.ws, "orchard", max_chars=delta - 1)
        self.assertFalse(small["candidates"])
        self.assertEqual(small["left_out"][0]["reason"]["code"], "over_budget")
        self.assertLessEqual(small["budget"]["used"], delta - 1)

    def test_cap_sections_duplicates_and_source_hashes(self):
        path = self.concept("orchard", "Orchard", "# Orchard\n## Pruning\nCut branches.\n## History\n" + "x" * 2300)
        # CRLF is normalized as packet content, but hashes identify original bytes.
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        result = navigation.navigate(self.ws, "orchard pruning")
        self.assertEqual(result["candidates"][0]["select"], ".context/knowledge/orchard.md#Pruning")
        self.assertLessEqual(result["candidates"][0]["raw_characters"], 2000)
        self.assertEqual(result["candidates"][0]["characters"],
                         len(Tasks.render_packet({"files": Tasks(self.root).files([result["candidates"][0]["select"]])}))
                         - len(Tasks.render_packet({"files": Tasks(self.root).files([])})))
        self.concept("duplicate", "Orchard duplicate", "# Orchard\n## Pruning\nA.\n## Pruning\nB.\n")
        dup = navigation.navigate(self.ws, "orchard pruning")
        candidate = next(c for c in dup["candidates"] if "duplicate.md" in c["select"])
        self.assertNotIn("#", candidate["select"])
        self.assertIn("duplicate_heading", [w["code"] for w in candidate["warnings"]])

    def test_oversized_sources_are_reported_without_truncation(self):
        self.concept("orchard", "Orchard", "# Orchard\n" + "x" * 2100)
        result = navigation.navigate(self.ws, "orchard")
        self.assertFalse(result["candidates"])
        self.assertEqual(result["left_out"][0]["reason"]["code"], "source_cap")
        self.assertGreater(result["left_out"][0]["raw_characters"], 2000)

    def test_stale_only_is_flagged_and_covered_hazard_is_omitted(self):
        self.concept("contacts", "Orchard contacts", "# Contacts\nOrchard gardener phone.\n", stale_after="2020-01-01T00:00:00Z")
        result = navigation.navigate(self.ws, "orchard gardener contact")
        self.assertEqual(result["candidates"][0]["signals"]["freshness"], "stale")
        self.assertIn("signals", [w["code"] for w in result["candidates"][0]["warnings"]])
        self.concept("current", "Orchard contacts", "# Contacts\nOrchard gardener phone.\n")
        result = navigation.navigate(self.ws, "orchard gardener contact")
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["left_out"][0]["reason"]["code"], "covered_hazard")

    def test_one_hop_fragments_and_no_recursive_walk(self):
        self.concept("orchard", "Orchard", "# Orchard\n[orchard tools](tools.md#kit)\n")
        self.concept("tools", "Tools", "# Tools\n## Kit\n[orchard](deep.md)\n")
        self.concept("deep", "Deep", "# Deep\nA hidden orchard mention.\n")
        result = navigation.navigate(self.ws, "orchard")
        values = [c["select"] for c in result["candidates"]]
        self.assertIn(".context/knowledge/tools.md#Kit", values)
        self.assertNotIn(".context/knowledge/deep.md", values)

    def test_missing_link_and_gap_without_guess(self):
        self.concept("orchard", "Orchard", "# Orchard\n[Fermentation](missing.md)\n")
        result = navigation.navigate(self.ws, "fermentation")
        self.assertFalse(result["candidates"])
        self.assertIn("no_coverage", [g["code"] for g in result["gaps"]])
        self.assertIn("missing_link", [g["code"] for g in result["gaps"]])

    def test_accents_invalid_metadata_language_and_cli_sorted_json(self):
        self.concept("cafe", "Café", "# Café\nCafé fuerte.\n")
        self.concept("invalid", "Café", "# Café\n", tags="wrong type")
        self.settings(language="es")
        result = navigation.navigate(self.ws, "cafe")
        self.assertEqual(len(result["candidates"]), 1)
        self.assertIn("candidatos", result["notes"][0]["text"])
        out, err = io.StringIO(), io.StringIO()
        before = self.snapshot()
        with redirect_stdout(out), redirect_stderr(err):
            code = relay_cli.main(["--root", str(self.root), "navigate", "cafe", "--limit", "1"])
        self.assertEqual(code, 0, err.getvalue())
        self.assertIn("experimentales", err.getvalue())
        parsed = json.loads(out.getvalue())
        self.assertEqual(out.getvalue(), json.dumps(parsed, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        self.assertEqual(self.snapshot(), before)
        self.assertNotIn("invalid", out.getvalue())
        for kwargs in ({"max_chars": 0}, {"max_chars": True}, {"limit": 0}, {"limit": 101}):
            with self.assertRaises(ContextError):
                navigation.navigate(self.ws, "cafe", **kwargs)
        with self.assertRaises(ContextError):
            navigation.navigate(self.ws, " ")

    def test_cli_suggestions_feed_explicit_task_packet_and_remain_versioned(self):
        source = self.concept("orchard", "Orchard", "# Orchard\n## Pruning\nCut dead branches.\n## Harvest\nPick ripe fruit.\n")

        def command(*args):
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                code = relay_cli.main(["--root", str(self.root), *args])
            self.assertEqual(code, 0, err.getvalue())
            return json.loads(out.getvalue())

        before = self.snapshot()
        suggestion = command("navigate", "orchard pruning")["candidates"][0]
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(suggestion["select"], ".context/knowledge/orchard.md#Pruning")
        opened = command("start", "pruning", "--goal", "Summarize pruning", "--accept", "Source-backed summary",
                         "--select", suggestion["select"])
        self.assertEqual(opened["status"], "ready")
        self.assertIsNone(opened["review"])
        packet_path = self.root / "handoff.md"
        command("context", "pruning", "--out", str(packet_path))
        packet = Tasks(self.root).packet(Tasks(self.root).load("pruning"))
        selected = [f for f in packet["files"] if f["role"] == "knowledge"]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["section"], "Pruning")
        self.assertIn("Cut dead branches", selected[0]["content"])
        self.assertNotIn("Pick ripe fruit", selected[0]["content"])
        self.assertIn(opened["packet_id"], packet_path.read_text())
        # Even edits outside the selected section still change the full-file hash.
        source.write_text(source.read_text().replace("ripe fruit", "ripe apples"), encoding="utf-8")
        changed = command("show", "pruning")
        self.assertEqual(changed["freshness"], "changed")
        self.assertEqual(changed["status"], "needs_review")
        self.assertIsNone(changed["review"])
