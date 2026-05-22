"""
Capsule Integration Tests.

Requires PostgreSQL.  The entire module is skipped at import time if the
DB is unreachable, preventing pytest-django from attempting DB setup.
"""

from __future__ import annotations

import socket

import pytest


def _postgres_online() -> bool:
    try:
        with socket.create_connection(("localhost", 45432), timeout=2):
            return True
    except OSError:
        return False


if not _postgres_online():
    pytest.skip("PostgreSQL not reachable on localhost:45432", allow_module_level=True)

from apps.capsules.models import Capsule, CapsuleInstallation  # noqa: E402
from apps.capsules.services.capsule_core import (  # noqa: E402
    activate_capsule,
    archive_capsule,
    certify_capsule,
    create_capsule_instance,
    edit_capsule,
    suspend_capsule,
)
from apps.capsules.services.capsule_execution import (  # noqa: E402
    _check_capabilities,
    merge_parameters,
    validate_parameters,
)

pytestmark = pytest.mark.django_db(transaction=True)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

class TestCapsuleLifecycleIntegration:
    def test_certify_and_activate_flow(self):
        capsule = Capsule.objects.create(
            name="lifecycle-test",
            version="1.0.0",
            tenant_id="test-tenant",
            realm="default",
            status=Capsule.STATUS_DRAFT,
            execution_graph=[],
            parameters_schema={},
        )
        certified = certify_capsule(capsule)
        assert certified.status == Capsule.STATUS_CERTIFIED
        assert certified.registry_signature is not None
        assert certified.registry_signature.startswith("sha256:")

        activated = activate_capsule(certified)
        assert activated.status == Capsule.STATUS_ACTIVE
        assert activated.is_active is True

    def test_edit_draft_in_place(self):
        capsule = Capsule.objects.create(
            name="edit-draft",
            version="1.0.0",
            tenant_id="test-tenant",
            realm="default",
            status=Capsule.STATUS_DRAFT,
            description="original",
            execution_graph=[],
            parameters_schema={},
        )
        updated = edit_capsule(capsule, {"description": "updated"})
        assert updated.id == capsule.id
        assert updated.description == "updated"
        assert updated.version == "1.0.0"

    def test_edit_active_spawns_new_version(self):
        parent = Capsule.objects.create(
            name="edit-active",
            version="1.0.0",
            tenant_id="test-tenant",
            realm="default",
            status=Capsule.STATUS_ACTIVE,
            description="parent",
            execution_graph=[{"step_id": "s1", "action": "search"}],
            parameters_schema={},
        )
        child = edit_capsule(parent, {"description": "child"})
        assert child.id != parent.id
        assert child.version == "1.0.1"
        assert child.status == Capsule.STATUS_DRAFT
        assert child.parent_id == parent.id  # type: ignore[attr-defined]
        assert child.description == "child"

    def test_suspend_and_archive(self):
        capsule = Capsule.objects.create(
            name="suspend-archive",
            version="1.0.0",
            tenant_id="test-tenant",
            realm="default",
            status=Capsule.STATUS_ACTIVE,
            execution_graph=[],
            parameters_schema={},
        )
        suspended = suspend_capsule(capsule, reason="security review")
        assert suspended.status == Capsule.STATUS_SUSPENDED
        assert suspended.is_active is False

        archived = archive_capsule(suspended)
        assert archived.status == Capsule.STATUS_ARCHIVED
        assert archived.is_active is False

    def test_create_instance_increments_execution_count(self):
        capsule = Capsule.objects.create(
            name="instance-test",
            version="1.0.0",
            tenant_id="test-tenant",
            realm="default",
            status=Capsule.STATUS_ACTIVE,
            execution_graph=[],
            parameters_schema={},
            execution_count=5,
        )
        instance = create_capsule_instance(
            capsule=capsule,
            session_id="sess-123",
            parameter_values={"q": "test"},
            triggered_by="api",
        )
        assert instance.capsule_id == capsule.id  # type: ignore[attr-defined]
        assert instance.status == "running"
        assert instance.session_id == "sess-123"

        capsule.refresh_from_db()
        assert capsule.execution_count == 6

    def test_create_instance_rejects_non_active(self):
        capsule = Capsule.objects.create(
            name="inactive-test",
            version="1.0.0",
            tenant_id="test-tenant",
            realm="default",
            status=Capsule.STATUS_DRAFT,
            execution_graph=[],
            parameters_schema={},
        )
        with pytest.raises(ValueError) as exc:
            create_capsule_instance(capsule, "sess-1", {}, "api")
        assert "non-active" in str(exc.value)


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------

class TestCapsuleExecutionIntegration:
    def test_validate_parameters_db_capsule(self):
        capsule = Capsule.objects.create(
            name="param-test",
            version="1.0.0",
            tenant_id="test-tenant",
            realm="default",
            status=Capsule.STATUS_DRAFT,
            parameters_schema={
                "query": {"required": True, "type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            execution_graph=[],
        )
        valid, error = validate_parameters(capsule, {"query": "AI"})
        assert valid is True
        assert error is None

        valid, error = validate_parameters(capsule, {})
        assert valid is False
        assert error is not None
        assert "Missing required parameter" in error

    def test_merge_parameters_with_installation(self):
        capsule = Capsule.objects.create(
            name="merge-test",
            version="1.0.0",
            tenant_id="test-tenant",
            realm="default",
            status=Capsule.STATUS_DRAFT,
            parameters_schema={
                "format": {"default": "json"},
                "limit": {"default": 10},
            },
            execution_graph=[],
        )
        installation = CapsuleInstallation.objects.create(
            capsule=capsule,
            tenant_id="test-tenant",
            realm="default",
            parameter_overrides={"format": "pdf"},
        )
        merged = merge_parameters(capsule, installation, {"limit": 50})
        assert merged == {"format": "pdf", "limit": 50}

    def test_capability_enforcement_db_capsule(self):
        capsule = Capsule.objects.create(
            name="cap-test",
            version="1.0.0",
            tenant_id="test-tenant",
            realm="default",
            status=Capsule.STATUS_ACTIVE,
            capabilities_whitelist=["search"],
            execution_graph=[{"step_id": "s1", "action": "sql_query"}],
            parameters_schema={},
        )
        with pytest.raises(PermissionError) as exc:
            for step in capsule.execution_graph:
                _check_capabilities(capsule, step["action"])
        assert "sql_query" in str(exc.value)
