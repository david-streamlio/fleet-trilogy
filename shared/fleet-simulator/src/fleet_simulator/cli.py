"""The one fleet-simulator CLI. Same code path for single-truck and fleet-scale runs."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import threading
import time
from dataclasses import asdict, dataclass

from fleet_telemetry_model import to_json

from fleet_simulator.fleet import FleetSimulator
from fleet_simulator.publisher import PulsarPublisher
from fleet_simulator.scenario import SIMULATED_TICK_SECONDS

logger = logging.getLogger("fleet_simulator")

DEFAULT_SERVICE_URL = "pulsar://localhost:6650"
DEFAULT_TOPIC = "persistent://public/default/truck-telemetry"
DEFAULT_INCIDENT_RATE = 0.03
STOP_POLL_SECONDS = 0.2


@dataclass
class RunSummary:
    events: int
    achieved_rate_eps: float
    elapsed_seconds: float
    pct_slowdown: float
    trucks_in_incident: int

    def to_dict(self) -> dict:
        return asdict(self)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fleet-simulate",
        description=(
            "The one fleet telemetry simulator. Publishes TelemetryEvent JSON to "
            "Pulsar. Runs on a laptop, not the Pi."
        ),
    )
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    parser.add_argument("--topic", default=DEFAULT_TOPIC)
    parser.add_argument("--token", default=None, help="Pulsar auth token, if required")

    parser.add_argument("--fleet-size", type=int, default=1)
    parser.add_argument(
        "--incident-rate",
        type=float,
        default=DEFAULT_INCIDENT_RATE,
        help="per-tick probability a truck not already in an incident starts one",
    )
    parser.add_argument("--incident-corridor", default=None)
    parser.add_argument(
        "--incident-trucks",
        type=int,
        default=0,
        help="number of trucks to pin to --incident-corridor with a correlated, "
        "overlapping-window incident",
    )
    parser.add_argument(
        "--warmup-ticks",
        type=int,
        default=0,
        help="ticks of normal baseline telemetry to emit before a forced "
        "(--incident-corridor) incident begins",
    )

    parser.add_argument(
        "--rate", type=float, default=None, help="target events/sec across the whole fleet"
    )
    parser.add_argument("--duration", type=float, default=None, help="stop after N seconds")
    parser.add_argument("--total", type=int, default=None, help="stop after exactly N events")

    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print sample events to stdout without connecting to Pulsar",
    )
    return parser


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _register_stop_handler(stop_event: threading.Event) -> None:
    def _handle(signum, frame):
        logger.info("received signal %s, stopping", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)


def _sleep_interruptibly(seconds: float, stop_event: threading.Event) -> None:
    deadline = time.monotonic() + seconds
    while not stop_event.is_set():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        stop_event.wait(min(remaining, STOP_POLL_SECONDS))


def run_dry_run(fleet: FleetSimulator, count: int) -> None:
    for _ in range(count):
        for event in fleet.tick():
            print(to_json(event))


def run_publish_loop(
    fleet: FleetSimulator,
    publisher: PulsarPublisher,
    *,
    rate: float | None,
    duration: float | None,
    total: int | None,
    stop_event: threading.Event,
) -> RunSummary:
    tick_interval_wallclock = (
        len(fleet.truck_ids) / rate if rate else SIMULATED_TICK_SECONDS
    )
    start = time.monotonic()
    published = 0
    slowdown_count = 0

    while not stop_event.is_set():
        if total is not None and published >= total:
            break
        if duration is not None and (time.monotonic() - start) >= duration:
            break

        tick_start = time.monotonic()
        for event in fleet.tick():
            if total is not None and published >= total:
                break
            publisher.publish(to_json(event).encode("utf-8"))
            published += 1
            if event.ground_truth == "slowdown_incident":
                slowdown_count += 1

        elapsed_tick = time.monotonic() - tick_start
        sleep_for = tick_interval_wallclock - elapsed_tick
        if sleep_for > 0:
            _sleep_interruptibly(sleep_for, stop_event)

    elapsed = time.monotonic() - start
    return RunSummary(
        events=published,
        achieved_rate_eps=(published / elapsed) if elapsed > 0 else 0.0,
        elapsed_seconds=elapsed,
        pct_slowdown=(slowdown_count / published * 100.0) if published else 0.0,
        trucks_in_incident=len(fleet.trucks_with_incidents()),
    )


def main(argv: list[str] | None = None) -> int:
    _setup_logging()
    args = build_parser().parse_args(argv)

    fleet = FleetSimulator(
        fleet_size=args.fleet_size,
        seed=args.seed,
        incident_rate=args.incident_rate,
        incident_corridor=args.incident_corridor,
        incident_trucks=args.incident_trucks,
        warmup_ticks=args.warmup_ticks,
    )

    if args.dry_run:
        run_dry_run(fleet, count=min(args.total or 5, 5))
        return 0

    stop_event = threading.Event()
    _register_stop_handler(stop_event)

    publisher = PulsarPublisher(service_url=args.service_url, topic=args.topic, token=args.token)
    try:
        summary = run_publish_loop(
            fleet,
            publisher,
            rate=args.rate,
            duration=args.duration,
            total=args.total,
            stop_event=stop_event,
        )
    finally:
        publisher.flush()
        publisher.close()

    print(json.dumps(summary.to_dict()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
