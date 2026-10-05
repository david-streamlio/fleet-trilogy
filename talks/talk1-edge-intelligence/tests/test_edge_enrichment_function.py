from datetime import UTC, datetime

import pytest
from fleet_telemetry_model import (
    EnrichmentCard,
    GpsPosition,
    Signals,
    TelemetryEvent,
    from_json,
    to_json,
)
from llm_inference import InProcessLlmBackend, SubprocessLlmBackend
from talk1_edge_intelligence.function import EdgeEnrichmentFunction


class _Context:
    def __init__(self, user_config: dict) -> None:
        self._user_config = user_config

    def get_user_config_map(self) -> dict:
        return self._user_config


def _slowdown_event() -> str:
    return to_json(
        TelemetryEvent(
            timestamp=datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC),
            truck_id="truck-47",
            speed_mph=35.0,
            gps=GpsPosition(lat=0.0, lon=0.0),
            heading=0.0,
            route_segment="seg-1",
            corridor="I-95N",
            planned_eta=datetime(2026, 9, 12, 13, 0, 0, tzinfo=UTC),
            current_eta=datetime(2026, 9, 12, 13, 0, 0, tzinfo=UTC),
            signals=Signals(rolling_avg_speed=35.0, eta_slip_min=4.0, stop_go_index=0.8),
            _ground_truth="slowdown_incident",
        )
    )


@pytest.fixture(autouse=True)
def _mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "1")


def test_default_backend_is_in_process_and_kept_across_calls():
    function = EdgeEnrichmentFunction()
    context = _Context({})
    card = from_json(EnrichmentCard, function.process(_slowdown_event(), context))
    assert card.truck_id == "truck-47"

    backend = function._backend
    assert isinstance(backend, InProcessLlmBackend)
    assert backend._threads == 4
    assert backend._gpu_layers == 0
    function.process(_slowdown_event(), context)
    assert function._backend is backend


def test_user_config_threads_and_gpu_layers_reach_the_in_process_backend():
    function = EdgeEnrichmentFunction()
    function.process(_slowdown_event(), _Context({"threads": "1", "llm_gpu_layers": "99"}))
    assert function._backend._threads == 1
    assert function._backend._gpu_layers == 99


def test_subprocess_backend_is_selectable():
    function = EdgeEnrichmentFunction()
    function.process(_slowdown_event(), _Context({"llm_backend": "subprocess"}))
    assert isinstance(function._backend, SubprocessLlmBackend)


def test_unknown_backend_is_rejected():
    function = EdgeEnrichmentFunction()
    with pytest.raises(ValueError, match="llm_backend"):
        function.process(_slowdown_event(), _Context({"llm_backend": "cloud"}))
