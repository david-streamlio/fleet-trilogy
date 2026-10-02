"""A held-out pool of synthetic escalation precedents for the RAG experiment
(a one-off scratch script outside the repo, never committed) — NOT used by the shipped
harness or `ESCALATION_SCENARIOS` in eval_lib.py.

Real diagnostic grounding (2026-09-27, Gemma-3-1B-it, n=30/scenario,
eval-results/compare-edge-triage-COMP-J2D9D71YNJ-20260926T195623Z.json): the model's
failure isn't a simple directional bias. On "benign" (expected hold) it tallies
lower=19/raise=8/hold=3 — over-reacts toward de-escalating a case with nothing
notable either way. On "de-escalate-worthy" (expected lower_or_hold, a case with
an explicit positive safety signal) it tallies raise=19/lower=7/hold=4 — over-
reacts the OTHER direction on a case that should calm down. That inconsistency
(not a stable lean) is consistent with a genuine rule-application failure on a
moderately complex written conditional, not a knowledge gap — which is exactly
the situation worked examples (what retrieval provides) are documented to help
with more reliably than restating the rule more forcefully did (row 3 in
docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md already tried the latter and it
overcorrected).

Ground truth here is mechanically derived from the exact same rules already
written into DEFAULT_PROMPT_TEMPLATE (triage_function.py) — a risk trigger
(hazardous/liquid cargo, poor-visibility weather, or behind-schedule-under-
pressure dispatch) means "raise"; no risk trigger plus an explicit positive
safety signal (a documented defensive maneuver or completed safety check) means
"lower"; anything else (no risk trigger, no positive signal) means "hold". This
is the same epistemic status as ESCALATION_SCENARIOS itself: this eval's own
documented hypothesis about reasonable behavior, not an independently-verified
fact.

Deliberately does not reproduce any of ESCALATION_SCENARIOS' three literal
field combinations — retrieval must find a *similar*, not identical, precedent,
or this would just be answer-lookup, not a real test of whether retrieved
examples help.
"""

from __future__ import annotations

from dataclasses import dataclass

_WEATHER: tuple[tuple[str, bool], ...] = (
    ("Overcast, dry roads", False),
    ("Sunny, dry pavement, good visibility", False),
    ("Light drizzle, roads still mostly dry", False),
    ("Steady rain, wet roads", True),
    ("Freezing rain, icy patches forming", True),
    ("Dense fog, visibility under 200 feet", True),
    ("Blowing snow, reduced visibility", True),
)

_CARGO: tuple[tuple[str, bool], ...] = (
    ("Dry goods / palletized retail freight", False),
    ("Refrigerated produce, non-hazardous", False),
    ("Empty trailer, deadheading to next pickup", False),
    ("Construction materials, non-hazardous", False),
    ("Liquid propane, pressurized tanker", True),
    ("Bulk diesel fuel, tanker", True),
    ("Industrial solvents, flammable", True),
    ("Compressed medical oxygen tanks", True),
)

_DISPATCH: tuple[tuple[str, bool, bool], ...] = (
    ("On schedule, no incidents reported", False, False),
    ("Slightly ahead of schedule", False, False),
    ("Running 15 minutes behind schedule", True, False),
    ("Running 40 minutes behind schedule, dispatcher requesting update", True, False),
    ("Behind schedule after a mandated rest stop", True, False),
    (
        "On schedule; driver completed a documented pre-trip brake and tire safety check",
        False,
        True,
    ),
    (
        "Ahead of schedule; driver executed a documented evasive maneuver to avoid road debris",
        False,
        True,
    ),
)


@dataclass(frozen=True)
class EscalationPrecedent:
    weather_condition: str
    cargo_type: str
    dispatch_status: str
    expected_direction: str  # "raise" | "hold" | "lower"

    def as_query_text(self) -> str:
        return f"Weather: {self.weather_condition}. Cargo: {self.cargo_type}. Dispatch: {self.dispatch_status}."


def _direction(weather_risk: bool, cargo_risk: bool, dispatch_risk: bool, dispatch_positive: bool) -> str:
    if weather_risk or cargo_risk or dispatch_risk:
        return "raise"
    if dispatch_positive:
        return "lower"
    return "hold"


def _build_precedents() -> tuple[EscalationPrecedent, ...]:
    # Hand-picked combinations (not a full cross product) spanning every
    # direction with real variety in wording -- not a mechanical sweep of all
    # 7x8x7 = 392 combinations, which would mostly be redundant for a ~2-item
    # retrieval experiment.
    picks: list[tuple[int, int, int]] = [
        (0, 0, 0), (1, 1, 1), (2, 2, 0),  # hold: no risk, no positive signal
        (3, 0, 0), (0, 4, 0), (0, 0, 2),  # raise: single risk trigger each of the 3 kinds
        (4, 5, 3), (5, 6, 4), (6, 7, 2),  # raise: multiple risk triggers stacked
        (1, 3, 0), (2, 0, 1), (0, 1, 0),  # hold: varied benign combos
        (0, 0, 5), (1, 1, 6),  # lower: positive signal, no risk trigger
        (3, 4, 5), (6, 5, 4),  # raise: bad weather + hazardous cargo together
        (0, 2, 3), (2, 3, 4),  # raise: dispatch-only risk trigger, benign otherwise
        (4, 0, 6), (5, 2, 5),  # lower: positive signal despite one field being merely neutral
        (2, 4, 0), (1, 5, 1),  # raise: hazardous cargo alone
        (0, 3, 0), (1, 0, 2),  # raise: single risk trigger, varied field
    ]
    precedents = []
    for w_idx, c_idx, d_idx in picks:
        weather, w_risk = _WEATHER[w_idx % len(_WEATHER)]
        cargo, c_risk = _CARGO[c_idx % len(_CARGO)]
        dispatch, d_risk, d_positive = _DISPATCH[d_idx % len(_DISPATCH)]
        direction = _direction(w_risk, c_risk, d_risk, d_positive)
        precedents.append(
            EscalationPrecedent(
                weather_condition=weather, cargo_type=cargo, dispatch_status=dispatch, expected_direction=direction
            )
        )
    return tuple(precedents)


ESCALATION_PRECEDENTS: tuple[EscalationPrecedent, ...] = _build_precedents()
