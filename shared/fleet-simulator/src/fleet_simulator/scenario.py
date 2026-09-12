"""Per-truck telemetry generation: normal driving vs. the canonical SLOWDOWN.

One state machine, used identically whether there's one truck or a hundred — the
fleet dimension in fleet.py is just "run more of these," not a fork in the logic.
Per docs/CANON.md: sustained ~35mph + a stop/go pattern + a slipping ETA. Braking and
downshift bursts corroborate the stop/go pattern independently of speed oscillation.
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from fleet_telemetry_model import GpsPosition, Signals, TelemetryEvent

NOMINAL_SPEED_MPH = 68.0
NOMINAL_SPEED_JITTER_MPH = 2.0

SLOWDOWN_SPEED_MPH = 35.0
SLOWDOWN_OSCILLATION_AMPLITUDE_MPH = 10.0
SLOWDOWN_ETA_SLIP_PER_TICK_MINUTES = 0.6
MIN_INCIDENT_TICKS = 24
MAX_INCIDENT_TICKS = 48

BRAKE_EVENT_DECEL_THRESHOLD_MPH = 2.0
DOWNSHIFT_EVENT_DECEL_THRESHOLD_MPH = 5.0

PLANNED_TRIP_MINUTES = 45.0
SIMULATED_TICK_SECONDS = 5.0  # physical seconds of driving each event represents

SPEED_WINDOW_SIZE = 6
OSCILLATION_REFERENCE_MPH = 12.0
EVENT_WINDOW_REFERENCE = 6

_CORRIDOR_START_LAT = 33.95
_CORRIDOR_START_LON = -84.40
_LAT_PER_MPH_TICK = 4.5e-6
_SEGMENT_TICKS = 12


@dataclass
class TruckState:
    """Everything needed to generate the next tick of telemetry for one truck."""

    truck_id: str
    corridor: str
    start_time: datetime
    rng: random.Random
    incident_rate: float = 0.03
    force_incident_start_tick: int | None = None

    tick: int = 0
    lat: float = field(default=_CORRIDOR_START_LAT)
    lon: float = field(default=_CORRIDOR_START_LON)
    prior_speed_mph: float = field(default=NOMINAL_SPEED_MPH)
    speed_window: deque[float] = field(default_factory=lambda: deque(maxlen=SPEED_WINDOW_SIZE))
    event_window: deque[int] = field(default_factory=lambda: deque(maxlen=EVENT_WINDOW_REFERENCE))

    in_incident: bool = False
    incident_ticks_remaining: int = 0
    incident_elapsed_ticks: int = 0
    eta_slip_minutes: float = 0.0
    had_incident: bool = False

    def __post_init__(self) -> None:
        self.planned_eta = self.start_time + timedelta(minutes=PLANNED_TRIP_MINUTES)

    def step(self) -> TelemetryEvent:
        timestamp = self.start_time + timedelta(seconds=self.tick * SIMULATED_TICK_SECONDS)
        self._maybe_start_incident()

        if self.in_incident:
            speed = self._incident_speed()
            self.eta_slip_minutes += SLOWDOWN_ETA_SLIP_PER_TICK_MINUTES
        else:
            speed = NOMINAL_SPEED_MPH + self.rng.uniform(
                -NOMINAL_SPEED_JITTER_MPH, NOMINAL_SPEED_JITTER_MPH
            )
        speed = max(0.0, speed)

        decel = self.prior_speed_mph - speed
        brake_events = 1 if decel >= BRAKE_EVENT_DECEL_THRESHOLD_MPH else 0
        downshift_events = 1 if decel >= DOWNSHIFT_EVENT_DECEL_THRESHOLD_MPH else 0
        self.prior_speed_mph = speed

        self.speed_window.append(speed)
        self.event_window.append(brake_events + downshift_events)

        self.lat += speed * _LAT_PER_MPH_TICK
        segment_index = self.tick // _SEGMENT_TICKS
        current_eta = self.planned_eta + timedelta(minutes=self.eta_slip_minutes)

        event = TelemetryEvent(
            timestamp=timestamp,
            truck_id=self.truck_id,
            speed_mph=speed,
            gps=GpsPosition(lat=self.lat, lon=self.lon),
            heading=0.0,
            route_segment=f"{self.corridor}-segment-{segment_index}",
            corridor=self.corridor,
            planned_eta=self.planned_eta,
            current_eta=current_eta,
            signals=self._compute_signals(),
            brake_events=brake_events,
            downshift_events=downshift_events,
            _ground_truth="slowdown_incident" if self.in_incident else "normal",
        )

        self._advance_incident_countdown()
        self.tick += 1
        return event

    def _maybe_start_incident(self) -> None:
        if self.in_incident:
            return
        forced = (
            self.force_incident_start_tick is not None
            and self.tick >= self.force_incident_start_tick
        )
        random_onset = self.rng.random() < self.incident_rate
        if forced or random_onset:
            self.in_incident = True
            self.had_incident = True
            self.incident_elapsed_ticks = 0
            self.incident_ticks_remaining = self.rng.randint(
                MIN_INCIDENT_TICKS, MAX_INCIDENT_TICKS
            )
            self.force_incident_start_tick = None

    def _incident_speed(self) -> float:
        oscillation = SLOWDOWN_OSCILLATION_AMPLITUDE_MPH * math.sin(
            self.incident_elapsed_ticks / 2.0
        )
        return SLOWDOWN_SPEED_MPH + oscillation + self.rng.uniform(-1.5, 1.5)

    def _advance_incident_countdown(self) -> None:
        if not self.in_incident:
            return
        self.incident_elapsed_ticks += 1
        self.incident_ticks_remaining -= 1
        if self.incident_ticks_remaining <= 0:
            self.in_incident = False

    def _compute_signals(self) -> Signals:
        rolling_avg_speed = sum(self.speed_window) / len(self.speed_window)
        oscillation_amplitude = (
            max(self.speed_window) - min(self.speed_window)
            if len(self.speed_window) > 1
            else 0.0
        )
        event_burst = sum(self.event_window)
        stop_go_index = min(
            1.0,
            0.5 * (oscillation_amplitude / OSCILLATION_REFERENCE_MPH)
            + 0.5 * (event_burst / EVENT_WINDOW_REFERENCE),
        )
        return Signals(
            rolling_avg_speed=rolling_avg_speed,
            eta_slip_min=self.eta_slip_minutes,
            stop_go_index=stop_go_index,
        )
