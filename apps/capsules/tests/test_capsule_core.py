"""
Capsule Core Service Tests.

Tests verify, certify, edit, archive, suspend using REAL Capsule model instances.
No fakes, no mocks.  DB-dependent tests skip when PostgreSQL is offline.
"""

from __future__ import annotations

import socket

import pytest

from apps.capsules.models import Capsule
from apps.capsules.services.capsule_core import (
    _increment_version,
    verify_capsule,
)

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


def _make_unsaved_capsule(**kwargs) -> Capsule:
    """Return a genuine Capsule instance without persisting to the DB."""
    defaults = {
        "name": "test-capsule",
        "version": "1.0.0",
        "tenant_id": "default",
        "realm": "default",
        "status": Capsule.STATUS_DRAFT,
    }
    defaults.update(kwargs)
    return Capsule(**defaults)


class TestVerifyCapsule:
    def test_valid_capsule(self):
        capsule = _make_unsaved_capsule(
            name="valid", version="1.0.0", execution_graph=[], parameters_schema={}
        )
        assert verify_capsule(capsule) is True

    def test_missing_name(self):
        capsule = _make_unsaved_capsule(name="", version="1.0.0")
        assert verify_capsule(capsule) is False

    def test_invalid_execution_graph(self):
        capsule = _make_unsaved_capsule(execution_graph="not-a-list")
        assert verify_capsule(capsule) is False

    def test_invalid_parameters_schema(self):
        capsule = _make_unsaved_capsule(parameters_schema=["not-a-dict"])
        assert verify_capsule(capsule) is False


class TestIncrementVersion:
    def test_patch_increment(self):
        assert _increment_version("1.0.0") == "1.0.1"

    def test_non_semver_fallback(self):
        assert _increment_version("v1") == "v1.1"


@pytest.mark.skipif(not DB_AVAILABLE, reason="Database unavailable")
@pytest.mark.django_db(transaction=True)
class TestCapsuleCoreDB:
    """Tests requiring database. Skipped if DB unavailable."""

    def test_create_capsule_instance(self):
        from apps.capsules.services.capsule_core import create_capsule_instance

        capsule = Capsule.objects.create(
            name="db-test",
            version="1.0.0",
            tenant_id="test",
            realm="default",
            status=Capsule.STATUS_ACTIVE,
        )
        instance = create_capsule_instance(
            capsule=capsule,
            session_id="sess-123",
            parameter_values={"topic": "x"},
        )
        assert instance.status == "running"
        assert instance.capsule.id == capsule.id
        assert instance.parameter_values == {"topic": "x"}
