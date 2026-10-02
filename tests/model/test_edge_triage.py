"""Edge Triage Pipeline (coprocessor -> LlmTriageFunction) Tier 3 model evals — see
talk1_edge_intelligence.coprocessor / .triage_function. Opt-in, real
llama.cpp-family runtime (see conftest.py's llm_backend/edge_triage_context fixtures).

Post-pivot (docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md section 5): severity is no
longer a model output at all (severity_classifier.py computes baseline_severity
identically for every model given the same event), so there is nothing left to
"calibrate" a model's severity judgment against — every model would score
identically on that axis regardless of quality. What a model actually controls now
is escalation, given a fixed baseline plus genuinely unstructured operational
context (weather/cargo/dispatch status). This file used to hold a hand-tuned
_SEVERITY_SIGNAL_PROFILE (see git history for the six-round saga that produced it)
comparing the model's severity output against eta_slip_min-derived tiers — that
question no longer applies to the current pipeline at all, so it's gone, not
patched.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent
from talk1_edge_intelligence.coprocessor import TelemetryCoprocessorFunction
from talk1_edge_intelligence.triage_function import LlmTriageFunction

from tests.model.eval_lib import (
    ESCALATION_SCENARIOS,
    check_escalation_direction,
    edge_triage_format_reliability,
    run_edge_triage_trials,
)

pytestmark = pytest.mark.model


def _canonical_event(eta_slip_min: float = 10.0) -> TelemetryEvent:
    """One canonical Edge Triage Pipeline event, used for both the format-reliability check and
    as the base for the escalation-direction scenarios below. truck_id="truck-47"
    matches trip_context.py's pre-seeded entry, so contextual_triggers carries real
    weather/cargo/dispatch data by default, same as production — the escalation
    scenarios below override those specific fields per-scenario without touching
    the event itself (see run_edge_triage_trials' contextual_trigger_overrides)."""
    now = datetime.now(tz=UTC)
    return TelemetryEvent(
        timestamp=now,
        truck_id="truck-47",
        speed_mph=28.0,
        gps=GpsPosition(lat=33.95, lon=-84.4),
        heading=0.0,
        route_segment="I-95N-segment-3",
        corridor="I-95N",
        planned_eta=now,
        current_eta=now,
        signals=Signals(rolling_avg_speed=28.0, eta_slip_min=eta_slip_min, stop_go_index=0.72),
        peak_deceleration_g=0.30,
        abs_engaged=False,
        brake_events=4,
        downshift_events=2,
        _ground_truth="slowdown_incident",
    )


def test_edge_triage_format_reliability_and_escalation_direction(request, edge_triage_context, edge_triage_report):
    total_n = request.config.getoption("--model-eval-runs")
    per_scenario_n = max(1, total_n // 3)
    format_threshold = request.config.getoption("--model-format-threshold")
    max_mismatch_rate = request.config.getoption("--model-severity-max-mismatch-rate")

    coprocessor = TelemetryCoprocessorFunction()
    triage = LlmTriageFunction()
    try:
        # Gate 1: format reliability on one canonical event, full N.
        format_event = _canonical_event()
        format_trials = run_edge_triage_trials(coprocessor, triage, edge_triage_context, format_event, total_n)
        assert len(format_trials) == total_n, (
            f"coprocessor gated out the canonical event (eta_slip_min={format_event.signals.eta_slip_min}, "
            "0 trials produced) — check the default gate bounds against this test's event"
        )
        edge_triage_report.add_latencies([t.latency_seconds for t in format_trials])
        format_result = edge_triage_format_reliability(format_event, format_trials)
        edge_triage_report.format_reliability = format_result

        assert format_result["rate"] >= format_threshold, (
            f"Edge Triage Pipeline format reliability {format_result['rate']:.1%} over {format_result['total']} runs "
            f"is below threshold {format_threshold:.1%}; sample failures: {format_result['sample_failures']}"
        )

        # Gate 2 (only meaningful once gate 1 clears — a low parse rate would starve
        # escalation-direction of samples the same way it used to starve severity
        # calibration): escalation direction across the three operational-context
        # scenarios, baseline_severity held at "medium" to isolate the context variable.
        scenario_trials = {}
        for scenario_name, scenario in ESCALATION_SCENARIOS.items():
            scenario_event = _canonical_event()
            trials = run_edge_triage_trials(
                coprocessor,
                triage,
                edge_triage_context,
                scenario_event,
                per_scenario_n,
                contextual_trigger_overrides=scenario["contextual_triggers"],
                baseline_severity_override="medium",
            )
            scenario_trials[scenario_name] = trials
            edge_triage_report.add_latencies([t.latency_seconds for t in trials])

        escalation_result = check_escalation_direction(scenario_trials)
        edge_triage_report.escalation_calibration = escalation_result

        assert escalation_result["total"] > 0, "no grammar-valid triage cards were produced to check escalation on"
        assert escalation_result["mismatch_rate"] <= max_mismatch_rate, (
            f"Edge Triage Pipeline escalation-direction mismatch rate {escalation_result['mismatch_rate']:.1%} over "
            f"{escalation_result['total']} cards exceeds bound {max_mismatch_rate:.1%}; "
            f"sample mismatches: {escalation_result['sample_mismatches']}"
        )
    finally:
        triage.close()
