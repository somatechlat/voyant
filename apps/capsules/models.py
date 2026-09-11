"""
Voyant Capsule Models.

Cross-compatible with somaAgent01 Capsule format v1.0.0.
All models inherit TenantModel for realm + tenant_id isolation.
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.core.models import TenantModel, TimeStampedModel


class Capability(models.Model):
    """A capability maps 1:1 to an existing MCP tool or Voyant feature."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100, db_index=True)
    schema = models.JSONField(default=dict)
    config = models.JSONField(default=dict)
    is_enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "capabilities"
        verbose_name_plural = "capabilities"

    def __str__(self) -> str:
        return f"Capability({self.name})"


class Constitution(TenantModel, TimeStampedModel):
    """The supreme regulatory document. Immutable once signed."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.CharField(max_length=50)
    content_hash = models.CharField(max_length=64, unique=True, db_index=True)
    signature = models.TextField()
    content = models.JSONField()
    is_active = models.BooleanField(default=False, db_index=True)
    activated_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = "constitutions"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_active"]),
            models.Index(fields=["content_hash"]),
        ]

    def __str__(self) -> str:
        return f"Constitution(v{self.version}:{self.content_hash[:8]})"


class Capsule(TenantModel, TimeStampedModel):
    """Capsule definition — the atomic unit of installable intelligence."""

    STATUS_DRAFT = "draft"
    STATUS_CERTIFIED = "certified"
    STATUS_ACTIVE = "active"
    STATUS_ARCHIVED = "archived"
    STATUS_SUSPENDED = "suspended"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_CERTIFIED, "Certified"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_ARCHIVED, "Archived"),
        (STATUS_SUSPENDED, "Suspended"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, db_index=True)
    version = models.CharField(max_length=50, default="1.0.0")
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent capsule this was cloned from",
    )

    # Soul (Identity)
    system_prompt = models.TextField(default="")
    personality_traits = models.JSONField(default=dict)
    neuromodulator_baseline = models.JSONField(default=dict)

    # Body (Voyant-specific payload)
    capsule_type = models.CharField(
        max_length=100, default="voyant.intelligence_recipe", db_index=True
    )
    execution_graph = models.JSONField(default=list)
    parameters_schema = models.JSONField(default=dict)
    output_formats = models.JSONField(default=list)
    rbac_rules = models.JSONField(default=dict)

    # Hands (Capabilities)
    capabilities = models.ManyToManyField(
        Capability, blank=True, related_name="capsules"
    )
    capabilities_whitelist = models.JSONField(default=list)
    resource_limits = models.JSONField(default=dict)

    # Governance
    constitution = models.ForeignKey(
        Constitution,
        on_delete=models.PROTECT,
        related_name="capsules",
        null=True,
        blank=True,
    )
    constitution_ref = models.JSONField(default=dict, blank=True)
    registry_signature = models.TextField(null=True, blank=True)
    certified_at = models.DateTimeField(null=True, blank=True)

    # Metadata
    is_active = models.BooleanField(default=True, db_index=True)
    install_count = models.PositiveIntegerField(default=0)
    execution_count = models.PositiveIntegerField(default=0)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = "capsules"
        unique_together = [["name", "version", "tenant_id"]]
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["tenant_id", "name", "version"]),
            models.Index(fields=["capsule_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"Capsule({self.name}:{self.version}:{self.status})"

    @property
    def is_certified(self) -> bool:
        return bool(
            self.registry_signature
            and self.status in (self.STATUS_CERTIFIED, self.STATUS_ACTIVE)
        )

    @property
    def soul(self) -> dict:
        return {
            "system_prompt": self.system_prompt,
            "personality_traits": self.personality_traits,
            "neuromodulator_baseline": self.neuromodulator_baseline,
        }

    @property
    def body(self) -> dict:
        return {
            "capsule_type": self.capsule_type,
            "execution_graph": self.execution_graph,
            "parameters_schema": self.parameters_schema,
            "output_formats": self.output_formats,
            "rbac_rules": self.rbac_rules,
            "capabilities_whitelist": self.capabilities_whitelist,
            "resource_limits": self.resource_limits,
        }


class CapsuleInstallation(TenantModel, TimeStampedModel):
    """Records which capsules are installed by which tenant."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    capsule = models.ForeignKey(
        Capsule, on_delete=models.CASCADE, related_name="installations"
    )
    installed_by = models.CharField(max_length=255, blank=True)
    is_enabled = models.BooleanField(default=True, db_index=True)
    parameter_overrides = models.JSONField(default=dict, blank=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = "capsule_installations"
        unique_together = [["capsule", "tenant_id"]]
        indexes = [
            models.Index(fields=["tenant_id", "is_enabled"]),
        ]

    def __str__(self) -> str:
        return f"CapsuleInstallation({self.capsule.name}:{self.tenant_id})"


class CapsuleInstance(TenantModel, TimeStampedModel):
    """Running execution of a Capsule."""

    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_TERMINATED = "terminated"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_FAILED, "Failed"),
        (STATUS_TERMINATED, "Terminated"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    capsule = models.ForeignKey(
        Capsule, on_delete=models.CASCADE, related_name="instances"
    )
    installation = models.ForeignKey(
        CapsuleInstallation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="instances",
    )
    session_id = models.CharField(max_length=255, db_index=True, blank=True)
    job_urn = models.CharField(max_length=512, blank=True, db_index=True)
    state = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=50, choices=STATUS_CHOICES, default=STATUS_RUNNING, db_index=True
    )
    triggered_by = models.CharField(
        max_length=50, default="mcp", db_index=True
    )  # "mcp" | "api" | "cron" | "dashboard"
    parameter_values = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    results = models.JSONField(default=dict, blank=True)
    artifacts = models.JSONField(default=list, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:  # pyright: ignore[reportIncompatibleVariableOverride]
        db_table = "capsule_instances"
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["session_id", "status"]),
            models.Index(fields=["job_urn"]),
        ]

    def __str__(self) -> str:
        return f"CapsuleInstance({self.capsule.name}:{self.status})"
