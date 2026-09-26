"""The I/O shell around `efficiency.py`: run a fleet simulation, feed the
resulting flagged-event count into `compare_approaches`, and print a report.

Per talk1's convention, all the pure logic (counting flagged events, scoring
approaches) lives in efficiency.py with no I/O of its own; this module is the
only place that touches `FleetSimulator` and stdout.
"""

from __future__ import annotations

import argparse

from fleet_simulator import FleetSimulator

from talk2_greenest_token.efficiency import (
    DEFAULT_APPROACHES,
    ApproachResult,
    compare_approaches,
    count_flagged_events,
    savings_factor,
)

DEFAULT_FLEET_SIZE = 200
DEFAULT_TICKS = 200
DEFAULT_SEED = 7


def run_fleet_efficiency_report(
    *,
    fleet_size: int = DEFAULT_FLEET_SIZE,
    ticks: int = DEFAULT_TICKS,
    seed: int | None = DEFAULT_SEED,
    incident_rate: float = 0.03,
) -> dict[str, ApproachResult]:
    """Run `fleet_size` trucks for `ticks` ticks and score both approaches
    against the number of flagged events that fleet run produced.

    Returns the same dict `compare_approaches` returns, so callers (tests,
    the CLI below) can inspect it directly.
    """
    simulator = FleetSimulator(fleet_size=fleet_size, seed=seed, incident_rate=incident_rate)
    flagged_event_count = 0
    for _ in range(ticks):
        flagged_event_count += count_flagged_events(simulator.tick())
    return compare_approaches(flagged_event_count, DEFAULT_APPROACHES)


def format_report(results: dict[str, ApproachResult], *, fleet_size: int, ticks: int) -> str:
    lines = [
        f"Fleet: {fleet_size} trucks x {ticks} ticks",
        f"Flagged (LLM-eligible) events: {next(iter(results.values())).calls}",
        "",
    ]
    for result in results.values():
        lines.append(f"[{result.approach}] {result.description}")
        lines.append(f"  calls:          {result.calls}")
        lines.append(f"  total latency:  {result.total_latency_s:.1f} s")
        lines.append(f"  total energy:   {result.total_energy_wh:.4f} Wh")
        lines.append(f"  total cost:     ${result.total_cost_usd:.4f}")
        lines.append("")

    small = results.get("small-model-cpu")
    full = results.get("full-precision-gpu")
    if small is not None and full is not None:
        factors = savings_factor(baseline=full, contender=small)
        energy_factor = factors["energy_factor"]
        energy_direction, energy_magnitude = (
            ("less", energy_factor) if energy_factor >= 1 else ("more", 1 / energy_factor)
        )
        latency_factor = factors["latency_factor"]
        latency_direction, latency_magnitude = (
            ("faster", latency_factor) if latency_factor >= 1 else ("slower", 1 / latency_factor)
        )
        lines.append("small-model-cpu vs. full-precision-gpu:")
        lines.append(f"  energy:  {energy_magnitude:.1f}x {energy_direction} energy per call")
        lines.append(f"  cost:    {factors['cost_factor']:.1f}x cheaper")
        lines.append(f"  latency: {latency_magnitude:.1f}x {latency_direction} per call")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="The Greenest Token: efficiency report for Tier 1 LLM calls at fleet scale."
    )
    parser.add_argument("--fleet-size", type=int, default=DEFAULT_FLEET_SIZE)
    parser.add_argument("--ticks", type=int, default=DEFAULT_TICKS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--incident-rate", type=float, default=0.03)
    args = parser.parse_args(argv)

    results = run_fleet_efficiency_report(
        fleet_size=args.fleet_size,
        ticks=args.ticks,
        seed=args.seed,
        incident_rate=args.incident_rate,
    )
    print(format_report(results, fleet_size=args.fleet_size, ticks=args.ticks))


if __name__ == "__main__":
    main()
