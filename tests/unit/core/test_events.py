"""
Unit tests for apps.core.lib.events — Kafka event producer and VoyantEvent.

Tests the data structures and event construction without requiring Kafka.
"""

import json
import uuid

from apps.core.lib.events import VoyantEvent

# =============================================================================
# VoyantEvent Tests
# =============================================================================


class TestVoyantEvent:
    def test_creation(self):
        event = VoyantEvent(
            event_type="job.started",
            event_id="abc-123",
            timestamp="2024-01-01T00:00:00",
            tenant_id="tenant_1",
            payload={"job_id": "j1", "status": "running"},
        )
        assert event.event_type == "job.started"
        assert event.event_id == "abc-123"
        assert event.tenant_id == "tenant_1"
        assert event.payload["job_id"] == "j1"

    def test_to_json(self):
        event = VoyantEvent(
            event_type="test.event",
            event_id="id-1",
            timestamp="2024-01-01T00:00:00",
            tenant_id="t1",
            payload={"key": "value"},
        )
        json_str = event.to_json()
        data = json.loads(json_str)
        assert data["event_type"] == "test.event"
        assert data["event_id"] == "id-1"
        assert data["tenant_id"] == "t1"
        assert data["payload"] == {"key": "value"}

    def test_to_json_roundtrip(self):
        event = VoyantEvent(
            event_type="roundtrip",
            event_id=str(uuid.uuid4()),
            timestamp="2024-06-15T12:00:00",
            tenant_id="t2",
            payload={"nested": {"key": [1, 2, 3]}},
        )
        json_str = event.to_json()
        data = json.loads(json_str)
        assert data["payload"]["nested"]["key"] == [1, 2, 3]

    def test_empty_payload(self):
        event = VoyantEvent(
            event_type="empty",
            event_id="id",
            timestamp="2024-01-01T00:00:00",
            tenant_id="t1",
            payload={},
        )
        json_str = event.to_json()
        data = json.loads(json_str)
        assert data["payload"] == {}

    def test_complex_payload(self):
        payload = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "array": [1, "two", 3.0],
            "nested": {"a": {"b": "deep"}},
        }
        event = VoyantEvent(
            event_type="complex",
            event_id="id",
            timestamp="2024-01-01T00:00:00",
            tenant_id="t1",
            payload=payload,
        )
        json_str = event.to_json()
        data = json.loads(json_str)
        assert data["payload"]["string"] == "value"
        assert data["payload"]["number"] == 42
        assert data["payload"]["null"] is None
        assert data["payload"]["nested"]["a"]["b"] == "deep"
