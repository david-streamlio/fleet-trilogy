from datetime import UTC, datetime

from llm_inference import (
    SubprocessLlmBackend,
    generate_enrichment_card_dict,
    render_enrichment_prompt,
    render_tier2_prompt,
)
from fleet_telemetry_model import EnrichmentCard, GpsPosition, Signals, TelemetryEvent


def _event() -> TelemetryEvent:
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
        _ground_truth="slowdown_incident",
    )


def test_render_enrichment_prompt_includes_truck_and_signals():
    prompt = render_enrichment_prompt(_event(), ["sustained_low_speed", "eta_slip"])
    assert "truck-47" in prompt
    assert "I-95N" in prompt
    assert "sustained_low_speed" in prompt


def test_generate_enrichment_card_dict_parses_mock_completion_into_a_valid_card():
    backend = SubprocessLlmBackend(mock=True)
    card_dict = generate_enrichment_card_dict(
        backend, _event(), ["sustained_low_speed", "stop_go_index", "eta_slip"]
    )
    card = EnrichmentCard(**card_dict)
    assert card.truck_id == "truck-47"
    assert card.corridor == "I-95N"


def test_render_tier2_prompt_summarizes_structured_cards():
    card = EnrichmentCard(
        event="traffic_incident_suspected",
        severity="high",
        signals=["sustained_low_speed", "stop_go_index", "eta_slip"],
        eta_impact=4.0,
        corridor="I-95N",
        truck_id="truck-47",
    )
    prompt = render_tier2_prompt("I-95N", [card])
    assert "I-95N" in prompt
    assert "truck-47" in prompt
    assert "traffic_incident_suspected" in prompt
