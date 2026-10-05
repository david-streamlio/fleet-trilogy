import json

import pytest
from fleet_telemetry_model import EnrichmentCard
from llm_inference import LlmBackend
from talk3_pulsar_speaks_english.fact_check import check_warning, fallback_warning
from talk3_pulsar_speaks_english.synthesizer import synthesize

# deploy/talk3-demo-cards.jsonl: two high, one medium; 9, 7 and 6 minutes.
_CARDS = [
    EnrichmentCard(
        event="traffic_incident_suspected",
        severity=severity,
        signals=["sustained_low_speed", "eta_slip"],
        eta_impact=eta,
        corridor="I-95N",
        truck_id=truck,
    )
    for truck, severity, eta in [
        ("truck-47", "high", 9.0),
        ("truck-12", "high", 7.0),
        ("truck-31", "medium", 6.0),
    ]
]


def _check(warning: str, *, reroute: bool = True) -> list[str]:
    return check_warning(
        warning, corridor="I-95N", cards=_CARDS, reroute_recommended=reroute
    )


@pytest.mark.parametrize(
    "warning",
    [
        "Drivers approaching I-95N, three trucks are slowing down; expect up to 9 minutes. Reroute around the corridor.",
        "On I-95 North, two trucks report high severity delays of 7 to 9 minutes; we recommend rerouting.",
        "Approaching I-95N: trucks 47 and 12 are experiencing high severity slowdowns. Please take a detour.",
        "On I-95N, truck 47 with a high severity slowdown leads a 9-minute delay; reroute if you can.",
    ],
)
def test_warnings_that_match_the_facts_pass(warning):
    assert _check(warning) == []


# Real slips from eval-results/talk3-single-core-m4max-20261004/ (runs*.jsonl).
@pytest.mark.parametrize(
    ("warning", "problem"),
    [
        (
            "Drivers approaching I-95N, we recommend rerouting; three trucks are experiencing significant delays, with an estimated impact of around 9 to 12 minutes.",
            "says 12 minutes",
        ),
        (
            "Drivers approaching I-95N, three trucks are experiencing trouble, with one reporting high severity and two others experiencing delays. We recommend rerouting traffic around I-95N.",
            "'one reporting high severity'",
        ),
        (
            "Approaching I-10E... Traffic is rerouted around I-95N due to a correlated slowdown with three trucks experiencing high severity issues.",
            "'three trucks experiencing high severity'",
        ),
        (
            "Drivers approaching I-95N, three trucks are experiencing significant delays; please reduce your speed and proceed with caution.",
            "doesn't say so",
        ),
        (
            "Three trucks are slowing down, so we recommend rerouting.",
            "doesn't name the corridor",
        ),
    ],
)
def test_real_slips_are_caught(warning, problem):
    problems = _check(warning)
    assert any(problem in p for p in problems), problems


def test_reroute_is_only_required_when_recommended():
    assert _check("On I-95N, expect delays of up to 9 minutes.", reroute=False) == []


@pytest.mark.parametrize("reroute", [True, False])
def test_fallback_warning_passes_its_own_check(reroute):
    warning = fallback_warning(corridor="I-95N", cards=_CARDS, reroute_recommended=reroute)
    assert _check(warning, reroute=reroute) == []
    assert "3 trucks" in warning and "2 at high severity" in warning


class _ScriptedBackend(LlmBackend):
    def __init__(self, *warnings: str) -> None:
        self._warnings = list(warnings)
        self.calls = 0

    def generate(self, prompt, config=None) -> str:
        self.calls += 1
        return json.dumps({"spoken_warning": self._warnings.pop(0)})


_GOOD = "On I-95N, three trucks report delays of up to 9 minutes. We recommend rerouting."
_BAD = "On I-95N, three trucks report delays of 9 to 12 minutes. We recommend rerouting."


def test_a_good_first_warning_is_used_as_is():
    backend = _ScriptedBackend(_GOOD)
    assert synthesize(_CARDS, backend).spoken_warning == _GOOD
    assert backend.calls == 1


def test_a_failed_warning_is_retried_once():
    backend = _ScriptedBackend(_BAD, _GOOD)
    assert synthesize(_CARDS, backend).spoken_warning == _GOOD
    assert backend.calls == 2


def test_two_failed_warnings_fall_back_to_plain_code():
    backend = _ScriptedBackend(_BAD, _BAD)
    synthesis = synthesize(_CARDS, backend)
    assert backend.calls == 2
    assert synthesis.spoken_warning == fallback_warning(
        corridor="I-95N", cards=_CARDS, reroute_recommended=True
    )
