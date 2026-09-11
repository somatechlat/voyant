"""
Approval Workflows — Django ORM models.

Provides gated approval for sensitive operations: action executions,
model deployments, policy changes, and data exports.

All models inherit TenantModel for multi-tenancy and UUIDModel for
consistent primary keys, following the enterprise patterns established
in apps/core/models.py.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone as tz

from apps.core.models import TenantModel, UUIDModel


class ApprovalRequest(TenantModel, UUIDModel):
    """
    A request for approval before a sensitive operation can proceed.

    Covers action execution gating, model deployment to production,
    policy changes, and data exports.
    """

    class RequestType(models.TextChoices):
        ACTION_EXECUTION = "action_execution", "Action Execution"
        MODEL_DEPLOYMENT = "model_deployment", "Model Deployment"
        POLICY_CHANGE = "policy_change", "Policy Change"
        DATA_EXPORT = "data_export", "Data Export"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"

    request_type = models.CharField(
        max_length=32,
        choices=RequestType.choices,
        db_index=True,
        help_text="Category of operation requiring approval",
    )
    resource_type = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Type of the resource being acted upon (e.g. 'ActionType', 'ModelVersion')",
    )
    resource_id = models.CharField(
        max_length=256,
        db_index=True,
        help_text="Identifier of the specific resource",
    )
    requester_id = models.CharField(
        max_length=256,
        db_index=True,
        help_text="User or service that initiated the request",
    )
    approver_id = models.CharField(
        max_length=256,
        blank=True,
        default="",
        db_index=True,
        help_text="User who approved or rejected the request",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason for approval, rejection, or request context",
    )
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the request was approved or rejected",
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Optional expiration — pending requests past this are auto-expired",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary context payload (action params, model metrics, etc.)",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "approval_request"
        indexes = [
            models.Index(
                fields=["tenant_id", "status", "-created_at"],
                name="idx_appr_tenant_status_created",
            ),
            models.Index(
                fields=["tenant_id", "requester_id"],
                name="idx_appr_tenant_requester",
            ),
            models.Index(
                fields=["tenant_id", "request_type"],
                name="idx_appr_tenant_type",
            ),
            models.Index(
                fields=["resource_type", "resource_id"],
                name="idx_appr_resource",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Approval({self.request_type} {self.resource_type}:{self.resource_id} "
            f"[{self.status}])"
        )

    @property
    def is_pending(self) -> bool:
        return self.status == self.Status.PENDING

    @property
    def is_expired(self) -> bool:
        if self.status != self.Status.PENDING:
            return False
        if self.expires_at and self.expires_at < tz.now():
            return True
        return False


class ApprovalRule(TenantModel, UUIDModel):
    """
    Configurable rule that determines when and how approvals are required.

    Rules are matched by ``request_type``. Auto-approve conditions allow
    bypassing the approval flow when specific JSON-field criteria are met
    (e.g. low-risk actions, non-production stages).
    """

    name = models.CharField(
        max_length=255,
        help_text="Human-readable rule name",
    )
    request_type = models.CharField(
        max_length=32,
        db_index=True,
        help_text="ApprovalRequest.RequestType this rule applies to",
    )
    auto_approve_conditions = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Conditions for auto-approval: '
            '{"max_risk_score": 3, "allowed_stages": ["staging"], "tags": ["low-risk"]}'
        ),
    )
    required_approvers_count = models.PositiveIntegerField(
        default=1,
        help_text="Number of distinct approvers required (currently only 1 is enforced)",
    )
    escalation_timeout_hours = models.PositiveIntegerField(
        default=24,
        help_text="Hours before a pending request is escalated / expired",
    )
    enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Disabled rules are skipped during evaluation",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "approval_rule"
        indexes = [
            models.Index(
                fields=["tenant_id", "request_type", "enabled"],
                name="idx_appr_rule_tenant_type",
            ),
        ]

    def __str__(self) -> str:
        return f"Rule({self.name} [{self.request_type}] enabled={self.enabled})"
