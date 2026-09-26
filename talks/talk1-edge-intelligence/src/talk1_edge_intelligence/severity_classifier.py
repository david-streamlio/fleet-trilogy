"""Deterministic severity classification — cheap math, not the LLM.

This is the architectural pivot documented in
docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md: across ten-plus rounds of real-model
testing, every model asked to derive a low/medium/high severity rating from
graduated numeric signals (speed deviation, braking magnitude, rule-engine wording)
produced mismatch rates from 33% to 73%, with degenerate constant-output collapses
the norm rather than the exception. A deterministic function does the identical
classification perfectly, instantly, for free, every time. Per docs/CANON.md's
"cheap math does detection, not the LLM" principle, severity belongs here, the same
category as eta_impact/truck_id already being hardcoded in
triage_function.build_grammar rather than left to the model to regenerate.

The LLM's role moves to what deterministic code genuinely can't do: synthesizing
genuinely unstructured operational context (weather, cargo type, dispatch status —
see trip_context.py) into a bounded escalate/confirm/de-escalate adjustment on top
of this baseline, not deriving severity from scratch. See triage_function.py.

Threshold provenance: peak_deceleration_g bands are adapted from industry-cited
Class 8 / heavy-duty truck harsh-braking ranges (-0.20g to -0.47g, with ~0.265g
cited as a common vendor default and ~0.47g as a "strict" one — Geotab/FleetRabbit,
via Google AI research, 2026-09-26). These are named, structured ranges, which is
more trustworthy than an unsourced single number, but they were not independently
verified against the primary vendor documentation — treat them as a reasonable,
grounded starting point, not verified ground truth. stop_go_index is used as the
"volatility/energy" modifier in place of a delta-v (pre/post event speed drop)
signal, which our schema doesn't carry (TelemetryEvent is a single snapshot, not a
pre/post-event time-series pair) — this is an honest substitution of a real signal
we do have for one we don't, not a claim they're equivalent. The 0.8 volatility
threshold reuses coprocessor.traffic_pattern_from_stop_go_index's existing "severe"
boundary for consistency rather than inventing a new one.
"""

from __future__ import annotations

# Class 8 / heavy-duty truck peak-deceleration bands (see module docstring for
# sourcing and caveats). Three bands, gap-free and non-overlapping, mirroring the
# lesson already learned twice this session (coprocessor.traffic_pattern_from_
# stop_go_index, and the brake-intensity diagnostic's v1-vs-v2 fix): a threshold
# scheme needs genuinely separated bands, not two tiers sharing one boundary.
LOW_G_CEILING = 0.22
HIGH_G_FLOOR = 0.45

# Reuses traffic_pattern_from_stop_go_index's existing "severe" boundary (see
# coprocessor.py) rather than inventing a new volatility threshold.
HIGH_VOLATILITY_STOP_GO_INDEX = 0.8


def classify_severity(peak_deceleration_g: float, abs_engaged: bool, stop_go_index: float) -> str:
    """Deterministic low/medium/high classification. Gap-free by construction: every
    (g, abs, stop_go_index) combination hits exactly one branch, no undefined region.

    ABS engagement is an unconditional override to "high" — a real, objective signal
    (tires losing traction) that always warrants the highest tier regardless of the
    other two inputs, not a signal a model needs to weigh against competing evidence.
    """
    g = abs(peak_deceleration_g)

    if abs_engaged:
        return "high"

    if g > HIGH_G_FLOOR:
        return "high"

    if g <= LOW_G_CEILING:
        return "medium" if stop_go_index > HIGH_VOLATILITY_STOP_GO_INDEX else "low"

    # LOW_G_CEILING < g <= HIGH_G_FLOOR
    return "high" if stop_go_index > HIGH_VOLATILITY_STOP_GO_INDEX else "medium"
