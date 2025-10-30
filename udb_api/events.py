"""Kafka / event bus integration for job lifecycle events.

Emits JSON lines to topic (default: udb.job.events) if KAFKA_BROKERS configured.
Falls back to no-op emitter when Kafka unavailable.
"""
from __future__ import annotations
import json
import os
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from opentelemetry import trace  # type: ignore

try:  # pragma: no cover - optional dependency
    from aiokafka import AIOKafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    AIOKafkaProducer = None  # type: ignore


class EventEmitter:
    def __init__(self, brokers: Optional[str], topic: str = "udb.job.events"):
        self.brokers = brokers
        self.topic = topic
        self._producer: Optional[AIOKafkaProducer] = None
        self._lock = asyncio.Lock()
        self._recent: list[dict] = []
        self._max_recent = 100

    async def start(self):  # pragma: no cover (network)
        if not self.brokers or not AIOKafkaProducer:
            return
        async with self._lock:
            if self._producer is None:
                self._producer = AIOKafkaProducer(bootstrap_servers=self.brokers.split(","))
                await self._producer.start()

    async def stop(self):  # pragma: no cover
        if self._producer:
            await self._producer.stop()
            self._producer = None

    async def emit(self, event: str, payload: Dict[str, Any]):
        record = {
            "event": event,
            **payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        data = (json.dumps(record) + "\n").encode()
        # store recent
        self._recent.append(record)
        if len(self._recent) > self._max_recent:
            self._recent = self._recent[-self._max_recent:]
        if not self.brokers or not self._producer:
            # Silent no-op (could log at debug)
            return
        try:  # pragma: no cover
            await self._producer.send_and_wait(self.topic, data)
        except Exception:
            # Swallow to avoid impacting primary flow; production could log structured error
            pass


_emitter: Optional[EventEmitter] = None


def get_emitter() -> EventEmitter:
    global _emitter
    if _emitter is None:
        brokers = os.getenv("KAFKA_BROKERS")
        topic = os.getenv("UDB_EVENTS_TOPIC", "udb.job.events")
        _emitter = EventEmitter(brokers, topic)
    return _emitter


async def emit_job_event(event: str, job_id: str, job_type: str, state: Optional[str] = None, extra: Optional[Dict[str, Any]] = None):
    emitter = get_emitter()
    payload: Dict[str, Any] = {"jobId": job_id, "jobType": job_type}
    if state:
        payload["state"] = state
    if extra:
        payload.update(extra)
    # tracing context enrichment
    try:  # pragma: no cover
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx and ctx.trace_id != 0:
            payload["traceId"] = format(ctx.trace_id, '032x')
            payload["spanId"] = format(ctx.span_id, '016x')
    except Exception:
        pass
    await emitter.emit(event, payload)

def recent_events(limit: int = 50) -> list[dict]:
    emitter = get_emitter()
    return emitter._recent[-limit:]
