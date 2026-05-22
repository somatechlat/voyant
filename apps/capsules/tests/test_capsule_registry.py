"""
Capsule Registry Service Tests.

Tests discovery, installation, validation using REAL models.
No fakes, no mocks. DB-dependent tests skip when PostgreSQL is offline.
"""

from __future__ import annotations

import socket

import pytest

from apps.capsules.services.capsule_registry import validate_capsule_definition

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


class TestValidateCapsuleDefinition:
    def test_valid_minimal_definition(self):
        data = {
            "name": "test-capsule",
            "version": "1.0.0",
            "soul": {},
            "body": {},
        }
        valid, error = validate_capsule_definition(data)
        assert valid is True
        assert error is None

    def test_invalid_missing_name(self):
        data = {"version": "1.0.0", "soul": {}, "body": {}}
        valid, error = validate_capsule_definition(data)
        assert valid is False
        assert error is not None
        assert "name" in error.lower()

    def test_invalid_output_format(self):
        data = {
            "name": "test",
            "version": "1.0.0",
            "soul": {},
            "body": {"output_formats": ["invalid_format"]},
        }
        valid, error = validate_capsule_definition(data)
        assert valid is False
        assert error is not None
        assert "output formats" in error.lower()


@pytest.mark.skipif(not DB_AVAILABLE, reason="Database unavailable")
@pytest.mark.django_db(transaction=True)
class TestCapsuleRegistryDB:
    def test_discover_capsules(self):
        from apps.capsules.models import Capsule
        from apps.capsules.services.capsule_registry import discover_capsules

        Capsule.objects.create(
            name="discoverable",
            version="1.0.0",
            tenant_id="test",
            realm="default",
            status=Capsule.STATUS_ACTIVE,
        )

        results = discover_capsules("test", "default")
        assert len(results) == 1
        assert results[0]["name"] == "discoverable"

    def test_discover_public_capsules(self):
        from apps.capsules.models import Capsule
        from apps.capsules.services.capsule_registry import discover_capsules

        Capsule.objects.create(
            name="public-capsule",
            version="1.0.0",
            tenant_id="public",
            realm="default",
            status=Capsule.STATUS_ACTIVE,
        )

        results = discover_capsules("other-tenant", "default")
        assert any(c["name"] == "public-capsule" for c in results)
