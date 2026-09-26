"""Flow B (coprocessor -> LlmTriageFunction) Tier 3 model evals — see
talk1_edge_intelligence.coprocessor / .triage_function. Opt-in, real
llama.cpp-family runtime (see conftest.py's llm_backend/flow_b_context fixtures).

Unlike Flow A, severity here is grammar-constrained to exactly one of
low/medium/high and eta_impact/truck_id are hardcoded post-generation, not model
output — see eval_lib.py's Flow B section for what that changes about what
"format reliability" and "severity calibration" actually measure here.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent
from talk1_edge_intelligence.coprocessor import TelemetryCoprocessorFunction
from talk1_edge_intelligence.triage_function import LlmTriageFunction

from tests.model.eval_lib import (
    check_flow_b_severity_calibration,
    expected_severity,
    flow_b_format_reliability,
    run_flow_b_trials,
)

pytestmark = pytest.mark.model

# Qualitative signals (rolling_avg_speed, stop_go_index) scaled to actually match each
# severity tier, keyed by eval_lib.expected_severity (the same tier boundaries
# check_flow_b_severity_calibration judges against) — the single source of truth for
# what "low"/"medium"/"high" means here.
#
# A real run of this fixture (2026-09-26, eval-results/compare-flow-b-*-20260926T131727Z)
# held stop_go_index=0.8 constant across every tier, so the "low" tier's small
# eta_slip_min was paired with the SAME "aggressive stop-and-go spikes" traffic_pattern
# text (see coprocessor.traffic_pattern_from_stop_go_index) as the "high" tier. Every one
# of 15 models across 5 different families converged on "medium"/"high" for the low tier
# regardless of size or training — strong evidence the qualitative cues, not eta_slip_min,
# were driving the model's judgment, and the fixture was internally inconsistent (a real
# low-severity event wouldn't pair a 4-minute ETA slip with an aggressive stop-go
# signature in the first place). stop_go_index can't go below
# detection.STOP_GO_INDEX_THRESHOLD (0.5) without the coprocessor gating the event out
# entirely (is_probable_slowdown needs all three signals), so "low" sits at that floor
# rather than in traffic_pattern_from_stop_go_index's lowest ("steady compression") bucket.
_SEVERITY_SIGNAL_PROFILE = {
    "low": {"rolling_avg_speed": 39.0, "stop_go_index": 0.50},
    "medium": {"rolling_avg_speed": 28.0, "stop_go_index": 0.60},
    "high": {"rolling_avg_speed": 15.0, "stop_go_index": 0.85},
}


def _event(eta_slip_min: float) -> TelemetryEvent:
    """Builds an event whose qualitative signals (speed, stop_go_index) actually
    match the severity tier eta_slip_min implies, per _SEVERITY_SIGNAL_PROFILE, so
    the model isn't judging a "low" numeric slip against "high"-looking context.
    Every profile still keeps all three cheap-math detection signals firing (see
    fleet_telemetry_model.detection) and every eta_slip_min used below sits inside
    the coprocessor's default [3.0, 60.0] LLM-triage gate (see
    coprocessor.DEFAULT_MIN/MAX_ETA_SLIP_MIN)."""
    profile = _SEVERITY_SIGNAL_PROFILE[expected_severity(eta_slip_min)]
    now = datetime.now(tz=UTC)
    return TelemetryEvent(
        timestamp=now,
        truck_id="truck-47",
        speed_mph=profile["rolling_avg_speed"],
        gps=GpsPosition(lat=33.95, lon=-84.4),
        heading=0.0,
        route_segment="I-95N-segment-3",
        corridor="I-95N",
        planned_eta=now,
        current_eta=now,
        signals=Signals(
            rolling_avg_speed=profile["rolling_avg_speed"],
            eta_slip_min=eta_slip_min,
            stop_go_index=profile["stop_go_index"],
        ),
        brake_events=4,
        downshift_events=2,
        _ground_truth="slowdown_incident",
    )


def test_flow_b_format_reliability_and_severity_calibration(request, flow_b_context, flow_b_report):
    total_n = request.config.getoption("--model-eval-runs")
    per_tier_n = max(1, total_n // 3)
    format_threshold = request.config.getoption("--model-format-threshold")
    max_mismatch_rate = request.config.getoption("--model-severity-max-mismatch-rate")

    # 4.0 -> low, 10.0 -> medium, 20.0 -> high, per eval_lib's SEVERITY_*_MAX_ETA_SLIP_MIN
    # thresholds — the same tiers Flow A's test_severity_calibration.py exercises.
    events = [_event(4.0), _event(10.0), _event(20.0)]

    coprocessor = TelemetryCoprocessorFunction()
    triage = LlmTriageFunction()

    events_and_trials = []
    for event in events:
        trials = run_flow_b_trials(coprocessor, triage, flow_b_context, event, per_tier_n)
        assert len(trials) == per_tier_n, (
            f"coprocessor gated out event with eta_slip_min={event.signals.eta_slip_min} "
            "(0 trials produced) — check the default gate bounds against this test's tiers"
        )
        events_and_trials.append((event, trials))
        flow_b_report.add_latencies([t.latency_seconds for t in trials])

    format_result = {"total": 0, "parsed": 0, "sample_failures": []}
    for event, trials in events_and_trials:
        tier_result = flow_b_format_reliability(event, trials)
        format_result["total"] += tier_result["total"]
        format_result["parsed"] += tier_result["parsed"]
        format_result["sample_failures"].extend(tier_result["sample_failures"])
    format_result["rate"] = (format_result["parsed"] / format_result["total"]) if format_result["total"] else 0.0
    format_result["sample_failures"] = format_result["sample_failures"][:5]
    flow_b_report.format_reliability = format_result

    severity_result = check_flow_b_severity_calibration(events_and_trials)
    flow_b_report.severity_calibration = severity_result

    assert format_result["rate"] >= format_threshold, (
        f"Flow B format reliability {format_result['rate']:.1%} over {format_result['total']} runs "
        f"is below threshold {format_threshold:.1%}; sample failures: {format_result['sample_failures']}"
    )
    assert severity_result["total"] > 0, "no grammar-valid triage cards were produced to check calibration on"
    assert severity_result["mismatch_rate"] <= max_mismatch_rate, (
        f"Flow B severity calibration mismatch rate {severity_result['mismatch_rate']:.1%} over "
        f"{severity_result['total']} cards exceeds bound {max_mismatch_rate:.1%}; "
        f"sample mismatches: {severity_result['sample_mismatches']}"
    )
