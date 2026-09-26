"""LLMTriageFunction — configurable Pulsar Function around the eta_slip-gated
triage step (severity / event_label / dispatch_action) reviewed against Google
AI's demo draft.

Two real bugs in that draft are fixed here:

1. Its dynamically-built GBNF grammar left backslash-quote tokens (meant to
   read as "low"/"medium"/"high") sitting outside any "..." string literal —
   verified against llama.cpp's actual grammar parser (llama-grammar.cpp's
   parse_sequence, which only recognizes a term starting with a quote, [, <
   or !, a word-char, (, ., *, +, ?, or {; a bare backslash falls into the
   final else-break and the grammar never loads). See build_grammar below —
   built once with a real llama-completion run (gemma-3-1b-it) confirming it
   loads and constrains output correctly.
2. Its refactor mixed a raw-string template with an f-string that re-escaped
   backslash-quote sequences differently (one collapses to a bare quote in a
   non-raw Python string, the other doesn't), corrupting the truck_id field
   specifically. build_grammar sidesteps hand-escaping entirely by using
   json.dumps() for the one value that needs it.

Config (model/binary paths, cache path, prompt template, generation params) is
read from the function's user-config map, not hardcoded or passed to
__init__ — __init__ takes no arguments per the Pulsar Functions Python
contract, and user config isn't available until a context exists. Setup runs
lazily on the first process() call and is skipped on every call after, so a
model/prompt/grammar change is a `pulsar-admin functions update
--user-config` away, not a code change.
"""

from __future__ import annotations

import json

from llm_inference import LlmGenerationConfig, LlmInferenceError, SubprocessLlmBackend
from llm_inference.structured import extract_json_object

DEFAULT_BINARY_PATH = "~/tools/llama.cpp/build/bin/llama-completion"
DEFAULT_MODEL_PATH = "~/tools/models/qwen2.5-3b-instruct-GGUF/qwen2.5-3b-instruct-q8_0.gguf"
DEFAULT_CACHE_PATH = "/tmp/telemetry_base.cache"
DEFAULT_MAX_TOKENS = 150
DEFAULT_TEMPERATURE = 0.2
DEFAULT_THREADS = 4
DEFAULT_TIMEOUT_SECONDS = 60.0

# Static rules sit first so they form a stable --prompt-cache-ro prefix across
# calls; only the "Context variables" tail differs per event.
DEFAULT_PROMPT_TEMPLATE = (
    "You are an advanced transportation dispatch intelligence node.\n"
    "Evaluate the metrics and environmental context variables below to synthesize "
    "operational triage strategy.\n\n"
    "SEVERITY RULE ENGINE (EVALUATED AGAINST TOTAL COMBINED CONTEXT):\n"
    "- low: Minor friction, localized ripple effect, no structural route alterations required.\n"
    "- medium: Noticeable corridor congestion, active delay accumulation, recommend situational speed adjustments.\n"
    "- high: Multi-variable compounding slowdowns (e.g., active incident, peak rush hour constraints). Requires structural route changes.\n\n"
    "Context variables for current incident footprint:\n"
    "Truck ID: {truck_id}\n"
    "Corridor Location: {corridor}\n"
    "Pre-existing Fired Mathematical Signals: {signals}\n"
    "Current Velocity Track: {rolling_avg_speed} (Baseline Expectation: {historical_baseline_speed})\n"
    "Current Traffic Footprint Pattern: {traffic_pattern}\n"
    "System Environmental Constraints: {local_time}\n"
    "Calculated Primary ETA Slip Deficit: {eta_slip_min} minutes\n\n"
    "Respond using the validated format template. DO NOT include markdown code boxes or introductory prose."
)


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


