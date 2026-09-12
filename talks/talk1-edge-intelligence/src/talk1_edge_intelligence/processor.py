"""Tier 1 (edge) enrichment: the pure pipeline core.

process_event() has no Pulsar dependency and no I/O of its own — it is a plain
function of (event, backend). That is what lets it run identically as a plain
app, inside `pulsar-admin functions localrun`, or in a unit test with a mock
LlmBackend. See pulsar_adapter.py and function.py for the two runtime shells
around this same function.
"""

from __future__ import annotations

from fleet_telemetry_model import EnrichmentCard, TelemetryEvent, is_probable_slowdown
from fleet_telemetry_model.detection import evaluate_signals
from llm_inference import LlmBackend, generate_enrichment_card_dict


def process_event(event: TelemetryEvent, backend: LlmBackend) -> EnrichmentCard | None:
    """Return an EnrichmentCard if cheap math has flagged a probable slowdown, else None.

    Detection (is_probable_slowdown) is math and happens first; the backend is only
    asked to interpret events that cheap math already flagged, per docs/CANON.md.
    """
    if not is_probable_slowdown(event):
        return None
    triggered_signals = evaluate_signals(event)
    card_dict = generate_enrichment_card_dict(backend, event, triggered_signals)
    return EnrichmentCard(**card_dict)
