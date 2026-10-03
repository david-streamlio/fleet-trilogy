"""Tier 2 (cloud/hive) global synthesis: the pure decision core.

Per docs/CANON.md, Tier 2 aggregates enrichment cards across trucks and decides
whether an incident is one truck's local problem or a corridor-wide incident,
decides on a reroute, and generates the spoken proactive warning. Exactly like
Tier 1 (see talk1_edge_intelligence.processor.process_event), the *decision* here
is cheap code/math over already-structured data — grouping by corridor, counting
distinct trucks, thresholding severity. The LLM's only job is turning the
already-decided facts into the spoken_warning text (see prompting.py); it never
decides scope or reroute itself.

synthesize() has no Pulsar dependency and no I/O of its own — a plain function of
(cards, backend), just like talk1's process_event. See report.py for the runtime
shell that pulls cards off a simulated/real fleet.
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict

from fleet_telemetry_model import EnrichmentCard, IncidentSynthesis
from llm_inference.client import LlmBackend

from talk3_pulsar_speaks_english.prompting import generate_spoken_warning

SCOPE_SINGLE_TRUCK = "single_truck"
SCOPE_CORRIDOR_WIDE = "corridor_wide"

HIGH_SEVERITY = "high"


def group_by_corridor(cards: list[EnrichmentCard]) -> dict[str, list[EnrichmentCard]]:
    """Split a mixed batch of enrichment cards (any corridor, any truck) into one
    list per corridor — the unit synthesize() operates on.
    """
    groups: dict[str, list[EnrichmentCard]] = defaultdict(list)
    for card in cards:
        groups[card.corridor].append(card)
    return dict(groups)


def decide_scope(cards: list[EnrichmentCard]) -> str:
    """single_truck when every card in this corridor's batch came from the same
    truck; corridor_wide when two or more distinct trucks are reporting into the
    same corridor at once. Plain set-counting — no LLM involved, per CANON.md.
    """
    truck_ids = {card.truck_id for card in cards}
    return SCOPE_SINGLE_TRUCK if len(truck_ids) <= 1 else SCOPE_CORRIDOR_WIDE


def decide_reroute(cards: list[EnrichmentCard], scope: str) -> tuple[bool, str | None]:
    """Simple, explainable reroute logic, kept as plain code per CANON.md's
    "detection/decision is cheap math, LLM only interprets/generates language"
    rule: a reroute is recommended only when the incident is corridor-wide AND at
    least one reporting truck flagged high severity. A single truck's local
    problem, or a corridor-wide but low/medium-severity pattern, does not trigger
    a reroute recommendation.
    """
    if scope != SCOPE_CORRIDOR_WIDE:
        return False, None
    if not any(card.severity.lower() == HIGH_SEVERITY for card in cards):
        return False, None
    corridor = cards[0].corridor
    truck_count = len({card.truck_id for card in cards})
    high_count = len(
        {card.truck_id for card in cards if card.severity.lower() == HIGH_SEVERITY}
    )
    # Only claim "high-severity" for every truck when it's true -- the LLM narrates
    # this text verbatim-ish, so an overstated fact here becomes an overstated
    # spoken warning (seen in a Talk 3 demo run: 3 trucks, 2 high, 1 medium).
    if high_count == truck_count:
        detail = (
            f"Reroute traffic around {corridor} — {truck_count} trucks reporting a "
            "correlated high-severity slowdown."
        )
    else:
        detail = (
            f"Reroute traffic around {corridor} — {truck_count} trucks reporting a "
            f"correlated slowdown, {high_count} at high severity."
        )
    return True, detail


def synthesize(
    cards: list[EnrichmentCard],
    backend: LlmBackend,
    *,
    incident_id: str | None = None,
) -> IncidentSynthesis | None:
    """Aggregate one corridor's worth of enrichment cards into an IncidentSynthesis.

    Returns None for an empty card list — there is nothing to synthesize. Cards
    for more than one corridor may be passed in; only the cards matching the
    first card's corridor are synthesized (callers with a multi-corridor batch
    should call this once per group from group_by_corridor() instead).

    Decision (scope, reroute) is cheap code, computed before the backend is ever
    invoked; the backend is only asked to phrase the spoken_warning, per
    docs/CANON.md's "LLM interprets/narrates, never decides" rule.
    """
    if not cards:
        return None

    corridor = cards[0].corridor
    corridor_cards = [card for card in cards if card.corridor == corridor]

    scope = decide_scope(corridor_cards)
    reroute_recommended, reroute_detail = decide_reroute(corridor_cards, scope)
    spoken_warning = generate_spoken_warning(
        backend,
        corridor=corridor,
        cards=corridor_cards,
        scope=scope,
        reroute_recommended=reroute_recommended,
        reroute_detail=reroute_detail,
    )

    return IncidentSynthesis(
        incident_id=incident_id or str(uuid.uuid4()),
        corridor=corridor,
        affected_truck_ids=sorted({card.truck_id for card in corridor_cards}),
        scope=scope,
        reroute_recommended=reroute_recommended,
        reroute_detail=reroute_detail,
        spoken_warning=spoken_warning,
        synthesized_at=time.time(),
    )
