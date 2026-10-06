from fleet_telemetry_model import EnrichmentCard
from llm_inference import SubprocessLlmBackend

from talk3_pulsar_speaks_english.prompting import (
    PUBLISHED_SYNTHESIS_WARNING_PROMPT,
    REROUTE_RULE,
    SYNTHESIS_WARNING_PROMPT,
    generate_spoken_warning,
    render_synthesis_prompt,
)
from talk3_pulsar_speaks_english.synthesizer import SCOPE_CORRIDOR_WIDE

_CARDS = [
    EnrichmentCard(
        event="traffic_incident_suspected",
        severity="high",
        signals=["sustained_low_speed", "stop_go_index", "eta_slip"],
        eta_impact=4.0,
        corridor="I-95N",
        truck_id="truck-01",
    ),
    EnrichmentCard(
        event="traffic_incident_suspected",
        severity="high",
        signals=["sustained_low_speed", "stop_go_index", "eta_slip"],
        eta_impact=5.0,
        corridor="I-95N",
        truck_id="truck-02",
    ),
]


def test_render_synthesis_prompt_states_decisions_as_already_made():
    prompt = render_synthesis_prompt(
        corridor="I-95N",
        cards=_CARDS,
        scope=SCOPE_CORRIDOR_WIDE,
        reroute_recommended=True,
        reroute_detail="Reroute around I-95N.",
    )
    assert "I-95N" in prompt
    assert "corridor_wide" in prompt
    assert "Reroute around I-95N." in prompt
    assert "truck-01" in prompt and "truck-02" in prompt
    # Grounding: no fully-realistic literal example sentence, only a placeholder.
    assert "<your warning text here>" in prompt


def test_render_synthesis_prompt_never_asks_the_model_to_decide_scope():
    prompt = render_synthesis_prompt(
        corridor="I-95N",
        cards=_CARDS,
        scope=SCOPE_CORRIDOR_WIDE,
        reroute_recommended=True,
        reroute_detail="Reroute around I-95N.",
    )
    assert "already decided" in prompt.lower()


def test_generate_spoken_warning_returns_nonempty_text_with_mock_backend():
    backend = SubprocessLlmBackend(mock=True)
    warning = generate_spoken_warning(
        backend,
        corridor="I-95N",
        cards=_CARDS,
        scope=SCOPE_CORRIDOR_WIDE,
        reroute_recommended=True,
        reroute_detail="Reroute around I-95N.",
    )
    assert isinstance(warning, str)
    assert warning.strip()


def test_generate_spoken_warning_falls_back_to_raw_text_when_no_json_present():
    class _PlainTextBackend(SubprocessLlmBackend):
        def generate(self, prompt, config=None):  # noqa: ANN001
            return "Expect delays on I-95N; consider an alternate route."

    warning = generate_spoken_warning(
        _PlainTextBackend(mock=True),
        corridor="I-95N",
        cards=_CARDS,
        scope=SCOPE_CORRIDOR_WIDE,
        reroute_recommended=True,
        reroute_detail="Reroute around I-95N.",
    )
    assert warning == "Expect delays on I-95N; consider an alternate route."


def test_generate_spoken_warning_prefers_structured_spoken_warning_key():
    class _JsonBackend(SubprocessLlmBackend):
        def generate(self, prompt, config=None):  # noqa: ANN001
            return '{"spoken_warning": "Slow traffic ahead on I-95N, please use caution."}'

    warning = generate_spoken_warning(
        _JsonBackend(mock=True),
        corridor="I-95N",
        cards=_CARDS,
        scope=SCOPE_CORRIDOR_WIDE,
        reroute_recommended=True,
        reroute_detail="Reroute around I-95N.",
    )
    assert warning == "Slow traffic ahead on I-95N, please use caution."


def _render(reroute_recommended: bool, **kwargs) -> str:
    return render_synthesis_prompt(
        corridor="I-95N",
        cards=_CARDS,
        scope=SCOPE_CORRIDOR_WIDE,
        reroute_recommended=reroute_recommended,
        reroute_detail="Reroute around I-95N." if reroute_recommended else None,
        **kwargs,
    )


def test_a_recommended_reroute_is_stated_as_a_recommendation():
    prompt = _render(True)
    assert "A reroute is only ever a recommendation, never already happening" in prompt
    assert "never that traffic is being, or has been, rerouted" in prompt
    assert prompt.replace(REROUTE_RULE, "") == _render(True, template=PUBLISHED_SYNTHESIS_WARNING_PROMPT)


def test_without_a_reroute_the_prompt_is_the_published_one():
    # The rule's "drivers should consider it" made the model suggest alternative routes
    # when none was recommended, so it is only added when one is.
    assert _render(False) == _render(False, template=PUBLISHED_SYNTHESIS_WARNING_PROMPT)
    assert "reroute is only ever a recommendation" not in _render(False)


def test_published_template_has_no_reroute_rule():
    assert "{reroute_rule}" not in PUBLISHED_SYNTHESIS_WARNING_PROMPT
    assert "{reroute_rule}" in SYNTHESIS_WARNING_PROMPT
