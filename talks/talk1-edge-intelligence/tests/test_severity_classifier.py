from talk1_edge_intelligence.severity_classifier import (
    HIGH_G_FLOOR,
    HIGH_VOLATILITY_STOP_GO_INDEX,
    LOW_G_CEILING,
    classify_severity,
)


def test_abs_engaged_always_overrides_to_high():
    # Even a trivial g-force and calm stop_go_index -- ABS is an unconditional override.
    assert classify_severity(peak_deceleration_g=0.01, abs_engaged=True, stop_go_index=0.0) == "high"


def test_low_g_and_calm_volatility_is_low():
    assert classify_severity(peak_deceleration_g=0.10, abs_engaged=False, stop_go_index=0.5) == "low"


def test_low_g_but_high_volatility_escalates_to_medium():
    assert (
        classify_severity(peak_deceleration_g=0.10, abs_engaged=False, stop_go_index=0.9) == "medium"
    )


def test_mid_band_g_with_calm_volatility_is_medium():
    mid = (LOW_G_CEILING + HIGH_G_FLOOR) / 2
    assert classify_severity(peak_deceleration_g=mid, abs_engaged=False, stop_go_index=0.1) == "medium"


def test_high_g_and_calm_volatility_is_still_high():
    assert classify_severity(peak_deceleration_g=0.60, abs_engaged=False, stop_go_index=0.1) == "high"


def test_severe_volatility_escalates_each_band_by_one_level():
    # By design, severe stop_go_index escalates the base g-force tier by exactly one
    # level, applied consistently across every band -- not a narrow sub-band the way
    # Google's original matrix only escalated its upper g-force range. Low -> medium,
    # medium -> high; high is already the ceiling, so it stays high either way.
    mid = (LOW_G_CEILING + HIGH_G_FLOOR) / 2
    assert (
        classify_severity(peak_deceleration_g=mid, abs_engaged=False, stop_go_index=0.9) == "high"
    )
    assert (
        classify_severity(peak_deceleration_g=0.60, abs_engaged=False, stop_go_index=0.9) == "high"
    )


def test_boundaries_are_gap_free_and_non_overlapping():
    # Every value on a boundary must resolve to exactly one branch -- no undefined
    # region, the exact bug found (and fixed) in Google's proposed matrices this
    # session. Sweep a fine grid across and around both g-force boundaries and both
    # stop_go_index conditions; every call must return a valid label without raising.
    valid = {"low", "medium", "high"}
    g_values = [x / 100 for x in range(100)]  # 0.00 .. 0.99
    for g in g_values:
        for stop_go_index in (0.0, HIGH_VOLATILITY_STOP_GO_INDEX, 1.0):
            result = classify_severity(peak_deceleration_g=g, abs_engaged=False, stop_go_index=stop_go_index)
            assert result in valid, f"g={g}, stop_go_index={stop_go_index} produced invalid label {result!r}"


def test_negative_g_force_is_handled_via_absolute_value():
    # Real deceleration is signed negative; classify_severity takes the magnitude.
    assert classify_severity(peak_deceleration_g=-0.60, abs_engaged=False, stop_go_index=0.1) == "high"
    assert classify_severity(peak_deceleration_g=-0.10, abs_engaged=False, stop_go_index=0.1) == "low"
