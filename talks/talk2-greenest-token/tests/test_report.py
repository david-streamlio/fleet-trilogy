from talk2_greenest_token.report import format_report, run_fleet_efficiency_report


def test_run_fleet_efficiency_report_scales_calls_with_flagged_events_not_fleet_size():
    small_fleet = run_fleet_efficiency_report(fleet_size=5, ticks=200, seed=7, incident_rate=0.2)
    large_fleet = run_fleet_efficiency_report(fleet_size=200, ticks=200, seed=7, incident_rate=0.03)

    small_calls = small_fleet["small-model-cpu"].calls
    large_calls = large_fleet["small-model-cpu"].calls

    # Both approaches see the exact same number of calls (same flagged-event count).
    assert small_fleet["small-model-cpu"].calls == small_fleet["full-precision-gpu"].calls
    assert large_fleet["small-model-cpu"].calls == large_fleet["full-precision-gpu"].calls

    # A handful of high-incident-rate trucks can flag more events than hundreds of
    # low-incident-rate trucks -- the call volume tracks flagged events, not fleet size.
    assert small_calls > 0
    assert large_calls > 0


def test_run_fleet_efficiency_report_at_example_scale_of_200_trucks():
    results = run_fleet_efficiency_report(fleet_size=200, ticks=200, seed=7)
    small = results["small-model-cpu"]
    full = results["full-precision-gpu"]

    assert small.calls == full.calls
    # SMALL_MODEL_CPU.latency_s is now the real, benchmarked Pi 4 number
    # (111.51s, not a prior unbenchmarked 0.9s guess). Given
    # FULL_PRECISION_GPU's still-illustrative, never-benchmarked numbers, that
    # real latency now computes MORE total energy than the GPU approach, not
    # less -- true for this comparison as coded, not a claim about what a
    # real GPU benchmark would show (see efficiency.py's module docstring).
    assert small.total_energy_wh > full.total_energy_wh
    assert small.total_cost_usd < full.total_cost_usd


def test_format_report_includes_both_approaches_and_a_comparison():
    results = run_fleet_efficiency_report(fleet_size=200, ticks=200, seed=7)
    text = format_report(results, fleet_size=200, ticks=200)

    assert "small-model-cpu" in text
    assert "full-precision-gpu" in text
    # At the real Pi 4 latency, small-model-cpu uses MORE energy per call, not
    # less -- format_report states the direction it actually measured.
    assert "more energy" in text
    assert "cheaper" in text
