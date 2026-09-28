from datetime import UTC, datetime

from fleet_simulator import FleetSimulator
from fleet_telemetry_model import EnrichmentCard, GpsPosition, Signals, TelemetryEvent
from fleet_telemetry_model.detection import evaluate_signals
from llm_inference import SubprocessLlmBackend, generate_enrichment_card_dict

from talk3_pulsar_speaks_english.synthesizer import (
    SCOPE_CORRIDOR_WIDE,
    SCOPE_SINGLE_TRUCK,
    decide_reroute,
    decide_scope,
    group_by_corridor,
    synthesize,
)


def _card(*, truck_id: str, corridor: str, severity: str = "high") -> EnrichmentCard:
    return EnrichmentCard(
        event="traffic_incident_suspected",
        severity=severity,
        signals=["sustained_low_speed", "stop_go_index", "eta_slip"],
        eta_impact=4.0,
        corridor=corridor,
        truck_id=truck_id,
    )


def _telemetry_event(
    *, truck_id: str, corridor: str, rolling_avg_speed: float, eta_slip_min: float, stop_go_index: float
) -> TelemetryEvent:
    return TelemetryEvent(
        timestamp=datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC),
        truck_id=truck_id,
        speed_mph=rolling_avg_speed,
        gps=GpsPosition(lat=0.0, lon=0.0),
        heading=0.0,
        route_segment="seg-1",
        corridor=corridor,
        planned_eta=datetime(2026, 9, 12, 13, 0, 0, tzinfo=UTC),
        current_eta=datetime(2026, 9, 12, 13, 0, 0, tzinfo=UTC),
        signals=Signals(
            rolling_avg_speed=rolling_avg_speed,
            eta_slip_min=eta_slip_min,
            stop_go_index=stop_go_index,
        ),
        _ground_truth="slowdown_incident",
    )


def _card_for_event(event: TelemetryEvent, backend) -> EnrichmentCard | None:
    """Mirrors talk1_edge_intelligence.processor.process_event, duplicated here
    per docs/CANON.md (talk packages never depend on each other). The mock
    backend returns a fixed canned completion regardless of input, so truck_id
    and corridor are overridden from the real event afterward.
    """
    from fleet_telemetry_model import is_probable_slowdown

    if not is_probable_slowdown(event):
        return None
    triggered_signals = evaluate_signals(event)
    card_dict = generate_enrichment_card_dict(backend, event, triggered_signals)
    card_dict["truck_id"] = event.truck_id
    card_dict["corridor"] = event.corridor
    return EnrichmentCard(**card_dict)


# --- group_by_corridor ---------------------------------------------------


def test_group_by_corridor_splits_mixed_batch():
    cards = [
        _card(truck_id="truck-01", corridor="I-95N"),
        _card(truck_id="truck-02", corridor="I-95N"),
        _card(truck_id="truck-03", corridor="I-75S"),
    ]
    groups = group_by_corridor(cards)
    assert set(groups) == {"I-95N", "I-75S"}
    assert len(groups["I-95N"]) == 2
    assert len(groups["I-75S"]) == 1


# --- decide_scope ----------------------------------------------------------


def test_decide_scope_single_truck_when_only_one_truck_reports():
    cards = [_card(truck_id="truck-47", corridor="I-95N")]
    assert decide_scope(cards) == SCOPE_SINGLE_TRUCK


def test_decide_scope_corridor_wide_when_multiple_trucks_report():
    cards = [
        _card(truck_id="truck-01", corridor="I-95N"),
        _card(truck_id="truck-02", corridor="I-95N"),
    ]
    assert decide_scope(cards) == SCOPE_CORRIDOR_WIDE


# --- decide_reroute ----------------------------------------------------------


def test_decide_reroute_false_for_single_truck_scope():
    cards = [_card(truck_id="truck-47", corridor="I-95N", severity="high")]
    recommended, detail = decide_reroute(cards, SCOPE_SINGLE_TRUCK)
    assert recommended is False
    assert detail is None


