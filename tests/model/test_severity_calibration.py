"""(e) SEVERITY CALIBRATION — does the model's "severity" match the tier implied by the
input's own eta_slip_min (see eval_lib.expected_severity), rather than being a
plausible-looking but ungrounded guess? Opt-in, real llama.cpp-family runtime.

Unlike grounding/format-reliability (one fixed event, n repeats), this exercises three
representative events — one per severity tier — so the check actually covers all three
boundaries instead of testing the model's calibration at a single eta_slip_min value.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent

from tests.model.eval_lib import check_severity_calibration, run_enrichment_trials

pytestmark = pytest.mark.model


def _event(eta_slip_min: float) -> TelemetryEvent:
    """speed 35mph + stop_go_index 0.7 keep all three detection signals firing
    (see fleet_telemetry_model.detection) regardless of which tier eta_slip_min lands in."""
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
        signals=Signals(rolling_avg_speed=35.0, eta_slip_min=eta_slip_min, stop_go_index=0.7),
        brake_events=4,
        downshift_events=2,
        _ground_truth="slowdown_incident",
    )


def test_severity_calibration_within_bound(request, llm_backend, tier3_report):
    total_n = request.config.getoption("--model-eval-runs")
    per_tier_n = max(1, total_n // 3)
    max_mismatch_rate = request.config.getoption("--model-severity-max-mismatch-rate")
    timeout_seconds = request.config.getoption("--model-timeout-seconds")

    # 3.0 -> low, 10.0 -> medium, 20.0 -> high, per eval_lib's threshold constants.
    events = [_event(3.0), _event(10.0), _event(20.0)]
    events_and_trials = []
    for event in events:
        trials = run_enrichment_trials(llm_backend, event, per_tier_n, timeout_seconds)
        events_and_trials.append((event, trials))
        tier3_report.add_latencies([t.latency_seconds for t in trials])

    result = check_severity_calibration(events_and_trials)
    tier3_report.severity_calibration = result

    assert result["total"] > 0, "no parseable cards were produced to check severity calibration on"
    assert result["mismatch_rate"] <= max_mismatch_rate, (
        f"severity calibration mismatch rate {result['mismatch_rate']:.1%} over "
        f"{result['total']} parsed cards exceeds bound {max_mismatch_rate:.1%}; "
        f"sample mismatches: {result['sample_mismatches']}"
    )
