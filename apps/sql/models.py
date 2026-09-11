"""Models for the SQL app — saved queries and sharing."""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class SavedQuery(UUIDModel, TenantModel):
    """
    A user-saved SQL query that can be reused, shared, and parameterized.

    Inherits UUIDModel for a UUID primary key, TenantModel for multi-tenancy
    isolation (realm, tenant_id, timestamps), and RBAC-aware querying.
    """

    name = models.CharField(
        max_length=255,
        help_text="Human-readable name for the saved query",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional description explaining the query's purpose",
    )
    query_text = models.TextField(
        help_text="The SQL query text",
    )
    language = models.CharField(
        max_length=32,
        default="sql",
        help_text="Query language (e.g., 'sql')",
    )
    parameters = models.JSONField(
        null=True,
        blank=True,
        default=dict,
        help_text="Optional parameter definitions for parameterized queries",
    )
    is_public = models.BooleanField(
        default=False,
        db_index=True,
        help_text="If true, the query is visible to all users in the same tenant",
    )
    shared_with = models.JSONField(
        default=list,
        blank=True,
        help_text="List of user IDs the query is explicitly shared with",
    )
    created_by = models.CharField(
        max_length=256,
        db_index=True,
        help_text="User ID of the query creator (from auth context)",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_saved_query"
        verbose_name = "Saved Query"
        verbose_name_plural = "Saved Queries"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "created_by", "-updated_at"]),
            models.Index(fields=["tenant_id", "is_public", "-updated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.language})"
