"""Cheap-math thresholding over the signals a TelemetryEvent already carries.

Per docs/CANON.md: detection is math, not the LLM. A SLOWDOWN requires all three
signals to co-occur — sustained low speed, a stop/go pattern (oscillation and/or
braking/downshifting, already folded into `stop_go_index`), and a slipping ETA. Any
one alone is noise.
"""

from __future__ import annotations

from fleet_telemetry_model.schemas import TelemetryEvent

SUSTAINED_SPEED_THRESHOLD_MPH = 40.0
STOP_GO_INDEX_THRESHOLD = 0.5
ETA_SLIP_THRESHOLD_MINUTES = 2.0

SUSTAINED_LOW_SPEED_SIGNAL = "sustained_low_speed"
STOP_GO_INDEX_SIGNAL = "stop_go_index"
ETA_SLIP_SIGNAL = "eta_slip"


def evaluate_signals(
    event: TelemetryEvent,
    *,
    speed_threshold_mph: float = SUSTAINED_SPEED_THRESHOLD_MPH,
    stop_go_index_threshold: float = STOP_GO_INDEX_THRESHOLD,
    eta_slip_threshold_minutes: float = ETA_SLIP_THRESHOLD_MINUTES,
) -> list[str]:
    """Return the names of the cheap-math signals that crossed their threshold."""
    triggered = []
    if event.signals.rolling_avg_speed <= speed_threshold_mph:
        triggered.append(SUSTAINED_LOW_SPEED_SIGNAL)
    if event.signals.stop_go_index >= stop_go_index_threshold:
        triggered.append(STOP_GO_INDEX_SIGNAL)
    if event.signals.eta_slip_min >= eta_slip_threshold_minutes:
        triggered.append(ETA_SLIP_SIGNAL)
    return triggered


def is_probable_slowdown(event: TelemetryEvent, **kwargs: float) -> bool:
    """True only when all three signals co-occur — the SLOWDOWN definition from CANON.md."""
    return len(evaluate_signals(event, **kwargs)) == 3
