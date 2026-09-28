"""LlmTriageFunction — configurable Pulsar Function around the eta_slip-gated
triage step, reviewed against Google AI's demo draft and revised once more after a
real architectural pivot (2026-09-26, see docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md).

Two real GBNF bugs were fixed early on (still relevant to build_grammar below):

1. A dynamically-built grammar left backslash-quote tokens (meant to read as
   "low"/"medium"/"high") sitting outside any "..." string literal — verified
   against llama.cpp's actual grammar parser (llama-grammar.cpp's parse_sequence,
   which only recognizes a term starting with a quote, [, <, or !, a word-char, (,
   ., *, +, ?, or {; a bare backslash falls into the final else-break and the
   grammar never loads).
2. A refactor mixed a raw-string template with an f-string that re-escaped
   backslash-quote sequences differently, corrupting a hardcoded field.
   build_grammar sidesteps hand-escaping entirely by using json.dumps() for the
   one value that needs it.

The bigger change: severity is NO LONGER an LLM output. Ten-plus rounds of real-model
testing this session (docs/TALK2-DATA-ENGINEERING-IMPACT-TRACK.md) found every model
asked to classify severity from graduated numeric signals unreliable — mismatch rates
from 33% to 73%, degenerate constant-output collapses the norm, not the exception —
while coprocessor.severity_classifier.classify_severity does the identical
classification perfectly, instantly, for free. Per docs/CANON.md's "cheap math does
detection, not the LLM" principle, that's exactly where it belongs: the same category
as eta_impact/truck_id already being hardcoded below rather than left to the model.

The LLM's job now is bounded and matched to what it's actually good at: given a
deterministically-computed baseline_severity and genuinely unstructured operational
context (weather, cargo type, dispatch status — trip_context.py, none of which
reduces cleanly to a threshold), decide whether to raise, lower, or hold that
baseline, and explain why. Config (model/binary paths, cache path, prompt template,
generation params) is read from the function's user-config map, not hardcoded or
passed to __init__ — __init__ takes no arguments per the Pulsar Functions Python
contract, and user config isn't available until a context exists. Setup runs lazily
on the first process() call and is skipped on every call after.

The escalation vocabulary was originally "escalate"/"confirm"/"de_escalate", changed
to "raise"/"hold"/"lower" after a real diagnostic run (docs/TALK2-DATA-ENGINEERING-
IMPACT-TRACK.md) found Gemma-3-1B-it writing "escalate" into the free-text
recommended_action field even when it had just chosen "de_escalate". The hypothesis
was substring priming ("de_escalate" contains "escalate"); a follow-up run disproved
it -- the identical contradiction shape reappeared with "raise"/"lower", which share
no letters at all, and the rename also shifted both models' overall escalation
distribution in an unpredictable way on top of not fixing the original problem.

recommended_action is therefore NO LONGER an LLM output either (see
RECOMMENDED_ACTIONS below) -- a template lookup keyed on escalation, the same
"move it to cheap math once the model proves unreliable at it" pattern applied to
severity itself above. The model's only remaining free-text job is risk_synthesis:
explain the escalation decision, not restate it in different words. This removes
the recommended_action/escalation contradiction by construction rather than by
hoping a wording change avoids it.

Runtime backend switched from SubprocessLlmBackend to LlmServerBackend
(2026-09-26): a 14-model Flow B comparison run was measured taking far longer
than the model spectrum alone predicted. Root cause: SubprocessLlmBackend shells
out to a one-shot CLI binary per generate() call, so every one of the ~120 trials
per model reloaded the full model weights and reinitialized the Metal GPU backend
from scratch (confirmed via `lsof` showing the Metal shader library get re-mapped
on every subprocess launch). LlmServerBackend starts `llama-server` once and keeps
it running across every process() call instead — see its docstring in
llm_inference/client.py for the measured before/after numbers, including the
fact that this also fixes the file-based prompt cache (`--prompt-cache-ro`)
having silently never worked at all, since nothing ever wrote that cache file.
"""

from __future__ import annotations

import json

