"""
Action Execution Engine — ONT-F-027 / ONT-F-028.

Executes ActionType definitions against Object instances with:
  - Parameter validation against the action's JSON schema
  - Pre-condition rule checking (status, fields, permissions)
  - Post-execution side effects (audit log, webhooks, field updates)
  - Undo support via recorded previous state

All methods enforce tenant isolation and follow the project's
TenantModel / UUIDModel patterns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx
from django.db import models, transaction

from apps.core.models import AuditLog, TenantModel, UUIDModel
from apps.ontology.models import ActionType, Object

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Execution history model
# ---------------------------------------------------------------------------


class ActionExecution(TenantModel, UUIDModel):
    """
    Records each action execution for undo support and audit trail.

    ONT-F-028: Stores previous_values so that undo can revert changes.
    """

    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_UNDONE = "undone"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_UNDONE, "Undone"),
    ]

    action_type = models.ForeignKey(
        ActionType,
        on_delete=models.PROTECT,
        related_name="executions",
    )
    target_object = models.ForeignKey(
        Object,
        on_delete=models.PROTECT,
        related_name="action_executions",
    )
    params = models.JSONField(default=dict, blank=True)
    previous_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of object properties before execution (for undo)",
    )
    changes = models.JSONField(
        default=dict,
        blank=True,
        help_text="Diff of changes applied during execution",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS)
    actor = models.CharField(max_length=256, blank=True, default="")
    errors = models.JSONField(default=list, blank=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_action_execution"
        indexes = [
            models.Index(
                fields=["tenant_id", "action_type_id"],
                name="idx_exec_tenant_action",
            ),
            models.Index(
                fields=["tenant_id", "target_object_id"],
                name="idx_exec_tenant_obj",
            ),
        ]

    def __str__(self) -> str:
        return f"Execution({self.action_type_id} on {self.target_object_id} [{self.status}])"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ActionResult:
    """Result returned by ActionExecutor.execute()."""

    success: bool
    action_id: str | None = None
    object_id: str | None = None
    changes: dict[str, Any] = field(default_factory=dict)
    side_effects_executed: list[str] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)


@dataclass
class UndoResult:
    """Result returned by ActionExecutor.undo()."""

    success: bool
    action_id: str | None = None
    object_id: str | None = None
    reverted_fields: list[str] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Permission checker hook
# ---------------------------------------------------------------------------


def default_permission_check(tenant_id: str, actor: str, permission: str) -> bool:
    """
    Stub permission checker. Always returns True.

    Replace with SpiceDB / Authzed integration when auth layer is ready.
    ONT-F-027: permission_check rule delegates here.
    """
    return True


# ---------------------------------------------------------------------------
# ActionExecutor
# ---------------------------------------------------------------------------


class ActionExecutor:
    """
    Central engine for executing ActionType operations on Object instances.

    ONT-F-027: Validates params → checks pre-condition rules → applies
    side effects → records execution for undo.

    Usage::

        executor = ActionExecutor()
        result = executor.execute(tenant_id, action_type_id, object_id, params)
    """

    # Allow overriding for testing
    permission_checker: Any = default_permission_check

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute(
        self,
        tenant_id: str,
        action_type_id: str,
        object_id: str,
        params: dict[str, Any],
        *,
        actor: str = "",
    ) -> ActionResult:
        """
        ONT-F-027: Execute an action on an object instance.

        Steps:
          1. Load ActionType (must be active) and Object (must exist).
          2. Validate parameters against the action's parameter schema.
          3. Check pre-condition rules against the object.
          4. Record previous state, apply changes, run side effects.

        Args:
            tenant_id: Tenant identifier for isolation.
            action_type_id: UUID of the ActionType to execute.
            object_id: UUID of the target Object.
            params: User-supplied parameters.
            actor: User or service performing the action.

        Returns:
            ActionResult with success flag, changes, and any errors.
        """
        # 1. Load and validate action type + target object
        action_type, error = self._load_action_type(tenant_id, action_type_id)
        if error:
            return ActionResult(success=False, errors=[error])

        obj, error = self._load_object(tenant_id, object_id)
        if error:
            return ActionResult(success=False, errors=[error])

        # 2. Validate params
        param_errors = self.validate_params(action_type, params)
        if param_errors:
            return ActionResult(success=False, errors=param_errors)

        # 3. Check pre-condition rules
        violations = self.check_rules(action_type, obj, tenant_id=tenant_id, actor=actor)
        if violations:
            return ActionResult(success=False, errors=violations)

        # 4. Snapshot, apply, execute side effects, record
        return self._commit_execution(
            tenant_id, action_type, obj, params, actor=actor,
        )

    def validate_params(
        self,
        action_type: ActionType,
        params: dict[str, Any],
    ) -> list[dict[str, str]]:
        """
        ONT-F-027: Validate user-supplied parameters against the action's schema.

        The ``parameters`` field on ActionType is a list of param definitions:
        ``[{"name": "reason", "type": "string", "required": true}, ...]``

        Returns:
            List of error dicts. Empty list means validation passed.
        """
        errors: list[dict[str, str]] = []
        schema: list[dict[str, Any]] = action_type.parameters or []

        for param_def in schema:
            name = param_def.get("name", "")
            param_type = param_def.get("type", "string")
            required = param_def.get("required", False)
            value = params.get(name)

            # Required check
            if value is None:
                if required:
                    errors.append({
                        "field": name,
                        "code": "required",
                        "message": f"Parameter '{name}' is required",
                    })
                continue

            # Type check
            type_ok = _check_param_type(value, param_type)
            if not type_ok:
                errors.append({
                    "field": name,
                    "code": "invalid_type",
                    "message": f"Parameter '{name}' expects {param_type}, got {type(value).__name__}",
                })

        return errors

    def check_rules(
        self,
        action_type: ActionType,
        obj: Object,
        *,
        tenant_id: str = "",
        actor: str = "",
    ) -> list[dict[str, str]]:
        """
        ONT-F-027: Check pre-condition rules against the target object.

        Supported rule types:
          - status_check: object.properties[field] == value
          - field_exists:  required field is present in object.properties
          - field_value:   object.properties[field] == expected value
          - permission_check: caller has the required_permission

        Returns:
            List of violation dicts. Empty list means all rules passed.
        """
        violations: list[dict[str, str]] = []
        rules: list[dict[str, Any]] = action_type.rules or []

        for rule in rules:
            rule_type = rule.get("type", "")
            handler = _RULE_HANDLERS.get(rule_type)
            if handler is None:
                violations.append({
                    "code": "unknown_rule",
                    "message": f"Unknown rule type '{rule_type}'",
                })
                continue

            result = handler(
                rule=rule,
                obj=obj,
                action_type=action_type,
                tenant_id=tenant_id,
                actor=actor,
                permission_checker=self.permission_checker,
            )
            if result is not None:
                violations.append(result)

        return violations

    def execute_side_effects(
        self,
        action_type: ActionType,
        obj: Object,
        changes: dict[str, Any],
        *,
        tenant_id: str = "",
        actor: str = "",
    ) -> list[str]:
        """
        ONT-F-027: Execute post-action side effects.

        Supported side effect types:
          - notification: log a notification event (stub)
          - webhook: POST to a URL via httpx
          - audit_log: write to AuditLog model
          - field_update: update additional object properties

        Returns:
            List of side effect type names that were executed.
        """
        executed: list[str] = []
        effects: list[dict[str, Any]] = action_type.side_effects or []

        for effect in effects:
            effect_type = effect.get("type", "")
            handler = _SIDE_EFFECT_HANDLERS.get(effect_type)
            if handler is None:
                logger.warning("Unknown side effect type '%s', skipping", effect_type)
                continue

            try:
                handler(
                    effect=effect,
                    action_type=action_type,
                    obj=obj,
                    changes=changes,
                    tenant_id=tenant_id,
                    actor=actor,
                )
                executed.append(effect_type)
            except Exception:
                logger.exception("Side effect '%s' failed for action %s", effect_type, action_type.id)

        return executed

    def undo(
        self,
        tenant_id: str,
        action_id: str,
    ) -> UndoResult:
        """
        ONT-F-028: Undo a previously executed action.

        Only works if the action type is undoable and the execution
        record is in 'success' status.

        Args:
            tenant_id: Tenant identifier for isolation.
            action_id: UUID of the ActionExecution to undo.

        Returns:
            UndoResult with success flag and reverted field names.
        """
        try:
            execution = ActionExecution.objects.get(
                tenant_id=tenant_id,
                id=action_id,
            )
        except ActionExecution.DoesNotExist:
            return UndoResult(
                success=False,
                errors=[{"code": "not_found", "message": "Action execution not found"}],
            )

        if execution.status == ActionExecution.STATUS_UNDONE:
            return UndoResult(
                success=False,
                action_id=action_id,
                errors=[{"code": "already_undone", "message": "Action has already been undone"}],
            )

        if execution.status != ActionExecution.STATUS_SUCCESS:
            return UndoResult(
                success=False,
                action_id=action_id,
                errors=[{"code": "invalid_status", "message": f"Cannot undo execution with status '{execution.status}'"}],
            )

        action_type = execution.action_type
        if not action_type.undoable:
            return UndoResult(
                success=False,
                action_id=action_id,
                errors=[{"code": "not_undoable", "message": "This action type does not support undo"}],
            )

        # Apply undo rules
        reverted_fields: list[str] = []
        undo_rules: list[dict[str, Any]] = action_type.undo_rules or []
        obj = execution.target_object

        with transaction.atomic():
            for rule in undo_rules:
                rule_type = rule.get("type", "")
                handler = _UNDO_HANDLERS.get(rule_type)
                if handler is None:
                    logger.warning("Unknown undo rule type '%s', skipping", rule_type)
                    continue

                reverted = handler(
                    rule=rule,
                    obj=obj,
                    execution=execution,
                )
                reverted_fields.extend(reverted)

            # If no explicit undo rules, fall back to full property revert
            if not undo_rules:
                reverted_fields = self._full_revert(obj, execution)

            obj.version += 1
            obj.save(update_fields=["properties", "version", "updated_at"])

            execution.status = ActionExecution.STATUS_UNDONE
            execution.save(update_fields=["status", "updated_at"])

        logger.info(
            "Undone action execution %s on %s/%s (reverted: %s)",
            action_id, tenant_id, execution.target_object_id, reverted_fields,
        )

        return UndoResult(
            success=True,
            action_id=action_id,
            object_id=str(execution.target_object_id),
            reverted_fields=reverted_fields,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_action_type(
        tenant_id: str,
        action_type_id: str,
    ) -> tuple[ActionType | None, dict[str, str] | None]:
        """Load an active ActionType or return an error dict."""
        try:
            at = ActionType.objects.get(
                tenant_id=tenant_id,
                id=action_type_id,
                deleted_at__isnull=True,
            )
        except ActionType.DoesNotExist:
            return None, {"code": "not_found", "message": "ActionType not found"}
        if at.status != ActionType.STATUS_ACTIVE:
            return None, {
                "code": "inactive",
                "message": f"ActionType status is '{at.status}'",
            }
        return at, None

    @staticmethod
    def _load_object(
        tenant_id: str,
        object_id: str,
    ) -> tuple[Object | None, dict[str, str] | None]:
        """Load an Object or return an error dict."""
        try:
            obj = Object.objects.get(
                tenant_id=tenant_id,
                id=object_id,
                deleted_at__isnull=True,
            )
        except Object.DoesNotExist:
            return None, {"code": "not_found", "message": "Target object not found"}
        return obj, None

    def _commit_execution(
        self,
        tenant_id: str,
        action_type: ActionType,
        obj: Object,
        params: dict[str, Any],
        *,
        actor: str = "",
    ) -> ActionResult:
        """Snapshot previous state, apply changes, run side effects, record."""
        with transaction.atomic():
            previous_values = dict(obj.properties)
            changes = self._apply_params_to_object(obj, params)
            obj.version += 1
            obj.save(update_fields=["properties", "version", "updated_at"])

            side_effects_run = self.execute_side_effects(
                action_type, obj, changes, tenant_id=tenant_id, actor=actor,
            )

            execution = ActionExecution.objects.create(
                tenant_id=tenant_id,
                action_type=action_type,
                target_object=obj,
                params=params,
                previous_values=previous_values,
                changes=changes,
                status=ActionExecution.STATUS_SUCCESS,
                actor=actor,
            )

        logger.info(
            "Executed action %s on %s/%s (execution=%s)",
            action_type.name, tenant_id, str(obj.id), execution.id,
        )
        return ActionResult(
            success=True,
            action_id=str(execution.id),
            object_id=str(obj.id),
            changes=changes,
            side_effects_executed=side_effects_run,
        )

    @staticmethod
    def _apply_params_to_object(
        obj: Object,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Merge relevant param values into object properties.

        Only keys that exist in ``params`` and are meant for the object
        (i.e. top-level scalar values) are merged. Returns the diff of
        what actually changed.
        """
        changes: dict[str, Any] = {}
        for key, value in params.items():
            old_value = obj.properties.get(key)
            if old_value != value:
                changes[key] = {"old": old_value, "new": value}
                obj.properties[key] = value
        return changes

    @staticmethod
    def _full_revert(
        obj: Object,
        execution: ActionExecution,
    ) -> list[str]:
        """Revert all properties to the snapshot taken before execution."""
        reverted = []
        for key, old_val in execution.previous_values.items():
            current = obj.properties.get(key)
            if current != old_val:
                obj.properties[key] = old_val
                reverted.append(key)
        # Remove keys that were added during the action
        for key in list(obj.properties.keys()):
            if key not in execution.previous_values:
                del obj.properties[key]
                reverted.append(key)
        return reverted


