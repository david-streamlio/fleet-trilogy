import json

import pytest
from fleet_telemetry_model import EnrichmentCard, IncidentSynthesis, from_json, to_json
from llm_inference import InProcessLlmBackend, SubprocessLlmBackend
from llm_inference.client import LlmGenerationConfig
from talk3_pulsar_speaks_english import function as function_module
from talk3_pulsar_speaks_english.function import GlobalSynthesisFunction
from talk3_pulsar_speaks_english.prompting import (
    PUBLISHED_SYNTHESIS_WARNING_PROMPT,
    render_synthesis_prompt,
)
from talk3_pulsar_speaks_english.synthesizer import (
    SCOPE_CORRIDOR_WIDE,
    decide_reroute,
    decide_scope,
)


class _Context:
    def __init__(self, user_config: dict) -> None:
        self._user_config = user_config

    def get_user_config_map(self) -> dict:
        return self._user_config


def _card(truck_id: str) -> str:
    return to_json(
        EnrichmentCard(
            event="traffic_incident_suspected",
            severity="high",
            signals=["sustained_low_speed", "stop_go_index", "eta_slip"],
            eta_impact=8.0,
            corridor="I-95N",
            truck_id=truck_id,
        )
    )


@pytest.fixture(autouse=True)
def _mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "1")


class _RecordingBackend:
    """Stands in for InProcessLlmBackend; records every prompt and config."""

    instances: list["_RecordingBackend"] = []

    def __init__(self, *args, **kwargs) -> None:
        self.calls: list[tuple[str, LlmGenerationConfig | None]] = []
        _RecordingBackend.instances.append(self)

    def generate(self, prompt: str, config: LlmGenerationConfig | None = None) -> str:
        self.calls.append((prompt, config))
        return '{"spoken_warning": "On I-95N, two trucks report a slowdown."}'


@pytest.fixture
def recording_backend(monkeypatch):
    _RecordingBackend.instances = []
    monkeypatch.setattr(function_module, "InProcessLlmBackend", _RecordingBackend)
    return _RecordingBackend


def _synthesize_two(user_config: dict) -> list[tuple[str, LlmGenerationConfig | None]]:
    function = GlobalSynthesisFunction()
    context = _Context(user_config)
    function.process(_card("truck-47"), context)
    function.process(_card("truck-12"), context)
    return function._backend.calls


def _expected_default_prompt() -> str:
    cards = [from_json(EnrichmentCard, _card(t)) for t in ("truck-47", "truck-12")]
    scope = decide_scope(cards)
    reroute_recommended, reroute_detail = decide_reroute(cards, scope)
    return render_synthesis_prompt(
        corridor="I-95N",
        cards=cards,
        scope=scope,
        reroute_recommended=reroute_recommended,
        reroute_detail=reroute_detail,
    )


def test_default_threshold_synthesizes_on_second_card():
    function = GlobalSynthesisFunction()
    context = _Context({})
    assert function.process(_card("truck-47"), context) is None
    synthesis = from_json(
        IncidentSynthesis, function.process(_card("truck-12"), context)
    )
    assert synthesis.scope == SCOPE_CORRIDOR_WIDE
    assert set(synthesis.affected_truck_ids) == {"truck-47", "truck-12"}


def test_user_config_threshold_waits_for_all_three_trucks():
    function = GlobalSynthesisFunction()
    context = _Context({"corridor_threshold": "3"})
    assert function.process(_card("truck-47"), context) is None
    assert function.process(_card("truck-12"), context) is None
    synthesis = from_json(
        IncidentSynthesis, function.process(_card("truck-31"), context)
    )
    assert set(synthesis.affected_truck_ids) == {"truck-47", "truck-12", "truck-31"}
    assert synthesis.reroute_recommended


def test_user_config_extra_args_reach_the_backend():
    function = GlobalSynthesisFunction()
    function.process(
        _card("truck-47"),
        _Context({"llm_backend": "subprocess", "llm_extra_args": "-no-cnv  --top-k 1"}),
    )
    assert function._backend._extra_args == ("-no-cnv", "--top-k", "1")


