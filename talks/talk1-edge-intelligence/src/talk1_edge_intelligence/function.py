"""Pulsar Functions entrypoint for Tier 1 edge enrichment.

Deployed with `pulsar-admin functions localrun` (see deploy/run_tier1_localrun.sh
and deploy/README.md) today, and with managed mode later — both just point Pulsar
Functions at EdgeEnrichmentFunction below. It is a thin wrapper: all real logic
lives in processor.process_event, which is unit-tested without any Pulsar Functions
runtime at all.
"""

from __future__ import annotations

import os

from fleet_telemetry_model import TelemetryEvent, from_json, to_json
from llm_inference import SubprocessLlmBackend

from talk1_edge_intelligence.processor import process_event


class EdgeEnrichmentFunction:
    """Matches the Pulsar Functions Python API: a class with process(self, input, context)."""

    def __init__(self) -> None:
        self._backend: SubprocessLlmBackend | None = None

    def process(self, input: str, context) -> str | None:
        backend = self._backend or self._build_backend(context)
        event = from_json(TelemetryEvent, input)
        card = process_event(event, backend)
        return to_json(card) if card is not None else None

    def _build_backend(self, context) -> SubprocessLlmBackend:
        user_config = context.get_user_config_map() if context is not None else {}
        backend = SubprocessLlmBackend(
            binary_path=user_config.get("llm_binary_path")
            or os.environ.get("LLM_BINARY_PATH"),
            model_path=user_config.get("llm_model_path")
            or os.environ.get("LLM_MODEL_PATH"),
        )
        self._backend = backend
        return backend
