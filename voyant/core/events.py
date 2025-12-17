"""
Kafka Event Producer for Voyant

Emits events to Kafka topics for:
- Job lifecycle (created, started, completed, failed)
- Quality alerts
- Lineage updates
- Billing/metering events
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from voyant.core.config import get_settings
from voyant.core.event_schema import validate_event

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class VoyantEvent:
    """Base event structure."""
    event_type: str
    event_id: str
    timestamp: str
    tenant_id: str
    payload: Dict[str, Any]
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))


class KafkaProducer:
    """Kafka producer for Voyant events."""
    
    TOPICS = {
        "jobs": "voyant.jobs",
        "quality": "voyant.quality.alerts",
        "lineage": "voyant.lineage",
        "billing": "voyant.billing.events",
        "audit": "voyant.audit",
    }
    
    def __init__(self):
        self.bootstrap_servers = settings.kafka_bootstrap_servers
        self._producer = None
    
    def _get_producer(self):
        """Lazy-load Kafka producer."""
        if self._producer is None:
            try:
                from confluent_kafka import Producer
                self._producer = Producer({
                    "bootstrap.servers": self.bootstrap_servers,
                    "client.id": "voyant-api",
                    "acks": "all",
                    "retries": 3,
                })
                logger.info(f"Kafka producer connected to {self.bootstrap_servers}")
            except ImportError:
                logger.warning("confluent-kafka not installed")
            except Exception as e:
                logger.error(f"Kafka producer init failed: {e}")
        return self._producer
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery."""
        if err:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}]")
    
    def emit(self, topic_key: str, event: VoyantEvent, skip_validation: bool = False) -> bool:
        """Emit event to Kafka topic."""
        # Validate schema unless skipped
        if not skip_validation:
            validation = validate_event(event.event_type, event.payload)
            if not validation.valid:
                logger.error(f"Schema validation failed for {event.event_type}: {validation.errors}")
                return False

        producer = self._get_producer()
        if not producer:
            logger.warning(f"No Kafka producer, event not sent: {event.event_type}")
            # Return True in dev/test if producer missing, to avoid failing valid logic? 
            # Or False? Standard behavior was False. Keeping False but maybe strictly we should 
            # allow fallback if no kafka. 
            # For now, consistent with previous behavior: return False.
            return False
        
        topic = self.TOPICS.get(topic_key, topic_key)
        
        try:
            producer.produce(
                topic=topic,
                key=event.tenant_id.encode(),
                value=event.to_json().encode(),
                callback=self._delivery_callback,
            )
            producer.poll(0)
            return True
        except Exception as e:
            logger.error(f"Failed to emit event: {e}")
            return False
    
    def flush(self, timeout: float = 10.0):
        """Flush pending messages."""
        producer = self._get_producer()
        if producer:
            producer.flush(timeout)
    
    def close(self):
        """Close producer."""
        if self._producer:
            self._producer.flush()
            self._producer = None


# Singleton producer
_producer: Optional[KafkaProducer] = None

def get_kafka_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer()
    return _producer


# Convenience functions
def emit_job_event(
    event_type: str,
    job_id: str,
    tenant_id: str,
    job_type: str,
    status: str,
    **extra,
) -> bool:
    """Emit job lifecycle event."""
    import uuid
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
    """Emit quality alert event."""
    import uuid
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
    """Emit billing/metering event."""
    import uuid
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
