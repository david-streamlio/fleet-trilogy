"""(b) GROUNDING / ANTI-HALLUCINATION — feed known values, assert emitted numbers are
traceable to the input, not invented. Opt-in, real llama.cpp-family runtime."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent

from tests.model.eval_lib import check_grounding, run_enrichment_trials

pytestmark = pytest.mark.model


def _known_value_event() -> TelemetryEvent:
    """speed 35 mph, eta_slip_min 18 — known values per the eval spec, so any eta_impact
    the model emits should be traceable to eta_slip_min=18, not invented."""
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
        signals=Signals(rolling_avg_speed=35.0, eta_slip_min=18.0, stop_go_index=0.8),
        brake_events=5,
        downshift_events=3,
        _ground_truth="slowdown_incident",
    )


def test_grounding_violation_rate_within_bound(request, llm_backend, tier3_report):
    n = request.config.getoption("--model-eval-runs")
    max_violation_rate = request.config.getoption("--model-grounding-max-violation-rate")
    timeout_seconds = request.config.getoption("--model-timeout-seconds")
    event = _known_value_event()

    trials = run_enrichment_trials(llm_backend, event, n, timeout_seconds)
    result = check_grounding(event, trials)
    tier3_report.grounding = result
    tier3_report.add_latencies([t.latency_seconds for t in trials])

    assert result["total"] > 0, "no parseable cards were produced to check grounding on"
    assert result["violation_rate"] <= max_violation_rate, (
        f"grounding violation rate {result['violation_rate']:.1%} over {result['total']} "
        f"parsed cards exceeds bound {max_violation_rate:.1%}; "
        f"sample violations: {result['sample_violations']}"
    )
