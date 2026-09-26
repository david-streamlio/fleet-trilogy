import json
import logging
from datetime import UTC, datetime

from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent, to_json
from talk1_edge_intelligence.coprocessor import (
    TelemetryCoprocessorFunction,
    build_triage_payload,
    traffic_pattern_from_stop_go_index,
)


class _FakeContext:
    """Minimal stand-in for a Pulsar Functions Context: get_logger() and
    get_user_config_value(key), the two methods TelemetryCoprocessorFunction calls.
    """

    def __init__(self, user_config: dict | None = None) -> None:
        self._user_config = user_config or {}
        self._logger = logging.getLogger("test")

    def get_logger(self) -> logging.Logger:
        return self._logger

    def get_user_config_value(self, key: str) -> str | None:
        return self._user_config.get(key)


def _event(*, rolling_avg_speed: float, eta_slip_min: float, stop_go_index: float) -> TelemetryEvent:
    return TelemetryEvent(
        timestamp=datetime(2026, 9, 12, 17, 15, 0, tzinfo=UTC),
        truck_id="truck-47",
        speed_mph=rolling_avg_speed,
        gps=GpsPosition(lat=0.0, lon=0.0),
        heading=0.0,
        route_segment="seg-1",
        corridor="I-95N",
        planned_eta=datetime(2026, 9, 12, 18, 0, 0, tzinfo=UTC),
        current_eta=datetime(2026, 9, 12, 18, 0, 0, tzinfo=UTC),
        signals=Signals(
            rolling_avg_speed=rolling_avg_speed,
            eta_slip_min=eta_slip_min,
            stop_go_index=stop_go_index,
        ),
        _ground_truth="slowdown_incident",
    )


def test_traffic_pattern_thresholds_match_googles_reviewed_stop_go_index_mapping():
    assert "aggressive" in traffic_pattern_from_stop_go_index(0.8)
    assert "moderate" in traffic_pattern_from_stop_go_index(0.5)
    assert "steady" in traffic_pattern_from_stop_go_index(0.1)


def test_build_triage_payload_shape_matches_llm_triage_function_expectations():
    event = _event(rolling_avg_speed=35.0, eta_slip_min=13.8, stop_go_index=0.8)
    payload = build_triage_payload(event, ["sustained_low_speed", "stop_go_index", "eta_slip"])

    assert payload["truck_id"] == "truck-47"
    assert payload["corridor"] == "I-95N"
    assert payload["signals"] == ["sustained_low_speed", "stop_go_index", "eta_slip"]
    assert payload["metrics"]["eta_slip_min"] == 13.8
    assert payload["metrics"]["rolling_avg_speed"] == 35.0
    assert "aggressive" in payload["metrics"]["traffic_pattern"]
    # No fabricated historical_baseline_speed — only a real, timestamp-derived local_time.
    assert payload["contextual_triggers"]["local_time"] == event.timestamp.isoformat()
    assert "historical_baseline_speed" not in payload["contextual_triggers"]


def test_process_returns_none_when_cheap_math_does_not_flag_a_slowdown():
    event = _event(rolling_avg_speed=68.0, eta_slip_min=0.0, stop_go_index=0.0)
    function = TelemetryCoprocessorFunction()
    result = function.process(to_json(event), _FakeContext())
    assert result is None


def test_process_returns_none_when_eta_slip_below_min_gate():
    # All three signals co-occur (a real math-confirmed slowdown), but the slip is
    # tiny — below the default 3.0-minute gate — so it's not worth LLM compute.
    event = _event(rolling_avg_speed=35.0, eta_slip_min=2.5, stop_go_index=0.8)
    function = TelemetryCoprocessorFunction()
    result = function.process(to_json(event), _FakeContext())
    assert result is None


def test_process_returns_none_when_eta_slip_above_max_gate():
    event = _event(rolling_avg_speed=35.0, eta_slip_min=90.0, stop_go_index=0.8)
    function = TelemetryCoprocessorFunction()
    result = function.process(to_json(event), _FakeContext())
    assert result is None


def test_process_returns_triage_payload_when_all_three_signals_co_occur_within_gate():
    event = _event(rolling_avg_speed=35.0, eta_slip_min=13.8, stop_go_index=0.8)
    function = TelemetryCoprocessorFunction()
    result = function.process(to_json(event), _FakeContext())

    assert result is not None
    payload = json.loads(result)
    assert payload["truck_id"] == "truck-47"
    assert set(payload["signals"]) == {"sustained_low_speed", "stop_go_index", "eta_slip"}
    assert payload["metrics"]["eta_slip_min"] == 13.8


def test_process_gate_bounds_are_configurable_via_user_config():
    # A slip of 2.5 min is below the default 3.0 min gate but within a
    # user-configured 2.0 min gate — lazy config must actually take effect.
    event = _event(rolling_avg_speed=35.0, eta_slip_min=2.5, stop_go_index=0.8)
    function = TelemetryCoprocessorFunction()
    context = _FakeContext({"min_eta_slip_min": "2.0"})

    result = function.process(to_json(event), context)

    assert result is not None
    assert function._min_eta_slip_min == 2.0


def test_process_only_configures_once():
    event = _event(rolling_avg_speed=35.0, eta_slip_min=13.8, stop_go_index=0.8)
    function = TelemetryCoprocessorFunction()
    context = _FakeContext({"min_eta_slip_min": "3.0"})

    function.process(to_json(event), context)
    context._user_config["min_eta_slip_min"] = "999.0"
    function.process(to_json(event), context)

    assert function._min_eta_slip_min == 3.0


def test_process_returns_none_on_unparseable_input():
    function = TelemetryCoprocessorFunction()
    result = function.process("not json", _FakeContext())
    assert result is None
