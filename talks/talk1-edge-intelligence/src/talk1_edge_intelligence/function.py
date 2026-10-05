"""Pulsar Functions entrypoint for Tier 1 edge enrichment.

Deployed with `pulsar-admin functions localrun` (see deploy/run_tier1_localrun.sh
and deploy/README.md) today, and with managed mode later — both just point Pulsar
Functions at EdgeEnrichmentFunction below. It is a thin wrapper: all real logic
lives in processor.process_event, which is unit-tested without any Pulsar Functions
runtime at all.

The model runs inside this Function by default (`InProcessLlmBackend`,
llama-cpp-python), loaded once and kept on `self`; `llm_backend=subprocess` keeps
the old fresh-`llama-completion`-per-call backend (2026-10-05, see
TODO-INPROCESS-LLM.md).
"""

from __future__ import annotations

import os

from fleet_telemetry_model import TelemetryEvent, from_json, to_json
from llm_inference import InProcessLlmBackend, LlmBackend, SubprocessLlmBackend

from talk1_edge_intelligence.processor import process_event


class EdgeEnrichmentFunction:
    """Matches the Pulsar Functions Python API: a class with process(self, input, context)."""

    def __init__(self) -> None:
        self._backend: LlmBackend | None = None

    def process(self, input: str, context) -> str | None:
        backend = self._backend or self._build_backend(context)
        event = from_json(TelemetryEvent, input)
        card = process_event(event, backend)
        return to_json(card) if card is not None else None

    def _build_backend(self, context) -> LlmBackend:
        """`llm_backend` picks how the model runs:
        - `inprocess` (default): llama-cpp-python inside this Function instance. The
          model loads once and stays on `self`. `threads` (default 4) and
          `llm_gpu_layers` (default 0, CPU only) are its load-time settings.
        - `subprocess`: a fresh llama.cpp process per call (`llm_binary_path`),
          reloading the model every time.
        """
        user_config = context.get_user_config_map() if context is not None else {}
        model_path = user_config.get("llm_model_path") or os.environ.get("LLM_MODEL_PATH")
        kind = user_config.get("llm_backend") or "inprocess"
        if kind == "inprocess":
            backend = InProcessLlmBackend(
                model_path,
                threads=int(user_config.get("threads") or 4),
                gpu_layers=int(user_config.get("llm_gpu_layers") or 0),
            )
        elif kind == "subprocess":
            backend = SubprocessLlmBackend(
                binary_path=user_config.get("llm_binary_path")
                or os.environ.get("LLM_BINARY_PATH"),
                model_path=model_path,
            )
        else:
            raise ValueError(f"llm_backend must be 'inprocess' or 'subprocess', got {kind!r}")
        self._backend = backend
        return backend
