"""Pre-seeded route-planning data: per-segment expected average speed, populated
during route planning (before a truck departs a segment), not fabricated at
inference time.

A real Tier-3 eval investigation (2026-09-26, chasing why the Flow B "low"
severity tier stayed miscalibrated even after fixing the traffic_pattern
confound in coprocessor.py) found that handing the LLM two raw numbers — actual
speed and a bare planned-speed baseline — and letting it compute the deviation
itself didn't work: neither of two real models used the numbers that way.
Precomputing the deviation as cheap math and handing the model the already-computed
fact instead did work for one of them (LFM2.5-350M: ~0% -> 60% correct "low" calls,
no regression on the other). See coprocessor.velocity_context's docstring for the
full account. This module is the real (if currently static/illustrative) data
source that computation needs.

No live route-planning system exists yet — this is a lookup by
TelemetryEvent.route_segment standing in for where that data would come from once
one does. Segments with no entry get no baseline at all, same honesty discipline
as everywhere else in this repo (coprocessor.py never fabricates a value for a
field it has no real source for) — see get_route_segment_plan.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RouteSegmentPlan:
    route_segment: str
    planned_avg_speed_mph: float


# Illustrative pre-seeded data — keys must match TelemetryEvent.route_segment exactly.
# "I-95N-segment-3" is the segment tests/model/test_flow_b_triage.py's severity-tier
# fixture already uses, so those evals exercise a real (not "unknown") baseline.
ROUTE_SEGMENT_PLANS: dict[str, RouteSegmentPlan] = {
    "I-95N-segment-3": RouteSegmentPlan(route_segment="I-95N-segment-3", planned_avg_speed_mph=45.0),
}


def get_route_segment_plan(route_segment: str) -> RouteSegmentPlan | None:
    """None for any segment with no pre-seeded plan — never a fabricated guess."""
    return ROUTE_SEGMENT_PLANS.get(route_segment)
