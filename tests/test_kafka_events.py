import asyncio
import json
import os
import time
from typing import List

from aiokafka import AIOKafkaConsumer
from fastapi.testclient import TestClient
import pytest

from udb_api.app import app


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("KAFKA_BROKERS"), reason="Kafka not configured")
def test_analyze_emits_kafka_event():
    os.environ["UDB_DISABLE_RATE_LIMIT"] = "1"
    os.environ["UDB_ENABLE_EVENTS"] = "1"
    client = TestClient(app)
    resp = client.post("/analyze", json={})
    assert resp.status_code == 200
    job_id = resp.json()["jobId"]

    brokers = os.getenv("KAFKA_BROKERS")
    topic = os.getenv("UDB_EVENTS_TOPIC", "udb.job.events")

    messages: List[dict] = []

    async def _consume():
        consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=brokers.split(","),
            auto_offset_reset="latest",
            enable_auto_commit=False,
            consumer_timeout_ms=5000,
        )
        await consumer.start()
        try:
            start = time.time()
            while time.time() - start < 10:
                async for msg in consumer:
                    try:
                        data = json.loads(msg.value.decode())
                        messages.append(data)
                        if data.get("jobId") == job_id:
                            return
                    except Exception:
                        pass
                await asyncio.sleep(0.5)
        finally:
            await consumer.stop()

    asyncio.get_event_loop().run_until_complete(_consume())
    assert any(m.get("jobId") == job_id for m in messages), "No event for jobId found"
    # Basic schema keys
    match = next(m for m in messages if m.get("jobId") == job_id)
    for key in ["event", "jobId", "jobType", "timestamp"]:
        assert key in match