"""
Test Events Integration (Real Kafka)

Verifies that events are validated and successfully transmitted to a Real Kafka Broker.
NO MOCKS.
"""
import pytest
import os
import json
import uuid
import time
from typing import Optional
from voyant.core.events import KafkaProducer, VoyantEvent, get_kafka_producer
from voyant.core.event_schema import register_schema, EventSchema, FieldSpec, FieldType, clear_registry

KAFKA_AVAILABLE = False
try:
    from confluent_kafka import Consumer, Producer
    # Check simple connection? For now assume if import works we try integration
    KAFKA_AVAILABLE = True
except ImportError:
    pass

@pytest.fixture
def clean_registry():
    clear_registry()
    yield
    clear_registry()

@pytest.fixture
def kafka_consumer_fixture():
    """Real Kafka Consumer to verify events."""
    if not KAFKA_AVAILABLE:
        pytest.skip("confluent-kafka not installed")
        
    group_id = f"test-group-{uuid.uuid4()}"
    # Default to HOST PORT 45092 for external tests if env var not set
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:45092")
    
    try:
        c = Consumer({
            'bootstrap.servers': bootstrap,
            'group.id': group_id,
            'auto.offset.reset': 'earliest'
        })
        c.subscribe(['voyant.jobs'])
        yield c
        c.close()
    except Exception as e:
        pytest.skip(f"Could not connect to Kafka at {bootstrap}: {e}")

@pytest.mark.integration
@pytest.mark.skipif(not KAFKA_AVAILABLE, reason="requires confluent-kafka")
def test_emit_and_consume_real_event(clean_registry, kafka_consumer_fixture):
    """
    Integration Test: Emit Valid Event -> Real Kafka -> Consume & Verify.
    """
    # 1. Register Schema
    schema = EventSchema(
        name="test.integration.event",
        version="1.0.0",
        fields=[
            FieldSpec("job_id", FieldType.STRING),
            FieldSpec("status", FieldType.STRING),
        ]
    )
    register_schema(schema)
    
    # 2. Emit Event using Real Producer
    # Note: KafkaProducer internal logic loads settingsenv
    producer = get_kafka_producer()
    
    unique_id = str(uuid.uuid4())
    event = VoyantEvent(
        event_type="test.integration.event",
        event_id=unique_id,
        timestamp="2024-01-01T00:00:00Z",
        tenant_id="tenant-integration",
        payload={"job_id": unique_id, "status": "active"},
    )
    
    # This calls producer.produce() -> Real Network Call
    success = producer.emit("jobs", event)
    assert success is True, "Failed to emit event to Kafka"
    
    producer.flush() # Force send matching VIBE reliability
    
    # 3. Consume from Kafka and Verify
    # Poll for a few seconds
    found = False
    start = time.time()
    while time.time() - start < 10:
        msg = kafka_consumer_fixture.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
            
        # Parse
        val = msg.value().decode('utf-8')
        data = json.loads(val)
        
        if data["event_id"] == unique_id:
            found = True
            assert data["payload"]["job_id"] == unique_id
            break
            
    assert found, "Did not receive event from Real Kafka topic 'voyant.jobs' within 10s"

def test_emit_invalid_event_schema_check(clean_registry):
    """
    Unit-ish test for Schema Validation logic (No Mocks, just logical verification).
    Does NOT require Kafka connection if validation fails first.
    """
    schema = EventSchema(
        name="test.fail",
        version="1.0.0",
        fields=[FieldSpec("required_field", FieldType.INTEGER)]
    )
    register_schema(schema)
    
    producer = KafkaProducer() # Clean instance
    
    event = VoyantEvent(
        event_type="test.fail",
        event_id="1",
        timestamp="now",
        tenant_id="t1",
        payload={} # Missing field
    )
    
    # Should fail validation BEFORE reaching Kafka
    success = producer.emit("jobs", event)
    assert success is False
