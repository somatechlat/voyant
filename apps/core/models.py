"""Core models for multi-tenancy and audit logging."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from django.db import models

from apps.core.middleware import get_current_user

logger = logging.getLogger(__name__)


class TimeStampedModel(models.Model):
    """
    Abstract base model that provides self-updating created and modified fields.

    All Voyant models should inherit from this to ensure consistent timestamp tracking.
    """

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when the record was created",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        db_index=True,
        help_text="Timestamp when the record was last updated",
    )

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class RBACManager(models.Manager):
    """
    Custom manager that auto-filters querysets by realm and tenant_id.

    If a current user is present in the request context and is NOT an admin,
    the queryset is filtered to the user's realm and tenant_id. Admins and
    unauthenticated contexts receive unfiltered querysets for backward
    compatibility with management commands and background tasks.
    """

    def get_queryset(self) -> models.QuerySet:
        qs = super().get_queryset()
        user: Any | None = get_current_user()
        if user is None:
            return qs
        if "voyant-admin" in getattr(user, "roles", []):
            return qs
        realm = getattr(user, "realm", None) or "default"
        tenant_id = getattr(user, "tenant_id", None) or "default"
        return qs.filter(realm=realm, tenant_id=tenant_id)


class TenantModel(TimeStampedModel):
    """
    Abstract base model that provides multi-tenancy support with realm isolation.

    All tenant-scoped models should inherit from this to ensure proper isolation.
    """

    realm = models.CharField(
        max_length=64,
        db_index=True,
        default="default",
        help_text="Realm identifier for RBAC realm isolation",
    )
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )

    objects = RBACManager()

    class Meta:  # type: ignore[assignment]
        abstract = True
        indexes = [
            models.Index(fields=["tenant_id", "-created_at"]),
            models.Index(fields=["realm", "tenant_id", "created_at"]),
        ]


class UUIDModel(models.Model):
    """
    Abstract base model that uses UUID as primary key.

    Provides a consistent UUID-based primary key across all models.
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique identifier (UUID)",
    )

    class Meta:
        abstract = True


class AuditLog(TenantModel, UUIDModel):
    """
    Audit log for tracking all critical operations in Voyant.

    Provides immutable audit trail for compliance and security monitoring.
    """

    actor = models.CharField(
        max_length=256,
        help_text="User or service that performed the action",
    )
    action = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Action performed (e.g., 'job.created', 'data.accessed')",
    )
    resource_type = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Type of resource affected (e.g., 'job', 'source')",
    )
    resource_id = models.CharField(
        max_length=256,
        db_index=True,
        help_text="Identifier of the affected resource",
    )
    outcome = models.CharField(
        max_length=32,
        choices=[
            ("success", "Success"),
            ("failure", "Failure"),
            ("denied", "Denied"),
        ],
        db_index=True,
        help_text="Outcome of the action",
    )
    details = models.JSONField(
        default=dict,
        help_text="Additional details about the action",
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the actor",
    )
    user_agent = models.TextField(
        blank=True,
        help_text="User agent string of the client",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_audit_log"
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "action", "-created_at"]),
            models.Index(fields=["tenant_id", "resource_type", "resource_id"]),
            models.Index(fields=["actor", "-created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.action} by {self.actor} on {self.resource_type}:{self.resource_id}"
        )


class SystemSetting(models.Model):
    """
    System-wide configuration settings stored in the database.

    Allows runtime configuration without code changes.
    """

    class ValueType(models.TextChoices):
        """Supported value types for settings."""

        STRING = "string", "String"
        INTEGER = "integer", "Integer"
        FLOAT = "float", "Float"
        BOOLEAN = "boolean", "Boolean"
        JSON = "json", "JSON"

    key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Unique setting key (e.g., 'max_concurrent_jobs')",
    )
    value = models.TextField(
        help_text="Setting value (stored as text, cast based on value_type)",
    )
    value_type = models.CharField(
        max_length=16,
        choices=ValueType.choices,
        default=ValueType.STRING,
        help_text="Data type of the value",
    )
    description = models.TextField(
        blank=True,
        help_text="Human-readable description of the setting",
    )
    is_secret = models.BooleanField(
        default=False,
        help_text="Whether this setting contains sensitive data",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the setting was last updated",
    )

    class Meta:
        db_table = "voyant_system_setting"
        verbose_name = "System Setting"
        verbose_name_plural = "System Settings"
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key} = {self.value if not self.is_secret else '***'}"

    def get_value(self) -> Any:
        """
        Parse and return the setting value with proper type casting.

        Returns:
            The setting value cast to the appropriate Python type.

        Raises:
            ValueError: If the value cannot be cast to the specified type.
        """
        import json

        if self.value_type == self.ValueType.STRING:
            return self.value
        elif self.value_type == self.ValueType.INTEGER:
            return int(self.value)
        elif self.value_type == self.ValueType.FLOAT:
            return float(self.value)
        elif self.value_type == self.ValueType.BOOLEAN:
            return self.value.lower() in ("true", "1", "yes", "on")
        elif self.value_type == self.ValueType.JSON:
            return json.loads(self.value)
        else:
            return self.value