from llm_inference import LlmGenerationConfig, LlmInferenceError, LlmServerBackend
from llm_inference.structured import extract_json_object

DEFAULT_BINARY_PATH = "~/tools/llama.cpp/build/bin/llama-server"
DEFAULT_MODEL_PATH = "~/tools/models/qwen2.5-3b-instruct-GGUF/qwen2.5-3b-instruct-q8_0.gguf"
# 150 was fine for the old severity/event_label/dispatch_action shape, but a real
# diagnostic run found it truncating 8/10 completions once risk_synthesis became
# the model's only free-text field (Gemma-3-1B-it routinely writes 100+ word
# justifications for it) -- the exact same "grammar-forced JSON runs out of token
# budget mid-value" failure this repo already fixed once before, recurring because
# the schema changed shape. Verified fix: 300 tokens, 0/10 truncations on the same
# real run that failed 8/10 at 150.
DEFAULT_MAX_TOKENS = 300
DEFAULT_TEMPERATURE = 0.2
# This dev machine (M4) has 12 performance + 4 efficiency cores (sysctl
# hw.perflevel0/1.physicalcpu) -- 4 was leaving two-thirds of the performance
# cores idle. 12 matches the performance-core count, leaving the 4 efficiency
# cores for the OS/everything else rather than starving them.
DEFAULT_THREADS = 12
DEFAULT_TIMEOUT_SECONDS = 60.0

SEVERITY_LEVELS = ("low", "medium", "high")

# Static rules sit first so they form a stable --prompt-cache-ro prefix across
# calls; only the "Context variables" tail differs per event. Deliberately does NOT
# include the raw physics signals (deceleration, ABS, stop_go_index) that already
# determined baseline_severity — handing those to the model too would reintroduce
# exactly the "re-derive severity from raw numbers" job this pivot removed. Only
# the baseline (already a fact, not a question) and the genuinely unstructured
# operational fields are here.
DEFAULT_PROMPT_TEMPLATE = (
    "You are a fleet dispatch operational-risk assessor.\n"
    "A deterministic vehicle-physics system has already computed a baseline severity "
    "for this event from sensor signals (deceleration, ABS, speed instability). Treat "
    "that baseline as a correct starting point. Your only job is to decide whether the "
    "three operational-context fields below, taken together, are strong enough "
    "evidence to move away from it.\n\n"
    "BASELINE SEVERITY (already computed from vehicle physics): {baseline_severity}\n\n"
    "Operational context:\n"
    "Weather: {weather_condition}\n"
    "Cargo: {cargo_type}\n"
    "Dispatch status: {dispatch_status}\n\n"
    "How to weigh each field:\n"
    "- Cargo is a risk multiplier ONLY if it is hazardous, liquid, or otherwise "
    "dangerous if spilled or shifted. Empty, dry, or general freight is NOT a risk "
    "factor.\n"
    "- Weather is a risk multiplier ONLY if it degrades traction or visibility (rain, "
    "ice, snow, fog). Clear or dry conditions are NOT a risk factor.\n"
    "- A dispatch status describing the driver handling a hazard safely (a documented "
    "defensive or evasive maneuver, a completed safety check) is evidence the driver "
    "is in control -- that is a reason to hold or lower, never a reason to raise. "
    "Being behind schedule under pressure IS a genuine risk factor; being ahead of "
    "schedule or on schedule is not.\n\n"
    "Decision:\n"
    "- raise: at least one field above is a genuine risk multiplier by the rules "
    "above (e.g. hazardous cargo together with poor weather).\n"
    "- lower: none of the fields are risk multipliers, and at least one positively "
    "indicates safe, controlled conditions.\n"
    "- hold: the fields are mixed, or none clearly point either way.\n\n"
    "Truck ID: {truck_id}\n"
    "Corridor: {corridor}\n\n"
    "First write risk_synthesis: name the SPECIFIC field(s) that drove your decision "
    "and why, using the rules above. Then set escalation to match what you just wrote "
    "-- your escalation value and your risk_synthesis text must agree; never write "
    "reasoning for one decision and then choose a different one. "
    "Respond using the validated format template. DO NOT include markdown code boxes or introductory prose."
)

