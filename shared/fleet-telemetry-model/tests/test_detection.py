from datetime import UTC, datetime

from fleet_telemetry_model import (
    GpsPosition,
    Signals,
    TelemetryEvent,
    is_probable_slowdown,
)


def _event(*, rolling_avg_speed: float, eta_slip_min: float, stop_go_index: float) -> TelemetryEvent:
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC)
    return TelemetryEvent(
        timestamp=now,
        truck_id="truck-47",
        speed_mph=rolling_avg_speed,
        gps=GpsPosition(lat=33.95, lon=-84.40),
        heading=0.0,
        route_segment="I-95N-segment-0",
        corridor="I-95N",
        planned_eta=now,
        current_eta=now,
        signals=Signals(
            rolling_avg_speed=rolling_avg_speed,
            eta_slip_min=eta_slip_min,
            stop_go_index=stop_go_index,
        ),
        _ground_truth="normal",
    )


def test_nominal_traffic_is_not_a_slowdown():
    event = _event(rolling_avg_speed=68.0, eta_slip_min=0.0, stop_go_index=0.0)
    assert is_probable_slowdown(event) is False


def test_all_three_signals_together_is_a_slowdown():
    event = _event(rolling_avg_speed=35.0, eta_slip_min=4.0, stop_go_index=0.8)
    assert is_probable_slowdown(event) is True


def test_low_speed_alone_is_not_a_slowdown():
    event = _event(rolling_avg_speed=35.0, eta_slip_min=0.0, stop_go_index=0.0)
    assert is_probable_slowdown(event) is False


def test_stop_go_index_alone_is_not_a_slowdown():
    event = _event(rolling_avg_speed=68.0, eta_slip_min=0.0, stop_go_index=0.9)
    assert is_probable_slowdown(event) is False
