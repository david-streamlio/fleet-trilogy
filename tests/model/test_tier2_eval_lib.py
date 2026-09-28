"""Fast, offline unit tests for tier2_eval_lib.py's pure check functions --
no real model needed, unlike test_tier2_synthesis.py/test_compare_tier2_models.py.
Locks in two real bugs found from actual model output (see check_tier2_grounding's
_corridor_mention_patterns/_mentions_reroute_affirmatively docstrings): a naive
exact-string corridor check and negation-blind reroute-keyword check both scored
correct model behavior as a grounding violation.
"""

from __future__ import annotations

from tests.model.tier2_eval_lib import Tier2Scenario, Tier2Trial, check_tier2_grounding

_NO_REROUTE_SCENARIO = Tier2Scenario(
    name="single-truck", corridor="I-95N", cards=[], scope="single_truck", reroute_recommended=False, reroute_detail=None
)
_REROUTE_SCENARIO = Tier2Scenario(
    name="corridor-wide-with-reroute",
    corridor="I-95N",
    cards=[],
    scope="corridor_wide",
    reroute_recommended=True,
    reroute_detail="Reroute traffic around I-95N.",
)


def _trial(text: str) -> Tier2Trial:
    return Tier2Trial(raw_output=text, latency_seconds=0.1, spoken_warning=text, structured=True)


def test_accepts_natural_corridor_paraphrase_not_just_the_literal_code():
    # Real Gemma-3-4B-it output, scored a false 100% violation under the old
    # exact-string check because it wrote "I-95 North" instead of "I-95N".
    trial = _trial("Approaching I-95 North, drivers of trucks are experiencing a sustained slowdown.")
    result = check_tier2_grounding([trial], _NO_REROUTE_SCENARIO)
    assert result["violations"] == 0


def test_accepts_negated_reroute_language_as_correctly_holding():
    # Real Qwen3-8B output, scored a false violation under the old bare
    # substring check because "No reroute is recommended" contains "reroute".
    trial = _trial("Drivers on I-95N, there are 2 trucks ahead causing slowdowns. No reroute is recommended.")
    result = check_tier2_grounding([trial], _NO_REROUTE_SCENARIO)
    assert result["violations"] == 0


def test_still_flags_a_genuinely_missing_corridor():
    trial = _trial("A truck ahead is experiencing a sustained slowdown. Expect delays.")
    result = check_tier2_grounding([trial], _NO_REROUTE_SCENARIO)
    assert result["violations"] == 1
    assert "not mentioned" in result["sample_violations"][0]["problems"][0]


def test_still_flags_a_genuine_hallucinated_reroute():
    trial = _trial("Approaching I-95N, please use an alternate route to avoid delays.")
    result = check_tier2_grounding([trial], _NO_REROUTE_SCENARIO)
    assert result["violations"] == 1
    assert "reroute" in result["sample_violations"][0]["problems"][0]


def test_affirmative_reroute_language_counted_when_actually_recommended():
    trial = _trial("Approaching I-95N, please use an alternate route due to a major slowdown.")
    result = check_tier2_grounding([trial], _REROUTE_SCENARIO)
    assert result["violations"] == 0
    assert result["reroute_mentioned_when_recommended"] == 1
