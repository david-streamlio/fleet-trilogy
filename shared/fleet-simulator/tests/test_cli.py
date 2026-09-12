import json
import threading

from fleet_simulator.cli import run_dry_run, run_publish_loop
from fleet_simulator.fleet import FleetSimulator


class FakePublisher:
    def __init__(self):
        self.published: list[bytes] = []

    def publish(self, payload: bytes) -> None:
        self.published.append(payload)


def test_run_dry_run_prints_valid_telemetry_event_json(capsys):
    fleet = FleetSimulator(fleet_size=1, seed=0, incident_rate=0.0)
    run_dry_run(fleet, count=3)
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 3
    for line in lines:
        payload = json.loads(line)
        assert payload["truck_id"] == "truck-47"
        assert "_ground_truth" in payload


def _dry_run_payloads_without_timestamps(fleet: FleetSimulator, count: int, capsys) -> list[dict]:
    run_dry_run(fleet, count=count)
    payloads = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    for payload in payloads:
        del payload["timestamp"], payload["planned_eta"], payload["current_eta"]
    return payloads


def test_run_dry_run_is_deterministic_for_the_same_seed(capsys):
    fleet_a = FleetSimulator(fleet_size=3, seed=7, incident_rate=0.1)
    payloads_a = _dry_run_payloads_without_timestamps(fleet_a, count=4, capsys=capsys)

    fleet_b = FleetSimulator(fleet_size=3, seed=7, incident_rate=0.1)
    payloads_b = _dry_run_payloads_without_timestamps(fleet_b, count=4, capsys=capsys)

    assert payloads_a == payloads_b


def test_run_dry_run_differs_for_different_seeds(capsys):
    fleet_a = FleetSimulator(fleet_size=3, seed=1, incident_rate=0.1)
    payloads_a = _dry_run_payloads_without_timestamps(fleet_a, count=4, capsys=capsys)

    fleet_b = FleetSimulator(fleet_size=3, seed=2, incident_rate=0.1)
    payloads_b = _dry_run_payloads_without_timestamps(fleet_b, count=4, capsys=capsys)

    assert payloads_a != payloads_b


def test_run_publish_loop_stops_at_total_and_reports_summary():
    fleet = FleetSimulator(fleet_size=1, seed=0, incident_rate=1.0)
    publisher = FakePublisher()
    summary = run_publish_loop(
        fleet,
        publisher,
        rate=1000.0,
        duration=None,
        total=5,
        stop_event=threading.Event(),
    )
    assert summary.events == 5
    assert len(publisher.published) == 5
    assert summary.pct_slowdown == 100.0
    assert summary.trucks_in_incident == 1
    assert summary.achieved_rate_eps > 0


def test_run_publish_loop_stops_immediately_if_stop_event_already_set():
    fleet = FleetSimulator(fleet_size=1, seed=0, incident_rate=0.0)
    publisher = FakePublisher()
    stop_event = threading.Event()
    stop_event.set()
    summary = run_publish_loop(
        fleet, publisher, rate=1000.0, duration=None, total=None, stop_event=stop_event
    )
    assert summary.events == 0
    assert publisher.published == []


def test_run_publish_loop_fleet_size_n_reports_correct_slowdown_count():
    fleet = FleetSimulator(
        fleet_size=4, seed=0, incident_rate=0.0, incident_corridor="I-95N", incident_trucks=2
    )
    publisher = FakePublisher()
    summary = run_publish_loop(
        fleet,
        publisher,
        rate=1000.0,
        duration=None,
        # enough ticks that forced incidents (jittered 0-3 ticks) have all started
        total=16,
        stop_event=threading.Event(),
    )
    assert summary.events == 16
    assert summary.trucks_in_incident == 2
