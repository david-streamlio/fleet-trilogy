from datetime import UTC, datetime

from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent
from llm_inference import SubprocessLlmBackend
from talk1_edge_intelligence.processor import process_event


def _event(*, rolling_avg_speed: float, eta_slip_min: float, stop_go_index: float) -> TelemetryEvent:
    return TelemetryEvent(
        timestamp=datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC),
        truck_id="truck-47",
        speed_mph=rolling_avg_speed,
        gps=GpsPosition(lat=0.0, lon=0.0),
        heading=0.0,
        route_segment="seg-1",
        corridor="I-95N",
        planned_eta=datetime(2026, 9, 12, 13, 0, 0, tzinfo=UTC),
        current_eta=datetime(2026, 9, 12, 13, 0, 0, tzinfo=UTC),
        signals=Signals(
            rolling_avg_speed=rolling_avg_speed,
            eta_slip_min=eta_slip_min,
            stop_go_index=stop_go_index,
        ),
        _ground_truth="slowdown_incident",
    )


def test_process_event_returns_none_when_cheap_math_does_not_flag_a_slowdown():
    event = _event(rolling_avg_speed=68.0, eta_slip_min=0.0, stop_go_index=0.0)
    backend = SubprocessLlmBackend(mock=True)
    assert process_event(event, backend) is None


def test_process_event_returns_enrichment_card_when_all_three_signals_co_occur():
    event = _event(rolling_avg_speed=35.0, eta_slip_min=4.0, stop_go_index=0.8)
    backend = SubprocessLlmBackend(mock=True)
    card = process_event(event, backend)
    assert card is not None
    assert card.truck_id == "truck-47"
    assert card.corridor == "I-95N"
    assert card.severity
    assert card.signals
