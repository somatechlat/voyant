"""Add PIIDetection and QualityScore models for §4.4 Data Catalog."""

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ontology", "0004_objecttype_backing_dataset"),
    ]

    operations = [
        migrations.CreateModel(
            name="PIIDetection",
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
                    "column_name",
                    models.CharField(
                        help_text="Name of the column where PII was detected",
                        max_length=255,
                    ),
                ),
                (
                    "dataset_urn",
                    models.CharField(
                        blank=True,
                        db_index=True,
                        default="",
                        help_text="URN of the dataset this detection belongs to",
                        max_length=512,
                    ),
                ),
                (
                    "pii_type",
                    models.CharField(
                        choices=[
                            ("email", "Email Address"),
                            ("phone", "Phone Number"),
                            ("ssn", "Social Security Number"),
                            ("credit_card", "Credit Card Number"),
                            ("ip_address", "IP Address"),
                            ("name", "Person Name"),
                            ("address", "Physical Address"),
                            ("dob", "Date of Birth"),
                        ],
                        help_text="Type of PII detected",
                        max_length=32,
                    ),
                ),
                (
                    "confidence",
                    models.FloatField(
                        help_text="Detection confidence score (0.0 to 1.0)",
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("regex", "Regex Pattern"),
                            ("name_pattern", "Column Name Pattern"),
                            ("ml", "Machine Learning"),
                        ],
                        help_text="Detection method used",
                        max_length=32,
                    ),
                ),
                (
                    "detected_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When the detection was performed",
                    ),
                ),
                (
                    "auto_classified",
                    models.BooleanField(
                        default=False,
                        help_text="True if auto-classified (confidence > 0.85)",
                    ),
                ),
            ],
            options={
                "db_table": "ontology_pii_detection",
                "ordering": ["-created_at"],
                "abstract": False,
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "dataset_urn"],
                        name="idx_pii_tenant_dataset",
                    ),
                    models.Index(
                        fields=["tenant_id", "column_name"],
                        name="idx_pii_tenant_column",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="QualityScore",
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
                    "dataset_id",
                    models.CharField(
                        db_index=True,
                        help_text="Identifier of the dataset (URN or ID)",
                        max_length=512,
                    ),
                ),
                (
                    "overall",
                    models.FloatField(
                        help_text="Weighted overall quality score (0\u2013100)",
                    ),
                ),
                (
                    "completeness",
                    models.FloatField(
                        help_text="% of non-null values across all columns",
                    ),
                ),
                (
                    "uniqueness",
                    models.FloatField(
                        help_text="% of unique values in key columns",
                    ),
                ),
                (
                    "timeliness",
                    models.FloatField(
                        help_text="Freshness score based on expected update frequency",
                    ),
                ),
                (
                    "consistency",
                    models.FloatField(
                        help_text="% of values matching expected format/type",
                    ),
                ),
                (
                    "accuracy",
                    models.FloatField(
                        help_text="% of values within expected range",
                    ),
                ),
                (
                    "computed_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When the quality score was computed",
                    ),
                ),
                (
                    "report",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Detailed per-column quality report",
                    ),
                ),
            ],
            options={
                "db_table": "ontology_quality_score",
                "ordering": ["-created_at"],
                "abstract": False,
                "indexes": [
                    models.Index(
                        fields=["tenant_id", "dataset_id"],
                        name="idx_qs_tenant_dataset",
                    ),
                    models.Index(
                        fields=["tenant_id", "-computed_at"],
                        name="idx_qs_tenant_computed",
                    ),
                ],
            },
        ),
        # Abstract TenantModel indexes for PIIDetection
        migrations.AddIndex(
            model_name="piidetection",
            index=models.Index(
                fields=["tenant_id", "-created_at"],
                name="idx_pii_tenant_created",
            ),
        ),
        migrations.AddIndex(
            model_name="piidetection",
            index=models.Index(
                fields=["realm", "tenant_id", "created_at"],
                name="idx_pii_realm_tenant",
            ),
        ),
        # Abstract TenantModel indexes for QualityScore
        migrations.AddIndex(
            model_name="qualityscore",
            index=models.Index(
                fields=["tenant_id", "-created_at"],
                name="idx_qs_tenant_created",
            ),
        ),
        migrations.AddIndex(
            model_name="qualityscore",
            index=models.Index(
                fields=["realm", "tenant_id", "created_at"],
                name="idx_qs_realm_tenant",
            ),
        ),
    ]