# Deterministic, not model output -- see module docstring. Keyed on escalation, the
# one field the model does control, so the action always agrees with the decision by
# construction.
RECOMMENDED_ACTIONS = {
    "raise": "Escalate for driver/dispatcher review.",
    "hold": "Continue monitoring; no status change.",
    "lower": "Log and continue; no immediate action needed.",
}


def recommended_action_for(escalation: str) -> str:
    return RECOMMENDED_ACTIONS.get(escalation, RECOMMENDED_ACTIONS["hold"])


def apply_escalation(baseline_severity: str, escalation: str) -> str:
    """Moves baseline_severity by exactly one SEVERITY_LEVELS step for "raise"/
    "lower", clamped at the ends; "hold" (or anything else) leaves it unchanged.
    Deterministic, cheap-math application of the model's bounded decision -- the
    model never states a severity value itself.
    """
    idx = SEVERITY_LEVELS.index(baseline_severity)
    if escalation == "raise":
        idx = min(idx + 1, len(SEVERITY_LEVELS) - 1)
    elif escalation == "lower":
        idx = max(idx - 1, 0)
    return SEVERITY_LEVELS[idx]


def _gbnf_quoted_literal(raw_value: str) -> str:
    """A GBNF quoted-string term whose matched OUTPUT is exactly
    json.dumps(raw_value) — a valid JSON string, quote characters included.

    A GBNF term's own delimiting quotes are consumed by the parser, not
    reproduced in the output — embedding json.dumps(raw_value) directly as a
    term (i.e. "<json.dumps output>") loses its outer quote characters from
    the generated text, which is the bug this replaces (verified against a
    real llama-completion run: truck_id came out as `truck-03` instead of
    `"truck-03"`). To force those quote characters into the output, they must
    appear as *content* inside the term, escaped per GBNF's own string syntax
    (backslash-quote for a literal quote, double-backslash for a literal
    backslash) — hence re-escaping json.dumps' result before wrapping it in a
    fresh pair of real delimiter quotes.
    """
    desired_output = json.dumps(raw_value)
    gbnf_content = desired_output.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{gbnf_content}"'


def build_grammar(truck_id: str) -> str:
    """GBNF grammar hardcoding truck_id (cheap math already knows it) as a literal,
    constraining escalation to a proper quoted-string alternation, and leaving
    risk_synthesis as the ONLY free-text field — the model's actual, non-deterministic
    job. Notably absent: severity (cheap math) and recommended_action (a deterministic
    template on escalation, RECOMMENDED_ACTIONS above) — see module docstring for why
    both were removed from what the model generates.
    """
    truck_id_literal = _gbnf_quoted_literal(truck_id)
    return (
        # risk_synthesis comes BEFORE escalation deliberately: grammar-constrained
        # decoding is strictly left-to-right, so field order is reasoning order. An
        # earlier version put escalation first and a real smoke-test run showed the
        # model committing to a decision while its own (later-generated)
        # risk_synthesis argued for the opposite -- the model had to decide before it
        # had "thought through" the justification for that decision. This ordering
        # lets the free-text reasoning inform the structured choice instead of the
        # other way around.
        'root ::= "{\\n"'
        ' "  \\"risk_synthesis\\": \\"" [^"]* "\\",\\n"'
        ' "  \\"escalation\\": " ("\\"raise\\"" | "\\"hold\\"" | "\\"lower\\"") ",\\n"'
        f' "  \\"truck_id\\": " {truck_id_literal} "\\n"'
        ' "}"'
    )


