"""Pulsar publishing: batched producer, retry/backoff on broker hiccups."""

from __future__ import annotations

import logging
import time

import pulsar

logger = logging.getLogger("fleet_simulator.publisher")


class PulsarPublishError(RuntimeError):
    """Raised when a publish fails even after retrying."""


class PulsarPublisher:
    def __init__(
        self,
        *,
        service_url: str,
        topic: str,
        token: str | None = None,
        batching_max_messages: int = 100,
        batching_max_publish_delay_ms: int = 10,
        max_retries: int = 5,
        base_backoff_seconds: float = 0.5,
    ) -> None:
        authentication = pulsar.AuthenticationToken(token) if token else None
        self._client = pulsar.Client(service_url, authentication=authentication)
        self._producer = self._client.create_producer(
            topic,
            batching_enabled=True,
            batching_max_messages=batching_max_messages,
            batching_max_publish_delay_ms=batching_max_publish_delay_ms,
            block_if_queue_full=True,
        )
        self._max_retries = max_retries
        self._base_backoff_seconds = base_backoff_seconds

    def publish(self, payload: bytes) -> None:
        attempt = 0
        while True:
            try:
                self._producer.send(payload)
                return
            except Exception as exc:  # pulsar.Error and friends
                attempt += 1
                if attempt > self._max_retries:
                    raise PulsarPublishError(
                        f"publish failed after {self._max_retries} retries: {exc}"
                    ) from exc
                backoff = self._base_backoff_seconds * (2 ** (attempt - 1))
                logger.warning(
                    "publish failed (attempt %d/%d): %s; retrying in %.1fs",
                    attempt,
                    self._max_retries,
                    exc,
                    backoff,
                )
                time.sleep(backoff)

    def flush(self) -> None:
        self._producer.flush()

    def close(self) -> None:
        try:
            self._producer.close()
        finally:
            self._client.close()
