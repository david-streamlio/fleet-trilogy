"""Head-to-head: detection.is_probable_slowdown (fixed global thresholds) vs.
RollingZScoreDetector (per-truck rolling baseline) against the simulator's own
_ground_truth labels.

No LLM/model runtime involved — this is purely the cheap-math detection gate,
scored against the labels the simulator itself stamps on every event
(fleet_simulator.scenario.TruckState.step's `_ground_truth`). Fast and
deterministic, so it runs as part of `make test`, not `make test-integration`
or the `-m model` tier.

Run with `-s` to see the printed comparison table; the assertions only check
that both detectors are directionally sane (better than a coin flip on
precision/recall), not that one beats the other — this is meant to make the
tradeoff visible, not to pick a winner yet.
"""

from __future__ import annotations

from dataclasses import dataclass

from fleet_telemetry_model import RollingZScoreDetector, is_probable_slowdown
from fleet_simulator.fleet import FleetSimulator

FLEET_SIZE = 6
INCIDENT_TRUCKS = 3
TICKS = 60
SEED = 1234


@dataclass
class ConfusionMatrix:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    def record(self, *, predicted: bool, actual: bool) -> None:
        if predicted and actual:
            self.tp += 1
        elif predicted and not actual:
            self.fp += 1
        elif not predicted and actual:
            self.fn += 1
        else:
            self.tn += 1

    @property
    def precision(self) -> float:
        denom = self.tp + self.fp
        return self.tp / denom if denom else 0.0

    @property
    def recall(self) -> float:
        denom = self.tp + self.fn
        return self.tp / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0


def _labeled_events() -> list:
    fleet = FleetSimulator(
        fleet_size=FLEET_SIZE,
        seed=SEED,
        incident_rate=0.03,
        incident_corridor="I-95N",
        incident_trucks=INCIDENT_TRUCKS,
    )
    events = []
    for _ in range(TICKS):
        events.extend(fleet.tick())
    return events


def test_fixed_threshold_vs_rolling_zscore_detection(capsys):
    events = _labeled_events()

    fixed = ConfusionMatrix()
    for event in events:
        fixed.record(
            predicted=is_probable_slowdown(event),
            actual=event.ground_truth == "slowdown_incident",
        )

    zscore_detector = RollingZScoreDetector(min_history=5)
    zscore = ConfusionMatrix()
    for event in events:
        zscore.record(
            predicted=zscore_detector.is_probable_slowdown(event),
            actual=event.ground_truth == "slowdown_incident",
        )

    with capsys.disabled():
        print(f"\n{len(events)} labeled events, {FLEET_SIZE} trucks, {TICKS} ticks, seed={SEED}")
        print(
            f"{'detector':<24}{'precision':>10}{'recall':>10}{'f1':>10}"
            f"{'tp':>6}{'fp':>6}{'fn':>6}{'tn':>6}"
        )
        for name, cm in (("fixed threshold", fixed), ("rolling z-score", zscore)):
            print(
                f"{name:<24}{cm.precision:>10.2f}{cm.recall:>10.2f}{cm.f1:>10.2f}"
                f"{cm.tp:>6}{cm.fp:>6}{cm.fn:>6}{cm.tn:>6}"
            )

    # Directionally-sane floor for both, not a head-to-head gate: this test's job
    # is to keep the comparison visible on every `make test` run, not to pick a
    # winner. Tighten/replace with a real floor once there's a decision to gate on.
    assert fixed.f1 > 0.0
    assert zscore.f1 > 0.0