# ---------------------------------------------------------------------------
# Parameter type checking
# ---------------------------------------------------------------------------

_PARAM_TYPE_MAP: dict[str, tuple[type, ...]] = {
    "string": (str,),
    "integer": (int,),
    "float": (float, int),
    "boolean": (bool,),
    "array": (list,),
    "object": (dict,),
}


def _check_param_type(value: Any, param_type: str) -> bool:
    """Return True if *value* matches the expected *param_type*."""
    expected = _PARAM_TYPE_MAP.get(param_type)
    if expected is None:
        return True  # Unknown type → accept anything
    return isinstance(value, expected) and not isinstance(value, bool) if param_type == "integer" else isinstance(value, expected)


# ---------------------------------------------------------------------------
# Rule handlers
# ---------------------------------------------------------------------------


def _rule_status_check(
    *, rule: dict[str, Any], obj: Object, **_: Any,
) -> dict[str, str] | None:
    """
    ONT-F-027: Verify object has expected status field value.

    Rule format: ``{"type": "status_check", "field": "status", "value": "open"}``
    Defaults to checking ``status`` property.
    """
    field_name = rule.get("field", "status")
    expected = rule.get("value")
    actual = obj.properties.get(field_name)
    if actual != expected:
        return {
            "code": "status_check_failed",
            "message": f"Expected {field_name}='{expected}', got '{actual}'",
        }
    return None


