"""Rolling per-truck z-score detection — an alternative to detection.py's fixed
global thresholds (Option A from the "better detection method" discussion; see
docs/CANON.md for why detection must stay cheap math, not ML).

Fixed thresholds (40mph / 0.5 stop-go / 2.0min slip) are the same number for every
truck on every corridor, so a truck whose *normal* cruising speed on a mountain
corridor is 45mph gets judged against the same bar as one that normally cruises at
70mph. A rolling z-score judges each truck against its own recent history instead:
a signal only counts as anomalous when it deviates from *that truck's own baseline*
by more than `z_threshold` standard deviations, in the direction that matters
(speed dropping, stop/go rising, ETA slip rising).

Still cheap math, not a trained model: no training data, no model artifact to
version, just running mean/variance over a bounded per-truck window. State (one
rolling window per truck, per signal) is the price of that — this can't be a pure
function of one event like detection.evaluate_signals is, so it's a class instead.

The baseline for a given call is always computed from history *before* that call's
event is added — an event never gets to shift the very baseline it's being judged
against. A truck's history starts empty, so `min_history` calls are needed before
any detection is possible for that truck; until then every signal reads as "not
enough history yet" (never triggered), matching evaluate_signals's "safe" default
of not flagging noise.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field

from fleet_telemetry_model.detection import (
    ETA_SLIP_SIGNAL,
    STOP_GO_INDEX_SIGNAL,
    SUSTAINED_LOW_SPEED_SIGNAL,
)
from fleet_telemetry_model.schemas import TelemetryEvent

DEFAULT_WINDOW_SIZE = 40
DEFAULT_MIN_HISTORY = 10
DEFAULT_Z_THRESHOLD = 2.0


@dataclass
class _TruckHistory:
    window_size: int
    speed: deque[float] = field(init=False)
    stop_go_index: deque[float] = field(init=False)
    eta_slip_min: deque[float] = field(init=False)

    def __post_init__(self) -> None:
        self.speed = deque(maxlen=self.window_size)
        self.stop_go_index = deque(maxlen=self.window_size)
        self.eta_slip_min = deque(maxlen=self.window_size)


def _mean_stddev(values: deque[float]) -> tuple[float, float]:
    n = len(values)
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    return mean, variance**0.5


def _z_score(value: float, history: deque[float]) -> float | None:
    """None means "not enough history to judge" — never treated as anomalous."""
    if len(history) < 2:
        return None
    mean, stddev = _mean_stddev(history)
    if stddev == 0.0:
        # Every past sample was identical; any deviation at all is infinitely
        # anomalous in direction, none is anomalous if value == mean.
        return 0.0 if value == mean else float("inf") * (1 if value > mean else -1)
    return (value - mean) / stddev


class RollingZScoreDetector:
    """Stateful, per-truck alternative to detection.is_probable_slowdown.

    Not thread-safe and not shared across processes — one instance per running
    Tier 1 worker, same lifetime assumption as the Pulsar Function's own instance
    state (see talk1_edge_intelligence.function.EdgeEnrichmentFunction).
    """

    def __init__(
        self,
        *,
        window_size: int = DEFAULT_WINDOW_SIZE,
        min_history: int = DEFAULT_MIN_HISTORY,
        z_threshold: float = DEFAULT_Z_THRESHOLD,
    ) -> None:
        if min_history < 2:
            raise ValueError("min_history must be >= 2 (need at least 2 points for a stddev)")
        self._window_size = window_size
        self._min_history = min_history
        self._z_threshold = z_threshold
        self._history: dict[str, _TruckHistory] = defaultdict(
            lambda: _TruckHistory(window_size=window_size)
        )

    def evaluate_signals(self, event: TelemetryEvent) -> list[str]:
        """Return the cheap-math signals that are anomalous relative to this
        truck's own rolling baseline, then record this event into that baseline
        for future calls — unless this exact signal just fired anomalous, in
        which case its baseline is left alone this tick.

        Without that guard, a sustained incident drags its own rising values
        into the window that's supposed to represent "normal," so the baseline
        drifts to match the incident and the detector goes blind partway
        through the exact event it's meant to catch. Freezing a signal's
        baseline while it's anomalous keeps it pinned to the last known-normal
        reading for as long as the anomaly lasts.
        """
        history = self._history[event.truck_id]
        triggered: list[str] = []
        speed_anomalous = stop_go_anomalous = eta_slip_anomalous = False

        if len(history.speed) >= self._min_history:
            speed_z = _z_score(event.signals.rolling_avg_speed, history.speed)
            speed_anomalous = speed_z is not None and speed_z <= -self._z_threshold

            stop_go_z = _z_score(event.signals.stop_go_index, history.stop_go_index)
            stop_go_anomalous = stop_go_z is not None and stop_go_z >= self._z_threshold

            eta_slip_z = _z_score(event.signals.eta_slip_min, history.eta_slip_min)
            eta_slip_anomalous = eta_slip_z is not None and eta_slip_z >= self._z_threshold

            if speed_anomalous:
                triggered.append(SUSTAINED_LOW_SPEED_SIGNAL)
            if stop_go_anomalous:
                triggered.append(STOP_GO_INDEX_SIGNAL)
            if eta_slip_anomalous:
                triggered.append(ETA_SLIP_SIGNAL)

        if not speed_anomalous:
            history.speed.append(event.signals.rolling_avg_speed)
        if not stop_go_anomalous:
            history.stop_go_index.append(event.signals.stop_go_index)
        if not eta_slip_anomalous:
            history.eta_slip_min.append(event.signals.eta_slip_min)
        return triggered

    def is_probable_slowdown(self, event: TelemetryEvent) -> bool:
        """True only when all three signals are anomalous at once — same
        co-occurrence rule as detection.is_probable_slowdown, just judged against
        a per-truck rolling baseline instead of one fixed global threshold.
        """
        return len(self.evaluate_signals(event)) == 3
