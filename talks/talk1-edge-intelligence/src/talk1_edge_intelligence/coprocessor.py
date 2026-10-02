"""TelemetryCoprocessorFunction — the Edge Triage Pipeline's producer: a standalone Pulsar
Function that sits upstream of LlmTriageFunction, consuming raw TelemetryEvent
JSON from the existing (single, shared — see docs/CANON.md) telemetry topic and
emitting the triage payload shape LlmTriageFunction.process() already expects.

Deliberately reuses the real detection already in fleet_telemetry_model
(is_probable_slowdown / evaluate_signals) rather than inventing a second,
parallel detection path — per CANON.md there is exactly one detection
implementation, and it's cheap math, not the LLM. On top of that it applies an
eta_slip_min magnitude gate (configurable, defaults reviewed against Google
AI's draft) purely as a resource-management filter: even a real, math-confirmed
slowdown may be too minor or too obviously catastrophic to be worth spending
LLM compute interpreting.

Also deliberately does NOT fabricate data TelemetryEvent doesn't have. Google
AI's reviewed draft computed a rolling-window "chaos index" (no rolling window
exists here — TelemetryEvent is a single snapshot, not a time series) and
hardcoded a fake historical_baseline_speed context field with a comment
admitting it would be "programmatically generated in production." This module
maps the real stop_go_index scalar to a descriptive traffic_pattern string
instead of a fabricated trend, and derives local_time from the event's real
timestamp. historical_baseline_speed now DOES get emitted, but only from a real
source — route_plans.py's pre-seeded per-segment plan (see velocity_context
below) — and only for segments that actually have one; a segment with no plan
gets no baseline at all, same as before, rather than a fabricated one. See
triage_function.py's DEFAULT_PROMPT_TEMPLATE, which still renders "unknown" for
that field when it's absent.

Also computes `baseline_severity` deterministically now (severity_classifier.py)
rather than leaving it to the LLM — see build_triage_payload's docstring and
docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md for why.
"""

from __future__ import annotations

import json

from fleet_telemetry_model import (
    TelemetryEvent,
    evaluate_signals,
    from_json,
    is_probable_slowdown,
)

from talk1_edge_intelligence.route_plans import get_route_segment_plan
from talk1_edge_intelligence.severity_classifier import classify_severity
from talk1_edge_intelligence.trip_context import get_trip_context

DEFAULT_MIN_ETA_SLIP_MIN = 3.0
DEFAULT_MAX_ETA_SLIP_MIN = 60.0


def traffic_pattern_from_stop_go_index(stop_go_index: float) -> str:
    """Descriptive label for the real stop_go_index scalar — not a fabricated trend.

    build_triage_payload (below) is only ever called after is_probable_slowdown has
    already confirmed all three signals, including stop_go_index >=
    detection.STOP_GO_INDEX_THRESHOLD (0.5) — so in real production use, every call
    this function actually receives lands in (0.5, 1.0], never the "steady" branch
    below. The three thresholds above 0.5 split that real range into three
    genuinely distinct descriptions (not two, as an earlier version had it): a
    real Tier-3 eval run found that when two tiers land in the same bucket here,
    the LLM doesn't split its severity call evenly between them — it defaults to
    the more severe one, regardless of which two tiers were sharing text. Fewer
    than three distinct buckets across the reachable range silently miscalibrates
    the model reading this field, not just the eval measuring it — see
    tests/model/test_edge_triage.py's _SEVERITY_SIGNAL_PROFILE comment for the
    full account.
    """
    if stop_go_index > 0.8:
        return "severe stop-and-go compaction (repeated hard braking)"
    if stop_go_index > 0.65:
        return "elevated velocity variance (frequent speed cycling)"
    if stop_go_index > 0.3:
        return "mild speed oscillations (intermittent deceleration)"
    return "steady compression (uniform linear deceleration)"


def velocity_context(actual_speed_mph: float, route_segment: str) -> str | None:
    """Cheap-math deviation-from-plan description, or None if route_segment has no
    pre-seeded plan (route_plans.py) — never a fabricated baseline.

    Handing the LLM this already-computed fact, instead of a bare planned-speed
    number and letting the model subtract the two itself, is a real, confirmed fix,
    not a guess: a real Tier-3 eval investigation (2026-09-26) chasing why the "low"
    severity tier stayed miscalibrated found that giving two small real models
    (Gemma-3-1B-it, LFM2.5-350M) a raw planned-speed number changed nothing for
    either — neither one reliably computed the deviation itself, and for Gemma it
    made an unrelated tier's calibration worse. Precomputing the percentage here
    and handing it over as a stated fact instead: no effect on Gemma-3-1B-it either
    way (no regression), but LFM2.5-350M's correct "low" call rate went from ~0% to
    60%, and it was genuinely differentiated (a mix of low/medium/high outputs, not
    a keyword-triggered 100%-low overcorrection like an earlier, unfounded-assertion
    version of this same idea caused). Model-dependent, not a universal fix — see
    tests/model/test_edge_triage.py's _SEVERITY_SIGNAL_PROFILE comment for the
    full multi-round account — but a real, no-downside win for at least one model,
    built on real data rather than an assertion.
    """
    plan = get_route_segment_plan(route_segment)
    if plan is None:
        return None
    deviation_pct = 100 * (1 - actual_speed_mph / plan.planned_avg_speed_mph)
    direction = "below" if deviation_pct >= 0 else "above"
    return f"{plan.planned_avg_speed_mph:.0f} mph planned, {abs(deviation_pct):.0f}% {direction} plan"


