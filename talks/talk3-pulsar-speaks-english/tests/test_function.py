import json

import pytest
from fleet_telemetry_model import EnrichmentCard, IncidentSynthesis, from_json, to_json
from talk3_pulsar_speaks_english.function import GlobalSynthesisFunction
from talk3_pulsar_speaks_english.synthesizer import SCOPE_CORRIDOR_WIDE


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
        _card("truck-47"), _Context({"llm_extra_args": "-no-cnv  --top-k 1"})
    )
    assert function._backend._extra_args == ("-no-cnv", "--top-k", "1")


def test_user_config_is_valid_json_for_localrun():
    # deploy/run_tier2_localrun.sh builds --user-config as a JSON object of strings.
    config = json.loads('{"llm_extra_args": "-no-cnv", "corridor_threshold": "3"}')
    function = GlobalSynthesisFunction()
    for truck in ("truck-47", "truck-12"):
        assert function.process(_card(truck), _Context(config)) is None
