"""Fleet orchestration: one code path for a single truck or a hundred.

--fleet-size 1 (the default) is single Truck 47 mode: one truck, its own
--incident-rate chance of an isolated slowdown. --fleet-size N > 1 runs N trucks
through the exact same TruckState.step() logic; --incident-corridor plus
--incident-trucks just pins M of those trucks to one corridor and forces their
incidents to start within the same few ticks, so Talk 3 has a correlated,
overlapping-window incident to aggregate instead of isolated noise.
"""

from __future__ import annotations

import random
from datetime import datetime

from fleet_telemetry_model import TelemetryEvent

from fleet_simulator.scenario import TruckState

TRUCK_47_ID = "truck-47"
DEFAULT_CORRIDOR = "I-95N"
BACKGROUND_CORRIDORS = ["I-95N", "I-75S", "I-20E", "I-85N"]
FORCED_INCIDENT_START_JITTER_TICKS = 3


def _truck_ids(fleet_size: int) -> list[str]:
    if fleet_size == 1:
        return [TRUCK_47_ID]
    return [f"truck-{i:02d}" for i in range(1, fleet_size + 1)]


class FleetSimulator:
    """Generates one TelemetryEvent per truck per tick, across the whole fleet."""

    def __init__(
        self,
        *,
        fleet_size: int = 1,
        seed: int | None = None,
        incident_rate: float = 0.03,
        incident_corridor: str | None = None,
        incident_trucks: int = 0,
        start_time: datetime | None = None,
    ) -> None:
        if incident_corridor and incident_trucks > fleet_size:
            raise ValueError("--incident-trucks cannot exceed --fleet-size")

        self._rng = random.Random(seed)
        start_time = start_time or datetime.now().astimezone()
        truck_ids = _truck_ids(fleet_size)
        forced_ids = set(truck_ids[:incident_trucks]) if incident_corridor else set()

        self._trucks: list[TruckState] = []
        for index, truck_id in enumerate(truck_ids):
            is_forced = truck_id in forced_ids
            corridor = (
                incident_corridor
                if is_forced
                else BACKGROUND_CORRIDORS[index % len(BACKGROUND_CORRIDORS)]
            )
            self._trucks.append(
                TruckState(
                    truck_id=truck_id,
                    corridor=corridor,
                    start_time=start_time,
                    rng=random.Random(self._rng.random()),
                    incident_rate=incident_rate,
                    force_incident_start_tick=(
                        self._rng.randint(0, FORCED_INCIDENT_START_JITTER_TICKS)
                        if is_forced
                        else None
                    ),
                )
            )

    @property
    def truck_ids(self) -> list[str]:
        return [truck.truck_id for truck in self._trucks]

    def tick(self) -> list[TelemetryEvent]:
        """Advance every truck by one tick and return their events."""
        return [truck.step() for truck in self._trucks]

    def trucks_with_incidents(self) -> list[str]:
        """Truck ids that have entered a slowdown incident at least once this run."""
        return [truck.truck_id for truck in self._trucks if truck.had_incident]
