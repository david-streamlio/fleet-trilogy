"""End-to-end: publish enrichment cards -> aggregate -> synthesize -> republish,
against a real Pulsar broker.

Opt-in (`@pytest.mark.integration`, run via `make test-integration`). Spins up
Pulsar standalone with testcontainers-python, so it needs Docker. Never required
for `make test` — see docs/CANON.md and deploy/README.md for why unit tests never
touch Pulsar or the LLM runtime.

Mirrors tests/integration/test_pipeline.py's Tier 1 pattern, adapted for Tier 2's
aggregation: two cards for two distinct trucks on the same corridor are
published so the accumulator crosses synthesize()'s single_truck/corridor_wide
threshold within one short window, per pulsar_adapter.run's `window_seconds`.
"""

from __future__ import annotations

import threading
import time

import pulsar
import pytest
from fleet_telemetry_model import (
    ENRICHMENT_CARDS_TOPIC,
    INCIDENTS_TOPIC,
    EnrichmentCard,
    IncidentSynthesis,
    from_json,
    to_json,
)
from llm_inference import SubprocessLlmBackend
from talk3_pulsar_speaks_english.pulsar_adapter import run as run_adapter

testcontainers = pytest.importorskip("testcontainers")
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

pytestmark = pytest.mark.integration

PULSAR_IMAGE = "apachepulsar/pulsar:3.2.2"


@pytest.fixture(scope="module")
def pulsar_service_url():
    container = (
        DockerContainer(PULSAR_IMAGE)
        .with_command("bin/pulsar standalone")
        .with_exposed_ports(6650, 8080)
    )
    container.start()
    try:
        wait_for_logs(container, "messaging service is ready", timeout=120)
        host = container.get_container_host_ip()
        port = container.get_exposed_port(6650)
        yield f"pulsar://{host}:{port}"
    finally:
        container.stop()


def _card(truck_id: str) -> EnrichmentCard:
    return EnrichmentCard(
        event="slowdown",
        severity="high",
        signals=["sustained_low_speed", "stop_go_index", "eta_slip"],
        eta_impact=6.0,
        corridor="I-95N",
        truck_id=truck_id,
    )


def test_publish_consume_synthesize_republish_end_to_end(pulsar_service_url):
    client = pulsar.Client(pulsar_service_url)

    stop_event = threading.Event()
    adapter_thread = threading.Thread(
        target=run_adapter,
        kwargs={
            "service_url": pulsar_service_url,
            "backend": SubprocessLlmBackend(mock=True),
            "stop_event": stop_event,
            "window_seconds": 1.0,
        },
        daemon=True,
    )
    adapter_thread.start()
    # The adapter's consumer subscription must exist before we publish — a
    # subscription created after a message is sent starts at Latest by
    # default and never sees it.
    time.sleep(2.0)
    # Same rule for the result side: subscribe to the incidents topic before
    # anything can be published to it, or a fast synthesis is missed entirely.
    result_consumer = client.subscribe(INCIDENTS_TOPIC, "test-consumer")

    producer = client.create_producer(ENRICHMENT_CARDS_TOPIC)
    producer.send(to_json(_card("truck-47")).encode("utf-8"))
    producer.send(to_json(_card("truck-48")).encode("utf-8"))
    producer.close()
    try:
        msg = result_consumer.receive(timeout_millis=30_000)
        synthesis = from_json(IncidentSynthesis, msg.data())
        result_consumer.acknowledge(msg)
        result_consumer.close()

        assert synthesis.corridor == "I-95N"
        assert set(synthesis.affected_truck_ids) == {"truck-47", "truck-48"}
        assert synthesis.scope == "corridor_wide"
    finally:
        stop_event.set()
        adapter_thread.join(timeout=10)
        client.close()
