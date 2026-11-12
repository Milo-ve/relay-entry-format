"""Workspace-enabled Jev: when it is called, when it is skipped, and what it may change.

Mocked provider only. Nothing here measures Jev's quality.
"""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from okf_icm import jev, jev_policy, settings
from okf_icm.relay_cli import main
from okf_icm.routing import apply_jev, route
from okf_icm.storage import ContextError
from okf_icm.tasks import Tasks
from okf_icm.workspace import initialize

KEY = {"TYPESAFE_API_KEY": "test-secret"}


def observation(approach="draft", confidence=0.7, conflict=0.1, **extra):
    rest = (1 - confidence) / 3
    probabilities = {name: (confidence if name == approach else rest) for name in jev.OPTIONS}
    return {"question_version": jev.QUESTION_VERSION, "requested_model": "jev-latest", "status": "ok", "model": "fixture-jev",
            "signals": {"approach": approach, "probabilities": probabilities, "conflict": conflict, **extra}, "usage": {"input_tokens": 9}}


class Gate(unittest.TestCase):
    def configured(self, **values):
        return {**settings.DEFAULTS, **values}

    def reason(self, use="route", env=KEY, **kwargs):
        configured = kwargs.pop("configured", self.configured(jev_mode="auto"))
        with patch.dict(os.environ, env, clear=True):
            return jev_policy.decide(use, configured, **kwargs)["reason"]

    def test_each_reason_in_order(self):
        self.assertEqual(self.reason(configured=self.configured()), "not-enabled")
        self.assertEqual(self.reason(use="evaluate"), "use-not-enabled")
        self.assertEqual(self.reason(decisive=True), "rules-decisive")
        self.assertEqual(self.reason(shareable=False), "nothing-shareable")
        self.assertEqual(self.reason(env={}), "no-key")
        self.assertEqual(self.reason(calls=5), "budget-exhausted")
        self.assertEqual(self.reason(configured=self.configured(jev_mode="auto", jev_max_calls=0)), "budget-exhausted")
        self.assertEqual(self.reason(), "call")

    def test_flag_wins_over_the_setting_in_both_directions(self):
        self.assertEqual(jev_policy.mode("off", self.configured(jev_mode="auto")), ("off", "flag"))
        self.assertEqual(jev_policy.mode("shadow", self.configured()), ("shadow", "flag"))
        self.assertEqual(jev_policy.mode(None, self.configured(jev_mode="auto")), ("route", "setting"))
        self.assertEqual(jev_policy.mode(None, self.configured(jev_mode="shadow")), ("shadow", "setting"))
        # An explicit flag is not held back by the workspace's list of uses or by decisive rules.
        self.assertEqual(self.reason(use="evaluate", flag="shadow", decisive=True), "call")
        with self.assertRaises(ValueError):
            jev_policy.decide("publish", self.configured())


class Lowering(unittest.TestCase):
    def test_only_a_confident_bounded_transformation_from_the_default_may_select_direct(self):
        lowered = apply_jev(route("Tidy the list", risk="low"), observation("transform", 0.9), "route", may_lower=True)
        self.assertEqual((lowered["profile"], lowered["reason_codes"]), ("direct", ["conservative-default", "jev-bounded-transformation"]))
        self.assertEqual(lowered["decision_source"], "rules-and-jev")
        for case in (dict(obs=observation("transform", 0.9), may_lower=False),
                     dict(obs=observation("transform", 0.75), may_lower=True),
                     dict(obs=observation("transform", 0.9, conflict=0.4), may_lower=True),
                     dict(obs=observation("draft", 0.9), may_lower=True),
                     dict(obs=observation("transform", 0.9, source_instructions=0.9), may_lower=True)):
            with self.subTest(case=case):
                kept = apply_jev(route("Tidy the list", risk="low"), case["obs"], "route", may_lower=case["may_lower"])
                self.assertEqual(kept["profile"], "standard")
        shadow = apply_jev(route("Tidy the list", risk="low"), observation("transform", 0.9), "shadow", may_lower=True)
        self.assertEqual(shadow["profile"], "standard")
        blocked = apply_jev(route("Tidy", risk="low", blockers=["No approval"]), observation("transform", 0.95), "route", may_lower=True)
        self.assertEqual(blocked["profile"], "clarify")

    def test_source_instruction_signal_is_a_flag_in_any_mode_and_changes_no_route(self):
        for mode in ("shadow", "route"):
            flagged = apply_jev(route("Draft"), observation(source_instructions=0.8), mode)
            self.assertEqual((flagged["profile"], flagged["jev"]["flags"]), ("standard", ["source-instructions"]))
        self.assertNotIn("flags", apply_jev(route("Draft"), observation(source_instructions=0.4), "route")["jev"])


