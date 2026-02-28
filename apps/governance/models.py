"""Data governance models for contracts, lineage, and policies."""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class DataContract(TenantModel, UUIDModel):
    """
    Data contract defining schema validation and quality rules.

    Represents agreements about data structure, quality, and usage between
    data producers and consumers.
    """

    class Status(models.TextChoices):
        """Contract status."""

        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        DEPRECATED = "deprecated", "Deprecated"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(
        max_length=255,
        help_text="Human-readable name for the data contract",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the contract",
    )
    dataset_urn = models.CharField(
        max_length=512,
        db_index=True,
        help_text="DataHub URN for the dataset this contract applies to",
    )
    schema_definition = models.JSONField(
        default=dict,
        help_text="JSON schema defining expected data structure",
    )
    quality_rules = models.JSONField(
        default=list,
        help_text="List of data quality rules and constraints",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Current status of the contract",
    )
    version = models.CharField(
        max_length=32,
        default="1.0.0",
        help_text="Semantic version of the contract",
    )
    owner = models.CharField(
        max_length=255,
        help_text="Owner or team responsible for this contract",
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metadata about the contract",
    )

    class Meta:
        db_table = "voyant_data_contract"
        verbose_name = "Data Contract"
        verbose_name_plural = "Data Contracts"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "-created_at"]),
            models.Index(fields=["dataset_urn"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name", "version"],
                name="unique_contract_version_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} v{self.version} ({self.status})"


class LineageNode(TenantModel, UUIDModel):
    """
    Data lineage node representing a dataset or transformation.

    Tracks data flow and dependencies between datasets, enabling impact
    analysis and data provenance tracking.
    """

    class NodeType(models.TextChoices):
        """Type of lineage node."""

        DATASET = "dataset", "Dataset"
        TRANSFORMATION = "transformation", "Transformation"
        MODEL = "model", "ML Model"
        REPORT = "report", "Report"
        API = "api", "API Endpoint"

    urn = models.CharField(
        max_length=512,
        unique=True,
        db_index=True,
        help_text="Unique resource name (URN) for this node",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name for the node",
    )
    node_type = models.CharField(
        max_length=32,
        choices=NodeType.choices,
        default=NodeType.DATASET,
        db_index=True,
        help_text="Type of lineage node",
    )
    platform = models.CharField(
        max_length=128,
        blank=True,
        help_text="Platform or system where this node exists",
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the node",
    )
    upstream_urns = models.JSONField(
        default=list,
        help_text="List of URNs for upstream dependencies",
    )
    downstream_urns = models.JSONField(
        default=list,
        help_text="List of URNs for downstream consumers",
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metadata about the node",
    )

    class Meta:
        db_table = "voyant_lineage_node"
        verbose_name = "Lineage Node"
        verbose_name_plural = "Lineage Nodes"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "node_type", "-created_at"]),
            models.Index(fields=["urn"]),
            models.Index(fields=["platform"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.node_type})"


class Policy(TenantModel, UUIDModel):
    """
    Governance policy defining access control and compliance rules.

    Policies enforce data governance requirements such as access control,
    data retention, and compliance with regulations.
    """

    class PolicyType(models.TextChoices):
        """Type of governance policy."""

        ACCESS_CONTROL = "access_control", "Access Control"
        DATA_RETENTION = "data_retention", "Data Retention"
        DATA_QUALITY = "data_quality", "Data Quality"
        COMPLIANCE = "compliance", "Compliance"
        USAGE = "usage", "Usage Policy"

    class Status(models.TextChoices):
        """Policy status."""

        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(
        max_length=255,
        help_text="Human-readable name for the policy",
    )
    description = models.TextField(
        blank=True,
        help_text="Detailed description of the policy",
    )
    policy_type = models.CharField(
        max_length=32,
        choices=PolicyType.choices,
        default=PolicyType.ACCESS_CONTROL,
        db_index=True,
        help_text="Type of governance policy",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Current status of the policy",
    )
    rules = models.JSONField(
        default=dict,
        help_text="Policy rules and conditions in JSON format",
    )
    scope = models.JSONField(
        default=dict,
        help_text="Scope definition (datasets, users, operations)",
    )
    enforcement_level = models.CharField(
        max_length=32,
        default="strict",
        help_text="Enforcement level: strict, warn, or audit",
    )
    owner = models.CharField(
        max_length=255,
        help_text="Owner or team responsible for this policy",
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metadata about the policy",
    )

    class Meta:
        db_table = "voyant_policy"
        verbose_name = "Governance Policy"
        verbose_name_plural = "Governance Policies"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "policy_type", "status"]),
            models.Index(fields=["status", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="unique_policy_name_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.policy_type})"


class QuotaTier(models.Model):
    """
    Quota tier definition for tenant resource limits.

    Defines resource limits for different subscription tiers.
    """

    tier_id = models.CharField(
        max_length=64,
        primary_key=True,
        help_text="Unique identifier for the tier",
    )
    name = models.CharField(
        max_length=128,
        help_text="Display name for the tier",
    )
    max_jobs_per_day = models.IntegerField(
        default=100,
        help_text="Maximum number of jobs per day",
    )
    max_artifacts_gb = models.FloatField(
        default=10.0,
        help_text="Maximum artifact storage in GB",
    )
    max_sources = models.IntegerField(
        default=10,
        help_text="Maximum number of data sources",
    )
    max_concurrent_jobs = models.IntegerField(
        default=5,
        help_text="Maximum concurrent running jobs",
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional tier metadata",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the tier was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the tier was last updated",
    )

    class Meta:
        db_table = "voyant_quota_tier"
        verbose_name = "Quota Tier"
        verbose_name_plural = "Quota Tiers"
        ordering = ["tier_id"]

    def __str__(self) -> str:
        return f"{self.name} ({self.tier_id})"


class TenantQuota(TenantModel):
    """
    Tenant-specific quota assignment and usage tracking.

    Tracks which tier a tenant is on and their current resource usage.
    """

    tier = models.ForeignKey(
        QuotaTier,
        on_delete=models.PROTECT,
        related_name="tenant_quotas",
        help_text="Assigned quota tier",
    )
    jobs_today = models.IntegerField(
        default=0,
        help_text="Number of jobs executed today",
    )
    artifacts_gb = models.FloatField(
        default=0.0,
        help_text="Current artifact storage usage in GB",
    )
    sources_count = models.IntegerField(
        default=0,
        help_text="Current number of data sources",
    )
    concurrent_jobs = models.IntegerField(
        default=0,
        help_text="Current number of concurrent running jobs",
    )
    last_reset_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Last time daily counters were reset",
    )

    class Meta:
        db_table = "voyant_tenant_quota"
        verbose_name = "Tenant Quota"
        verbose_name_plural = "Tenant Quotas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id"],
                name="unique_quota_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"Quota for {self.tenant_id} ({self.tier.name})"
