"""The I/O shell around synthesizer.py: run a fleet simulation, turn every
flagged event into an EnrichmentCard (Tier 1's job, duplicated here in miniature
— see _card_for_event below), group cards by corridor, and synthesize an
IncidentSynthesis per corridor that produced any.

Per talk1/talk2's convention, all the pure decision logic (scope, reroute,
grouping) lives in synthesizer.py with no I/O of its own; this module is the
only place in this package that touches FleetSimulator or stdout.
"""

from __future__ import annotations

import argparse
from collections import defaultdict

from fleet_simulator import FleetSimulator
from fleet_telemetry_model import EnrichmentCard, IncidentSynthesis, is_probable_slowdown
from fleet_telemetry_model.detection import evaluate_signals
from llm_inference import LlmBackend, SubprocessLlmBackend, generate_enrichment_card_dict

from talk3_pulsar_speaks_english.synthesizer import synthesize

DEFAULT_FLEET_SIZE = 12
DEFAULT_TICKS = 60
DEFAULT_SEED = 7
DEFAULT_INCIDENT_CORRIDOR = "I-95N"
DEFAULT_INCIDENT_TRUCKS = 3


def _card_for_event(event, backend: LlmBackend) -> EnrichmentCard | None:
    """Tier 1's process_event logic (talk1_edge_intelligence.processor), duplicated
    here rather than imported: per docs/CANON.md, talk packages never depend on
    each other. This is the one place that rule creates minor duplication with
    talk1 — correct here, since talk1 and talk3 are separate demo packages, not
    shared logic (the schemas/detection/prompting themselves all still live in
    shared/ and are imported, not copied).

    The mock backend returns a fixed canned completion regardless of the prompt,
    so truck_id/corridor are overridden from the real event afterward — a real
    model is instructed, via its own prompt, to copy those fields through exactly.
    """
    if not is_probable_slowdown(event):
        return None
    triggered_signals = evaluate_signals(event)
    card_dict = generate_enrichment_card_dict(backend, event, triggered_signals)
    card_dict["truck_id"] = event.truck_id
    card_dict["corridor"] = event.corridor
    return EnrichmentCard(**card_dict)


def run_fleet_synthesis_report(
    *,
    fleet_size: int = DEFAULT_FLEET_SIZE,
    ticks: int = DEFAULT_TICKS,
    seed: int | None = DEFAULT_SEED,
    incident_corridor: str = DEFAULT_INCIDENT_CORRIDOR,
    incident_trucks: int = DEFAULT_INCIDENT_TRUCKS,
    backend: LlmBackend | None = None,
) -> list[IncidentSynthesis]:
    """Run `fleet_size` trucks for `ticks` ticks, forcing `incident_trucks` of
    them into a correlated incident on `incident_corridor`, and return one
    IncidentSynthesis per corridor that produced at least one enrichment card.
    """
    backend = backend or SubprocessLlmBackend(mock=True)
    simulator = FleetSimulator(
        fleet_size=fleet_size,
        seed=seed,
        incident_corridor=incident_corridor,
        incident_trucks=incident_trucks,
    )

    cards_by_corridor: dict[str, list[EnrichmentCard]] = defaultdict(list)
    for _ in range(ticks):
        for event in simulator.tick():
            card = _card_for_event(event, backend)
            if card is not None:
                cards_by_corridor[card.corridor].append(card)

    syntheses = []
    for cards in cards_by_corridor.values():
        synthesis = synthesize(cards, backend)
        if synthesis is not None:
            syntheses.append(synthesis)
    return syntheses


def format_report(syntheses: list[IncidentSynthesis]) -> str:
    if not syntheses:
        return "No incidents synthesized this run."
    lines = []
    for synthesis in syntheses:
        lines.append(f"[{synthesis.corridor}] scope={synthesis.scope} incident_id={synthesis.incident_id}")
        lines.append(f"  affected trucks: {', '.join(synthesis.affected_truck_ids)}")
        lines.append(f"  reroute: {synthesis.reroute_recommended} ({synthesis.reroute_detail or 'n/a'})")
        lines.append(f"  spoken warning: {synthesis.spoken_warning}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Pulsar Speaks English: Tier 2 global synthesis demo report."
    )
    parser.add_argument("--fleet-size", type=int, default=DEFAULT_FLEET_SIZE)
    parser.add_argument("--ticks", type=int, default=DEFAULT_TICKS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--incident-corridor", default=DEFAULT_INCIDENT_CORRIDOR)
    parser.add_argument("--incident-trucks", type=int, default=DEFAULT_INCIDENT_TRUCKS)
    args = parser.parse_args(argv)

    syntheses = run_fleet_synthesis_report(
        fleet_size=args.fleet_size,
        ticks=args.ticks,
        seed=args.seed,
        incident_corridor=args.incident_corridor,
        incident_trucks=args.incident_trucks,
    )
    print(format_report(syntheses))


if __name__ == "__main__":
    main()
