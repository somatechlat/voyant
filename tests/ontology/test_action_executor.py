"""
Tests for apps.ontology.action_executor — Action Execution Engine.

Covers:
  - Parameter validation (valid, missing required, wrong type)
  - Rule checking (status_check, field_exists, field_value, permission)
  - Full execution flow (success, rule violation, permission denied)
  - Side effects (audit_log, field_update)
  - Undo support (success, not undoable, already undone)

Uses real DB via @pytest.mark.django_db (integration tests).

ONT-F-027: Action execution
ONT-F-028: Undo support
"""

from __future__ import annotations

import uuid

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.django_db,
]

from apps.core.models import AuditLog  # noqa: E402
from apps.ontology.action_executor import (  # noqa: E402
    ActionExecutor,
)
from apps.ontology.models import ActionType, Object  # noqa: E402
from apps.ontology.services import ObjectTypeService  # noqa: E402

TENANT = "test-tenant-action"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def executor():
    """Return a fresh ActionExecutor instance."""
    return ActionExecutor()


@pytest.fixture
def object_type(db):
    """Create an ObjectType with properties suitable for action tests."""
    ot = ObjectTypeService.create(
        TENANT,
        name="Ticket",
        description="A support ticket",
        properties=[
            {"name": "title", "property_type": "string", "required": True},
            {"name": "status", "property_type": "string", "required": True, "default_value": "open"},
            {"name": "priority", "property_type": "string", "default_value": "low"},
            {"name": "assignee", "property_type": "string"},
        ],
    )
    return ot


@pytest.fixture
def ticket(object_type):
    """Create a Ticket object instance."""
    obj = Object.objects.create(
        tenant_id=TENANT,
        object_type=object_type,
        properties={"title": "Fix login", "status": "open", "priority": "low"},
        version=1,
    )
    return obj


@pytest.fixture
def active_action(object_type):
    """Create an active ActionType with params, rules, and side effects."""
    at = ActionType.objects.create(
        tenant_id=TENANT,
        name="assign_ticket",
        status=ActionType.STATUS_ACTIVE,
        target_object_type=object_type,
        parameters=[
            {"name": "assignee", "type": "string", "required": True},
            {"name": "priority", "type": "string", "required": False},
        ],
        rules=[
            {"type": "status_check", "field": "status", "value": "open"},
            {"type": "field_exists", "field": "title"},
        ],
        side_effects=[
            {"type": "audit_log"},
        ],
        undoable=True,
        undo_rules=[
            {"type": "field_revert", "fields": ["assignee"]},
        ],
        required_permission="ticket.assign",
    )
    return at


@pytest.fixture
def draft_action(object_type):
    """Create a draft (inactive) ActionType."""
    return ActionType.objects.create(
        tenant_id=TENANT,
        name="draft_action",
        status=ActionType.STATUS_DRAFT,
        target_object_type=object_type,
    )


# =========================================================================
# Parameter Validation
# =========================================================================


class TestValidateParams:
    """ONT-F-027: Validate action parameters against schema."""

    def test_valid_params(self, executor, active_action):
        """All required params present with correct types → no errors."""
        errors = executor.validate_params(active_action, {"assignee": "alice"})
        assert errors == []

    def test_valid_params_with_optional(self, executor, active_action):
        """Required + optional params → no errors."""
        errors = executor.validate_params(
            active_action, {"assignee": "alice", "priority": "high"},
        )
        assert errors == []

    def test_missing_required_param(self, executor, active_action):
        """Missing required param → error on that field."""
        errors = executor.validate_params(active_action, {})
        assert len(errors) == 1
        assert errors[0]["field"] == "assignee"
        assert errors[0]["code"] == "required"

    def test_wrong_type_param(self, executor, active_action):
        """Wrong param type → error."""
        errors = executor.validate_params(active_action, {"assignee": 123})
        assert len(errors) == 1
        assert errors[0]["field"] == "assignee"
        assert errors[0]["code"] == "invalid_type"

    def test_no_params_schema(self, executor, draft_action):
        """ActionType with empty params schema → anything accepted."""
        errors = executor.validate_params(draft_action, {"random": "data"})
        assert errors == []


# =========================================================================
# Rule Checking
# =========================================================================


