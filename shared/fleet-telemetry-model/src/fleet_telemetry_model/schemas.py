"""The one telemetry schema, one enrichment-card schema, and one incident schema.

This is the contract for the whole trilogy: every talk reads/writes these shapes over
Pulsar. See docs/CANON.md at the repo root for the facts these models encode.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GpsPosition(BaseModel):
    lat: float
    lon: float


class Signals(BaseModel):
    """Cheap-math signals computed by the simulator (or, later, Tier 1) — no LLM involved."""

    rolling_avg_speed: float
    eta_slip_min: float
    stop_go_index: float = Field(ge=0.0, le=1.0)


class TelemetryEvent(BaseModel):
    """A single raw sample published to the truck-telemetry Pulsar topic.

    `ground_truth` is only ever present in simulator output (wire key `_ground_truth`,
    a leading underscore so it's obvious this is simulation-only) — strip it with
    `fleet_telemetry_model.serialization.strip_ground_truth` before handing a payload
    to anything that's supposed to be doing real inference, not grading itself.
    """

    model_config = ConfigDict(populate_by_name=True)

    timestamp: datetime
    truck_id: str
    speed_mph: float
    gps: GpsPosition
    heading: float
    route_segment: str
    corridor: str
    planned_eta: datetime
    current_eta: datetime
    signals: Signals
    brake_events: int = 0
    downshift_events: int = 0
    ground_truth: Literal["normal", "slowdown_incident"] = Field(alias="_ground_truth")


class EnrichmentCard(BaseModel):
    """Tier 1 (edge) output / Tier 2 (cloud) input.

    `signals` names which cheap-math signals crossed their threshold (e.g.
    ["sustained_low_speed", "stop_go_index", "eta_slip"]) — the evidence, not a
    narrative. The LLM's interpretation text is a separate concern (see
    llm-inference's structured-output helper), kept out of this wire schema for now.
    """

    event: str
    severity: str
    signals: list[str]
    eta_impact: float
    corridor: str
    truck_id: str


class IncidentSynthesis(BaseModel):
    """Tier 2 (cloud/hive) output: global synthesis + spoken proactive warning."""

    incident_id: str
    corridor: str
    affected_truck_ids: list[str]
    scope: str  # "single_truck" | "corridor_wide"
    reroute_recommended: bool
    reroute_detail: str | None
    spoken_warning: str
    synthesized_at: float
