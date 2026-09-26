import json
import logging
from datetime import UTC, datetime

from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent, to_json
from talk1_edge_intelligence.coprocessor import (
    TelemetryCoprocessorFunction,
    build_triage_payload,
    traffic_pattern_from_stop_go_index,
    velocity_context,
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


def _event(
    *, rolling_avg_speed: float, eta_slip_min: float, stop_go_index: float, route_segment: str = "seg-1"
) -> TelemetryEvent:
    return TelemetryEvent(
        timestamp=datetime(2026, 9, 12, 17, 15, 0, tzinfo=UTC),
        truck_id="truck-47",
        speed_mph=rolling_avg_speed,
        gps=GpsPosition(lat=0.0, lon=0.0),
        heading=0.0,
        route_segment=route_segment,
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


def test_traffic_pattern_thresholds_give_three_distinct_descriptions_in_the_detection_valid_range():
    # (0.5, 1.0] is the only range build_triage_payload ever actually sees in production
    # (is_probable_slowdown already requires stop_go_index >= detection.STOP_GO_INDEX_THRESHOLD),
    # so it needs three genuinely distinct descriptions across THAT range, not just two —
    # see this function's own docstring for why (a real Tier-3 eval run showed the LLM
    # defaults to the more severe of two tiers whenever they share text).
    mild = traffic_pattern_from_stop_go_index(0.55)
    elevated = traffic_pattern_from_stop_go_index(0.72)
    severe = traffic_pattern_from_stop_go_index(0.9)
    assert len({mild, elevated, severe}) == 3
    assert "mild" in mild
    assert "elevated" in elevated
    assert "severe" in severe
    assert "steady" in traffic_pattern_from_stop_go_index(0.1)


def test_build_triage_payload_shape_matches_llm_triage_function_expectations():
    event = _event(rolling_avg_speed=35.0, eta_slip_min=13.8, stop_go_index=0.9)
    payload = build_triage_payload(event, ["sustained_low_speed", "stop_go_index", "eta_slip"])

    assert payload["truck_id"] == "truck-47"
    assert payload["corridor"] == "I-95N"
    assert payload["signals"] == ["sustained_low_speed", "stop_go_index", "eta_slip"]
    assert payload["metrics"]["eta_slip_min"] == 13.8
    assert payload["metrics"]["rolling_avg_speed"] == 35.0
    assert "severe" in payload["metrics"]["traffic_pattern"]
    assert payload["contextual_triggers"]["local_time"] == event.timestamp.isoformat()
    # "seg-1" has no pre-seeded route plan (route_plans.py) -- no fabricated
    # historical_baseline_speed, same honesty discipline as everywhere else here.
    assert "historical_baseline_speed" not in payload["contextual_triggers"]


def test_velocity_context_is_none_for_a_segment_with_no_pre_seeded_plan():
    assert velocity_context(actual_speed_mph=35.0, route_segment="seg-1") is None


def test_velocity_context_computes_real_deviation_for_a_pre_seeded_segment():
    # I-95N-segment-3 is pre-seeded in route_plans.py at 45.0 mph planned.
    context = velocity_context(actual_speed_mph=39.0, route_segment="I-95N-segment-3")
    assert context is not None
    assert "45" in context
    assert "13%" in context
    assert "below" in context


def test_build_triage_payload_includes_real_baseline_for_a_pre_seeded_segment():
    event = _event(
        rolling_avg_speed=39.0, eta_slip_min=4.0, stop_go_index=0.55, route_segment="I-95N-segment-3"
    )
    payload = build_triage_payload(event, ["sustained_low_speed", "stop_go_index", "eta_slip"])
    assert "historical_baseline_speed" in payload["contextual_triggers"]
    assert "45" in payload["contextual_triggers"]["historical_baseline_speed"]


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
