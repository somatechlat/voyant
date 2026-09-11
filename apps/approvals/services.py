"""
Approval Workflows — Business logic services.

Provides ApprovalService for creating, approving, rejecting, and
managing approval requests. Integrates with the event system for
real-time notifications.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.utils import timezone as tz

from apps.approvals.models import ApprovalRequest, ApprovalRule

logger = logging.getLogger(__name__)


class ApprovalService:
    """
    Stateless service for approval workflow operations.

    All methods accept an explicit ``tenant_id`` so they can be called
    from API views, background tasks, and integration hooks alike.
    """

    # ── Request creation ────────────────────────────────────────────────

    @staticmethod
    def create_request(
        tenant_id: str,
        request_type: str,
        resource_type: str,
        resource_id: str,
        requester_id: str,
        reason: str = "",
        metadata: dict[str, Any] | None = None,
        realm: str = "default",
    ) -> ApprovalRequest:
        """
        Create an approval request. Checks auto-approve rules first.

        Args:
            tenant_id: Tenant scope.
            request_type: One of ApprovalRequest.RequestType values.
            resource_type: Type of resource (e.g. 'ActionType', 'ModelVersion').
            resource_id: UUID of the specific resource.
            requester_id: User or service requesting the operation.
            reason: Human-readable context for the request.
            metadata: Arbitrary payload (action params, metrics, etc.).
            realm: RBAC realm.

        Returns:
            The created (or auto-approved) ApprovalRequest.
        """
        # Check if any enabled rule auto-approves this request
        auto_approved = ApprovalService.check_auto_approve(
            tenant_id=tenant_id,
            request_type=request_type,
            metadata=metadata or {},
        )

        now = tz.now()
        rule = ApprovalService._get_matching_rule(tenant_id, request_type)
        escalation_hours = rule.escalation_timeout_hours if rule else 24

        status = (
            ApprovalRequest.Status.APPROVED
            if auto_approved
            else ApprovalRequest.Status.PENDING
        )

        request = ApprovalRequest.objects.create(
            tenant_id=tenant_id,
            realm=realm,
            request_type=request_type,
            resource_type=resource_type,
            resource_id=resource_id,
            requester_id=requester_id,
            status=status,
            reason=reason,
            metadata=metadata or {},
            approved_at=now if auto_approved else None,
            expires_at=None if auto_approved else now + timedelta(hours=escalation_hours),
            approver_id="system-auto-approve" if auto_approved else "",
        )

        action = "auto-approved" if auto_approved else "created (pending)"
        logger.info(
            "Approval request %s: id=%s type=%s resource=%s:%s requester=%s",
            action,
            request.id,
            request_type,
            resource_type,
            resource_id,
            requester_id,
        )

        # Publish real-time event
        ApprovalService._publish_event(tenant_id, request, "approval.created")

        return request

    # ── Approve ─────────────────────────────────────────────────────────

    @staticmethod
    def approve(
        tenant_id: str,
        request_id: str,
        approver_id: str,
        reason: str = "",
    ) -> ApprovalRequest:
        """
        Approve a pending approval request.

        Args:
            tenant_id: Tenant scope.
            request_id: UUID of the ApprovalRequest.
            approver_id: User performing the approval.
            reason: Optional note from the approver.

        Returns:
            The updated ApprovalRequest.

        Raises:
            ApprovalRequest.DoesNotExist: If the request is not found.
            ValueError: If the request is not in pending status.
        """
        request = ApprovalRequest.objects.get(
            id=request_id,
            tenant_id=tenant_id,
        )

        if request.status != ApprovalRequest.Status.PENDING:
            raise ValueError(
                f"Cannot approve request with status '{request.status}'. "
                "Only pending requests can be approved."
            )

        now = tz.now()
        request.status = ApprovalRequest.Status.APPROVED
        request.approver_id = approver_id
        request.reason = reason or request.reason
        request.approved_at = now
        request.save(
            update_fields=[
                "status",
                "approver_id",
                "reason",
                "approved_at",
                "updated_at",
            ]
        )

        logger.info(
            "Approval request approved: id=%s approver=%s",
            request.id,
            approver_id,
        )

        ApprovalService._publish_event(tenant_id, request, "approval.approved")

        return request

    # ── Reject ──────────────────────────────────────────────────────────

    @staticmethod
    def reject(
        tenant_id: str,
        request_id: str,
        approver_id: str,
        reason: str = "",
    ) -> ApprovalRequest:
        """
        Reject a pending approval request.

        Args:
            tenant_id: Tenant scope.
            request_id: UUID of the ApprovalRequest.
            approver_id: User performing the rejection.
            reason: Required reason for rejection.

        Returns:
            The updated ApprovalRequest.

        Raises:
            ApprovalRequest.DoesNotExist: If the request is not found.
            ValueError: If the request is not in pending status.
        """
        request = ApprovalRequest.objects.get(
            id=request_id,
            tenant_id=tenant_id,
        )

        if request.status != ApprovalRequest.Status.PENDING:
            raise ValueError(
                f"Cannot reject request with status '{request.status}'. "
                "Only pending requests can be rejected."
            )

        now = tz.now()
        request.status = ApprovalRequest.Status.REJECTED
        request.approver_id = approver_id
        request.reason = reason or "Rejected without reason"
        request.approved_at = now
        request.save(
            update_fields=[
                "status",
                "approver_id",
                "reason",
                "approved_at",
                "updated_at",
            ]
        )

        logger.info(
            "Approval request rejected: id=%s approver=%s reason=%s",
            request.id,
            approver_id,
            reason,
        )

        ApprovalService._publish_event(tenant_id, request, "approval.rejected")

        return request

    # ── Auto-approve check ──────────────────────────────────────────────

    @staticmethod
    def check_auto_approve(
        tenant_id: str,
        request_type: str,
        metadata: dict[str, Any],
    ) -> bool:
        """
        Check if any enabled rule auto-approves this request based on metadata.

        Auto-approve conditions are evaluated as key-value checks against the
        metadata dict. All conditions must match (AND logic).

        Supported condition types:
          - ``max_risk_score``: metadata.risk_score <= value
          - ``allowed_stages``: metadata.stage in value list
          - ``tags``: any metadata tag intersects with value list

        Args:
            tenant_id: Tenant scope.
            request_type: ApprovalRequest.RequestType value.
            metadata: Request metadata to evaluate against conditions.

        Returns:
            True if auto-approved, False otherwise.
        """
        rule = ApprovalService._get_matching_rule(tenant_id, request_type)
        if rule is None:
            return False

        conditions = rule.auto_approve_conditions or {}
        if not conditions:
            return False

        # max_risk_score check
        if "max_risk_score" in conditions:
            risk_score = metadata.get("risk_score", 999)
            if risk_score > conditions["max_risk_score"]:
                return False

        # allowed_stages check
        if "allowed_stages" in conditions:
            stage = metadata.get("stage", "")
            if stage not in conditions["allowed_stages"]:
                return False

        # tags intersection check
        if "tags" in conditions:
            request_tags = set(metadata.get("tags", []))
            allowed_tags = set(conditions["tags"])
            if not request_tags.intersection(allowed_tags):
                return False

        logger.info(
            "Auto-approved: tenant=%s type=%s rule=%s",
            tenant_id,
            request_type,
            rule.name,
        )
        return True

    # ── Escalate expired ────────────────────────────────────────────────

    @staticmethod
    def escalate_expired(tenant_id: str) -> int:
        """
        Expire all pending requests that have passed their ``expires_at``.

        Should be called periodically (e.g. via a management command or Celery beat).

        Args:
            tenant_id: Tenant scope.

        Returns:
            Number of requests expired.
        """
        now = tz.now()
        expired = ApprovalRequest.objects.filter(
            tenant_id=tenant_id,
            status=ApprovalRequest.Status.PENDING,
            expires_at__lt=now,
        )
        count = expired.update(
            status=ApprovalRequest.Status.EXPIRED,
            reason="Automatically expired — escalation timeout reached",
            approved_at=now,
            updated_at=now,
        )

        if count:
            logger.info(
                "Expired %d pending approval requests for tenant=%s",
                count,
                tenant_id,
            )

        return count

    # ── Private helpers ─────────────────────────────────────────────────

    @staticmethod
    def _get_matching_rule(
        tenant_id: str,
        request_type: str,
    ) -> ApprovalRule | None:
        """Return the first enabled rule matching the request type, or None."""
        return (
            ApprovalRule.objects.filter(
                tenant_id=tenant_id,
                request_type=request_type,
                enabled=True,
            )
            .order_by("created_at")
            .first()
        )

    @staticmethod
    def _publish_event(
        tenant_id: str,
        request: ApprovalRequest,
        event_type: str,
    ) -> None:
        """Publish a real-time approval event via the channel layer."""
        try:
            from apps.core.events import _group, _publish

            payload = {
                "event_type": event_type,
                "approval_id": str(request.id),
                "request_type": request.request_type,
                "resource_type": request.resource_type,
                "resource_id": request.resource_id,
                "requester_id": request.requester_id,
                "approver_id": request.approver_id,
                "status": request.status,
                "created_at": request.created_at.isoformat(),
            }
            _publish(
                _group(tenant_id, "approval_events"),
                "event_approval",
                payload,
            )
        except Exception as exc:
            logger.debug("Failed to publish approval event: %s", exc)

    # ── Integration helpers ─────────────────────────────────────────────

    @staticmethod
    def request_action_approval(
        tenant_id: str,
        action_type_id: str,
        action_type_name: str,
        object_id: str,
        requester_id: str,
        params: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        """
        Convenience wrapper for creating an action execution approval request.

        Args:
            tenant_id: Tenant scope.
            action_type_id: UUID of the ActionType.
            action_type_name: Human-readable action type name.
            object_id: UUID of the target Object.
            requester_id: User requesting the action.
            params: Action parameters (stored in metadata).

        Returns:
            The created ApprovalRequest.
        """
        return ApprovalService.create_request(
            tenant_id=tenant_id,
            request_type=ApprovalRequest.RequestType.ACTION_EXECUTION,
            resource_type="ActionType",
            resource_id=action_type_id,
            requester_id=requester_id,
            reason=f"Action '{action_type_name}' requires approval before execution",
            metadata={
                "action_type_name": action_type_name,
                "target_object_id": object_id,
                "params": params or {},
            },
        )

    @staticmethod
    def request_deployment_approval(
        tenant_id: str,
        model_version_id: str,
        model_name: str,
        version: int,
        requester_id: str,
        metrics: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        """
        Convenience wrapper for creating a model deployment approval request.

        Args:
            tenant_id: Tenant scope.
            model_version_id: UUID of the ModelVersion.
            model_name: Human-readable model name.
            version: Version number.
            requester_id: User requesting the deployment.
            metrics: Model metrics (stored in metadata).

        Returns:
            The created ApprovalRequest.
        """
        return ApprovalService.create_request(
            tenant_id=tenant_id,
            request_type=ApprovalRequest.RequestType.MODEL_DEPLOYMENT,
            resource_type="ModelVersion",
            resource_id=model_version_id,
            requester_id=requester_id,
            reason=(
                f"Model '{model_name}' v{version} requires approval "
                "before deployment to production"
            ),
            metadata={
                "model_name": model_name,
                "version": version,
                "stage": "production",
                "metrics": metrics or {},
            },
        )
