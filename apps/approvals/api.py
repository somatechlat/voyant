"""Approval Workflows API — REST endpoints for approval requests and rules."""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.approvals.models import ApprovalRequest, ApprovalRule
from apps.approvals.services import ApprovalService
from apps.core.middleware import get_tenant_id
from apps.core.security.auth import get_current_user, require_permission

logger = logging.getLogger(__name__)

approval_router = Router(tags=["approvals"], auth=require_permission("read:*"))


# ── Approval Requests ────────────────────────────────────────────────────────


@approval_router.get("")
def list_pending_approvals(request):
    """
    List pending approval requests for the current user.

    Returns approvals where the current user is the requester or
    where the user could act as an approver (all pending in the tenant).
    """
    tenant_id = get_tenant_id(request)
    user = get_current_user(request)

    qs = ApprovalRequest.objects.filter(
        tenant_id=tenant_id,
        status=ApprovalRequest.Status.PENDING,
    ).order_by("-created_at")

    # If not admin, show only requests the user made or can approve
    if "voyant-admin" not in user.roles:
        qs = qs.filter(requester_id=user.user_id)

    return [
        _serialize_request(r)
        for r in qs[:100]
    ]


@approval_router.post("", auth=require_permission("write:approvals"))
def create_approval_request(request, payload: dict[str, Any]):
    """
    Create a new approval request.

    Body:
        request_type: action_execution | model_deployment | policy_change | data_export
        resource_type: Type of resource (e.g. 'ActionType')
        resource_id: UUID of the resource
        reason: (optional) Why approval is needed
        metadata: (optional) Arbitrary context data
    """
    tenant_id = get_tenant_id(request)
    user = get_current_user(request)

    request_type = payload.get("request_type")
    if not request_type:
        raise HttpError(400, "request_type is required")

    valid_types = [c[0] for c in ApprovalRequest.RequestType.choices]
    if request_type not in valid_types:
        raise HttpError(400, f"Invalid request_type. Valid: {valid_types}")

    resource_type = payload.get("resource_type", "")
    resource_id = payload.get("resource_id", "")
    if not resource_type or not resource_id:
        raise HttpError(400, "resource_type and resource_id are required")

    approval = ApprovalService.create_request(
        tenant_id=tenant_id,
        request_type=request_type,
        resource_type=resource_type,
        resource_id=resource_id,
        requester_id=user.user_id,
        reason=payload.get("reason", ""),
        metadata=payload.get("metadata", {}),
    )

    return _serialize_request(approval)


@approval_router.put(
    "/{approval_id}/approve",
    auth=require_permission("write:approvals"),
)
def approve_request(request, approval_id: str, payload: dict[str, Any] | None = None):
    """
    Approve a pending approval request.

    Body (optional):
        reason: Approver's note
    """
    tenant_id = get_tenant_id(request)
    user = get_current_user(request)

    try:
        approval = ApprovalService.approve(
            tenant_id=tenant_id,
            request_id=approval_id,
            approver_id=user.user_id,
            reason=(payload or {}).get("reason", ""),
        )
    except ApprovalRequest.DoesNotExist:
        raise HttpError(404, "Approval request not found")
    except ValueError as exc:
        raise HttpError(400, str(exc))

    return _serialize_request(approval)


@approval_router.put(
    "/{approval_id}/reject",
    auth=require_permission("write:approvals"),
)
def reject_request(request, approval_id: str, payload: dict[str, Any]):
    """
    Reject a pending approval request.

    Body:
        reason: (recommended) Why the request is being rejected
    """
    tenant_id = get_tenant_id(request)
    user = get_current_user(request)

    try:
        approval = ApprovalService.reject(
            tenant_id=tenant_id,
            request_id=approval_id,
            approver_id=user.user_id,
            reason=payload.get("reason", ""),
        )
    except ApprovalRequest.DoesNotExist:
        raise HttpError(404, "Approval request not found")
    except ValueError as exc:
        raise HttpError(400, str(exc))

    return _serialize_request(approval)


@approval_router.get("/history")
def list_approval_history(request):
    """
    List approval history (audit trail).

    Returns all resolved (approved/rejected/expired) requests for the tenant.
    """
    tenant_id = get_tenant_id(request)

    qs = ApprovalRequest.objects.filter(
        tenant_id=tenant_id,
    ).exclude(
        status=ApprovalRequest.Status.PENDING,
    ).order_by("-approved_at")[:200]

    return [
        _serialize_request(r)
        for r in qs
    ]


# ── Approval Rules ───────────────────────────────────────────────────────────


@approval_router.get("/rules")
def list_rules(request):
    """List all approval rules for the tenant."""
    tenant_id = get_tenant_id(request)

    rules = ApprovalRule.objects.filter(tenant_id=tenant_id).order_by("-created_at")
    return [
        _serialize_rule(r)
        for r in rules
    ]


@approval_router.post(
    "/rules",
    auth=require_permission("write:approvals"),
)
def create_rule(request, payload: dict[str, Any]):
    """
    Create a new approval rule.

    Body:
        name: Human-readable rule name
        request_type: ApprovalRequest.RequestType this rule applies to
        auto_approve_conditions: (optional) JSON conditions for auto-approval
        required_approvers_count: (optional, default 1)
        escalation_timeout_hours: (optional, default 24)
        enabled: (optional, default true)
    """
    tenant_id = get_tenant_id(request)

    name = payload.get("name", "")
    request_type = payload.get("request_type", "")
    if not name or not request_type:
        raise HttpError(400, "name and request_type are required")

    valid_types = [c[0] for c in ApprovalRequest.RequestType.choices]
    if request_type not in valid_types:
        raise HttpError(400, f"Invalid request_type. Valid: {valid_types}")

    rule = ApprovalRule.objects.create(
        tenant_id=tenant_id,
        name=name,
        request_type=request_type,
        auto_approve_conditions=payload.get("auto_approve_conditions", {}),
        required_approvers_count=payload.get("required_approvers_count", 1),
        escalation_timeout_hours=payload.get("escalation_timeout_hours", 24),
        enabled=payload.get("enabled", True),
    )

    return _serialize_rule(rule)


# ── Serializers ──────────────────────────────────────────────────────────────


def _serialize_request(r: ApprovalRequest) -> dict[str, Any]:
    """Serialize an ApprovalRequest to a dict."""
    return {
        "id": str(r.id),
        "request_type": r.request_type,
        "resource_type": r.resource_type,
        "resource_id": r.resource_id,
        "requester_id": r.requester_id,
        "approver_id": r.approver_id,
        "status": r.status,
        "reason": r.reason,
        "approved_at": r.approved_at.isoformat() if r.approved_at else None,
        "expires_at": r.expires_at.isoformat() if r.expires_at else None,
        "metadata": r.metadata,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


def _serialize_rule(r: ApprovalRule) -> dict[str, Any]:
    """Serialize an ApprovalRule to a dict."""
    return {
        "id": str(r.id),
        "name": r.name,
        "request_type": r.request_type,
        "auto_approve_conditions": r.auto_approve_conditions,
        "required_approvers_count": r.required_approvers_count,
        "escalation_timeout_hours": r.escalation_timeout_hours,
        "enabled": r.enabled,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }
