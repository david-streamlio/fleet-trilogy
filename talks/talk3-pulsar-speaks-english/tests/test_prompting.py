from fleet_telemetry_model import EnrichmentCard
from llm_inference import SubprocessLlmBackend

from talk3_pulsar_speaks_english.prompting import (
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
