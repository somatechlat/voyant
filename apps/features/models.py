"""
Feature Store — Django ORM Models.

Provides FeatureGroup, Feature, FeatureValue, and FeatureVersion models
for a Palantir-class feature store supporting online and batch serving.
Part of Voyant v4.0 Phase 3 — FR-6.4.5.1 through FR-6.4.5.6.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class FeatureGroup(TenantModel, UUIDModel):
    """
    A logical grouping of related features that share an entity key.

    Example: a 'customer_risk' group with entity_key='customer_id' containing
    features like risk_score, transaction_count, etc.
    """

    name = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique name for this feature group",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description",
    )
    entity_key = models.CharField(
        max_length=128,
        help_text="Entity key column (e.g. 'customer_id', 'order_id')",
    )
    online_enabled = models.BooleanField(
        default=False,
        help_text="Whether online (low-latency Redis) serving is enabled",
    )
    batch_enabled = models.BooleanField(
        default=True,
        help_text="Whether batch (SQL-based) serving is enabled",
    )
    schedule = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Cron expression for scheduled feature computation",
    )
    tags = models.JSONField(
        default=dict,
        blank=True,
        help_text='Arbitrary metadata tags: {"team": "risk", "env": "prod"}',
    )
    created_by = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="User or service that created this group",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[assignment]
        db_table = "feature_group"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "name"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"FeatureGroup({self.name})"


class Feature(TenantModel, UUIDModel):
    """
    An individual feature (column) within a feature group.

    Each feature has a data type, a source expression (SQL or code snippet),
    and auto-computed statistics.
    """

    class DataType(models.TextChoices):
        STRING = "string", "String"
        INTEGER = "integer", "Integer"
        FLOAT = "float", "Float"
        BOOLEAN = "boolean", "Boolean"
        TIMESTAMP = "timestamp", "Timestamp"

    feature_group = models.ForeignKey(
        FeatureGroup,
        on_delete=models.CASCADE,
        related_name="features",
        help_text="Parent feature group",
    )
    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Feature name (unique within group)",
    )
    data_type = models.CharField(
        max_length=20,
        choices=DataType.choices,
        default=DataType.FLOAT,
        help_text="Data type of the feature value",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description",
    )
    source_expression = models.TextField(
        blank=True,
        default="",
        help_text="SQL expression or code snippet that computes this feature",
    )
    statistics = models.JSONField(
        default=dict,
        blank=True,
        help_text='Computed stats: {"mean": 42.0, "std": 3.1, "min": 0, "max": 100, "nulls_pct": 2.5}',
    )
    ordinal_position = models.PositiveIntegerField(
        default=0,
        help_text="Display/ordering position within the group",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[assignment]
        db_table = "feature"
        unique_together = [("feature_group", "name")]
        ordering = ["ordinal_position", "name"]
        indexes = [
            models.Index(fields=["feature_group", "name"]),
            models.Index(fields=["tenant_id", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Feature({self.feature_group.name}.{self.name})"


class FeatureValue(TenantModel, UUIDModel):
    """
    A materialised feature value for a specific entity instance.

    Stores the result of computing a feature for a given entity_key_value
    (e.g. customer_id=12345). Used for both online (Redis-cached) and
    batch (SQL-queried) serving.
    """

    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        related_name="values",
        help_text="The feature this value belongs to",
    )
    entity_key_value = models.CharField(
        max_length=512,
        db_index=True,
        help_text="Value of the entity key (e.g. 'cust_12345')",
    )
    value = models.JSONField(
        help_text="Computed feature value (JSON-encoded for type flexibility)",
    )
    computed_at = models.DateTimeField(
        db_index=True,
        help_text="Timestamp when this value was computed",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[assignment]
        db_table = "feature_value"
        ordering = ["-computed_at"]
        indexes = [
            models.Index(fields=["feature", "entity_key_value", "-computed_at"]),
            models.Index(fields=["tenant_id", "entity_key_value"]),
            models.Index(fields=["tenant_id", "-computed_at"]),
        ]

    def __str__(self) -> str:
        return f"FeatureValue({self.feature.name}={self.value} @ {self.computed_at})"


class FeatureVersion(UUIDModel):
    """
    Immutable snapshot of a feature's schema at a point in time.

    Provides versioning and lineage tracking (FR-6.4.5.4).
    """

    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE,
        related_name="versions",
        help_text="The feature this version belongs to",
    )
    version_number = models.PositiveIntegerField(
        help_text="Monotonically increasing version number",
    )
    schema_snapshot = models.JSONField(
        help_text='Frozen schema: {"data_type": "float", "source_expression": "...", "statistics": {}}',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When this version was created",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "feature_version"
        ordering = ["-version_number"]
        unique_together = [("feature", "version_number")]

    def __str__(self) -> str:
        return f"FeatureVersion({self.feature.name} v{self.version_number})"
