from datetime import UTC, datetime

import pytest
from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent
from talk2_greenest_token.efficiency import (
    FULL_PRECISION_GPU,
    SMALL_MODEL_CPU,
    compare_approaches,
    count_flagged_events,
    savings_factor,
)


def _event(*, rolling_avg_speed: float, eta_slip_min: float, stop_go_index: float) -> TelemetryEvent:
    return TelemetryEvent(
        timestamp=datetime(2026, 9, 12, 12, 0, 0, tzinfo=UTC),
        truck_id="truck-01",
        speed_mph=rolling_avg_speed,
        gps=GpsPosition(lat=0.0, lon=0.0),
        heading=0.0,
        route_segment="seg-1",
        corridor="I-95N",
        planned_eta=datetime(2026, 9, 12, 13, 0, 0, tzinfo=UTC),
        current_eta=datetime(2026, 9, 12, 13, 0, 0, tzinfo=UTC),
        signals=Signals(
            rolling_avg_speed=rolling_avg_speed,
            eta_slip_min=eta_slip_min,
            stop_go_index=stop_go_index,
        ),
        _ground_truth="slowdown_incident",
    )


def test_count_flagged_events_ignores_events_that_do_not_co_occur():
    events = [
        _event(rolling_avg_speed=68.0, eta_slip_min=0.0, stop_go_index=0.0),
        _event(rolling_avg_speed=35.0, eta_slip_min=0.0, stop_go_index=0.8),
    ]
    assert count_flagged_events(events) == 0


def test_count_flagged_events_counts_only_full_slowdown_matches():
    events = [
        _event(rolling_avg_speed=35.0, eta_slip_min=4.0, stop_go_index=0.8),
        _event(rolling_avg_speed=68.0, eta_slip_min=0.0, stop_go_index=0.0),
        _event(rolling_avg_speed=30.0, eta_slip_min=5.0, stop_go_index=0.9),
    ]
    assert count_flagged_events(events) == 2


def test_compare_approaches_scales_linearly_with_call_count():
    zero = compare_approaches(0)
    assert zero["small-model-cpu"].total_energy_wh == 0.0
    assert zero["full-precision-gpu"].total_cost_usd == 0.0

    hundred = compare_approaches(100)
    ten = compare_approaches(10)
    small_hundred = hundred["small-model-cpu"]
    small_ten = ten["small-model-cpu"]
    assert small_hundred.calls == 100
    assert small_hundred.total_latency_s == pytest.approx(small_ten.total_latency_s * 10)
    assert small_hundred.total_energy_wh == pytest.approx(small_ten.total_energy_wh * 10)
    assert small_hundred.total_cost_usd == pytest.approx(small_ten.total_cost_usd * 10)


def test_compare_approaches_rejects_negative_counts():
    with pytest.raises(ValueError):
        compare_approaches(-1)


def test_small_model_cpu_uses_far_less_power_and_cost_per_call_than_full_precision_gpu():
    assert SMALL_MODEL_CPU.power_watts < FULL_PRECISION_GPU.power_watts
    assert SMALL_MODEL_CPU.cost_per_call_usd < FULL_PRECISION_GPU.cost_per_call_usd


def test_savings_factor_reports_cost_advantage_but_energy_disadvantage_for_small_model_cpu():
    """With SMALL_MODEL_CPU.latency_s now the real, benchmarked Pi 4 number
    (111.51s, not the prior unbenchmarked 0.9s guess), energy_factor computes
    < 1 given FULL_PRECISION_GPU's still-illustrative, never-benchmarked
    numbers: the small CPU-only model draws less power per second but takes
    ~372x longer per call, so its computed energy per call is now higher, not
    lower, than the GPU profile's guessed numbers. That's real given those
    guesses; a real GPU benchmark could still move it. cost_factor is
    untouched either way — cost_per_call_usd is a flat, still-illustrative
    assumption on both approaches, independent of latency."""
    results = compare_approaches(500)
    factors = savings_factor(
        baseline=results["full-precision-gpu"], contender=results["small-model-cpu"]
    )
    assert factors["energy_factor"] < 1
    assert factors["cost_factor"] > 1
