import random
from datetime import UTC, datetime

from fleet_simulator.scenario import TruckState


def _truck(**overrides) -> TruckState:
    defaults = {
        "truck_id": "truck-47",
        "corridor": "I-95N",
        "start_time": datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC),
        "rng": random.Random(0),
        "incident_rate": 0.0,
    }
    defaults.update(overrides)
    return TruckState(**defaults)


def test_same_seed_produces_identical_event_sequences():
    a = _truck(rng=random.Random(42))
    b = _truck(rng=random.Random(42))
    events_a = [a.step() for _ in range(10)]
    events_b = [b.step() for _ in range(10)]
    assert [e.speed_mph for e in events_a] == [e.speed_mph for e in events_b]
    assert [e.ground_truth for e in events_a] == [e.ground_truth for e in events_b]


def test_no_incident_with_zero_incident_rate_and_no_forced_start():
    truck = _truck(incident_rate=0.0)
    events = [truck.step() for _ in range(30)]
    assert all(e.ground_truth == "normal" for e in events)
    assert truck.had_incident is False


def test_forced_incident_starts_within_jitter_window():
    truck = _truck(incident_rate=0.0, force_incident_start_tick=2)
    events = [truck.step() for _ in range(5)]
    assert any(e.ground_truth == "slowdown_incident" for e in events)
    assert truck.had_incident is True


def test_incident_events_show_lower_rolling_speed_and_growing_eta_slip():
    truck = _truck(incident_rate=0.0, force_incident_start_tick=0)
    events = [truck.step() for _ in range(20)]
    incident_events = [e for e in events if e.ground_truth == "slowdown_incident"]
    assert incident_events
    assert incident_events[-1].signals.rolling_avg_speed < 68.0
    assert incident_events[-1].signals.eta_slip_min > 0.0
