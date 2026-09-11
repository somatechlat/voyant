# Migration for SecurityPolicy and ColumnMask models (GOV-F-006, GOV-F-007)

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("governance", "0002_add_rls_column_mask_classification"),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityPolicy",
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
                ("name", models.CharField(help_text="Policy name", max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("inactive", "Inactive")],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "table_name",
                    models.CharField(
                        help_text="Fully-qualified table name (e.g. catalog.schema.table)",
                        max_length=255,
                    ),
                ),
                (
                    "column_name",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Column to filter on (optional, for documentation)",
                        max_length=255,
                    ),
                ),
                (
                    "filter_expression",
                    models.TextField(
                        help_text='SQL WHERE clause fragment, e.g. "tenant_id = current_user"'
                    ),
                ),
                (
                    "roles",
                    models.JSONField(
                        default=list,
                        help_text='Roles this policy applies to: ["analyst", "viewer"]',
                    ),
                ),
            ],
            options={
                "db_table": "governance_security_policy",
                "verbose_name": "Security Policy",
                "verbose_name_plural": "Security Policies",
                "abstract": False,
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "table_name"],
                        name="governance__tenant_sec_tbl_idx",
                    ),
                    models.Index(
                        fields=["tenant_id", "status"],
                        name="governance__tenant_sec_sts_idx",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ColumnMask",
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
                ("name", models.CharField(help_text="Policy name", max_length=255)),
                ("description", models.TextField(blank=True, default="")),
                (
                    "status",
                    models.CharField(
                        choices=[("active", "Active"), ("inactive", "Inactive")],
                        db_index=True,
                        default="active",
                        max_length=20,
                    ),
                ),
                (
                    "table_name",
                    models.CharField(
                        help_text="Fully-qualified table name (e.g. catalog.schema.table)",
                        max_length=255,
                    ),
                ),
                (
                    "column_name",
                    models.CharField(help_text="Column to mask", max_length=255),
                ),
                (
                    "mask_type",
                    models.CharField(
                        choices=[
                            ("null", "Null (replace with NULL)"),
                            ("hash", "Hash (SHA-256 of value)"),
                            ("partial", "Partial (show first/last N chars)"),
                            ("redact", "Redact (replace with [REDACTED])"),
                        ],
                        help_text="Masking strategy to apply",
                        max_length=20,
                    ),
                ),
                (
                    "mask_config",
                    models.JSONField(
                        default=dict,
                        help_text='Config: {"show_first": 2, "show_last": 4, "mask_char": "*"}',
                    ),
                ),
                (
                    "roles",
                    models.JSONField(
                        default=list,
                        help_text='Roles this mask applies to (empty = all roles): ["analyst"]',
                    ),
                ),
                (
                    "exempt_roles",
                    models.JSONField(
                        default=list,
                        help_text='Roles exempt from this mask: ["admin", "data_steward"]',
                    ),
                ),
            ],
            options={
                "db_table": "governance_column_mask_def",
                "verbose_name": "Column Mask",
                "verbose_name_plural": "Column Masks",
                "abstract": False,
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "table_name"],
                        name="governance__tenant_mask_tbl_idx",
                    ),
                ],
            },
        ),
    ]
