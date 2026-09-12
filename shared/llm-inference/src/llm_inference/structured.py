"""Prompting a small quantized instruct model toward structured output shaped like
an EnrichmentCard.

Tier 1 never sees raw, undetected telemetry — only an event plus the signal names
cheap math already flagged (see fleet_telemetry_model.detection). Tier 1 interprets;
it does not detect. The prompt text below is the whole point of keeping this in its
own small module: edit it freely without touching parsing/plumbing.
"""

from __future__ import annotations

import json
import re

from fleet_telemetry_model import TelemetryEvent

from llm_inference.client import LlmBackend, LlmGenerationConfig

# v2 — grounding fix. v1 gave a fully-populated numeric example ("eta_impact": 4.0,
# "corridor": "I-95N", "truck_id": "truck-47") and both Qwen2.5-1.5B/0.5B-Instruct
# (Q4_K_M) anchored on it: measured on a known-value event with eta_slip_min=18.0,
# the 1.5B model echoed the example's "eta_impact": 4.0 verbatim in 28/30 trials
# regardless of the real input (93.3% grounding-violation rate) and the 0.5B model
# did the same in 13/30 (43.3%) — copying the example's literal number rather than
# the real signal. v2 replaces every real-looking literal in the example with an
# explicit placeholder token and adds an explicit "copy these exact values" line, so
# there's no plausible-looking wrong number left for a small model to anchor on.
ENRICHMENT_CARD_PROMPT = """You are generating a structured enrichment card for fleet \
dispatch. Cheap math has already detected the signals below — do not re-derive \
detection, just classify severity and describe the ETA impact.

Respond with ONLY a single JSON object with exactly these keys: "event", "severity", \
"signals", "eta_impact", "corridor", "truck_id". No prose, no markdown fences.

Truck: {truck_id}
Corridor: {corridor}
Signals detected by cheap math: {signals}
Rolling average speed: {rolling_avg_speed:.1f} mph
ETA slip: {eta_slip_min:.1f} minutes

"eta_impact" MUST be the ETA slip value given above ({eta_slip_min:.1f}) — copy it \
exactly, do not invent or estimate a different number. "truck_id" and "corridor" \
MUST be copied exactly from above. Do not reuse any value from the shape below —
it is a structure template, not a real answer.

Shape (placeholders only, not real values): {{"event": "<event_name>", "severity": \
"<low|medium|high>", "signals": {signals}, "eta_impact": <copy the ETA slip value \
above>, "corridor": "<copy the corridor above>", "truck_id": "<copy the truck id \
above>"}}"""


def render_enrichment_prompt(event: TelemetryEvent, triggered_signals: list[str]) -> str:
    """Build the Tier 1 structured-output prompt from an event and its triggered signals."""
    return ENRICHMENT_CARD_PROMPT.format(
        truck_id=event.truck_id,
        corridor=event.corridor,
        signals=triggered_signals,
        rolling_avg_speed=event.signals.rolling_avg_speed,
        eta_slip_min=event.signals.eta_slip_min,
    )


def generate_enrichment_card_dict(
    backend: LlmBackend,
    event: TelemetryEvent,
    triggered_signals: list[str],
    config: LlmGenerationConfig | None = None,
) -> dict:
    """Run inference and return an EnrichmentCard-shaped dict (caller validates/constructs it)."""
    prompt = render_enrichment_prompt(event, triggered_signals)
    completion = backend.generate(prompt, config)
    return extract_json_object(completion)


_FENCE_PATTERN = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json_object(text: str) -> dict:
    """Pull the JSON object out of a completion.

    Public so the Tier 3 model-eval harness can inspect raw completions and parse
    outcomes separately (e.g. to log a failing raw output verbatim) without
    duplicating this parsing logic.

    Completion-mode llama.cpp backends (no chat template, `-no-cnv`) echo the whole
    prompt back before continuing it, and small quantized instruct models routinely
    restate the prompt's own JSON example — once, twice, or not followed by an answer
    at all — sometimes inside a ```json fenced block, sometimes bare, sometimes
    trailed by prose past a truncated max_tokens cutoff. The original implementation
    took `find("{")`/`rfind("}")` across the whole string, which spliced the echoed
    example and the real answer into one span and failed with "Extra data" — the
    model WAS often producing valid JSON; the naive extractor just grabbed the wrong
    span. Real captured examples this was built against (Qwen2.5-1.5B/0.5B-Instruct,
    Q4_K_M via mainline llama.cpp's `llama-completion -no-cnv`), see
    shared/llm-inference/tests/test_structured_extraction.py:
      - prompt + echoed example + ```json fenced answer + prose explaining it
      - prompt + echoed example twice + bare (unfenced) answer, ending "[end of text]"
      - prompt + echoed example twice, no real answer produced at all
      - prompt + echoed example + bare answer + prose running past a token cutoff

    Strategy: prefer the LAST fenced code block that parses as a JSON object (a model
    that bothers fencing puts its real answer there, not the inline prompt example);
    otherwise take the LAST complete top-level JSON object found anywhere in the text
    via `json.JSONDecoder.raw_decode` (which — unlike `json.loads` — stops at the end
    of one JSON value and ignores what follows, so trailing prose can't break it).
    "Last" over "first" because the prompt's own embedded example always appears
    earliest, ahead of anything the model itself adds.
    """
    for candidate in reversed(_FENCE_PATTERN.findall(text)):
        try:
            parsed = json.loads(candidate.strip())
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(parsed, dict):
            return parsed

    decoder = json.JSONDecoder()
    last_object: dict | None = None
    search_from = 0
    while (brace_index := text.find("{", search_from)) != -1:
        search_from = brace_index + 1
        try:
            parsed, _ = decoder.raw_decode(text, brace_index)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            last_object = parsed

    if last_object is None:
        raise ValueError(f"LLM completion did not contain a JSON object: {text!r}")
    return last_object
