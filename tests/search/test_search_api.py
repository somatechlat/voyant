"""
Integration tests for the Semantic Search API.
No mocks - uses the real local VectorStore and TF-IDF embeddings.
"""

import json

import pytest
from django.test import Client

from apps.search.lib.vector_store import get_vector_store


@pytest.mark.django_db
class TestSearchApiIntegration:
    """
    Verifies the Search API (index, query, delete) against real persistence.
    """

    @pytest.fixture(autouse=True)
    def setup_system(self, tmp_path):
        # Use a temporary vector storage path
        self.storage_path = str(tmp_path / "vectors.json")
        # Initialize store with temporary path
        self.store = get_vector_store(storage_path=self.storage_path)
        self.client = Client()
        self.tenant_id = "test-tenant-search"

        # We need to ensure the request has the tenant_id.
        self.headers = {"X-Tenant-ID": self.tenant_id}

    def test_indexing_and_search_lifecycle(self):
        """Verify full lifecycle: index -> search -> get -> delete."""

        # 1. Index items
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

        # 2. Query for "workflow"
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

        # 3. Get item by ID
        resp = self.client.get(f"/v1/search/{item_id}", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == item_id

        # 4. Delete item
        resp = self.client.delete(f"/v1/search/{item_id}", headers=self.headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "deleted"

        # 5. Verify deleted
        resp = self.client.get(f"/v1/search/{item_id}", headers=self.headers)
        assert resp.status_code == 404

    def test_tenant_isolation(self):
        """Verify that tenants cannot see each other's indexed items."""

        # Index item for tenant A
        self.client.post(
            "/v1/search/index",
            data=json.dumps({"text": "Private for Tenant A"}),
            content_type="application/json",
            headers=self.headers,  # tenant-tenant-search
        )

        # Query from tenant B
        other_headers = {"X-Tenant-ID": "other-tenant"}
        resp = self.client.post(
            "/v1/search/query",
            data=json.dumps({"query": "Private", "limit": 10}),
            content_type="application/json",
            headers=other_headers,
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 0