def test_decide_reroute_false_for_corridor_wide_without_high_severity():
    cards = [
        _card(truck_id="truck-01", corridor="I-95N", severity="medium"),
        _card(truck_id="truck-02", corridor="I-95N", severity="low"),
    ]
    recommended, detail = decide_reroute(cards, SCOPE_CORRIDOR_WIDE)
    assert recommended is False
    assert detail is None


def test_decide_reroute_true_for_corridor_wide_with_high_severity():
    cards = [
        _card(truck_id="truck-01", corridor="I-95N", severity="medium"),
        _card(truck_id="truck-02", corridor="I-95N", severity="high"),
    ]
    recommended, detail = decide_reroute(cards, SCOPE_CORRIDOR_WIDE)
    assert recommended is True
    assert detail is not None
    assert "I-95N" in detail


# --- synthesize --------------------------------------------------------------


def test_synthesize_returns_none_for_empty_cards():
    backend = SubprocessLlmBackend(mock=True)
    assert synthesize([], backend) is None


def test_synthesize_single_truck_produces_well_formed_synthesis_without_reroute():
    backend = SubprocessLlmBackend(mock=True)
    cards = [_card(truck_id="truck-47", corridor="I-95N", severity="high")]

    result = synthesize(cards, backend)

    assert result is not None
    assert result.corridor == "I-95N"
    assert result.affected_truck_ids == ["truck-47"]
    assert result.scope == SCOPE_SINGLE_TRUCK
    assert result.reroute_recommended is False
    assert result.reroute_detail is None
    assert result.spoken_warning
    assert result.incident_id
    assert result.synthesized_at > 0


def test_synthesize_corridor_wide_produces_reroute_and_spoken_warning():
    backend = SubprocessLlmBackend(mock=True)
    cards = [
        _card(truck_id="truck-01", corridor="I-95N", severity="high"),
        _card(truck_id="truck-02", corridor="I-95N", severity="high"),
        _card(truck_id="truck-03", corridor="I-95N", severity="medium"),
    ]

    result = synthesize(cards, backend)

    assert result is not None
    assert result.corridor == "I-95N"
    assert result.affected_truck_ids == ["truck-01", "truck-02", "truck-03"]
    assert result.scope == SCOPE_CORRIDOR_WIDE
    assert result.reroute_recommended is True
    assert result.reroute_detail
    assert result.spoken_warning


def test_synthesize_only_considers_the_first_card_corridor_when_batch_is_mixed():
    backend = SubprocessLlmBackend(mock=True)
    cards = [
        _card(truck_id="truck-01", corridor="I-95N", severity="high"),
        _card(truck_id="truck-99", corridor="I-75S", severity="high"),
    ]

    result = synthesize(cards, backend)

    assert result is not None
    assert result.corridor == "I-95N"
    assert result.affected_truck_ids == ["truck-01"]
    assert result.scope == SCOPE_SINGLE_TRUCK


# --- end-to-end with FleetSimulator's correlated-incident scenario ----------


def test_synthesize_over_a_fleet_simulator_corridor_wide_incident():
    backend = SubprocessLlmBackend(mock=True)
    simulator = FleetSimulator(
        fleet_size=6,
        seed=7,
        incident_corridor="I-95N",
        incident_trucks=3,
    )

    cards: list[EnrichmentCard] = []
    for _ in range(60):
        for event in simulator.tick():
            card = _card_for_event(event, backend)
            if card is not None:
                cards.append(card)

    groups = group_by_corridor(cards)
    assert "I-95N" in groups
    corridor_cards = groups["I-95N"]
    # Multiple forced trucks should have produced enrichment cards on I-95N by
    # the end of a 60-tick run (incidents are forced to start within the first
    # few ticks and run 24-48 ticks — see fleet_simulator.scenario).
    assert len({card.truck_id for card in corridor_cards}) > 1

    result = synthesize(corridor_cards, backend)

    assert result is not None
    assert result.corridor == "I-95N"
    assert result.scope == SCOPE_CORRIDOR_WIDE
    assert len(result.affected_truck_ids) > 1
    assert result.reroute_recommended is True
    assert result.spoken_warning
