from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from okf_icm import knowledge as k
from okf_icm.packets import build_packet
from okf_icm.storage import ContextError, atomic_write
from okf_icm.workspace import Workspace, initialize


class KnowledgeCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        initialize(self.root, "Knowledge")
        self.ws = Workspace(self.root)
        atomic_write(self.root / "body.md", "# Decision\nUse a local CLI.\n")
        atomic_write(self.root / "evidence.md", "Checked against the design document.\n")

    def add(self, cid="decisions/local-cli"):
        return k.add(self.ws, cid, "Local CLI", "Decision", "body.md", ["https://example.org/design"])

    def test_type_only_is_valid_okf(self):
        self.assertEqual(k.validate_meta({"type": "Custom Type"}), [])

    def test_duplicate_yaml_keys_refused(self):
        with self.assertRaises(ContextError):
            k.parse_concept("---\ntype: A\ntype: B\n---\n")

    def test_unsafe_yaml_never_executes(self):
        with self.assertRaises(ContextError):
            k.parse_concept("---\ntype: !!python/object/apply:os.system ['echo unsafe']\n---\n")

    def test_unknown_fields_survive_promotion(self):
        self.add()
        path = k.concept_path(self.ws, "decisions/local-cli")
        meta, body = k.parse_concept(path.read_text())
        meta["custom_extension"] = {"owner": "team:research"}
        path.write_text(k.serialize(meta, body))
        k.promote(self.ws, "decisions/local-cli", "evidence.md", "process:review", "Read design and checked claim", True)
        current, _ = k.parse_concept(path.read_text())
        self.assertEqual(current["custom_extension"], meta["custom_extension"])

    def test_add_is_draft_and_cannot_overwrite(self):
        self.add()
        report = k.inspect_bundle(self.ws)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["concepts"][0]["trust"], "unverified")
        self.assertEqual(report["concepts"][0]["status"], "draft")
        with self.assertRaises(FileExistsError):
            self.add()

    def test_reserved_names_and_traversal_refused(self):
        for cid in ("index", "domain/log", "../escape", "/absolute", "Uppercase", "x//y"):
            with self.subTest(cid=cid), self.assertRaises(ContextError):
                self.add(cid)

    def test_timestamps_require_timezone(self):
        for value in ("2026-11-07", "2026-11-07T10:00:00", "garbage"):
            self.assertTrue(k.validate_meta({"type": "Metric", "stale_after": value}))
        self.assertEqual(k.validate_meta({"type": "Metric", "stale_after": "2026-11-07T10:00:00Z"}), [])

    def test_verifier_mapping_and_list_are_supported(self):
        event = {"by": "human:milo", "at": "2026-11-07T10:00:00Z"}
        self.assertEqual(k.trust({"verified": event}), "human-reviewed")
        self.assertEqual(k.trust({"verified": [event]}), "human-reviewed")
        self.assertEqual(k.validate_meta({"type": "Decision", "verified": event}), [])

    def test_promotion_requires_actual_explicit_assertion(self):
        self.add()
        for confirmed, note, reviewer in ((False, "Checked", "process:review"), (True, "", "process:review"), (True, "Checked", "human:milo")):
            with self.subTest(reviewer=reviewer, note=note), self.assertRaises(ContextError):
                k.promote(self.ws, "decisions/local-cli", "evidence.md", reviewer, note, confirmed)

    def test_evidence_is_preserved_inside_bundle(self):
        self.add()
        result = k.promote(self.ws, "decisions/local-cli", "evidence.md", "process:review", "Checked design source", True)
        (self.root / "evidence.md").unlink()
        path = k.concept_path(self.ws, result["evidence"])
        self.assertIn("Checked against the design", path.read_text())
        self.assertEqual(k.inspect_bundle(self.ws)["errors"], [])
        self.assertEqual(result["trust"], "machine-confirmed")

    def test_promotion_requires_sources_and_fresh_concept(self):
        k.add(self.ws, "no-source", "No source", "Decision", "body.md", [])
        with self.assertRaisesRegex(ContextError, "at least one source"):
            k.promote(self.ws, "no-source", "evidence.md", "process:review", "Checked", True)
        self.add()
        path = k.concept_path(self.ws, "decisions/local-cli")
        meta, body = k.parse_concept(path.read_text())
        meta["stale_after"] = "2000-01-01T00:00:00Z"
        path.write_text(k.serialize(meta, body))
        with self.assertRaisesRegex(ContextError, "freshness"):
            k.promote(self.ws, "decisions/local-cli", "evidence.md", "process:review", "Checked", True)

    def test_broken_links_warn_but_do_not_break_okf(self):
        self.add()
        path = k.concept_path(self.ws, "decisions/local-cli")
        path.write_text(path.read_text() + "\n[Future](/domain/future.md)\n")
        report = k.inspect_bundle(self.ws)
        self.assertEqual(report["errors"], [])
        self.assertTrue(any("Unresolved link" in w["message"] for w in report["warnings"]))

    def test_nested_indices_and_empty_bundle(self):
        k.reindex(self.ws)
        self.add()
        k.reindex(self.ws)
        bundle = self.root / ".context/knowledge"
        self.assertIn("decisions/index.md", (bundle / "index.md").read_text())
        self.assertIn("local-cli.md", (bundle / "decisions/index.md").read_text())
        self.assertEqual(len(k.inspect_bundle(self.ws)["concepts"]), 1)

    def test_invalid_source_and_actor_are_detected(self):
        self.assertTrue(k.validate_meta({"type": "Metric", "sources": [{"title": "Missing resource"}]}))
        self.assertTrue(k.validate_meta({"type": "Metric", "generated": {"by": "anonymous"}}))


if __name__ == "__main__":
    unittest.main()
