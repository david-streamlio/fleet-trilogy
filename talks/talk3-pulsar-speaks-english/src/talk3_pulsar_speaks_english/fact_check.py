"""Check the LLM's spoken warning against the facts code handed it.

Keeping the LLM out of the decision (synthesizer.py) stops it deciding wrong, but
not saying something wrong: reading Tier 2's warnings by hand found a factual slip
in about 1 in 4 (eval-results/talk3-single-core-m4max-20261004/README.md) — "9 to
12 minutes" when no card says 12 (one truck is truck-12), "one truck at high
severity" when two were, a recommended reroute left out. Talk 2's string checks
passed all of them.

`check_warning()` is plain code, no I/O, and checks only what it can check exactly:

- every number of minutes is one of the cards' eta_impact values (ranges: both
  ends);
- a count of trucks "at high severity" matches the cards;
- a recommended reroute is mentioned, and the corridor is named.

It doesn't catch invented facts without a number in them ("impacting all lanes");
nothing short of another model could.
"""

from __future__ import annotations

import re

from fleet_telemetry_model import EnrichmentCard

from talk3_pulsar_speaks_english.speech import normalize_for_speech

_WORDS = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
    "twenty",
]
_NUMBER_WORDS = {word: float(i) for i, word in enumerate(_WORDS)}
_NUMBER = r"(\d+(?:\.\d+)?|" + "|".join(_WORDS) + r")"
# "9 minutes", "9-minute", "nine to 12 minutes", "9-12 min"
_MINUTES = re.compile(
    _NUMBER + r"(?:\s*(?:to|-|–)\s*" + _NUMBER + r")?[\s-]*(?:minutes?|mins?)\b"
)
# "three trucks experiencing high severity", "one with a high-severity delay"
_HIGH_COUNT = re.compile(
    _NUMBER
    + r"\s+(?:trucks?\s+)?(?:\w+\s+){0,3}?(?:with\s+)?(?:an?\s+)?high[- ]severity"
)
# Truck IDs aren't counts: "truck-47", "truck 47", "trucks 47 and 12".
_TRUCK_IDS = re.compile(r"\btrucks?[\s-]+\d+(?:\s*(?:,|and)\s*(?:truck[\s-]+)?\d+)*")
_REROUTE = re.compile(r"rerout|route around|detour|alternate route|go around")
HIGH_SEVERITY = "high"


def _value(token: str) -> float:
    return float(token) if token[0].isdigit() else _NUMBER_WORDS[token]


def check_warning(
    warning: str,
    *,
    corridor: str,
    cards: list[EnrichmentCard],
    reroute_recommended: bool,
) -> list[str]:
    """Return one line per claim in `warning` that the facts don't support;
    an empty list means it passed."""
    text = _TRUCK_IDS.sub("TRUCK_ID", warning.lower())
    problems = []

    minutes = {round(card.eta_impact) for card in cards}
    for match in _MINUTES.finditer(text):
        for token in filter(None, match.groups()):
            if round(_value(token)) not in minutes:
                problems.append(
                    f"says {token} minutes; the cards' delays are "
                    f"{sorted(minutes)} minutes"
                )

    high = sum(card.severity.lower() == HIGH_SEVERITY for card in cards)
    for match in _HIGH_COUNT.finditer(text):
        if _value(match.group(1)) != high:
            problems.append(
                f"says {match.group(0)!r}; {high} truck(s) reported high severity"
            )

    if reroute_recommended and not _REROUTE.search(text):
        problems.append("a reroute was recommended but the warning doesn't say so")

    spoken = normalize_for_speech(warning).lower()
    if (
        corridor.lower() not in warning.lower()
        and normalize_for_speech(corridor).lower() not in spoken
    ):
        problems.append(f"doesn't name the corridor {corridor}")
    return problems


def fallback_warning(
    *,
    corridor: str,
    cards: list[EnrichmentCard],
    reroute_recommended: bool,
) -> str:
    """A plain-code warning from the same facts, for when the model's attempts
    all fail check_warning(): less natural, never wrong."""
    trucks = len({card.truck_id for card in cards})
    high = sum(card.severity.lower() == HIGH_SEVERITY for card in cards)
    worst = max(round(card.eta_impact) for card in cards)
    if trucks == 1:
        situation = (
            f"one truck is reporting a slowdown, with delays of up to {worst} minutes"
        )
    else:
        severity = f", {high} at high severity," if high else ""
        situation = (
            f"{trucks} trucks are reporting a slowdown{severity} "
            f"with delays of up to {worst} minutes"
        )
    advice = (
        f"Reroute around {corridor} if you can."
        if reroute_recommended
        else "Expect delays and drive with care."
    )
    return f"On {corridor}, {situation}. {advice}"
