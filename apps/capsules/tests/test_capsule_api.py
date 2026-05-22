"""
Capsule API Tests.

Tests Ninja REST endpoints using REAL models — no fakes, no mocks.
DB-dependent tests skip when PostgreSQL is offline.
"""

from __future__ import annotations

import socket

import pytest
from django.test import Client

# --- Check DB availability at import time (no ORM connection needed) ---
DB_AVAILABLE = False
_db_host = "localhost"
_db_port = 45432
try:
    _sock = socket.create_connection((_db_host, _db_port), timeout=1)
    _sock.close()
    DB_AVAILABLE = True
except Exception:
    pass


@pytest.fixture
def client():
    return Client()


@pytest.mark.skipif(not DB_AVAILABLE, reason="Database unavailable")
@pytest.mark.django_db(transaction=True)
class TestCapsuleRegistryAPI:
    def test_list_registry_empty(self, client):
        response = client.get("/v1/capsules/registry")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.skipif(not DB_AVAILABLE, reason="Database unavailable")
@pytest.mark.django_db(transaction=True)
class TestCapsuleImportExportAPI:
    def test_import_endpoint(self, client):
        # Import requires auth (voyant-engineer role) — will get 401/403 without token
        payload = {
            "capsule": {
                "name": "imported-capsule",
                "version": "1.0.0",
                "tenant": "test",
                "soul": {"system_prompt": "test"},
                "body": {"capsule_type": "voyant.intelligence_recipe"},
            }
        }
        response = client.post(
            "/v1/capsules/import",
            data=payload,
            content_type="application/json",
        )
        # Without auth, expect 401 or 403
        assert response.status_code in (401, 403)
