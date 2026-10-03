"""Thin Pulsar adapter: consume enrichment cards, aggregate per corridor, publish
incident syntheses.

This is the "plain app" runtime path — no Pulsar Functions runtime required, just
a `pulsar.Client` consumer and producer wired around synthesizer.synthesize. It's
what an integration test would drive end-to-end. function.py is the alternate
runtime shell for `pulsar-admin functions localrun`; both share the same
accumulate/flush approach below.

Windowing note: Tier 1 is 1-in-1-out (process_event takes one TelemetryEvent and
returns at most one EnrichmentCard), so its adapter has no state between receives.
Tier 2 is fundamentally different — CANON.md's synthesize() needs *multiple*
trucks' cards for the same corridor to decide single_truck vs corridor_wide. This
adapter therefore keeps a simple in-memory `dict[corridor, list[EnrichmentCard]]`
accumulator. Each corridor's window opens when its *first* card arrives and
closes `window_seconds` later; on every receive-loop tick (the same
`receive_timeout_millis` idle-tick pattern talk1 uses, just repurposed here as a
"check if it's time to flush" signal rather than a no-op), every corridor whose
window has closed is synthesized into one IncidentSynthesis, published, and
cleared. (An earlier version flushed every corridor on one global wall-clock
timer that started with the adapter, so two cards published back-to-back could
straddle a flush boundary and come out as two single_truck incidents instead of
one corridor_wide one — seen live in a Talk 3 demo run.)

This is deliberately a toy polling/batching window for a conference demo, NOT a
real streaming windowing implementation: there's no event-time semantics, no
watermarks, no late-data handling, and no persistence of the accumulator across a
restart (a crash mid-window silently drops whatever had accumulated). A "real"
implementation would use Pulsar Functions' windowing API, or an external state
store keyed by corridor. Good enough to show the shape of Tier 2 aggregation on
stage; not what you'd ship.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict

import pulsar
from fleet_telemetry_model import (
    ENRICHMENT_CARDS_TOPIC,
    INCIDENTS_TOPIC,
    EnrichmentCard,
    from_json,
    to_json,
)
from llm_inference import LlmBackend

from talk3_pulsar_speaks_english.synthesizer import synthesize

logger = logging.getLogger("talk3_pulsar_speaks_english.pulsar_adapter")

DEFAULT_SUBSCRIPTION_NAME = "tier2-global-synthesizer"

# How often (in seconds) the accumulator is flushed, i.e. how often we ask
# How long (in seconds) a corridor's window stays open after its first card
# arrives, i.e. how long we wait for other trucks on the same corridor before
# synthesizing. Plain wall-clock time, not an event-time window boundary.
DEFAULT_WINDOW_SECONDS = 5.0


def run(
    *,
    service_url: str,
    backend: LlmBackend,
    input_topic: str = ENRICHMENT_CARDS_TOPIC,
    output_topic: str = INCIDENTS_TOPIC,
    subscription_name: str = DEFAULT_SUBSCRIPTION_NAME,
    stop_event: threading.Event | None = None,
    receive_timeout_millis: int = 1000,
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
) -> None:
    """Consume input_topic, accumulate EnrichmentCards per corridor, and once a
    corridor's window (opened by its first card) is `window_seconds` old, call
    synthesize() on its cards and publish the IncidentSynthesis to output_topic.

    Loops until stop_event is set. Callers own the backend's lifecycle (e.g. a
    SubprocessLlmBackend pointed at a local llama.cpp binary/model in the cloud
    tier).

    A receive() timeout is treated the same as a successful receive for the
    purpose of checking whether the window has elapsed — the loop always makes
    progress toward the next flush regardless of whether a message arrived on
    a given iteration.
    """
    stop_event = stop_event or threading.Event()
    client = pulsar.Client(service_url)
    accumulator: dict[str, list[EnrichmentCard]] = defaultdict(list)
    opened_at: dict[str, float] = {}
    try:
        consumer = client.subscribe(input_topic, subscription_name)
        producer = client.create_producer(output_topic)
        try:
            while not stop_event.is_set():
                try:
                    msg = consumer.receive(timeout_millis=receive_timeout_millis)
                except pulsar.Timeout:
                    pass
                else:
                    try:
                        card = from_json(EnrichmentCard, msg.data())
                        accumulator[card.corridor].append(card)
                        opened_at.setdefault(card.corridor, time.monotonic())
                        consumer.acknowledge(msg)
                    except Exception:
                        logger.exception(
                            "failed to process message %s", msg.message_id()
                        )
                        consumer.negative_acknowledge(msg)

                _flush(accumulator, opened_at, backend, producer, window_seconds)
        finally:
            producer.close()
            consumer.close()
    finally:
        client.close()


def _flush(
    accumulator: dict[str, list[EnrichmentCard]],
    opened_at: dict[str, float],
    backend: LlmBackend,
    producer: pulsar.Producer,
    window_seconds: float,
) -> None:
    """Synthesize and publish one IncidentSynthesis per corridor whose window has
    been open at least `window_seconds`, then clear that corridor's list and
    window. Corridors still inside their window are left to keep accumulating.
    """
    now = time.monotonic()
    for corridor, cards in list(accumulator.items()):
        if not cards or now - opened_at.get(corridor, now) < window_seconds:
            continue
        try:
            synthesis = synthesize(cards, backend)
            if synthesis is not None:
                producer.send(to_json(synthesis).encode("utf-8"))
        except Exception:
            logger.exception("failed to synthesize incident for corridor %s", corridor)
        finally:
            accumulator[corridor] = []
            opened_at.pop(corridor, None)
