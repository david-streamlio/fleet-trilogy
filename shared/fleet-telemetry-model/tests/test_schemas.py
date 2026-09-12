from datetime import UTC, datetime

from fleet_telemetry_model import (
    EnrichmentCard,
    GpsPosition,
    Signals,
    TelemetryEvent,
    from_json,
    strip_ground_truth,
    to_json,
)


def _event(ground_truth: str = "normal") -> TelemetryEvent:
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC)
    return TelemetryEvent(
        timestamp=now,
        truck_id="truck-47",
        speed_mph=35.0,
        gps=GpsPosition(lat=33.95, lon=-84.40),
        heading=0.0,
        route_segment="I-95N-segment-0",
        corridor="I-95N",
        planned_eta=now,
        current_eta=now,
        signals=Signals(rolling_avg_speed=35.0, eta_slip_min=4.0, stop_go_index=0.8),
        brake_events=2,
        downshift_events=1,
        _ground_truth=ground_truth,
    )


def test_ground_truth_round_trips_through_the_wire_alias():
    event = _event("slowdown_incident")
    payload = to_json(event)
    assert '"_ground_truth":"slowdown_incident"' in payload.replace(" ", "")

    restored = from_json(TelemetryEvent, payload)
    assert restored.ground_truth == "slowdown_incident"


def test_strip_ground_truth_removes_the_label_before_inference():
    event = _event("slowdown_incident")
    payload = event.model_dump(by_alias=True, mode="json")
    assert "_ground_truth" in payload

    stripped = strip_ground_truth(payload)
    assert "_ground_truth" not in stripped
    assert stripped["truck_id"] == "truck-47"


def test_enrichment_card_round_trips_json():
    card = EnrichmentCard(
        event="traffic_incident_suspected",
        severity="high",
        signals=["sustained_low_speed", "stop_go_index", "eta_slip"],
        eta_impact=4.0,
        corridor="I-95N",
        truck_id="truck-47",
    )
    restored = from_json(EnrichmentCard, to_json(card))
    assert restored == card