class TestCheckRules:
    """ONT-F-027: Pre-condition rule checking."""

    def test_status_check_pass(self, executor, active_action, ticket):
        """Object status matches expected value → no violations."""
        violations = executor.check_rules(active_action, ticket, tenant_id=TENANT)
        assert violations == []

    def test_status_check_fail(self, executor, active_action, object_type):
        """Object status does NOT match → violation reported."""
        obj = Object.objects.create(
            tenant_id=TENANT,
            object_type=object_type,
            properties={"title": "Done ticket", "status": "closed"},
            version=1,
        )
        violations = executor.check_rules(active_action, obj, tenant_id=TENANT)
        assert len(violations) == 1
        assert violations[0]["code"] == "status_check_failed"

    def test_field_exists_pass(self, executor, active_action, ticket):
        """Required field present → no violations."""
        violations = executor.check_rules(active_action, ticket, tenant_id=TENANT)
        assert violations == []

    def test_field_exists_fail(self, executor, active_action, object_type):
        """Required field missing → violation reported."""
        obj = Object.objects.create(
            tenant_id=TENANT,
            object_type=object_type,
            properties={"status": "open"},  # no 'title'
            version=1,
        )
        violations = executor.check_rules(active_action, obj, tenant_id=TENANT)
        assert any(v["code"] == "field_missing" for v in violations)

    def test_permission_denied(self, executor, object_type, ticket):
        """Permission check fails when checker returns False."""
        action = ActionType.objects.create(
            tenant_id=TENANT,
            name="restricted_action",
            status=ActionType.STATUS_ACTIVE,
            target_object_type=object_type,
            rules=[{"type": "permission_check"}],
            required_permission="admin.destroy",
        )

        def deny_all(tenant_id, actor, permission):
            return False

        executor.permission_checker = deny_all
        violations = executor.check_rules(action, ticket, tenant_id=TENANT, actor="eve")
        assert len(violations) == 1
        assert violations[0]["code"] == "permission_denied"


# =========================================================================
# Execute Action
# =========================================================================


class TestExecute:
    """ONT-F-027: Full action execution flow."""

    def test_execute_success(self, executor, active_action, ticket):
        """Happy path: valid params, rules pass → success with changes."""
        result = executor.execute(
            TENANT, str(active_action.id), str(ticket.id),
            {"assignee": "alice"}, actor="admin",
        )
        assert result.success is True
        assert result.action_id is not None
        assert result.object_id == str(ticket.id)
        assert "assignee" in result.changes
        assert result.changes["assignee"]["new"] == "alice"
        assert "audit_log" in result.side_effects_executed

    def test_execute_rule_violation(self, executor, active_action, object_type):
        """Status check fails → ActionResult with error, no changes."""
        obj = Object.objects.create(
            tenant_id=TENANT,
            object_type=object_type,
            properties={"title": "Closed", "status": "closed"},
            version=1,
        )
        result = executor.execute(
            TENANT, str(active_action.id), str(obj.id),
            {"assignee": "bob"},
        )
        assert result.success is False
        assert any(e["code"] == "status_check_failed" for e in result.errors)
        assert result.action_id is None

    def test_execute_permission_denied(self, executor, object_type, ticket):
        """Permission check fails → ActionResult with denied error."""
        action = ActionType.objects.create(
            tenant_id=TENANT,
            name="admin_only",
            status=ActionType.STATUS_ACTIVE,
            target_object_type=object_type,
            parameters=[{"name": "reason", "type": "string", "required": True}],
            rules=[{"type": "permission_check"}],
            required_permission="super.admin",
        )

        def deny_all(tenant_id, actor, permission):
            return False

        executor.permission_checker = deny_all
        result = executor.execute(
            TENANT, str(action.id), str(ticket.id),
            {"reason": "test"}, actor="eve",
        )
        assert result.success is False
        assert any(e["code"] == "permission_denied" for e in result.errors)

    def test_execute_action_not_found(self, executor):
        """Non-existent ActionType → not_found error."""
        result = executor.execute(
            TENANT, str(uuid.uuid4()), str(uuid.uuid4()), {},
        )
        assert result.success is False
        assert result.errors[0]["code"] == "not_found"

    def test_execute_inactive_action(self, executor, draft_action, ticket):
        """Draft action → inactive error."""
        result = executor.execute(
            TENANT, str(draft_action.id), str(ticket.id), {},
        )
        assert result.success is False
        assert result.errors[0]["code"] == "inactive"


# =========================================================================
# Side Effects
# =========================================================================


