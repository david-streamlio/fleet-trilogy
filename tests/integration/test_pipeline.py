"""End-to-end: publish -> consume -> enrich -> republish, against a real Pulsar broker.

Opt-in (`@pytest.mark.integration`, run via `make test-integration`). Spins up
Pulsar standalone with testcontainers-python, so it needs Docker. Never required
for `make test` — see docs/CANON.md and deploy/README.md for why unit tests never
touch Pulsar or the LLM runtime.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

import pulsar
import pytest
from fleet_telemetry_model import (
    DEFAULT_TELEMETRY_TOPIC,
    ENRICHMENT_CARDS_TOPIC,
    EnrichmentCard,
    GpsPosition,
    Signals,
    TelemetryEvent,
    from_json,
    to_json,
)
from llm_inference import SubprocessLlmBackend
from talk1_edge_intelligence.pulsar_adapter import run as run_adapter

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


def _incident_event() -> TelemetryEvent:
    return TelemetryEvent(
        timestamp=datetime.now(tz=UTC),
        truck_id="truck-47",
        speed_mph=35.0,
        gps=GpsPosition(lat=40.0, lon=-75.0),
        heading=0.0,
        route_segment="seg-1",
        corridor="I-95N",
        planned_eta=datetime.now(tz=UTC),
        current_eta=datetime.now(tz=UTC),
        signals=Signals(rolling_avg_speed=35.0, eta_slip_min=4.0, stop_go_index=0.8),
        _ground_truth="slowdown_incident",
    )


def test_publish_consume_enrich_republish_end_to_end(pulsar_service_url):
    client = pulsar.Client(pulsar_service_url)

    stop_event = threading.Event()
    adapter_thread = threading.Thread(
        target=run_adapter,
        kwargs={
            "service_url": pulsar_service_url,
            "backend": SubprocessLlmBackend(mock=True),
            "stop_event": stop_event,
        },
        daemon=True,
    )
    adapter_thread.start()
    # The adapter's consumer subscription must exist before we publish — a
    # subscription created after a message is sent starts at Latest by
    # default and never sees it.
    time.sleep(2.0)

    producer = client.create_producer(DEFAULT_TELEMETRY_TOPIC)
    producer.send(to_json(_incident_event()).encode("utf-8"))
    producer.close()
    try:
        result_consumer = client.subscribe(ENRICHMENT_CARDS_TOPIC, "test-consumer")
        msg = result_consumer.receive(timeout_millis=30_000)
        card = from_json(EnrichmentCard, msg.data())
        result_consumer.acknowledge(msg)
        result_consumer.close()

        assert card.truck_id == "truck-47"
        assert card.corridor == "I-95N"
    finally:
        stop_event.set()
        adapter_thread.join(timeout=10)
        client.close()
