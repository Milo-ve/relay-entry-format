"""Jev beyond routing: result signals at submit, candidate relevance in navigate, same-content checks in tidy.

Mocked provider only. Each use adds a signal for a person; none decides anything.
"""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from okf_icm import jev, knowledge, navigation, settings, tidy
from okf_icm.tasks import Tasks
from okf_icm.workspace import Workspace, initialize

KEY = {"TYPESAFE_API_KEY": "test-secret"}


def provider(answer):
    """A stand-in for `jev.nouls`: `answer(name, state)` gives each probability."""
    def reply(state, questions, model="jev-latest"):
        return {"requested_model": model, "status": "ok", "model": "fixture-jev",
                "answers": {name: answer(name, state) for name in questions}, "usage": {"input_tokens": 7}}
    return reply


class Case(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        initialize(self.root, "Synthetic Jev use checks", minimal=True)
        env = patch.dict(os.environ, KEY, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def configure(self, **values):
        path = self.root / ".context/relay/settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(values), encoding="utf-8")

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class EvaluateAtSubmit(Case):
    def setUp(self):
        super().setUp()
        self.write("policy.md", "# Policy\n\nRefunds take five days.\n")
        self.write("out/answer.md", "# Answer\n\nRefunds take two days and are guaranteed.\n")
        self.write("out/evidence.md", "# Evidence\n\nCompared the answer with the policy.\n")
        self.tasks = Tasks(self.root)
        self.tasks.start("faq", "Answer the refund question", ["States the refund time", "Cites the policy"], ["policy.md"])

    def submit(self, answer=lambda name, state: 0.5):
        with patch("okf_icm.jev.nouls", side_effect=provider(answer)) as nouls:
            status = self.tasks.submit("faq", ["out/answer.md"], ["out/evidence.md"], "Compared with the policy", "", "Review")
        return status, nouls

    def test_not_enabled_means_no_request_and_no_advisory(self):
        status, nouls = self.submit()
        nouls.assert_not_called()
        self.assertNotIn("advisory", status)
        self.assertNotIn("advisory", self.tasks.load("faq"))

    def test_signals_are_recorded_beside_the_submission_and_decide_nothing(self):
        self.configure(jev_mode="auto", jev_uses=["evaluate"])
        status, nouls = self.submit(lambda name, state: {"unsupported": 0.85, "criterion_0": 0.9, "criterion_1": 0.2}[name])
        advisory = status["advisory"]
        self.assertEqual((advisory["status"], advisory["flags"]), ("ok", ["unsupported-claim", "criterion-unmet"]))
        self.assertEqual([item["met"] for item in advisory["signals"]["criteria"]], [0.9, 0.2])
        self.assertEqual(status["status"], "awaiting_review")
        self.assertIsNone(status["review"])
        receipt = json.loads((self.root / ".context/relay/tasks/faq/submissions" / f"{status['submission']['submission_id']}.json").read_text())
        self.assertNotIn("advisory", receipt)
        self.assertEqual(receipt["submission_id"], advisory["submission_id"])
        state, questions = nouls.call_args.args
        self.assertEqual([item["path"] for item in state["sources"]], ["policy.md"])
        self.assertEqual([item["path"] for item in state["result"]], ["out/answer.md"])
        self.assertEqual(set(questions), {"unsupported", "criterion_0", "criterion_1"})
        # A flagged result can still be accepted by the reviewer: the signal is advice.
        accepted = self.tasks.review("faq", status["submission"]["submission_id"], "accept", "local-reviewer", "Checked by hand")
        self.assertEqual(accepted["status"], "accepted")

    def test_quiet_result_has_no_flags_and_refresh_drops_the_advisory(self):
        self.configure(jev_mode="shadow", jev_uses=["evaluate"])
        status, _ = self.submit(lambda name, state: 0.1 if name == "unsupported" else 0.9)
        self.assertEqual(status["advisory"]["flags"], [])
        refreshed = self.tasks.refresh("faq", "Inputs reviewed")
        self.assertNotIn("advisory", refreshed)
        self.assertNotIn("advisory", self.tasks.load("faq"))

    def test_skips_and_failures_are_recorded_and_never_block_the_submission(self):
        self.configure(jev_mode="auto", jev_uses=["evaluate"])
        with patch("okf_icm.tasks.EVALUATE_MAX_CHARS", 5):
            status, nouls = self.submit()
        nouls.assert_not_called()
        self.assertEqual((status["status"], status["advisory"]["status"], status["advisory"]["reason"]),
                         ("awaiting_review", "skipped", "nothing-shareable"))
        self.tasks.refresh("faq", "Again")
        failed = {"requested_model": "jev-latest", "status": "unavailable", "reason": jev.FAILED}
        with patch("okf_icm.jev.nouls", return_value=failed):
            status = self.tasks.submit("faq", ["out/answer.md"], ["out/evidence.md"], "Compared", "", "Review")
        self.assertEqual((status["status"], status["advisory"]["status"]), ("awaiting_review", "unavailable"))
        self.tasks.refresh("faq", "Once more")
        self.configure(jev_mode="auto", jev_uses=["route"])
        status, nouls = self.submit()
        nouls.assert_not_called()
        self.assertEqual(status["advisory"]["reason"], "use-not-enabled")


class RerankInNavigate(Case):
    def setUp(self):
        super().setUp()
        for name, body in (("kiln-firing", "Kiln firing schedule: ramp slowly, soak at peak, cool with the damper closed."),
                           ("kiln-loading", "Kiln loading: space the shelves, keep glaze off the kiln wash, place witness cones.")):
            meta = {"type": "Reference", "title": name.replace("-", " "), "tags": ["kiln"], "status": "stable",
                    "verified": {"by": "human:fixture", "at": "2020-01-01T00:00:00Z"}, "stale_after": "2099-01-01T00:00:00Z"}
            self.write(f".context/knowledge/{name}.md", knowledge.serialize(meta, f"# {name}\n\n{body}\n"))
        self.ws = Workspace(self.root)

    def navigate(self, answer=lambda name, state: 0.5, goal="How do I schedule a kiln firing?"):
        with patch("okf_icm.jev.nouls", side_effect=provider(answer)) as nouls:
            return navigation.navigate(self.ws, goal), nouls

    def test_not_enabled_is_unchanged_and_local(self):
        result, nouls = self.navigate()
        nouls.assert_not_called()
        self.assertNotIn("jev", result)
        self.assertTrue(all("jev_relevance" not in entry for entry in result["candidates"]))

    def test_shadow_records_relevance_and_auto_reorders_the_same_candidates(self):
        baseline, _ = self.navigate()
        order = [entry["select"] for entry in baseline["candidates"]]
        self.assertEqual(len(order), 2)
        favour_last = lambda name, state: {"c0": 0.4, "c1": 0.9}[name]
        self.configure(jev_mode="shadow", jev_uses=["rerank"])
        shadow, nouls = self.navigate(favour_last)
        self.assertEqual([entry["select"] for entry in shadow["candidates"]], order)
        self.assertEqual([entry["jev_relevance"] for entry in shadow["candidates"]], [0.4, 0.9])
        self.assertNotIn("reordered", shadow["jev"])
        self.assertEqual(set(nouls.call_args.args[0]["sources"]), {"c0", "c1"})
        self.configure(jev_mode="auto", jev_uses=["rerank"])
        auto, _ = self.navigate(favour_last)
        self.assertEqual([entry["select"] for entry in auto["candidates"]], order[::-1])
        self.assertEqual(sorted(entry["select"] for entry in auto["candidates"]), sorted(order))
        self.assertEqual(auto["budget"], baseline["budget"])

    def test_no_relevant_candidate_adds_a_gap_and_no_candidates_means_no_request(self):
        self.configure(jev_mode="auto", jev_uses=["rerank"])
        result, _ = self.navigate(lambda name, state: 0.1)
        self.assertEqual(result["jev"]["flags"], ["no-relevant-candidate"])
        self.assertIn("jev_no_support", [gap["code"] for gap in result["gaps"]])
        self.assertEqual(len(result["candidates"]), 2)  # a signal: nothing is removed
        empty, nouls = self.navigate(goal="Quarterly payroll reconciliation")
        nouls.assert_not_called()
        self.assertEqual((empty["candidates"], empty["jev"]["reason"]), ([], "nothing-shareable"))


class DedupeInTidy(Case):
    def setUp(self):
        super().setUp()
        common = " ".join(f"common{c}{c}" for c in "abcdefghijklmn")
        for name, own in (("first", "left"), ("second", "right")):
            self.write(f"notes/{name}.md", f"# {name}\n\n## Part\n\n{common} " + " ".join(f"{own}{c}{c}" for c in "abcdef") + "\n")

    def scan(self, answer=lambda name, state: 0.9, **values):
        configured = {**settings.DEFAULTS, **values}
        with patch("okf_icm.jev.nouls", side_effect=provider(answer)) as nouls:
            return tidy.scan(self.root, ["notes"], configured=configured), nouls

    def sections(self, result):
        return [item for item in result["findings"] if item["kind"] == "duplicate-section"]

    def test_partial_overlap_is_ignored_unless_the_workspace_asks(self):
        result, nouls = self.scan()
        nouls.assert_not_called()
        self.assertEqual(self.sections(result), [])
        self.assertNotIn("jev", result)
        result, nouls = self.scan(jev_mode="auto")  # enabled, but not for this use
        nouls.assert_not_called()
        self.assertEqual(result["jev"]["reason"], "use-not-enabled")

    def test_auto_turns_a_confident_yes_into_a_finding_and_shadow_only_lists_it(self):
        result, nouls = self.scan(jev_mode="auto", jev_uses=["dedupe"])
        found = self.sections(result)
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["evidence"]["basis"], found[0]["evidence"]["jev_same_content"]), ("jev", 0.9))
        self.assertEqual(found[0]["paths"], ["notes/first.md", "notes/second.md"])
        self.assertEqual(set(nouls.call_args.args[0]["pairs"]["p0"]), {"first", "second"})
        result, _ = self.scan(jev_mode="shadow", jev_uses=["dedupe"])
        self.assertEqual(self.sections(result), [])
        self.assertEqual(result["jev"]["judged"][0]["same_content"], 0.9)
        result, _ = self.scan(lambda name, state: 0.2, jev_mode="auto", jev_uses=["dedupe"])
        self.assertEqual(self.sections(result), [])

    def test_request_budget_is_respected_and_the_remainder_is_reported(self):
        common = " ".join(f"other{c}{c}" for c in "abcdefghijklmn")
        for name, own in (("third", "up"), ("fourth", "down")):
            self.write(f"notes/{name}.md", f"# {name}\n\n## Part\n\n{common} " + " ".join(f"{own}{c}{c}" for c in "abcdef") + "\n")
        with patch.object(tidy, "PAIRS_PER_CALL", 1):
            result, nouls = self.scan(jev_mode="auto", jev_uses=["dedupe"], jev_max_calls=1)
        self.assertEqual(nouls.call_count, 1)
        self.assertEqual((result["jev"]["calls"], result["jev"]["unjudged"], result["jev"]["reason"]), (1, 1, "budget-exhausted"))

    def test_without_a_key_nothing_is_sent(self):
        with patch.dict(os.environ, {}, clear=True):
            result, nouls = self.scan(jev_mode="auto", jev_uses=["dedupe"])
        nouls.assert_not_called()
        self.assertEqual((result["jev"]["status"], result["jev"]["reason"], result["jev"]["unjudged"]), ("skipped", "no-key", 1))


if __name__ == "__main__":
    unittest.main()
