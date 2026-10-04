"""Pure tests (no LLM) for round3_ablation: the variants, worked examples, tables and grammar."""
from __future__ import annotations

import json
import re

from talk1_edge_intelligence.severity_classifier import classify_severity
from talk1_edge_intelligence.triage_function import RECOMMENDED_ACTIONS, apply_escalation

from tests.model import round3_ablation as a
from tests.model import round3_eval as r
from tests.model.eval_lib import ESCALATION_SCENARIOS

_PAYLOAD = {
    "truck_id": "truck-47", "corridor": "I-95N", "baseline_severity": "high",
    "metrics": {"peak_deceleration_g": 0.3, "abs_engaged": False, "traffic_pattern": "severe stop-and-go compaction (repeated hard braking)"},
    "contextual_triggers": {"weather_condition": "Rain", "cargo_type": "Tanker", "dispatch_status": "Late"},
}


def test_base_variant_is_round3_exactly():
    assert a.render("base", _PAYLOAD) == r.render("full", _PAYLOAD)


def test_examples_follow_every_rule():
    cards = [json.loads(m) for m in re.findall(r"Answer:\n(\{.*?\n\})", a.examples_block(), re.S)]
    assert len(cards) == 3 and {c["escalation"] for c in cards} == {"raise", "hold", "lower"}
    for (tid, _c, g, abs_, traffic, *_rest), card in zip(a._EXAMPLES, cards):
        severe = "severe stop-and-go compaction" in traffic
        assert card["deceleration_band"] == a.band_for(g)
        assert card["abs_engaged"] == abs_ and card["severe_stop_and_go"] == ("yes" if severe else "no")
        assert card["baseline_severity"] == classify_severity(peak_deceleration_g=g, abs_engaged=abs_ == "yes", stop_go_index=0.85 if severe else 0.72)
        assert card["severity"] == apply_escalation(card["baseline_severity"], card["escalation"])
        assert card["recommended_action"] == RECOMMENDED_ACTIONS[card["escalation"]] and card["truck_id"] == tid


def test_examples_do_not_leak_the_test_cells():
    test_g = {p["peak_deceleration_g"] for p in r.SEVERITY_PROFILES.values()}
    test_context = {v for s in ESCALATION_SCENARIOS.values() for v in s["contextual_triggers"].values()}
    for ex in a._EXAMPLES:
        assert ex[2] not in test_g
        assert not {ex[5], ex[6], ex[7]} & test_context


def test_step1_table_agrees_with_classify_severity():
    rows = re.findall(r"^\| (yes|no) \| ([^|]+?) \| (yes|no|any) \| (low|medium|high) \|$", a.TABLES_PROMPT_TEMPLATE, re.M)
    assert len(rows) == 6
    probe = {"at or below 0.22 g": [0.1, 0.22], "0.22 to 0.45 g": [0.3, 0.45], "above 0.45 g": [0.5]}
    for abs_, band, sng, want in rows:
        for g in probe.get(band, [0.1, 0.3, 0.5]):
            for sg in ([0.85] if sng == "yes" else [0.72] if sng == "no" else [0.72, 0.85]):
                assert classify_severity(peak_deceleration_g=g, abs_engaged=abs_ == "yes", stop_go_index=sg) == want


def test_step3_table_agrees_with_apply_escalation():
    for b in a.LEVELS:
        row = re.search(rf"^\| {b} \| (\w+) \| (\w+) \| (\w+) \|$", a.TABLES_PROMPT_TEMPLATE, re.M)
        assert row and list(row.groups()) == [apply_escalation(b, e) for e in ("raise", "hold", "lower")]


def test_facts_and_scoring():
    assert a.facts_for("high-abs") == {"abs_engaged": "yes", "deceleration_band": "at or below 0.22 g", "severe_stop_and_go": "no"}
    card = {"abs_engaged": "yes", "deceleration_band": "at or below 0.22 g", "severe_stop_and_go": "no",
            "baseline_severity": "high", "risk_synthesis": "x", "escalation": "raise", "severity": "high",
            "recommended_action": RECOMMENDED_ACTIONS["raise"], "truck_id": "t"}
    s = a.score(card, "high-abs", "high", "raise", facts=True)
    assert s["facts_ok"] and s["all_ok"]
    assert not a.score({**card, "deceleration_band": "0.22 to 0.45 g"}, "high-abs", "high", "raise", facts=True)["facts_ok"]


def test_grammars_are_well_formed():
    for variant in a.VARIANTS:
        _prompt, gram = a.render(variant, _PAYLOAD)
        assert gram.startswith("root ::= ") and gram.count("(") == gram.count(")")
    consistent = a.build_grammar("truck-47", facts=True, consistent=True)
    # one branch per baseline x escalation, each with the derived severity
    for b in a.LEVELS:
        for e in ("raise", "hold", "lower"):
            assert f'severity\\\\\\": \\\\\\"{apply_escalation(b, e)}' in consistent or f'severity\\": \\"{apply_escalation(b, e)}' in consistent
