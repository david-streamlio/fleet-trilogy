"""Unit tests for the Edge Triage Pipeline trial runners in eval_lib.py (no model
needed: the coprocessor and triage function are stand-ins)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from itertools import pairwise

from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent

from tests.model.eval_lib import (
    run_edge_triage_trials,
    run_edge_triage_trials_interleaved,
)


def _event(truck_id: str = "truck-47") -> TelemetryEvent:
    now = datetime(2026, 10, 5, 12, 0, 0, tzinfo=UTC)
    return TelemetryEvent(
        timestamp=now,
        truck_id=truck_id,
        speed_mph=28.0,
        gps=GpsPosition(lat=0.0, lon=0.0),
        heading=0.0,
        route_segment="seg-1",
        corridor="I-95N",
        planned_eta=now,
        current_eta=now,
        signals=Signals(rolling_avg_speed=28.0, eta_slip_min=10.0, stop_go_index=0.72),
        _ground_truth="slowdown_incident",
    )


class _Coprocessor:
    """Passes every event through as a triage payload, except trucks in `gated`."""

    def __init__(self, gated: tuple[str, ...] = ()) -> None:
        self._gated = gated

    def process(self, input_item: str, context) -> str | None:
        event = json.loads(input_item)
        if event["truck_id"] in self._gated:
            return None
        return json.dumps(
            {
                "truck_id": event["truck_id"],
                "baseline_severity": "high",
                "contextual_triggers": {"weather_condition": "Heavy rain", "cargo_type": "Tanker"},
            }
        )


class _Backend:
    def __init__(self) -> None:
        self.last_timings: dict | None = None


class _Triage:
    """Records each payload it's asked to triage and echoes it back as the card."""

    def __init__(self) -> None:
        self.payloads: list[dict] = []
        self._backend = _Backend()

    def build_card(self, payload: str, context) -> str:
        self.payloads.append(json.loads(payload))
        self._backend.last_timings = {"prompt_tokens_evaluated": len(self.payloads)}
        return payload


def test_repeated_trials_send_the_same_payload_every_time():
    triage = _Triage()
    trials = run_edge_triage_trials(_Coprocessor(), triage, None, _event(), 3)
    assert len(trials) == 3
    assert triage.payloads[0] == triage.payloads[1] == triage.payloads[2]


def test_interleaved_trials_alternate_so_no_two_consecutive_calls_repeat():
    triage = _Triage()
    variants = [
        {"event": _event(), "contextual_trigger_overrides": {"weather_condition": weather}}
        for weather in ("Heavy rain", "Clear skies", "Fog")
    ]
    trials = run_edge_triage_trials_interleaved(_Coprocessor(), triage, None, variants, 2)

    weathers = [p["contextual_triggers"]["weather_condition"] for p in triage.payloads]
    assert weathers == ["Heavy rain", "Clear skies", "Fog"] * 2
    assert all(a != b for a, b in pairwise(weathers))
    # Grouped back per variant, in variant order.
    assert [len(t) for t in trials] == [2, 2, 2]
    assert {t.parsed["contextual_triggers"]["weather_condition"] for t in trials[1]} == {"Clear skies"}
    # Untouched fields keep the coprocessor's values.
    assert {p["contextual_triggers"]["cargo_type"] for p in triage.payloads} == {"Tanker"}


def test_interleaved_trials_apply_the_baseline_override():
    triage = _Triage()
    variants = [{"event": _event(), "baseline_severity_override": "medium"}]
    run_edge_triage_trials_interleaved(_Coprocessor(), triage, None, variants, 1)
    assert triage.payloads[0]["baseline_severity"] == "medium"


def test_a_gated_variant_gets_no_trials():
    triage = _Triage()
    variants = [{"event": _event("truck-47")}, {"event": _event("truck-gated")}]
    trials = run_edge_triage_trials_interleaved(_Coprocessor(gated=("truck-gated",)), triage, None, variants, 2)
    assert [len(t) for t in trials] == [2, 0]


def test_each_trial_carries_its_own_calls_timings():
    triage = _Triage()
    trials = run_edge_triage_trials(_Coprocessor(), triage, None, _event(), 2)
    assert [t.timings for t in trials] == [{"prompt_tokens_evaluated": 1}, {"prompt_tokens_evaluated": 2}]