def test_user_config_is_valid_json_for_localrun():
    # deploy/run_tier2_localrun.sh builds --user-config as a JSON object of strings.
    config = json.loads('{"llm_extra_args": "-no-cnv", "corridor_threshold": "3"}')
    function = GlobalSynthesisFunction()
    for truck in ("truck-47", "truck-12"):
        assert function.process(_card(truck), _Context(config)) is None


def test_multi_line_prompt_template_is_valid_json_for_localrun():
    config = json.loads(
        json.dumps(
            {"corridor_threshold": "3", "prompt_template": PUBLISHED_SYNTHESIS_WARNING_PROMPT}
        )
    )
    assert "\n" in config["prompt_template"]
    function = GlobalSynthesisFunction()
    for truck in ("truck-47", "truck-12"):
        assert function.process(_card(truck), _Context(config)) is None
    assert function._prompt_template == PUBLISHED_SYNTHESIS_WARNING_PROMPT


def test_prompt_template_comes_from_user_config(recording_backend):
    template = "Warn drivers on {corridor} ({truck_count} trucks, {scope}):\n{cards}"
    calls = _synthesize_two({"prompt_template": template})
    prompt, _ = calls[0]
    assert prompt.startswith("Warn drivers on I-95N (2 trucks, corridor_wide):\n- (truck-47)")


def test_max_tokens_and_temperature_reach_the_generation_config(recording_backend):
    calls = _synthesize_two({"max_tokens": "96", "temperature": "0"})
    _, config = calls[0]
    assert config.max_tokens == 96
    assert config.temperature == 0.0


def test_no_new_keys_keep_the_default_prompt_and_config(recording_backend):
    calls = _synthesize_two({})
    prompt, config = calls[0]
    assert prompt == _expected_default_prompt()
    assert config is None
    assert LlmGenerationConfig().max_tokens == 256
    assert LlmGenerationConfig().temperature == 0.7


def test_prompt_template_with_an_unknown_field_fails_at_configure_time(recording_backend):
    function = GlobalSynthesisFunction()
    with pytest.raises(ValueError, match="truck_id"):
        function.process(
            _card("truck-47"), _Context({"prompt_template": "Truck {truck_id} on {corridor}"})
        )
    assert all(not backend.calls for backend in recording_backend.instances)


def test_prompt_template_with_stray_braces_fails_at_configure_time():
    function = GlobalSynthesisFunction()
    with pytest.raises(ValueError, match="prompt_template"):
        function.process(
            _card("truck-47"), _Context({"prompt_template": 'Shape: {"spoken_warning": ""}'})
        )


def test_user_config_threads_and_timeout_reach_the_generation_config():
    function = GlobalSynthesisFunction()
    function.process(
        _card("truck-47"), _Context({"threads": "1", "timeout_seconds": "300"})
    )
    assert function._config.threads == 1
    assert function._config.timeout_seconds == 300.0


def test_no_threads_in_user_config_keeps_the_backend_defaults():
    function = GlobalSynthesisFunction()
    function.process(_card("truck-47"), _Context({}))
    assert function._config is None


def test_subprocess_backend_is_selectable():
    function = GlobalSynthesisFunction()
    function.process(_card("truck-47"), _Context({"llm_backend": "subprocess"}))
    assert isinstance(function._backend, SubprocessLlmBackend)


def test_default_backend_is_in_process_built_once_and_kept():
    function = GlobalSynthesisFunction()
    context = _Context({"threads": "1", "corridor_threshold": "2"})
    function.process(_card("truck-47"), context)
    backend = function._backend
    assert isinstance(backend, InProcessLlmBackend)
    assert backend._threads == 1
    assert backend._gpu_layers == 0
    synthesis = from_json(
        IncidentSynthesis, function.process(_card("truck-12"), context)
    )
    assert synthesis.spoken_warning
    assert function._backend is backend


def test_unknown_backend_is_rejected():
    function = GlobalSynthesisFunction()
    with pytest.raises(ValueError, match="llm_backend"):
        function.process(_card("truck-47"), _Context({"llm_backend": "cloud"}))
