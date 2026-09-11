import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ApprovalRequest",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "realm",
                    models.CharField(
                        db_index=True,
                        default="default",
                        help_text="Realm identifier for RBAC realm isolation",
                        max_length=64,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "request_type",
                    models.CharField(
                        choices=[
                            ("action_execution", "Action Execution"),
                            ("model_deployment", "Model Deployment"),
                            ("policy_change", "Policy Change"),
                            ("data_export", "Data Export"),
                        ],
                        db_index=True,
                        help_text="Category of operation requiring approval",
                        max_length=32,
                    ),
                ),
                (
                    "resource_type",
                    models.CharField(
                        db_index=True,
                        help_text="Type of the resource being acted upon (e.g. 'ActionType', 'ModelVersion')",
                        max_length=64,
                    ),
                ),
                (
                    "resource_id",
                    models.CharField(
                        db_index=True,
                        help_text="Identifier of the specific resource",
                        max_length=256,
                    ),
                ),
                (
                    "requester_id",
                    models.CharField(
                        db_index=True,
                        help_text="User or service that initiated the request",
                        max_length=256,
                    ),
                ),
                (
                    "approver_id",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text="User who approved or rejected the request",
                        max_length=256,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("approved", "Approved"),
                            ("rejected", "Rejected"),
                            ("expired", "Expired"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "reason",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Reason for approval, rejection, or request context",
                    ),
                ),
                (
                    "approved_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Timestamp when the request was approved or rejected",
                        null=True,
                    ),
                ),
                (
                    "expires_at",
                    models.DateTimeField(
                        blank=True,
                        db_index=True,
                        help_text="Optional expiration — pending requests past this are auto-expired",
                        null=True,
                    ),
                ),
                (
                    "metadata",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Arbitrary context payload (action params, model metrics, etc.)",
                    ),
                ),
            ],
            options={
                "db_table": "approval_request",
                "ordering": ["-created_at"],
                "abstract": False,
                "indexes": [
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
                    models.Index(
                        fields=["tenant_id", "-created_at"],
                        name="approvalrequ_tenant__b0c1f8_idx",
                    ),
                    models.Index(
                        fields=["realm", "tenant_id", "created_at"],
                        name="approvalrequ_realm_0f2e77_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ApprovalRule",
            fields=[
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="Timestamp when the record was created",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        db_index=True,
                        help_text="Timestamp when the record was last updated",
                    ),
                ),
                (
                    "realm",
                    models.CharField(
                        db_index=True,
                        default="default",
                        help_text="Realm identifier for RBAC realm isolation",
                        max_length=64,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Human-readable rule name",
                        max_length=255,
                    ),
                ),
                (
                    "request_type",
                    models.CharField(
                        db_index=True,
                        help_text="ApprovalRequest.RequestType this rule applies to",
                        max_length=32,
                    ),
                ),
                (
                    "auto_approve_conditions",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Conditions for auto-approval: {"max_risk_score": 3, "allowed_stages": ["staging"], "tags": ["low-risk"]}',
                    ),
                ),
                (
                    "required_approvers_count",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Number of distinct approvers required (currently only 1 is enforced)",
                    ),
                ),
                (
                    "escalation_timeout_hours",
                    models.PositiveIntegerField(
                        default=24,
                        help_text="Hours before a pending request is escalated / expired",
                    ),
                ),
                (
                    "enabled",
                    models.BooleanField(
                        db_index=True,
                        default=True,
                        help_text="Disabled rules are skipped during evaluation",
                    ),
                ),
            ],
            options={
                "db_table": "approval_rule",
                "ordering": ["-created_at"],
                "abstract": False,
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "request_type", "enabled"],
                        name="idx_appr_rule_tenant_type",
                    ),
                    models.Index(
                        fields=["tenant_id", "-created_at"],
                        name="approvalrule_tenant__8a4e95_idx",
                    ),
                    models.Index(
                        fields=["realm", "tenant_id", "created_at"],
                        name="approvalrule_realm_d3b1c0_idx",
                    ),
                ],
            },
        ),
    ]
