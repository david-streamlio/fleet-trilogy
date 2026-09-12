"""Tier 2 (cloud/hive) prompt template, described in docs/CANON.md.

Tier 2 never sees raw telemetry — only structured EnrichmentCards. It synthesizes
across trucks and writes the spoken proactive warning; that's free text, which is why
this stays separate from the structured Tier 1 helper in llm_inference.structured.
"""

from __future__ import annotations

from fleet_telemetry_model import EnrichmentCard

TIER2_SYNTHESIS_PROMPT = """You are synthesizing fleet-wide telemetry for a delivery \
network. You have received enrichment cards describing possible incidents from one or \
more trucks. Decide whether this is a single truck's local issue or a corridor-wide \
incident, then write a short, calm, spoken-style proactive warning (2-3 sentences) \
suitable for text-to-speech, aimed at other drivers approaching the same corridor.

Corridor: {corridor}
Number of trucks reporting: {truck_count}
Enrichment cards:
{cards}

Respond with the spoken warning only."""


def render_tier2_prompt(corridor: str, cards: list[EnrichmentCard]) -> str:
    """Build the Tier 2 (cloud/hive) global synthesis prompt from enrichment cards."""
    card_lines = "\n".join(
        f"- ({card.truck_id}) {card.event}, severity={card.severity}, "
        f"signals={card.signals}, eta_impact={card.eta_impact:.1f}min"
        for card in cards
    )
    return TIER2_SYNTHESIS_PROMPT.format(
        corridor=corridor,
        truck_count=len({card.truck_id for card in cards}),
        cards=card_lines,
    )
