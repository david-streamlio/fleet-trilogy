from datetime import UTC, datetime

from fleet_telemetry_model import GpsPosition, RollingZScoreDetector, Signals, TelemetryEvent
from fleet_telemetry_model.zscore_detection import DEFAULT_MIN_HISTORY


def _event(
    *, truck_id: str = "truck-47", rolling_avg_speed: float, eta_slip_min: float, stop_go_index: float
) -> TelemetryEvent:
    now = datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC)
    return TelemetryEvent(
        timestamp=now,
        truck_id=truck_id,
        speed_mph=rolling_avg_speed,
        gps=GpsPosition(lat=33.95, lon=-84.40),
        heading=0.0,
        route_segment="I-95N-segment-0",
        corridor="I-95N",
        planned_eta=now,
        current_eta=now,
        signals=Signals(
            rolling_avg_speed=rolling_avg_speed,
            eta_slip_min=eta_slip_min,
            stop_go_index=stop_go_index,
        ),
        _ground_truth="normal",
    )


def _feed_nominal_baseline(
    detector: RollingZScoreDetector, *, truck_id: str, count: int, base_speed: float = 68.0
) -> None:
    # Real telemetry always carries some jitter (see fleet_simulator.scenario's
    # NOMINAL_SPEED_JITTER_MPH) — a perfectly constant baseline has zero variance,
    # which makes any nonzero deviation read as an infinite z-score. Small
    # deterministic jitter keeps these tests realistic instead of hitting that
    # degenerate edge case.
    for i in range(count):
        jitter = 0.5 if i % 2 == 0 else -0.5
        detector.is_probable_slowdown(
            _event(
                truck_id=truck_id,
                rolling_avg_speed=base_speed + jitter,
                eta_slip_min=0.05 if i % 2 == 0 else 0.0,
                stop_go_index=0.02 if i % 2 == 0 else 0.0,
            )
        )


def test_cold_start_never_flags_before_min_history():
    detector = RollingZScoreDetector(min_history=DEFAULT_MIN_HISTORY)
    for _ in range(DEFAULT_MIN_HISTORY - 1):
        result = detector.is_probable_slowdown(
            _event(rolling_avg_speed=68.0, eta_slip_min=0.0, stop_go_index=0.0)
        )
        assert result is False
    # Even an extreme sample can't trigger detection until min_history is reached.
    result = detector.is_probable_slowdown(
        _event(rolling_avg_speed=10.0, eta_slip_min=20.0, stop_go_index=1.0)
    )
    assert result is False


def test_deviation_from_own_baseline_is_flagged():
    detector = RollingZScoreDetector(min_history=10, z_threshold=2.0)
    _feed_nominal_baseline(detector, truck_id="truck-47", count=10)

    result = detector.is_probable_slowdown(
        _event(rolling_avg_speed=20.0, eta_slip_min=15.0, stop_go_index=0.9)
    )
    assert result is True


def test_nominal_traffic_matching_baseline_is_not_flagged():
    detector = RollingZScoreDetector(min_history=10, z_threshold=2.0)
    _feed_nominal_baseline(detector, truck_id="truck-47", count=10)

    result = detector.is_probable_slowdown(
        _event(rolling_avg_speed=67.0, eta_slip_min=0.1, stop_go_index=0.02)
    )
    assert result is False


def test_one_signal_deviating_alone_is_not_flagged():
    detector = RollingZScoreDetector(min_history=10, z_threshold=2.0)
    _feed_nominal_baseline(detector, truck_id="truck-47", count=10)

    result = detector.is_probable_slowdown(
        _event(rolling_avg_speed=10.0, eta_slip_min=0.0, stop_go_index=0.0)
    )
    assert result is False


def test_baselines_are_independent_per_truck():
    detector = RollingZScoreDetector(min_history=10, z_threshold=2.0)
    _feed_nominal_baseline(detector, truck_id="truck-47", count=10)
    # truck-48 has no history of its own yet, so it must not benefit (or suffer)
    # from truck-47's baseline.
    result = detector.is_probable_slowdown(
        _event(truck_id="truck-48", rolling_avg_speed=68.0, eta_slip_min=0.0, stop_go_index=0.0)
    )
    assert result is False


def test_a_truck_with_a_naturally_slower_baseline_is_not_flagged_at_that_speed():
    # A mountain-corridor truck whose *normal* cruising speed is 45mph should not
    # be judged against the same fixed 40mph global threshold every other truck
    # gets judged against — that's the whole point of a per-truck baseline.
    detector = RollingZScoreDetector(min_history=10, z_threshold=2.0)
    _feed_nominal_baseline(detector, truck_id="truck-mountain", count=15, base_speed=45.0)
    result = detector.is_probable_slowdown(
        _event(truck_id="truck-mountain", rolling_avg_speed=44.5, eta_slip_min=0.0, stop_go_index=0.0)
    )
    assert result is False


def test_detection_does_not_go_blind_partway_through_a_sustained_incident():
    # Without freezing a signal's baseline while it's anomalous, a long enough
    # incident's own values get absorbed into the window that's supposed to
    # represent "normal," so the detector loses sensitivity partway through —
    # the exact recall collapse this fix targets. Simulate an incident well
    # past the window size and require every tick to still be flagged.
    detector = RollingZScoreDetector(window_size=40, min_history=10, z_threshold=2.0)
    _feed_nominal_baseline(detector, truck_id="truck-47", count=10)

    for tick in range(50):
        result = detector.is_probable_slowdown(
            _event(
                rolling_avg_speed=20.0,
                eta_slip_min=1.0 + tick * 0.6,
                stop_go_index=0.9,
            )
        )
        assert result is True, f"lost detection at incident tick {tick}"
