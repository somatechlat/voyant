"""
Kafka Event Producer for Voyant.

This module provides a standardized interface for emitting structured, schema-validated
events to Kafka topics. It abstracts the underlying `confluent_kafka` producer,
provides a singleton pattern for efficient connection management, and offers
high-level helper functions for dispatching common business events.

Key components:
- Event Schema: Defines the contract for all emitted events.
- KafkaProducer: A lazy-loading wrapper around the confluent_kafka producer.
- Helper Functions: `emit_*` functions for easy, one-line event dispatch.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from voyant.core.config import get_settings
from voyant.core.event_schema import validate_event

logger = logging.getLogger(__name__)


def _get_settings():
    # Lazy settings access to avoid import-time side effects (e.g., during Temporal
    # workflow sandbox validation).
    return get_settings()


@dataclass
class VoyantEvent:
    """
    Represents a standard event structure for all Voyant messages.

    Attributes:
        event_type: The unique name of the event (e.g., "job.started").
        event_id: A unique identifier (UUID) for this specific event instance.
        timestamp: An ISO 8601 timestamp of when the event was created.
        tenant_id: The identifier for the tenant associated with the event.
        payload: A dictionary containing the event-specific data, which must
                 conform to its registered EventSchema.
    """

    event_type: str
    event_id: str
    timestamp: str
    tenant_id: str
    payload: Dict[str, Any]

    def to_json(self) -> str:
        """Serialize the event to a JSON string."""
        return json.dumps(asdict(self))


class KafkaProducer:
    """
    A singleton wrapper around the confluent_kafka Producer.

    This class handles the lazy initialization of the Kafka producer, ensuring that
    the application can start even if Kafka is unavailable. It also provides a
    standardized `emit` method that includes schema validation.

    Security Note: The default configuration is suitable for local development.
    In a production environment, additional security parameters (e.g., for SASL
    authentication) should be added to the producer configuration dictionary.
    """

    TOPICS = {
        "jobs": "voyant.jobs",
        "quality": "voyant.quality.alerts",
        "lineage": "voyant.lineage",
        "billing": "voyant.billing.events",
        "audit": "voyant.audit",
    }

    def __init__(self):
        """Initialize the KafkaProducer wrapper."""
        self.bootstrap_servers = _get_settings().kafka_bootstrap_servers
        self._producer = None

    def _get_producer(self):
        """
        Lazy-load and initialize the underlying `confluent_kafka` Producer.

        This method will only attempt to create a producer on the first call to `emit`.
        If the `confluent-kafka` library is not installed, it will log a warning and
        subsequent `emit` calls will fail gracefully.
        """
        if self._producer is None:
            try:
                from confluent_kafka import Producer

                config = {
                    "bootstrap.servers": self.bootstrap_servers,
                    "client.id": "voyant-api",
                    "acks": "all",  # Wait for all in-sync replicas to acknowledge.
                    "retries": 3,  # Retry failed produce requests.
                }
                self._producer = Producer(config)
                logger.info(f"Kafka producer connected to {self.bootstrap_servers}")
            except ImportError:
                logger.warning(
                    "Cannot emit Kafka event: 'confluent-kafka' library is not installed."
                )
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}")
        return self._producer

    def _delivery_callback(self, err, msg):
        """Asynchronous callback for Kafka message delivery reports."""
        if err:
            logger.error(f"Kafka message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")

    def emit(
        self, topic_key: str, event: VoyantEvent, skip_validation: bool = False
    ) -> bool:
        """
        Validate and emit an event to a specified Kafka topic.

        Args:
            topic_key: A key referencing a topic in `self.TOPICS` (e.g., "jobs").
            event: The VoyantEvent object to send.
            skip_validation: If True, schema validation will be skipped. For tests only.

        Returns:
            True if the event was successfully produced, False otherwise. If the
            Kafka producer is not available or not configured, this will return False.
        """
        if not skip_validation:
            validation = validate_event(event.event_type, event.payload)
            if not validation.valid:
                logger.error(
                    f"Schema validation failed for {event.event_type}: {validation.errors}"
                )
                return False

        producer = self._get_producer()
        if not producer:
            logger.warning(
                f"Event not sent: Kafka producer is not available. Event: {event.event_type}"
            )
            return False

        topic = self.TOPICS.get(topic_key, topic_key)

        try:
            producer.produce(
                topic=topic,
                key=event.tenant_id.encode("utf-8"),
                value=event.to_json().encode("utf-8"),
                callback=self._delivery_callback,
            )
            # poll() serves delivery reports from previous produce() calls.
            producer.poll(0)
            return True
        except Exception as e:
            logger.error(f"Failed to produce Kafka event to topic '{topic}': {e}")
            return False

    def flush(self, timeout: float = 10.0):
        """
        Wait for all messages in the producer queue to be delivered.

        Args:
            timeout: The maximum time to wait in seconds.
        """
        producer = self._get_producer()
        if producer:
            producer.flush(timeout)

    def close(self):
        """Flush messages and close the producer connection."""
        if self._producer:
            self._producer.flush()
            self._producer = None


# Singleton producer instance to be shared across the application.
_producer: Optional[KafkaProducer] = None


def get_kafka_producer() -> KafkaProducer:
    """
    Get the singleton instance of the KafkaProducer.

    This factory function ensures that only one KafkaProducer is instantiated
    per application process, which is critical for performance and resource management.
    """
    global _producer
    if _producer is None:
        _producer = KafkaProducer()
    return _producer


# --- High-Level Event Emitter Functions ---


def emit_job_event(
    event_type: str,
    job_id: str,
    tenant_id: str,
    job_type: str,
    status: str,
    **extra,
) -> bool:
    """
    A convenience function to emit a job lifecycle event.

    Args:
        event_type: The specific event type (e.g., "job.started", "job.failed").
        job_id: The ID of the job.
        tenant_id: The tenant associated with the job.
        job_type: The type of job (e.g., "analyze").
        status: The status being reported.
        **extra: Additional key-value pairs to include in the event payload.

    Returns:
        True if the event was successfully produced, False otherwise.
    """
    event = VoyantEvent(
        event_type=event_type,
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        tenant_id=tenant_id,
        payload={
            "job_id": job_id,
            "job_type": job_type,
            "status": status,
            **extra,
        },
    )
    return get_kafka_producer().emit("jobs", event)


def emit_quality_alert(
    source_id: str,
    tenant_id: str,
    score: float,
    failed_checks: list,
) -> bool:
    """
    A convenience function to emit a data quality alert.

    Args:
        source_id: The ID of the data source being checked.
        tenant_id: The tenant associated with the source.
        score: A numeric score representing the quality.
        failed_checks: A list of checks that failed.

    Returns:
        True if the event was successfully produced, False otherwise.
    """
    event = VoyantEvent(
        event_type="quality.alert",
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        tenant_id=tenant_id,
        payload={
            "source_id": source_id,
            "score": score,
            "failed_checks": failed_checks,
            "severity": "critical" if score < 0.5 else "warning",
        },
    )
    return get_kafka_producer().emit("quality", event)


def emit_billing_event(
    tenant_id: str,
    event_type: str,
    metric_name: str,
    value: float,
    **metadata,
) -> bool:
    """
    A convenience function to emit a billing or metering event.

    Args:
        tenant_id: The tenant to bill for the usage.
        event_type: The type of event (e.g., "usage_recorded").
        metric_name: The name of the metric being recorded (e.g., "cpu_hours").
        value: The numeric value of the usage.
        **metadata: Additional key-value pairs for context.

    Returns:
        True if the event was successfully produced, False otherwise.
    """
    event = VoyantEvent(
        event_type=f"billing.{event_type}",
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        tenant_id=tenant_id,
        payload={
            "metric_name": metric_name,
            "value": value,
            **metadata,
        },
    )
    return get_kafka_producer().emit("billing", event)