def build_grammar(eta_slip_min: float, truck_id: str) -> str:
    """GBNF grammar hardcoding the two fields cheap math already knows
    (eta_impact, truck_id) as literals, constraining severity to a proper
    quoted-string alternation, and leaving event_label/dispatch_action as the
    only free-text fields — the model's actual, non-deterministic job.
    """
    truck_id_literal = _gbnf_quoted_literal(truck_id)
    return (
        'root ::= "{\\n"'
        ' "  \\"severity\\": " ("\\"low\\"" | "\\"medium\\"" | "\\"high\\"") ",\\n"'
        ' "  \\"event_label\\": \\"" [^"]* "\\",\\n"'
        ' "  \\"dispatch_action\\": \\"" [^"]* "\\",\\n"'
        f' "  \\"eta_impact\\": {eta_slip_min},\\n"'
        f' "  \\"truck_id\\": " {truck_id_literal} "\\n"'
        ' "}"'
    )


class LlmTriageFunction:
    """Matches the Pulsar Functions Python API: a class with process(self, input, context)."""

    def __init__(self) -> None:
        self._configured = False
        self._backend: SubprocessLlmBackend | None = None
        self._prompt_template = DEFAULT_PROMPT_TEMPLATE
        self._cache_path: str | None = None
        self._max_tokens = DEFAULT_MAX_TOKENS
        self._temperature = DEFAULT_TEMPERATURE
        self._threads = DEFAULT_THREADS
        self._timeout_seconds = DEFAULT_TIMEOUT_SECONDS

    def process(self, input_item: str, context) -> str | None:
        logger = context.get_logger()
        if not self._configured:
            self._configure(context)

        try:
            payload = json.loads(input_item)
            truck_id = payload["truck_id"]
            corridor = payload["corridor"]
            signals = payload["signals"]
            metrics = payload["metrics"]
            triggers = payload.get("contextual_triggers", {})
            eta_slip_min = float(metrics["eta_slip_min"])

            prompt = self._prompt_template.format(
                truck_id=truck_id,
                corridor=corridor,
                signals=json.dumps(signals),
                rolling_avg_speed=metrics.get("rolling_avg_speed"),
                traffic_pattern=metrics.get("traffic_pattern"),
                eta_slip_min=eta_slip_min,
                local_time=triggers.get("local_time", "unknown"),
                historical_baseline_speed=triggers.get("historical_baseline_speed", "unknown"),
            )
            grammar = build_grammar(eta_slip_min, truck_id)

            extra_args: tuple[str, ...] = ("--grammar", grammar, "--reverse-prompt", "}")
            if self._cache_path:
                extra_args += ("--prompt-cache", self._cache_path, "--prompt-cache-ro")

            config = LlmGenerationConfig(
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                threads=self._threads,
                timeout_seconds=self._timeout_seconds,
                extra_args=extra_args,
            )
            completion = self._backend.generate(prompt, config)
            card = extract_json_object(completion)
            # Grammar already forces these; setting them explicitly documents
            # the invariant and is free insurance against a parser quirk.
            card["eta_impact"] = eta_slip_min
            card["truck_id"] = truck_id
            return json.dumps(card)
        except LlmInferenceError as exc:
            logger.error(f"LLM triage inference failed for {input_item!r}: {exc}")
            return None
        except Exception as exc:  # noqa: BLE001 — Pulsar Functions expects process() to never raise
            logger.error(f"LLM triage function failed for {input_item!r}: {exc}")
            return None

    def _configure(self, context) -> None:
        get = context.get_user_config_value
        self._backend = SubprocessLlmBackend(
            binary_path=get("llm_binary_path") or DEFAULT_BINARY_PATH,
            model_path=get("llm_model_path") or DEFAULT_MODEL_PATH,
            extra_args=("-no-cnv",),
        )
        self._prompt_template = get("prompt_template") or DEFAULT_PROMPT_TEMPLATE
        self._cache_path = get("prompt_cache_path") or DEFAULT_CACHE_PATH
        self._max_tokens = int(get("max_tokens") or DEFAULT_MAX_TOKENS)
        self._temperature = float(get("temperature") or DEFAULT_TEMPERATURE)
        self._threads = int(get("threads") or DEFAULT_THREADS)
        self._timeout_seconds = float(get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS)
        self._configured = True
