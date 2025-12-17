"""
Test Events Integration

Verifies that events are validated against schemas before emission.
"""
import pytest
from unittest.mock import MagicMock, patch
from voyant.core.events import KafkaProducer, VoyantEvent
from voyant.core.event_schema import register_schema, EventSchema, FieldSpec, FieldType, clear_registry

@pytest.fixture
def clean_registry():
    clear_registry()
    yield
    clear_registry()

def test_emit_valid_event(clean_registry):
    """Test emitting a valid event."""
    # Register schema
    schema = EventSchema(
        name="test.event",
        version="1.0.0",
        fields=[
            FieldSpec("job_id", FieldType.STRING),
            FieldSpec("count", FieldType.INTEGER),
        ]
    )
    register_schema(schema)
    
    producer = KafkaProducer()
    # Mock internal producer to simulate successful send
    producer._get_producer = MagicMock(return_value=MagicMock())
    
    event = VoyantEvent(
        event_type="test.event",
        event_id="1",
        timestamp="2024-01-01T00:00:00Z",
        tenant_id="tenant1",
        payload={"job_id": "abc", "count": 10},
    )
    
    # Expect success
    success = producer.emit("jobs", event)
    assert success is True
    producer._get_producer().produce.assert_called_once()

def test_emit_invalid_event(clean_registry):
    """Test emitting an invalid event (missing required field)."""
    # Register schema
    schema = EventSchema(
        name="test.event",
        version="1.0.0",
        fields=[
            FieldSpec("job_id", FieldType.STRING),
            FieldSpec("count", FieldType.INTEGER), # Required
        ]
    )
    register_schema(schema)
    
    producer = KafkaProducer()
    producer._get_producer = MagicMock(return_value=MagicMock())
    
    event = VoyantEvent(
        event_type="test.event",
        event_id="1",
        timestamp="2024-01-01T00:00:00Z",
        tenant_id="tenant1",
        payload={"job_id": "abc"}, # Missing count
    )
    
    # Expect failure due to validation
    success = producer.emit("jobs", event)
    assert success is False
    # Producer should NOT be called
    producer._get_producer().produce.assert_not_called()

def test_emit_unknown_event(clean_registry):
    """Test emitting an event with no registered schema."""
    producer = KafkaProducer()
    producer._get_producer = MagicMock(return_value=MagicMock())
    
    event = VoyantEvent(
        event_type="unknown.event",
        event_id="1",
        timestamp="2024-01-01T00:00:00Z",
        tenant_id="tenant1",
        payload={"foo": "bar"},
    )
    
    # Expect failure (strict validation by default)
    success = producer.emit("jobs", event)
    assert success is False
    producer._get_producer().produce.assert_not_called()

def test_emit_skip_validation(clean_registry):
    """Test skipping validation."""
    producer = KafkaProducer()
    producer._get_producer = MagicMock(return_value=MagicMock())
    
    event = VoyantEvent(
        event_type="unknown.event",
        event_id="1",
        timestamp="2024-01-01T00:00:00Z",
        tenant_id="tenant1",
        payload={"foo": "bar"},
    )
    
    # Expect success with skip_validation=True
    success = producer.emit("jobs", event, skip_validation=True)
    assert success is True
    producer._get_producer().produce.assert_called_once()