def _rule_field_exists(
    *, rule: dict[str, Any], obj: Object, **_: Any,
) -> dict[str, str] | None:
    """
    ONT-F-027: Verify required field is present in object properties.

    Rule format: ``{"type": "field_exists", "field": "assignee"}``
    """
    field_name = rule.get("field", "")
    if field_name not in obj.properties or obj.properties[field_name] is None:
        return {
            "code": "field_missing",
            "message": f"Required field '{field_name}' is missing or null",
        }
    return None


def _rule_field_value(
    *, rule: dict[str, Any], obj: Object, **_: Any,
) -> dict[str, str] | None:
    """
    ONT-F-027: Verify field matches expected value.

    Rule format: ``{"type": "field_value", "field": "priority", "value": "high"}``
    """
    field_name = rule.get("field", "")
    expected = rule.get("value")
    actual = obj.properties.get(field_name)
    if actual != expected:
        return {
            "code": "field_value_mismatch",
            "message": f"Field '{field_name}' expected '{expected}', got '{actual}'",
        }
    return None


def _rule_permission_check(
    *,
    rule: dict[str, Any],
    action_type: ActionType,
    tenant_id: str,
    actor: str,
    permission_checker: Any,
    **_: Any,
) -> dict[str, str] | None:
    """
    ONT-F-027: Verify caller has the required permission.

    Rule format: ``{"type": "permission_check"}``
    Uses ``action_type.required_permission``.
    """
    permission = action_type.required_permission
    if not permission:
        return None  # No permission required

    if not permission_checker(tenant_id, actor, permission):
        return {
            "code": "permission_denied",
            "message": f"Actor '{actor}' lacks permission '{permission}'",
        }
    return None


