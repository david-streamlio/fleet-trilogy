"""(a) FORMAT RELIABILITY — see docs/CANON.md for the Truck 47 / I-95N scenario this
telemetry represents. Opt-in, real llama.cpp-family runtime (see conftest.py)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent

from tests.model.eval_lib import format_reliability, run_enrichment_trials

pytestmark = pytest.mark.model


def _truck_47_slowdown_event() -> TelemetryEvent:
    now = datetime.now(tz=UTC)
    return TelemetryEvent(
        timestamp=now,
        truck_id="truck-47",
        speed_mph=35.0,
        gps=GpsPosition(lat=33.95, lon=-84.4),
        heading=0.0,
        route_segment="I-95N-segment-3",
        corridor="I-95N",
        planned_eta=now,
        current_eta=now,
        signals=Signals(rolling_avg_speed=35.0, eta_slip_min=6.0, stop_go_index=0.7),
        brake_events=4,
        downshift_events=2,
        _ground_truth="slowdown_incident",
    )


def test_format_reliability_meets_threshold(request, llm_backend, tier3_report):
    n = request.config.getoption("--model-eval-runs")
    threshold = request.config.getoption("--model-format-threshold")
    timeout_seconds = request.config.getoption("--model-timeout-seconds")
    event = _truck_47_slowdown_event()

    trials = run_enrichment_trials(llm_backend, event, n, timeout_seconds)
    result = format_reliability(trials)
    tier3_report.format_reliability = result
    tier3_report.add_latencies([t.latency_seconds for t in trials])

    assert result["rate"] >= threshold, (
        f"format reliability {result['rate']:.1%} over {result['total']} runs is below "
        f"threshold {threshold:.1%}; sample failures: {result['sample_failures']}"
    )
