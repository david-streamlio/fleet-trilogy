import pytest
from fleet_simulator.fleet import TRUCK_47_ID, FleetSimulator


def test_fleet_size_one_is_truck_47():
    fleet = FleetSimulator(fleet_size=1, seed=0)
    assert fleet.truck_ids == [TRUCK_47_ID]


def test_fleet_size_n_produces_n_distinct_truck_ids():
    fleet = FleetSimulator(fleet_size=5, seed=0)
    assert len(fleet.truck_ids) == 5
    assert len(set(fleet.truck_ids)) == 5


def test_tick_returns_one_event_per_truck():
    fleet = FleetSimulator(fleet_size=5, seed=0, incident_rate=0.0)
    events = fleet.tick()
    assert len(events) == 5
    assert {e.truck_id for e in events} == set(fleet.truck_ids)


def test_incident_trucks_cannot_exceed_fleet_size():
    with pytest.raises(ValueError):
        FleetSimulator(
            fleet_size=5, incident_corridor="I-95N", incident_trucks=10, seed=0
        )


def test_correlated_incident_pins_trucks_to_corridor_and_forces_overlap():
    fleet = FleetSimulator(
        fleet_size=50,
        seed=0,
        incident_rate=0.0,
        incident_corridor="I-95N",
        incident_trucks=32,
    )
    events_by_tick = [fleet.tick() for _ in range(6)]

    forced_truck_ids = set(fleet.truck_ids[:32])
    forced_events = [
        e for tick_events in events_by_tick for e in tick_events if e.truck_id in forced_truck_ids
    ]
    assert all(e.corridor == "I-95N" for e in forced_events)

    incident_truck_ids = set(fleet.trucks_with_incidents())
    assert incident_truck_ids == forced_truck_ids

    background_truck_ids = set(fleet.truck_ids) - forced_truck_ids
    background_events = [
        e
        for tick_events in events_by_tick
        for e in tick_events
        if e.truck_id in background_truck_ids
    ]
    assert all(e.ground_truth == "normal" for e in background_events)
