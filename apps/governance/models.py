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

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
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

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
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

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
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

    .. deprecated:: 3.0.0
        This ORM model is **not used** by the current API implementation.
        The governance API uses the `QuotaTier` enum from `apps.core.lib.tenant_quotas` instead.
        Scheduled for removal in v4.0.0.
        See: docs/PHASE_A_STATUS.md (Orphaned Models section)
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

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
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

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
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


# ---------------------------------------------------------------------------
# Row-Level Security (GOV-F-003)
# ---------------------------------------------------------------------------


class RowSecurityPolicy(TenantModel, UUIDModel):
    """Row-level security policy for tenant-scoped data filtering.

    GOV-F-003: Defines row filters that restrict which rows a user/group
    can see in a given table. Enforced at query time by the Trino client
    and the governance middleware.
    """

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    name = models.CharField(max_length=255, help_text="Policy name")
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)

    # Target
    table_name = models.CharField(max_length=255, help_text="Table this policy applies to")
    column_name = models.CharField(max_length=255, blank=True, help_text="Column to filter on (optional)")

    # Filter
    filter_type = models.CharField(
        max_length=50,
        choices=[
            ("user_match", "User Match (column = current_user)"),
            ("role_based", "Role-Based (column IN allowed_values)"),
            ("custom_sql", "Custom SQL Filter"),
        ],
        help_text="Type of row filter",
    )
    filter_config = models.JSONField(
        default=dict,
        help_text='Filter config: {"column": "tenant_id", "role_map": {"admin": ["*"], "analyst": ["dept_a"]}}',
    )
    custom_sql = models.TextField(blank=True, help_text="Custom SQL WHERE clause (for custom_sql type)")

    # Scope
    applies_to_roles = models.JSONField(
        default=list,
        blank=True,
        help_text='Roles this policy applies to: ["analyst", "viewer"]',
    )
    applies_to_users = models.JSONField(
        default=list,
        blank=True,
        help_text='Specific user IDs this policy applies to',
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "governance_row_security_policy"
        indexes = [
            models.Index(fields=["tenant_id", "table_name"]),
            models.Index(fields=["tenant_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"RLS({self.name} on {self.table_name})"


# ---------------------------------------------------------------------------
# Column-Level Masking (GOV-F-004)
# ---------------------------------------------------------------------------


class ColumnMaskPolicy(TenantModel, UUIDModel):
    """Column-level masking policy for PII/sensitive data protection.

    GOV-F-004: Defines masking rules that transform column values at
    query time based on the user's role. For example, masking email
    addresses to show only the domain for non-HR users.
    """

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    MASK_TYPE_CHOICES = [
        ("full", "Full Mask (replace with ***)"),
        ("partial", "Partial Mask (show first/last N chars)"),
        ("hash", "Hash (SHA-256 of value)"),
        ("redact", "Redact (replace with [REDACTED])"),
        ("null", "Null (replace with NULL)"),
        ("custom", "Custom (apply custom function)"),
    ]

    name = models.CharField(max_length=255, help_text="Policy name")
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)

    # Target
    table_name = models.CharField(max_length=255, help_text="Table this policy applies to")
    column_name = models.CharField(max_length=255, help_text="Column to mask")

    # Masking
    mask_type = models.CharField(max_length=50, choices=MASK_TYPE_CHOICES)
    mask_config = models.JSONField(
        default=dict,
        help_text='Mask config: {"show_first": 2, "show_last": 4, "mask_char": "*"}',
    )

    # Scope
    applies_to_roles = models.JSONField(
        default=list,
        help_text='Roles this mask applies to (empty = all roles)',
    )
    exempt_roles = models.JSONField(
        default=list,
        help_text='Roles exempt from this mask (e.g. ["hr_admin"])',
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "governance_column_mask"
        indexes = [
            models.Index(fields=["tenant_id", "table_name"]),
        ]

    def __str__(self) -> str:
        return f"Mask({self.name} on {self.table_name}.{self.column_name})"


# ---------------------------------------------------------------------------
# Data Classification (Tags & Markings)
# ---------------------------------------------------------------------------


class DataClassification(TenantModel, UUIDModel):
    """Data classification tags for compliance (PII, sensitive, confidential).

    Maps to ISO/IEC 27001 A.8 (Asset Management) and GDPR requirements.
    """

    LEVEL_PUBLIC = "public"
    LEVEL_INTERNAL = "internal"
    LEVEL_CONFIDENTIAL = "confidential"
    LEVEL_RESTRICTED = "restricted"
    LEVEL_CHOICES = [
        (LEVEL_PUBLIC, "Public"),
        (LEVEL_INTERNAL, "Internal"),
        (LEVEL_CONFIDENTIAL, "Confidential"),
        (LEVEL_RESTRICTED, "Restricted"),
    ]

    name = models.CharField(max_length=255, help_text="Classification name (e.g. 'PII', 'Financial')")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_INTERNAL)
    description = models.TextField(blank=True, default="")

    # Target (what this classification applies to)
    target_type = models.CharField(
        max_length=50,
        choices=[
            ("table", "Table"),
            ("column", "Column"),
            ("object_type", "Ontology Object Type"),
        ],
    )
    target_name = models.CharField(max_length=255, help_text="Name of the target (table, column, etc.)")

    # Compliance
    requires_encryption = models.BooleanField(default=False)
    requires_masking = models.BooleanField(default=False)
    retention_days = models.IntegerField(null=True, blank=True, help_text="Data retention period")

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "governance_classification"
        indexes = [
            models.Index(fields=["tenant_id", "target_type", "target_name"]),
        ]

    def __str__(self) -> str:
        return f"Classification({self.name} [{self.level}] on {self.target_name})"
