"""Create feature store models — FR-6.4.5.1 through FR-6.4.5.6."""

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="FeatureGroup",
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
                        db_index=True,
                        help_text="Unique name for this feature group",
                        max_length=255,
                        unique=True,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Human-readable description",
                    ),
                ),
                (
                    "entity_key",
                    models.CharField(
                        help_text="Entity key column (e.g. 'customer_id', 'order_id')",
                        max_length=128,
                    ),
                ),
                (
                    "online_enabled",
                    models.BooleanField(
                        default=False,
                        help_text="Whether online (low-latency Redis) serving is enabled",
                    ),
                ),
                (
                    "batch_enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Whether batch (SQL-based) serving is enabled",
                    ),
                ),
                (
                    "schedule",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Cron expression for scheduled feature computation",
                        max_length=128,
                    ),
                ),
                (
                    "tags",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Arbitrary metadata tags: {"team": "risk", "env": "prod"}',
                    ),
                ),
                (
                    "created_by",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="User or service that created this group",
                        max_length=256,
                    ),
                ),
            ],
            options={
                "db_table": "feature_group",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="Feature",
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
                        db_index=True,
                        help_text="Feature name (unique within group)",
                        max_length=255,
                    ),
                ),
                (
                    "data_type",
                    models.CharField(
                        choices=[
                            ("string", "String"),
                            ("integer", "Integer"),
                            ("float", "Float"),
                            ("boolean", "Boolean"),
                            ("timestamp", "Timestamp"),
                        ],
                        default="float",
                        help_text="Data type of the feature value",
                        max_length=20,
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Human-readable description",
                    ),
                ),
                (
                    "source_expression",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="SQL expression or code snippet that computes this feature",
                    ),
                ),
                (
                    "statistics",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text='Computed stats: {"mean": 42.0, "std": 3.1, "min": 0, "max": 100, "nulls_pct": 2.5}',
                    ),
                ),
                (
                    "ordinal_position",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Display/ordering position within the group",
                    ),
                ),
                (
                    "feature_group",
                    models.ForeignKey(
                        help_text="Parent feature group",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="features",
                        to="features.featuregroup",
                    ),
                ),
            ],
            options={
                "db_table": "feature",
                "ordering": ["ordinal_position", "name"],
            },
        ),
        migrations.CreateModel(
            name="FeatureValue",
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
                    "entity_key_value",
                    models.CharField(
                        db_index=True,
                        help_text="Value of the entity key (e.g. 'cust_12345')",
                        max_length=512,
                    ),
                ),
                (
                    "value",
                    models.JSONField(
                        help_text="Computed feature value (JSON-encoded for type flexibility)",
                    ),
                ),
                (
                    "computed_at",
                    models.DateTimeField(
                        db_index=True,
                        help_text="Timestamp when this value was computed",
                    ),
                ),
                (
                    "feature",
                    models.ForeignKey(
                        help_text="The feature this value belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="values",
                        to="features.feature",
                    ),
                ),
            ],
            options={
                "db_table": "feature_value",
                "ordering": ["-computed_at"],
            },
        ),
        migrations.CreateModel(
            name="FeatureVersion",
            fields=[
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
                    "version_number",
                    models.PositiveIntegerField(
                        help_text="Monotonically increasing version number",
                    ),
                ),
                (
                    "schema_snapshot",
                    models.JSONField(
                        help_text='Frozen schema: {"data_type": "float", "source_expression": "...", "statistics": {}}',
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                        help_text="When this version was created",
                    ),
                ),
                (
                    "feature",
                    models.ForeignKey(
                        help_text="The feature this version belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="features.feature",
                    ),
                ),
            ],
            options={
                "db_table": "feature_version",
                "ordering": ["-version_number"],
            },
        ),
        # ── Indexes ──────────────────────────────────────────────────────────
        migrations.AddIndex(
            model_name="featuregroup",
            index=models.Index(
                fields=["tenant_id", "name"], name="feat_group_tenant_name_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="featuregroup",
            index=models.Index(
                fields=["tenant_id", "-created_at"], name="feat_group_tenant_created_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="featuregroup",
            index=models.Index(
                fields=["tenant_id", "created_at"], name="feat_group_tenant_crt_asc_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="feature",
            index=models.Index(
                fields=["feature_group", "name"], name="feat_grp_name_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="feature",
            index=models.Index(
                fields=["tenant_id", "-created_at"], name="feat_tenant_created_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="feature",
            index=models.Index(
                fields=["tenant_id", "created_at"], name="feat_tenant_crt_asc_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="featurevalue",
            index=models.Index(
                fields=["feature", "entity_key_value", "-computed_at"],
                name="fval_feat_ent_computed_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="featurevalue",
            index=models.Index(
                fields=["tenant_id", "entity_key_value"],
                name="fval_tenant_entity_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="featurevalue",
            index=models.Index(
                fields=["tenant_id", "-computed_at"],
                name="fval_tenant_computed_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="featurevalue",
            index=models.Index(
                fields=["tenant_id", "created_at"],
                name="fval_tenant_created_idx",
            ),
        ),
        # ── Unique constraints ───────────────────────────────────────────────
        migrations.AddConstraint(
            model_name="feature",
            constraint=models.UniqueConstraint(
                fields=("feature_group", "name"),
                name="unique_feature_name_per_group",
            ),
        ),
        migrations.AddConstraint(
            model_name="featureversion",
            constraint=models.UniqueConstraint(
                fields=("feature", "version_number"),
                name="unique_feature_version_number",
            ),
        ),
    ]
