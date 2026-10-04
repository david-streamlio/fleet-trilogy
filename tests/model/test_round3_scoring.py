"""Pure tests (no LLM) for round3_eval: prompts, grammars, chat wrapping and scoring."""
from __future__ import annotations

from talk1_edge_intelligence.triage_function import DEFAULT_PROMPT_TEMPLATE, RECOMMENDED_ACTIONS, build_grammar

from tests.model import round3_eval as r


def test_profiles_cover_every_severity_branch():
    assert [r.truth_for(p) for p in r.SEVERITY_PROFILES] == ["low", "medium", "medium", "high", "high", "high"]


def test_full_prompt_reuses_production_operational_rules_verbatim():
    rules = DEFAULT_PROMPT_TEMPLATE[
        DEFAULT_PROMPT_TEMPLATE.index("How to weigh each field:") : DEFAULT_PROMPT_TEMPLATE.index("Truck ID:")
    ]
    assert rules in r.FULL_PROMPT_TEMPLATE
    for action in RECOMMENDED_ACTIONS.values():
        assert action in r.FULL_PROMPT_TEMPLATE


def test_render_full_shows_the_physics_classify_severity_uses():
    payload = {
        "truck_id": "truck-47",
        "corridor": "I-95N",
        "metrics": {"peak_deceleration_g": 0.3, "abs_engaged": True, "traffic_pattern": "severe stop-and-go compaction (repeated hard braking)"},
        "baseline_severity": "high",
        "contextual_triggers": {"weather_condition": "Rain", "cargo_type": "Tanker", "dispatch_status": "Late"},
    }
    prompt, grammar = r.render("full", payload)
    assert "Peak deceleration: 0.3 g" in prompt and "ABS engaged: yes" in prompt
    assert "severe stop-and-go compaction" in prompt and "BASELINE SEVERITY (already" not in prompt
    assert '"truck-47\\"' in grammar  # truck_id forced as a literal, as in production
    narrow_prompt, narrow_grammar = r.render("narrow", payload)
    assert "BASELINE SEVERITY (already computed from vehicle physics): high" in narrow_prompt
    assert narrow_grammar == build_grammar("truck-47")


def test_chat_wrapping_matches_the_qwen_templates():
    assert r.wrap_prompt("P", "raw") == "P"
    assert r.wrap_prompt("P", "chat-off").endswith("<|im_start|>assistant\n<think>\n\n</think>\n\n")
    assert r.wrap_prompt("P", "chat-on").endswith("<|im_start|>assistant\n<think>\n")
    g = r.wrap_grammar(build_grammar("t"), "chat-on")
    assert g.startswith('root ::= think "</think>"') and "card ::=" in g
    assert r.wrap_grammar(build_grammar("t"), "chat-off") == build_grammar("t")


def test_split_card():
    assert r.split_card("thinking about it\n</think>\n\n{\"a\": 1}", "chat-on") == ("thinking about it\n", '{"a": 1}')
    assert r.split_card(' {"a": 1} ', "raw") == ("", '{"a": 1}')


def _full_card(base, esc, sev, act):
    return {"baseline_severity": base, "risk_synthesis": "x", "escalation": esc, "severity": sev, "recommended_action": act, "truck_id": "t"}


def test_score_full_task():
    good = r.score("full", _full_card("medium", "raise", "high", RECOMMENDED_ACTIONS["raise"]), "medium", "raise")
    assert good["all_ok"] and good["consistent"]
    # Right decisions from a wrong baseline: consistent, but the baseline and final severity are wrong.
    wrong_base = r.score("full", _full_card("low", "raise", "medium", RECOMMENDED_ACTIONS["raise"]), "medium", "raise")
    assert wrong_base["consistent"] and not wrong_base["baseline_ok"] and not wrong_base["severity_ok"] and not wrong_base["all_ok"]
    # The pre-narrowing failure: a severity that contradicts the model's own escalation.
    contradiction = r.score("full", _full_card("medium", "raise", "medium", RECOMMENDED_ACTIONS["raise"]), "medium", "raise")
    assert not contradiction["consistent"] and not contradiction["all_ok"]
    # lower_or_hold accepts either, end to end.
    for esc, sev in (("hold", "medium"), ("lower", "low")):
        s = r.score("full", _full_card("medium", esc, sev, RECOMMENDED_ACTIONS[esc]), "medium", "lower_or_hold")
        assert s["all_ok"], esc
    assert r.score("full", None, "medium", "raise") == {"format_ok": False}


def test_score_narrow_task():
    assert r.score("narrow", {"escalation": "hold", "risk_synthesis": "x"}, "medium", "lower_or_hold")["all_ok"]
    assert not r.score("narrow", {"escalation": "raise", "risk_synthesis": "x"}, "medium", "hold")["all_ok"]
