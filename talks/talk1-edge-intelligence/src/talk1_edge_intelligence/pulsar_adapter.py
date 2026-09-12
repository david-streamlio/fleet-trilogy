"""Thin Pulsar adapter: consume raw telemetry, run process_event, republish cards.

This is the "plain app" runtime path — no Pulsar Functions runtime required, just
a `pulsar.Client` consumer and producer wired around processor.process_event. It's
what the integration tests drive end-to-end. function.py is the alternate runtime
shell for `pulsar-admin functions localrun`; both call the exact same processor.
"""

from __future__ import annotations

import logging
import threading

import pulsar
from fleet_telemetry_model import (
    DEFAULT_TELEMETRY_TOPIC,
    ENRICHMENT_CARDS_TOPIC,
    TelemetryEvent,
    from_json,
    to_json,
)
from llm_inference import LlmBackend

from talk1_edge_intelligence.processor import process_event

logger = logging.getLogger("talk1_edge_intelligence.pulsar_adapter")

DEFAULT_SUBSCRIPTION_NAME = "tier1-edge-interpreter"


def run(
    *,
    service_url: str,
    backend: LlmBackend,
    input_topic: str = DEFAULT_TELEMETRY_TOPIC,
    output_topic: str = ENRICHMENT_CARDS_TOPIC,
    subscription_name: str = DEFAULT_SUBSCRIPTION_NAME,
    stop_event: threading.Event | None = None,
    receive_timeout_millis: int = 1000,
) -> None:
    """Consume input_topic, run process_event, publish any resulting card to output_topic.

    Loops until stop_event is set. Callers own the backend's lifecycle (e.g. a
    SubprocessLlmBackend pointed at the local llama.cpp binary/model on the Pi).
    """
    stop_event = stop_event or threading.Event()
    client = pulsar.Client(service_url)
    try:
        consumer = client.subscribe(input_topic, subscription_name)
        producer = client.create_producer(output_topic)
        try:
            while not stop_event.is_set():
                try:
                    msg = consumer.receive(timeout_millis=receive_timeout_millis)
                except pulsar.Timeout:
                    continue
                try:
                    event = from_json(TelemetryEvent, msg.data())
                    card = process_event(event, backend)
                    if card is not None:
                        producer.send(to_json(card).encode("utf-8"))
                    consumer.acknowledge(msg)
                except Exception:
                    logger.exception("failed to process message %s", msg.message_id())
                    consumer.negative_acknowledge(msg)
        finally:
            producer.close()
            consumer.close()
    finally:
        client.close()
