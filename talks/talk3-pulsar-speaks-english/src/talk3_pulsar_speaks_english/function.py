"""Pulsar Functions entrypoint for Tier 2 global synthesis.

Deployed with `pulsar-admin functions localrun` (see deploy/run_tier2_localrun.sh
and deploy/README.md) today, and with managed mode later — both just point Pulsar
Functions at GlobalSynthesisFunction below. It is a thin wrapper: the real
decision logic lives in synthesizer.synthesize (scope/reroute) and
prompting.generate_spoken_warning (the LLM's one job), both unit-tested without
any Pulsar Functions runtime at all.

Design tradeoff — Functions are per-message, Tier 2 needs aggregation:
The Pulsar Functions model is `process(self, input, context) -> output`, one
output per input message — fundamentally stateless/1-in-1-out, same shape as
Tier 1's EdgeEnrichmentFunction. But Tier 2's synthesize() needs *multiple*
trucks' EnrichmentCards for the same corridor before it can decide single_truck
vs corridor_wide (see synthesizer.py / docs/CANON.md). Pulsar Functions instances
are long-lived worker processes, though (they aren't spun up fresh per message),
so this class keeps the exact same kind of in-memory per-corridor accumulator
that pulsar_adapter.py's `run()` keeps, just as instance state on `self` instead
of a local variable in a loop: every process() call appends the incoming card to
self._accumulator[card.corridor], and only *emits* an IncidentSynthesis once that
corridor's count reaches a small threshold (default: 2 cards), at which point it
synthesizes, clears that corridor's accumulator, and returns the result. Calls
that don't cross the threshold return None (no output published for that
invocation) — Pulsar Functions permits this ("no-op" outputs are simply not
published).

This is the same toy-polling tradeoff pulsar_adapter.py documents, adapted to
fit the Functions API: no event-time windows, no watermarks, no persistence of
the accumulator across a function restart. It also means Tier 2-as-a-Function
has no wall-clock flush (unlike pulsar_adapter.py's window_seconds) — it only
ever flushes when enough cards have arrived, so a corridor stuck below threshold
just accumulates forever until the instance restarts. Good enough to demonstrate
the Functions deployment path on stage; pulsar_adapter.py's time-based flush is
the more complete of the two for an actual demo run.
"""

from __future__ import annotations

import os
from collections import defaultdict

from fleet_telemetry_model import EnrichmentCard, from_json, to_json
from llm_inference import (
    InProcessLlmBackend,
    LlmBackend,
    LlmGenerationConfig,
    SubprocessLlmBackend,
)

from talk3_pulsar_speaks_english.synthesizer import synthesize

DEFAULT_CORRIDOR_THRESHOLD = 2


class GlobalSynthesisFunction:
    """Matches the Pulsar Functions Python API: a class with process(self, input, context).

    See the module docstring above for why this class keeps a per-corridor
    accumulator as instance state rather than being a stateless 1-in-1-out
    wrapper like Tier 1's EdgeEnrichmentFunction.
    """

    def __init__(self, *, corridor_threshold: int = DEFAULT_CORRIDOR_THRESHOLD) -> None:
        self._backend: LlmBackend | None = None
        self._config: LlmGenerationConfig | None = None
        self._corridor_threshold = corridor_threshold
        self._accumulator: dict[str, list[EnrichmentCard]] = defaultdict(list)

    def process(self, input: str, context) -> str | None:
        backend = self._backend or self._build_backend(context)
        card = from_json(EnrichmentCard, input)
        cards = self._accumulator[card.corridor]
        cards.append(card)

        if len(cards) < self._corridor_threshold:
            return None

        synthesis = synthesize(cards, backend, config=self._config)
        self._accumulator[card.corridor] = []
        return to_json(synthesis) if synthesis is not None else None

    def _build_backend(self, context) -> LlmBackend:
        """One-time setup on the first message, from the Function's --user-config.

        `llm_extra_args` (space-separated, e.g. "-no-cnv") carries the model's
        one-shot flags from models.toml — without -no-cnv, mainline llama.cpp wraps
        Gemma's prompt in its chat template, which isn't the configuration the
        Tier 2 gates measured. `corridor_threshold` overrides how many cards a
        corridor needs before it's synthesized (e.g. 3 for a three-truck demo).
        `threads` (llama.cpp's -t, default 4) and `timeout_seconds` (default 60)
        override the generation settings, e.g. threads=1 to run the model on a
        single CPU core.

        `llm_backend` picks how the model runs:
        - `inprocess` (default since 2026-10-05): llama-cpp-python inside this
          Function instance. The model loads once and stays on `self` with the
          accumulator, and each call reuses the prompt prefix the previous one
          already read. `llm_gpu_layers` (default 0, CPU only) offloads layers to a
          GPU; the binary path and extra args don't apply.
        - `subprocess`: a fresh llama.cpp process per call (`llm_binary_path`,
          `llm_extra_args`), reloading the model every time. The Tier 2 gates in
          tests/model measured this one.
        """
        user_config = context.get_user_config_map() if context is not None else {}
        model_path = user_config.get("llm_model_path") or os.environ.get(
            "LLM_MODEL_PATH"
        )
        threads = user_config.get("threads")
        kind = user_config.get("llm_backend") or "inprocess"
        if kind == "inprocess":
            backend = InProcessLlmBackend(
                model_path,
                threads=int(threads) if threads else 4,
                gpu_layers=int(user_config.get("llm_gpu_layers") or 0),
            )
        elif kind == "subprocess":
            extra_args = user_config.get("llm_extra_args") or os.environ.get(
                "LLM_EXTRA_ARGS", ""
            )
            backend = SubprocessLlmBackend(
                binary_path=user_config.get("llm_binary_path")
                or os.environ.get("LLM_BINARY_PATH"),
                model_path=model_path,
                extra_args=tuple(extra_args.split()),
            )
        else:
            raise ValueError(
                f"llm_backend must be 'inprocess' or 'subprocess', got {kind!r}"
            )
        if user_config.get("corridor_threshold"):
            self._corridor_threshold = int(user_config["corridor_threshold"])
        overrides = {}
        if threads:
            overrides["threads"] = int(threads)
        if user_config.get("timeout_seconds"):
            overrides["timeout_seconds"] = float(user_config["timeout_seconds"])
        if overrides:
            self._config = LlmGenerationConfig(**overrides)
        self._backend = backend
        return backend
