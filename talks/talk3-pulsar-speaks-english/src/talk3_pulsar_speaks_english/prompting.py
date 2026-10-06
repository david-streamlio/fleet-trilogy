"""Prompting a small quantized instruct model toward Tier 2's spoken warning text.

Per docs/CANON.md, scope ("single_truck" vs "corridor_wide") and the reroute call
are decided by plain code in synthesizer.py *before* the backend is ever invoked
here. This prompt states those decisions as already-settled facts and asks the
model to do exactly one thing: phrase a short spoken-style warning that narrates
them. It never asks the model to decide scope or reroute — that mirrors Tier 1's
llm_inference.structured, which asks the model to classify severity/describe ETA
impact but never to re-derive detection.

Grounding note (same hard-won lesson as llm_inference.structured's v1->v2 fix):
a small quantized model shown a fully-realistic literal example will happily copy
it verbatim regardless of the real input. This prompt's example uses a placeholder
token (`<your warning text here>`) instead of a plausible-looking real sentence,
so there's nothing realistic-looking left to anchor on.

Corridor-omission finding (2026-09-27, docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md):
a real Tier 2 comparison run found Qwen2.5-3B-Instruct systematically dropping the
corridor name from otherwise well-formed, speakable warnings -- 100% omission on the
single-truck scenario, 50% on corridor-wide-no-reroute, 0% once a reroute was
involved. Not random: the model was making its own judgment call about what's
"important enough" to include in a short warning, and dropping the corridor whenever
it judged the situation minor. The prompt below now explicitly requires naming the
corridor, since simply listing it as an input fact (without ever saying it must
appear in the output) wasn't enough. This is a narrow, mechanical "always include
this literal fact" instruction, not a "reason about a nuanced tradeoff" one -- the
kind smaller models tend to follow far more reliably (contrast with talk1's
escalation-task prompt tuning, which repeatedly hit an overcorrection wall trying to
teach models to weigh multiple risk factors, not just always state one fact).

Reroute-tense finding (2026-10-05): the reroute detail is phrased as an instruction
("Reroute traffic around I-95N -- ..."), and Gemma-3-4B-it often narrated it as
already happening ("Traffic is rerouted around the corridor"), stating as done what
the decision only recommends -- in two demo takes running, and in 8 of 30 measured
warnings (eval-results/talk3-reroute-wording-20261005/). The prompt now says so in one
more narrow instruction, the same kind as the corridor rule, added only when a reroute
is recommended: in every prompt, its "drivers should consider it" made the model
suggest alternative routes when none was recommended (3 of 20). Without a reroute, the
prompt is exactly the published one.
PUBLISHED_SYNTHESIS_WARNING_PROMPT is the prompt before that line, which every Tier 2
measurement up to 2026-10-05 used (Talk 2's Tier 2 rows, Talk 3's single-core runs);
pass it as render_synthesis_prompt(template=...) to reproduce them.
"""

from __future__ import annotations

from fleet_telemetry_model import EnrichmentCard
from llm_inference.client import LlmBackend, LlmGenerationConfig
from llm_inference.structured import extract_json_object

PUBLISHED_SYNTHESIS_WARNING_PROMPT = """You are generating a short, calm, spoken-style proactive \
traffic warning (2-3 sentences) for text-to-speech, aimed at drivers approaching a \
corridor. Cheap math and fleet logic have already made every decision below — your \
only job is to phrase the warning in natural language. Do not change the scope or \
reroute decision, and do not invent facts that are not listed here.

Always name the corridor explicitly in your warning (e.g. "On {corridor}...") — \
never omit it, even when the situation seems minor.

Corridor: {corridor}
Affected trucks: {truck_count}
Scope (already decided): {scope}
Reroute recommended (already decided): {reroute_recommended}
Reroute detail (already decided): {reroute_detail}
Enrichment cards:
{cards}

Respond with ONLY the JSON shown in the shape below, filled in for real — no prose, \
no markdown fences, no extra keys.

Shape (a placeholder, not a real answer): {{"spoken_warning": "<your warning text \
here>"}}"""

# {reroute_rule} is REROUTE_RULE when a reroute is recommended, empty otherwise.
SYNTHESIS_WARNING_PROMPT = PUBLISHED_SYNTHESIS_WARNING_PROMPT.replace(
    "never omit it, even when the situation seems minor.\n",
    "never omit it, even when the situation seems minor.\n{reroute_rule}",
)
REROUTE_RULE = (
    "\nA reroute is only ever a recommendation, never already happening: say that "
    "drivers should consider it or that it is recommended -- never that traffic is "
    "being, or has been, rerouted.\n"
)


def render_synthesis_prompt(
    *,
    corridor: str,
    cards: list[EnrichmentCard],
    scope: str,
    reroute_recommended: bool,
    reroute_detail: str | None,
    template: str = SYNTHESIS_WARNING_PROMPT,
) -> str:
    """Build the Tier 2 spoken-warning prompt from already-decided scope/reroute
    facts plus the enrichment cards that fed those decisions. `template` defaults to
    the current prompt; PUBLISHED_SYNTHESIS_WARNING_PROMPT reproduces earlier runs.
    """
    card_lines = "\n".join(
        f"- ({card.truck_id}) {card.event}, severity={card.severity}, "
        f"signals={card.signals}, eta_impact={card.eta_impact:.1f}min"
        for card in cards
    )
    return template.format(
        corridor=corridor,
        truck_count=len({card.truck_id for card in cards}),
        scope=scope,
        reroute_recommended=reroute_recommended,
        reroute_detail=reroute_detail or "none",
        cards=card_lines,
        reroute_rule=REROUTE_RULE if reroute_recommended else "",  # unused by the published template
    )


def generate_spoken_warning(
    backend: LlmBackend,
    *,
    corridor: str,
    cards: list[EnrichmentCard],
    scope: str,
    reroute_recommended: bool,
    reroute_detail: str | None,
    config: LlmGenerationConfig | None = None,
) -> str:
    """Run inference and return the spoken warning text.

    Prefers the requested `{"spoken_warning": "..."}` shape, reusing
    llm_inference.structured.extract_json_object (public precisely so callers like
    this one don't re-implement completion-mode JSON extraction — see that
    function's docstring for why "last complete JSON object in the text" beats
    naive brace-finding). If a completion doesn't contain a parseable JSON object
    at all, or the object doesn't carry a non-empty "spoken_warning" string (e.g.
    a mock/free-text backend, or a real model that just answered in plain prose),
    falls back to using the raw completion text verbatim — Tier 2's only real
    contract is "some spoken-warning text came back," not "it was valid JSON."
    """
    prompt = render_synthesis_prompt(
        corridor=corridor,
        cards=cards,
        scope=scope,
        reroute_recommended=reroute_recommended,
        reroute_detail=reroute_detail,
    )
    completion = backend.generate(prompt, config)
    try:
        parsed = extract_json_object(completion)
    except ValueError:
        return completion.strip()

    warning = parsed.get("spoken_warning")
    if isinstance(warning, str) and warning.strip():
        return warning.strip()
    return completion.strip()