class WorkspaceSetting(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        initialize(self.root, "Synthetic Jev policy checks", minimal=True)
        (self.root / "policy.md").write_text("# Policy\n\nRefunds take five days.\n", encoding="utf-8")
        self.tasks = Tasks(self.root)

    def configure(self, **values):
        path = self.root / ".context/relay/settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(values), encoding="utf-8")

    def start(self, task="t", goal="Draft the answer", observed=None, env=KEY, **kwargs):
        with patch.dict(os.environ, env, clear=True), patch("okf_icm.tasks.jev.judge", return_value=observed or observation()) as judge:
            result = self.tasks.start(task, goal, ["Matches the policy"], kwargs.pop("selections", ["policy.md"]), **kwargs)
        return result["route"], judge

    def test_off_by_default_and_wrong_values_are_refused(self):
        found, judge = self.start()
        judge.assert_not_called()
        self.assertEqual(found["jev"], {"mode": "off"})
        for bad in ({"jev_mode": "route"}, {"jev_mode": True}, {"jev_uses": ["route", "publish"]}, {"jev_uses": ["route", "route"]},
                    {"jev_uses": "route"}, {"jev_max_calls": -1}, {"jev_max_calls": 51}, {"jev_max_calls": 1.5}, {"jev_max_calls": True}):
            with self.subTest(bad=bad):
                self.configure(**bad)
                with self.assertRaises(ContextError):
                    self.tasks.settings()

    def test_shadow_records_without_changing_the_route(self):
        self.configure(jev_mode="shadow")
        found, judge = self.start(observed=observation("design", 0.9, conflict=0.9))
        judge.assert_called_once()
        self.assertEqual(found["profile"], "standard")
        self.assertEqual((found["jev"]["mode"], found["jev"]["trigger"], found["jev"]["status"]), ("shadow", "setting", "ok"))

    def test_auto_raises_on_a_signal_and_sends_no_control_file(self):
        self.configure(jev_mode="auto")
        found, judge = self.start(observed=observation("draft", 0.6, conflict=0.8))
        self.assertEqual((found["profile"], found["decision_source"]), ("investigative", "rules-and-jev"))
        sent = judge.call_args.args[0]
        self.assertEqual([item["path"] for item in sent["sources"]], ["policy.md"])
        self.assertEqual(judge.call_args.kwargs, {"scan_sources": False})

    def test_auto_skips_when_the_rules_already_decided(self):
        self.configure(jev_mode="auto")
        cases = {"kind": dict(kind="transform", risk="low"), "risk": dict(risk="high"), "blocker": dict(blockers=["No approval"]),
                 "keyword": dict(goal="Diagnose the conflicting totals")}
        for name, kwargs in cases.items():
            with self.subTest(name=name):
                found, judge = self.start(task=name, **kwargs)
                judge.assert_not_called()
                self.assertEqual(found["jev"], {"mode": "route", "trigger": "setting", "use": "route",
                                                "status": "skipped", "reason": "rules-decisive"})

    def test_auto_without_a_key_or_a_budget_skips_and_keeps_the_rules(self):
        self.configure(jev_mode="auto")
        found, judge = self.start(env={})
        judge.assert_not_called()
        self.assertEqual((found["profile"], found["jev"]["reason"]), ("standard", "no-key"))
        self.configure(jev_mode="auto", jev_max_calls=0)
        found, judge = self.start(task="t2")
        judge.assert_not_called()
        self.assertEqual(found["jev"]["reason"], "budget-exhausted")
        self.configure(jev_mode="auto", jev_uses=["evaluate"])
        found, judge = self.start(task="t3")
        judge.assert_not_called()
        self.assertEqual(found["jev"]["reason"], "use-not-enabled")

    def test_auto_lowers_only_for_declared_low_risk_and_review_stays_required(self):
        self.configure(jev_mode="auto")
        confident = observation("transform", 0.92)
        found, _ = self.start(task="low", goal="Fix the heading spelling", observed=confident, risk="low")
        self.assertEqual((found["profile"], found["reason_codes"][-1]), ("direct", "jev-bounded-transformation"))
        self.assertTrue(self.tasks.packet(self.tasks.load("low"))["brief"]["review_required"])
        found, _ = self.start(task="standard", goal="Fix the heading spelling", observed=confident)
        self.assertEqual(found["profile"], "standard")
        # The per-command flag keeps its earlier promise: it never lowers.
        found, _ = self.start(task="flag", goal="Fix the heading spelling", observed=confident, risk="low", jev_mode="route")
        self.assertEqual(found["profile"], "standard")
        self.configure(jev_mode="shadow")
        found, _ = self.start(task="shadow", goal="Fix the heading spelling", observed=confident, risk="low")
        self.assertEqual(found["profile"], "standard")

    def test_flag_overrides_the_setting(self):
        self.configure(jev_mode="auto")
        found, judge = self.start(jev_mode="off")
        judge.assert_not_called()
        self.assertEqual(found["jev"], {"mode": "off"})
        self.configure(jev_mode="off")
        found, judge = self.start(task="t2", jev_mode="shadow", kind="transform", risk="low")
        judge.assert_called_once()  # asked for on the command: consulted even though the rules decided
        self.assertNotIn("trigger", found["jev"])

    def test_source_scan_rides_on_the_routing_request_and_only_with_sources(self):
        self.configure(jev_mode="auto", jev_uses=["route", "source-scan"])
        found, judge = self.start(observed=observation(source_instructions=0.9))
        self.assertEqual(judge.call_args.kwargs, {"scan_sources": True})
        self.assertEqual((found["profile"], found["jev"]["flags"]), ("standard", ["source-instructions"]))
        _, judge = self.start(task="bare", selections=[])
        self.assertEqual(judge.call_args.kwargs, {"scan_sources": False})

    def test_provider_failure_keeps_the_rules_and_refresh_returns_to_them(self):
        self.configure(jev_mode="auto")
        failed = {"question_version": jev.QUESTION_VERSION, "requested_model": "jev-latest", "status": "unavailable", "reason": jev.FAILED}
        found, _ = self.start(observed=failed)
        self.assertEqual((found["profile"], found["jev"]["status"], found["decision_source"]), ("standard", "unavailable", "rules"))
        with patch("okf_icm.tasks.jev.judge") as judge:
            refreshed = self.tasks.refresh("t", "Inputs reviewed")
            judge.assert_not_called()
        self.assertEqual(refreshed["route"]["jev"], {"mode": "off"})

    def test_cli_follows_the_setting_unless_told_otherwise(self):
        self.configure(jev_mode="auto")

        def run(*args):
            out = io.StringIO()
            with redirect_stdout(out), redirect_stderr(io.StringIO()), patch.dict(os.environ, KEY, clear=True), \
                    patch("okf_icm.tasks.jev.judge", return_value=observation("design", 0.9)) as judge:
                code = main(["--root", str(self.root), "start", *args, "--goal", "Draft the answer", "--accept", "Matches"])
            return code, json.loads(out.getvalue())["route"], judge
        code, found, judge = run("followed")
        self.assertEqual((code, found["profile"], judge.call_count), (0, "investigative", 1))
        code, found, judge = run("declined", "--jev", "off")
        self.assertEqual((code, found["profile"], judge.call_count), (0, "standard", 0))


class Provider(unittest.TestCase):
    def reply(self, body):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = json.dumps(body).encode()
        opener = Mock()
        opener.open.return_value = response
        return opener

    def test_scan_adds_one_question_to_the_same_request(self):
        body = {"model": "fixture-jev", "answers": {
            "approach": {"choice": "draft", "probabilities": {"transform": .1, "draft": .7, "diagnose": .1, "design": .1}},
            "conflict": {"noul": .2}, "source_instructions": {"noul": .85}}, "usage": {"input_tokens": 12}}
        opener = self.reply(body)
        with patch.dict(os.environ, KEY), patch("okf_icm.jev.request.build_opener", return_value=opener):
            result = jev.judge({"goal": "Draft"}, scan_sources=True)
        self.assertEqual((result["status"], result["question_version"]), ("ok", jev.SCAN_VERSION))
        self.assertEqual(result["signals"]["source_instructions"], .85)
        sent = json.loads(opener.open.call_args.args[0].data)
        self.assertEqual(set(sent["questions"]), {"approach", "conflict", "source_instructions"})
        self.assertEqual(opener.open.call_count, 1)
        del body["answers"]["source_instructions"]
        with patch.dict(os.environ, KEY), patch("okf_icm.jev.request.build_opener", return_value=self.reply(body)):
            self.assertEqual(jev.judge({"goal": "Draft"}, scan_sources=True)["status"], "unavailable")

    def test_nouls_returns_every_answer_or_none(self):
        body = {"model": "fixture-jev", "answers": {"a": {"noul": .9}, "b": {"noul": .1}}, "usage": {"input_tokens": 5}}
        with patch.dict(os.environ, KEY), patch("okf_icm.jev.request.build_opener", return_value=self.reply(body)):
            result = jev.nouls({"x": 1}, {"a": "First?", "b": "Second?"})
        self.assertEqual((result["status"], result["answers"]), ("ok", {"a": .9, "b": .1}))
        self.assertNotIn("test-secret", json.dumps(result))
        body["answers"]["b"] = {"noul": 7}
        with patch.dict(os.environ, KEY), patch("okf_icm.jev.request.build_opener", return_value=self.reply(body)):
            self.assertEqual(jev.nouls({"x": 1}, {"a": "First?", "b": "Second?"})["status"], "unavailable")
        with patch.dict(os.environ, {}, clear=True), patch("okf_icm.jev.request.build_opener") as opener:
            self.assertEqual(jev.nouls({"x": 1}, {"a": "First?"})["reason"], jev.NO_KEY)
            opener.assert_not_called()


if __name__ == "__main__":
    unittest.main()
