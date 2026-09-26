"""Pre-seeded operational context: weather, cargo type, dispatch status.

These are deliberately NOT part of TelemetryEvent (shared/fleet-telemetry-model's
schema) — they come from different systems entirely (a weather API, a cargo
manifest, the dispatch system), not the truck's own sensors, so they don't belong
on the raw telemetry wire schema. This module is where the coprocessor looks them
up when building a triage payload, the same pattern as route_plans.py's per-segment
planned-speed lookup: a real (if currently static/illustrative) data source, keyed
by truck_id, with an honest "no data -> no context" fallback rather than a
fabricated default.

This is also the ONLY genuinely LLM-appropriate input in the whole triage payload.
Per severity_classifier.py's docstring: everything numeric/categorical (g-force,
ABS, speed deviation, volatility) is cheap math now, because models handle
graduated numeric-threshold classification unreliably. Weather descriptions, cargo
type, and free-text dispatch status are the opposite case — genuinely unstructured
text that a fixed lookup table can't cleanly reduce to a threshold (e.g. "heavy
rain + liquid tanker cargo implies sloshing risk" is domain synthesis, not a
comparison), which is exactly the kind of job an LLM is suited for. See
triage_function.py's escalate/confirm/de-escalate design.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TripContext:
    truck_id: str
    weather_condition: str
    cargo_type: str
    dispatch_status: str


# Illustrative pre-seeded data. truck-47 matches the fixture id used throughout
# tests/model/test_flow_b_triage.py, so those evals exercise real (not "unknown")
# operational context.
TRIP_CONTEXTS: dict[str, TripContext] = {
    "truck-47": TripContext(
        truck_id="truck-47",
        weather_condition="Heavy rain, wet asphalt",
        cargo_type="Liquids / Chemical Tanker",
        dispatch_status="Running 20 minutes behind schedule",
    ),
}


def get_trip_context(truck_id: str) -> TripContext | None:
    """None for any truck with no pre-seeded context -- never a fabricated guess."""
    return TRIP_CONTEXTS.get(truck_id)