class LlmTriageFunction:
    """Matches the Pulsar Functions Python API: a class with process(self, input, context)."""

    def __init__(self) -> None:
        self._configured = False
        self._backend: LlmServerBackend | None = None
        self._prompt_template = DEFAULT_PROMPT_TEMPLATE
        self._max_tokens = DEFAULT_MAX_TOKENS
        self._temperature = DEFAULT_TEMPERATURE
        self._threads = DEFAULT_THREADS
        self._timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    def process(self, input_item: str, context) -> str | None:
        logger = context.get_logger()
        if not self._configured:
            self._configure(context)

        try:
            # Idempotent after the first successful call (see LlmServerBackend.start's
            # docstring) -- cheap to call unconditionally, and doing it here rather than
            # in _configure keeps a missing binary/model caught by this try/except
            # instead of propagating out of process() uncaught.
            self._backend.start()

            payload = json.loads(input_item)
            truck_id = payload["truck_id"]
            corridor = payload["corridor"]
            metrics = payload["metrics"]
            triggers = payload.get("contextual_triggers", {})
            eta_slip_min = float(metrics["eta_slip_min"])
            baseline_severity = payload["baseline_severity"]

            prompt = self._prompt_template.format(
                truck_id=truck_id,
                corridor=corridor,
                baseline_severity=baseline_severity,
                weather_condition=triggers.get("weather_condition", "unknown"),
                cargo_type=triggers.get("cargo_type", "unknown"),
                dispatch_status=triggers.get("dispatch_status", "unknown"),
            )
            grammar = build_grammar(truck_id)

            # No `stop` sequence here -- the grammar's root rule already ends with a
            # required literal "}" and grammar-constrained decoding terminates on its
            # own once that's satisfied (the grammar has no valid continuation after
            # it). A real run under LlmServerBackend found this out the hard way:
            # llama-server's `stop` field EXCLUDES the matched text from the returned
            # content (unlike whatever the old SubprocessLlmBackend/--reverse-prompt
            # CLI path did), so passing stop=("}",) here silently truncated the
            # required closing brace off every single completion -- 0% format
            # reliability, not a subtle miss.
            config = LlmGenerationConfig(
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                timeout_seconds=self._timeout_seconds,
                grammar=grammar,
            )
            completion = self._backend.generate(prompt, config)
            card = extract_json_object(completion)
            # Grammar already forces truck_id; setting it explicitly documents the
            # invariant and is free insurance against a parser quirk. baseline/final
            # severity, recommended_action, and eta_impact are all cheap-math facts,
            # never model output -- recommended_action is derived from escalation
            # (the one field the model does control) so it always agrees with the
            # decision by construction, not by hoping the model keeps them in sync.
            escalation = card.get("escalation", "hold")
            card["truck_id"] = truck_id
            card["baseline_severity"] = baseline_severity
            card["severity"] = apply_escalation(baseline_severity, escalation)
            card["recommended_action"] = recommended_action_for(escalation)
            card["eta_impact"] = eta_slip_min
            return json.dumps(card)
        except LlmInferenceError as exc:
            logger.error(f"LLM triage inference failed for {input_item!r}: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001 — Pulsar Functions expects process() to never raise
            logger.error(f"LLM triage function failed for {input_item!r}: {exc}")
            return None

    def _configure(self, context) -> None:
        get = context.get_user_config_value
        self._prompt_template = get("prompt_template") or DEFAULT_PROMPT_TEMPLATE
        self._max_tokens = int(get("max_tokens") or DEFAULT_MAX_TOKENS)
        self._temperature = float(get("temperature") or DEFAULT_TEMPERATURE)
        self._threads = int(get("threads") or DEFAULT_THREADS)
        self._timeout_seconds = float(get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS)
        self._backend = LlmServerBackend(
            binary_path=get("llm_binary_path") or DEFAULT_BINARY_PATH,
            model_path=get("llm_model_path") or DEFAULT_MODEL_PATH,
            threads=self._threads,
            startup_timeout_seconds=get("server_startup_timeout_seconds") or 60.0,
        )
        self._configured = True

    def close(self) -> None:
        """Shuts down the backend's server process, if one was started. Not part of
        the Pulsar Functions contract (that lifecycle has no explicit teardown hook;
        a deployed function's server just runs for the process's lifetime) -- this
        exists for callers that construct many short-lived instances back-to-back,
        e.g. a multi-model eval harness, which must close model N's server before
        starting model N+1's to avoid two servers competing for the GPU at once."""
        if self._backend is not None:
            self._backend.close()
