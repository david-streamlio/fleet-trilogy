"""TelemetryCoprocessorFunction — Flow B's producer: a standalone Pulsar
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
timestamp; it does not emit historical_baseline_speed at all, since there's no
real source for it in this schema. See triage_function.py's DEFAULT_PROMPT_TEMPLATE,
which renders "unknown" for that field when it's absent instead of a made-up number.
"""

from __future__ import annotations

import json

from fleet_telemetry_model import (
    TelemetryEvent,
    evaluate_signals,
    from_json,
    is_probable_slowdown,
)

DEFAULT_MIN_ETA_SLIP_MIN = 3.0
DEFAULT_MAX_ETA_SLIP_MIN = 60.0


def traffic_pattern_from_stop_go_index(stop_go_index: float) -> str:
    """Descriptive label for the real stop_go_index scalar — not a fabricated trend."""
    if stop_go_index > 0.7:
        return "high velocity variance (aggressive stop-and-go spikes)"
    if stop_go_index > 0.3:
        return "moderate speed oscillations (unstable wave flow)"
    return "steady compression (uniform linear deceleration)"


def build_triage_payload(event: TelemetryEvent, triggered_signals: list[str]) -> dict:
    """The Flow B payload shape LlmTriageFunction.process() parses."""
    return {
        "truck_id": event.truck_id,
        "corridor": event.corridor,
        "signals": triggered_signals,
        "metrics": {
            "rolling_avg_speed": event.signals.rolling_avg_speed,
            "eta_slip_min": event.signals.eta_slip_min,
            "traffic_pattern": traffic_pattern_from_stop_go_index(event.signals.stop_go_index),
        },
        "contextual_triggers": {
            "local_time": event.timestamp.isoformat(),
        },
    }


class TelemetryCoprocessorFunction:
    """Matches the Pulsar Functions Python API: a class with process(self, input, context).

    Config (the eta_slip_min gate bounds) is read from user config lazily on the
    first process() call — same convention as LlmTriageFunction, so both stages
    of Flow B are tunable via `pulsar-admin functions update --user-config`
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
        return json.dumps(build_triage_payload(event, triggered_signals))

    def _configure(self, context) -> None:
        get = context.get_user_config_value
        min_val = get("min_eta_slip_min")
        max_val = get("max_eta_slip_min")
        self._min_eta_slip_min = float(min_val) if min_val is not None else DEFAULT_MIN_ETA_SLIP_MIN
        self._max_eta_slip_min = float(max_val) if max_val is not None else DEFAULT_MAX_ETA_SLIP_MIN
        self._configured = True
