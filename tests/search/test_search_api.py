"""
Integration tests for the Semantic Search API.

Requires a running Milvus container. Tests skip automatically if Milvus
is unavailable — run ``docker compose up voyant_milvus`` first.
"""

import json

import pytest
from django.test import Client
from pymilvus import MilvusException

from apps.search.lib.milvus_store import get_vector_store

# Heartbeat Milvus once at module level; skip all tests if down.
try:
    _store = get_vector_store()
    _MILVUS_AVAILABLE = True
except MilvusException:
    _MILVUS_AVAILABLE = False


@pytest.mark.skipif(not _MILVUS_AVAILABLE, reason="Milvus not available")
@pytest.mark.django_db
class TestSearchApiIntegration:
    """Verifies the Search API (index, query, delete) against Milvus."""

    @pytest.fixture(autouse=True)
    def setup_system(self):
        self.store = get_vector_store()
        self.client = Client()
        self.tenant_id = "test-tenant-search"
        self.headers = {"X-Tenant-ID": self.tenant_id}

    def test_indexing_and_search_lifecycle(self):
        """Verify full lifecycle: index -> search -> get -> delete."""
        texts = [
            "Voyant is a powerful data platform for multimodal analytics.",
            "Keycloak provides open source identity and access management.",
            "Temporal is a scalable workflow orchestration engine.",
        ]

        for text in texts:
            resp = self.client.post(
                "/v1/search/index",
                data=json.dumps({"text": text, "metadata": {"category": "tech"}}),
                content_type="application/json",
                headers=self.headers,
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "indexed"

        # Query for "workflow"
        resp = self.client.post(
            "/v1/search/query",
            data=json.dumps({"query": "workflow engine", "limit": 1}),
            content_type="application/json",
            headers=self.headers,
        )
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert "Temporal" in results[0]["metadata"]["text_preview"]
        assert results[0]["score"] > 0

        item_id = results[0]["id"]

        # Get item by ID
        resp = self.client.get(f"/v1/search/{item_id}", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == item_id

        # Delete item
        resp = self.client.delete(f"/v1/search/{item_id}", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # Verify deleted
        resp = self.client.get(f"/v1/search/{item_id}", headers=self.headers)
        assert resp.status_code == 404

    def test_tenant_isolation(self):
        """Verify that tenants cannot see each other's indexed items."""
        self.client.post(
            "/v1/search/index",
            data=json.dumps({"text": "Private for Tenant A"}),
            content_type="application/json",
            headers=self.headers,
        )

        other_headers = {"X-Tenant-ID": "other-tenant"}
        resp = self.client.post(
            "/v1/search/query",
            data=json.dumps({"query": "Private", "limit": 10}),
            content_type="application/json",
            headers=other_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0