_RULE_HANDLERS: dict[str, Any] = {
    "status_check": _rule_status_check,
    "field_exists": _rule_field_exists,
    "field_value": _rule_field_value,
    "permission_check": _rule_permission_check,
}


# ---------------------------------------------------------------------------
# Side effect handlers
# ---------------------------------------------------------------------------


def _side_effect_notification(
    *, effect: dict[str, Any], action_type: ActionType, obj: Object, **_: Any,
) -> None:
    """
    ONT-F-027: Log a notification event (stub — no email/webhook yet).

    Side effect format: ``{"type": "notification", "channel": "email"}``
    """
    channel = effect.get("channel", "default")
    logger.info(
        "[NOTIFICATION] channel=%s action=%s object=%s",
        channel, action_type.name, obj.id,
    )


def _side_effect_webhook(
    *, effect: dict[str, Any], action_type: ActionType, obj: Object,
    changes: dict[str, Any], tenant_id: str, **_: Any,
) -> None:
    """
    ONT-F-027: Make an HTTP POST to a webhook URL via httpx.

    Side effect format: ``{"type": "webhook", "url": "https://example.com/hook"}``
    """
    url = effect.get("url", "")
    if not url:
        logger.warning("[WEBHOOK] No URL configured, skipping")
        return

    payload = {
        "action": action_type.name,
        "object_id": str(obj.id),
        "tenant_id": tenant_id,
        "changes": changes,
    }
    try:
        response = httpx.post(url, json=payload, timeout=10.0)
        response.raise_for_status()
        logger.info("[WEBHOOK] POST %s → %d", url, response.status_code)
    except httpx.HTTPError as exc:
        logger.error("[WEBHOOK] POST %s failed: %s", url, exc)
        raise


