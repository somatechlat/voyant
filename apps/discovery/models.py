"""Service discovery models."""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class ServiceDefinition(TenantModel, UUIDModel):
    """
    Represents a discovered external service and its API specification.

    Stores service metadata, endpoints, and OpenAPI specification details
    for the internal discovery catalog.
    """

    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Unique name for the service",
    )
    base_url = models.URLField(
        max_length=512,
        help_text="Base URL where the service can be accessed",
    )
    spec_url = models.URLField(
        max_length=512,
        blank=True,
        help_text="URL to the service's OpenAPI specification",
    )
    version = models.CharField(
        max_length=64,
        default="1.0.0",
        help_text="Service API version",
    )
    description = models.TextField(
        blank=True,
        help_text="Human-readable description of the service",
    )
    owner = models.CharField(
        max_length=255,
        default="unknown",
        help_text="Team or individual responsible for the service",
    )
    tags = models.JSONField(
        default=list,
        help_text="List of tags for categorizing the service",
    )
    endpoints = models.JSONField(
        default=list,
        help_text="List of API endpoints extracted from OpenAPI spec",
    )
    auth_type = models.CharField(
        max_length=64,
        default="none",
        help_text="Authentication type (e.g., OAuth2, Bearer, ApiKey)",
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metadata about the service",
    )
    first_seen = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Timestamp when service was first discovered",
    )
    last_seen = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when service was last seen or updated",
    )

    class Meta:
        db_table = "voyant_service_definition"
        verbose_name = "Service Definition"
        verbose_name_plural = "Service Definitions"
        ordering = ["-last_seen"]
        indexes = [
            models.Index(fields=["tenant_id", "name"]),
            models.Index(fields=["tenant_id", "-last_seen"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="unique_service_name_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.version})"


class Source(TenantModel, UUIDModel):
    """
    Represents a data source configuration.
    """
    name = models.CharField(max_length=255)
    source_type = models.CharField(max_length=128)
    status = models.CharField(max_length=64, default="pending")
    connection_config = models.JSONField()
    credentials = models.JSONField(null=True, blank=True)
    sync_schedule = models.CharField(max_length=128, null=True, blank=True)
    datahub_urn = models.CharField(max_length=512, null=True, blank=True)

    class Meta:
        db_table = "voyant_source"
        ordering = ["-created_at"]