def build_triage_payload(event: TelemetryEvent, triggered_signals: list[str]) -> dict:
    """The Edge Triage Pipeline payload shape LlmTriageFunction.process() parses.

    `baseline_severity` is computed here, deterministically, by
    severity_classifier.classify_severity — not left for the LLM to derive. See
    that module's docstring for why: ten-plus rounds of real-model testing this
    session found every model asked to classify severity from graduated numeric
    signals unreliable, while a function does the same classification perfectly.
    The LLM's job (triage_function.py) is now a bounded escalate/confirm/
    de-escalate adjustment on top of this baseline, driven by genuinely
    unstructured operational context (trip_context.py) that a lookup table can't
    reduce to a threshold — not re-deriving severity from scratch.
    """
    contextual_triggers = {"local_time": event.timestamp.isoformat()}
    context = velocity_context(event.signals.rolling_avg_speed, event.route_segment)
    if context is not None:
        contextual_triggers["historical_baseline_speed"] = context

    trip_context = get_trip_context(event.truck_id)
    if trip_context is not None:
        contextual_triggers["weather_condition"] = trip_context.weather_condition
        contextual_triggers["cargo_type"] = trip_context.cargo_type
        contextual_triggers["dispatch_status"] = trip_context.dispatch_status

    baseline_severity = classify_severity(
        peak_deceleration_g=event.peak_deceleration_g,
        abs_engaged=event.abs_engaged,
        stop_go_index=event.signals.stop_go_index,
    )

    return {
        "truck_id": event.truck_id,
        "corridor": event.corridor,
        "signals": triggered_signals,
        "metrics": {
            "rolling_avg_speed": event.signals.rolling_avg_speed,
            "eta_slip_min": event.signals.eta_slip_min,
            "traffic_pattern": traffic_pattern_from_stop_go_index(event.signals.stop_go_index),
            "peak_deceleration_g": event.peak_deceleration_g,
            "abs_engaged": event.abs_engaged,
        },
        "baseline_severity": baseline_severity,
        "contextual_triggers": contextual_triggers,
    }


class TelemetryCoprocessorFunction:
    """Matches the Pulsar Functions Python API: a class with process(self, input, context).

    Config (the eta_slip_min gate bounds) is read from user config lazily on the
    first process() call — same convention as LlmTriageFunction, so both stages
    of the Edge Triage Pipeline are tunable via `pulsar-admin functions update --user-config`
    without a code change.
    """

    def __init__(self) -> None:
        self._configured = False
        self._min_eta_slip_min = DEFAULT_MIN_ETA_SLIP_MIN
        self._max_eta_slip_min = DEFAULT_MAX_ETA_SLIP_MIN

    def process(self, input_item: str, context) -> str | None:
        logger = context.get_logger()
        if not self._configured:
            self._configure(context)

        try:
            event = from_json(TelemetryEvent, input_item)
        except Exception as exc:  # noqa: BLE001 — Pulsar Functions expects process() to never raise
            logger.error(f"coprocessor failed to parse telemetry event: {exc}")
            return None

        if not is_probable_slowdown(event):
            return None  # cheap math says no anomaly — nothing to triage

        eta_slip_min = event.signals.eta_slip_min
        if eta_slip_min < self._min_eta_slip_min or eta_slip_min > self._max_eta_slip_min:
            logger.info(
                f"[{event.truck_id}] eta_slip_min={eta_slip_min} outside "
                f"[{self._min_eta_slip_min}, {self._max_eta_slip_min}] gate — bypassing LLM triage"
            )
            return None

        triggered_signals = evaluate_signals(event)
        payload = build_triage_payload(event, triggered_signals)
        logger.info(
            f"[{event.truck_id}] high-value event detected -- signals={triggered_signals} "
            f"eta_slip_min={eta_slip_min} baseline_severity={payload['baseline_severity']!r} "
            f"-- forwarding to triage: {json.dumps(payload)}"
        )
        return json.dumps(payload)

    def _configure(self, context) -> None:
        get = context.get_user_config_value
        min_val = get("min_eta_slip_min")
        max_val = get("max_eta_slip_min")
        self._min_eta_slip_min = float(min_val) if min_val else DEFAULT_MIN_ETA_SLIP_MIN
        self._max_eta_slip_min = float(max_val) if max_val else DEFAULT_MAX_ETA_SLIP_MIN
        self._configured = True