def _side_effect_audit_log(
    *, effect: dict[str, Any], action_type: ActionType, obj: Object,
    changes: dict[str, Any], tenant_id: str, actor: str, **_: Any,
) -> None:
    """
    ONT-F-027: Write an entry to the AuditLog model.

    Side effect format: ``{"type": "audit_log"}``
    """
    AuditLog.objects.create(
        tenant_id=tenant_id,
        actor=actor or "system",
        action=f"action.{action_type.name}",
        resource_type="ontology_object",
        resource_id=str(obj.id),
        outcome="success",
        details={
            "action_type_id": str(action_type.id),
            "action_type_name": action_type.name,
            "changes": changes,
        },
    )
    logger.info(
        "[AUDIT_LOG] action=%s object=%s actor=%s",
        action_type.name, obj.id, actor,
    )


def _side_effect_field_update(
    *, effect: dict[str, Any], obj: Object, tenant_id: str, **_: Any,
) -> None:
    """
    ONT-F-027: Update additional object properties from the side effect config.

    Side effect format: ``{"type": "field_update", "updates": {"reviewed": true}}``
    """
    updates = effect.get("updates", {})
    for key, value in updates.items():
        obj.properties[key] = value
    obj.save(update_fields=["properties", "updated_at"])
    logger.info(
        "[FIELD_UPDATE] object=%s updated fields: %s",
        obj.id, list(updates.keys()),
    )


_SIDE_EFFECT_HANDLERS: dict[str, Any] = {
    "notification": _side_effect_notification,
    "webhook": _side_effect_webhook,
    "audit_log": _side_effect_audit_log,
    "field_update": _side_effect_field_update,
}


# ---------------------------------------------------------------------------
# Undo rule handlers
# ---------------------------------------------------------------------------


def _undo_status_revert(
    *, rule: dict[str, Any], obj: Object, execution: ActionExecution,
) -> list[str]:
    """
    ONT-F-028: Revert object status to previous value.

    Undo rule format: ``{"type": "status_revert", "field": "status"}``
    """
    field_name = rule.get("field", "status")
    previous = execution.previous_values.get(field_name)
    if previous is not None:
        obj.properties[field_name] = previous
        return [field_name]
    return []


def _undo_field_revert(
    *, rule: dict[str, Any], obj: Object, execution: ActionExecution,
) -> list[str]:
    """
    ONT-F-028: Revert specific field changes.

    Undo rule format: ``{"type": "field_revert", "fields": ["assignee", "priority"]}``
    """
    fields = rule.get("fields", [])
    reverted: list[str] = []
    for field_name in fields:
        if field_name in execution.previous_values:
            obj.properties[field_name] = execution.previous_values[field_name]
            reverted.append(field_name)
    return reverted


_UNDO_HANDLERS: dict[str, Any] = {
    "status_revert": _undo_status_revert,
    "field_revert": _undo_field_revert,
}