class TestSideEffects:
    """ONT-F-027: Post-execution side effects."""

    @pytest.mark.django_db
    def test_audit_log_side_effect(self, executor, active_action, ticket):
        """audit_log side effect creates an AuditLog entry."""
        executor.execute(
            TENANT, str(active_action.id), str(ticket.id),
            {"assignee": "alice"}, actor="admin",
        )
        log = AuditLog.objects.filter(
            tenant_id=TENANT,
            action__startswith="action.",
        ).order_by("-created_at").first()
        assert log is not None
        assert log.actor == "admin"
        assert log.resource_type == "ontology_object"
        assert log.resource_id == str(ticket.id)
        assert log.outcome == "success"

    @pytest.mark.django_db
    def test_field_update_side_effect(self, executor, object_type, ticket):
        """field_update side effect modifies additional object properties."""
        action = ActionType.objects.create(
            tenant_id=TENANT,
            name="close_ticket",
            status=ActionType.STATUS_ACTIVE,
            target_object_type=object_type,
            parameters=[{"name": "assignee", "type": "string", "required": True}],
            rules=[{"type": "status_check", "field": "status", "value": "open"}],
            side_effects=[
                {"type": "field_update", "updates": {"reviewed": True, "reviewer": "system"}},
            ],
            undoable=True,
            undo_rules=[{"type": "status_revert"}],
        )
        result = executor.execute(
            TENANT, str(action.id), str(ticket.id),
            {"assignee": "bob"}, actor="admin",
        )
        assert result.success is True
        # Refresh from DB
        ticket.refresh_from_db()
        assert ticket.properties["reviewed"] is True
        assert ticket.properties["reviewer"] == "system"

    @pytest.mark.django_db
    def test_notification_side_effect_logs(self, executor, object_type, ticket):
        """notification side effect runs without error (logs only)."""
        action = ActionType.objects.create(
            tenant_id=TENANT,
            name="notify_action",
            status=ActionType.STATUS_ACTIVE,
            target_object_type=object_type,
            side_effects=[{"type": "notification", "channel": "email"}],
        )
        result = executor.execute(
            TENANT, str(action.id), str(ticket.id), {},
        )
        assert result.success is True
        assert "notification" in result.side_effects_executed


# =========================================================================
# Undo Support
# =========================================================================


class TestUndo:
    """ONT-F-028: Undo action execution."""

    def test_undo_success(self, executor, active_action, ticket):
        """Undo a successful action → reverts assigned fields."""
        result = executor.execute(
            TENANT, str(active_action.id), str(ticket.id),
            {"assignee": "alice"}, actor="admin",
        )
        assert result.success is True

        undo_result = executor.undo(TENANT, result.action_id)
        assert undo_result.success is True
        assert "assignee" in undo_result.reverted_fields

        # Verify object was reverted
        ticket.refresh_from_db()
        assert ticket.properties.get("assignee") is None

    def test_undo_not_undoable(self, executor, object_type, ticket):
        """ActionType with undoable=False → error."""
        action = ActionType.objects.create(
            tenant_id=TENANT,
            name="permanent_action",
            status=ActionType.STATUS_ACTIVE,
            target_object_type=object_type,
            undoable=False,
        )
        result = executor.execute(
            TENANT, str(action.id), str(ticket.id), {},
        )
        assert result.success is True

        undo_result = executor.undo(TENANT, result.action_id)
        assert undo_result.success is False
        assert undo_result.errors[0]["code"] == "not_undoable"

    def test_undo_already_undone(self, executor, active_action, ticket):
        """Undoing the same action twice → already_undone error."""
        result = executor.execute(
            TENANT, str(active_action.id), str(ticket.id),
            {"assignee": "alice"}, actor="admin",
        )
        first_undo = executor.undo(TENANT, result.action_id)
        assert first_undo.success is True

        second_undo = executor.undo(TENANT, result.action_id)
        assert second_undo.success is False
        assert second_undo.errors[0]["code"] == "already_undone"

    def test_undo_not_found(self, executor):
        """Non-existent action_id → not_found error."""
        undo_result = executor.undo(TENANT, str(uuid.uuid4()))
        assert undo_result.success is False
        assert undo_result.errors[0]["code"] == "not_found"

    @pytest.mark.django_db
    def test_undo_status_revert(self, executor, object_type, ticket):
        """status_revert undo rule restores previous status."""
        action = ActionType.objects.create(
            tenant_id=TENANT,
            name="close_with_status",
            status=ActionType.STATUS_ACTIVE,
            target_object_type=object_type,
            parameters=[{"name": "status", "type": "string", "required": True}],
            rules=[{"type": "status_check", "field": "status", "value": "open"}],
            undoable=True,
            undo_rules=[{"type": "status_revert", "field": "status"}],
        )
        result = executor.execute(
            TENANT, str(action.id), str(ticket.id),
            {"status": "closed"}, actor="admin",
        )
        assert result.success is True
        ticket.refresh_from_db()
        assert ticket.properties["status"] == "closed"

        undo_result = executor.undo(TENANT, result.action_id)
        assert undo_result.success is True
        assert "status" in undo_result.reverted_fields
        ticket.refresh_from_db()
        assert ticket.properties["status"] == "open"
