"""
Unit tests for Milvus-backed VectorStore.

These tests exercise real code paths. Milvus container is not required —
connection-failure paths verify resilience logic. No mocks.
"""

import pytest
from pymilvus import MilvusException

from apps.search.lib.milvus_store import VectorItem, VectorStore, _MilvusConnection


class TestVectorItem:
    """Tests for the VectorItem dataclass."""

    def test_creation(self):
        item = VectorItem(id="doc-1", vector=[0.1, 0.2], metadata={"k": "v"})
        assert item.id == "doc-1"
        assert item.vector == [0.1, 0.2]
        assert item.metadata == {"k": "v"}

    def test_defaults(self):
        item = VectorItem(id="doc-1", vector=[0.1])
        assert item.metadata == {}


class TestMilvusConnection:
    """Tests for the resilient connection manager — real failure paths."""

    def test_client_raises_when_milvus_unavailable(self):
        conn = _MilvusConnection()
        with pytest.raises(MilvusException):
            conn.client()

    def test_backoff_increases_on_repeated_failures(self):
        conn = _MilvusConnection()
        # First failure sets backoff > 1.0
        with pytest.raises(MilvusException):
            conn.client()
        assert conn._backoff > 1.0

        # Immediate retry should fail fast with cooling-down message
        with pytest.raises(MilvusException) as exc_info:
            conn.client()
        assert "cooling down" in str(exc_info.value).lower()


class TestVectorStoreInterface:
    """Tests for VectorStore public interface — real failure paths."""

    def test_constructor_raises_when_milvus_unavailable(self):
        with pytest.raises(MilvusException):
            VectorStore()
