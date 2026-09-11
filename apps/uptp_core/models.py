"""UPTP Core models for template management and instance execution."""

from __future__ import annotations

import json
import logging
from typing import Any

from django.db import models

from apps.core.models import TenantModel, UUIDModel

logger = logging.getLogger(__name__)


# =============================================================================
# UPTP Template Model
# =============================================================================


class UPTPTemplate(TenantModel, UUIDModel):
    """
    Universal Parametric Template Pattern (UPTP) template definition.

    Represents a reusable, parameterized template that defines an executable
    pipeline pattern. Templates are the blueprints; instances are the executions.
    """

    class Status(models.TextChoices):
        """Template lifecycle status."""

        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        DEPRECATED = "deprecated", "Deprecated"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Unique template name (e.g. 'ingest.db.generic')",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description of what this template does",
    )
    template_body = models.JSONField(
        default=dict,
        help_text=(
            "Template definition as JSON. Contains the DAG of steps, "
            "parameter declarations, input/output schemas, and execution hints."
        ),
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Monotonically increasing version number",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Template lifecycle status",
    )
    category = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Execution category (ingestion, math, render, capsule)",
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="List of tags for categorization and search",
    )
    parameters_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "JSON Schema defining the expected parameters for this template. "
            "Used for runtime validation of instance parameters."
        ),
    )
    output_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text="JSON Schema describing the expected output format",
    )
    is_system = models.BooleanField(
        default=False,
        help_text="System templates cannot be deleted by users",
    )
    created_by = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="User or service that created this template",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_uptp_template"
        verbose_name = "UPTP Template"
        verbose_name_plural = "UPTP Templates"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "name"]),
            models.Index(fields=["tenant_id", "category", "-updated_at"]),
            models.Index(fields=["tenant_id", "status", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="uq_uptp_template_tenant_name",
            ),
        ]

    def __str__(self) -> str:
        return f"UPTPTemplate({self.name} v{self.version} [{self.status}])"

    def validate_parameters(self, params: dict[str, Any]) -> list[str]:
        """
        Validate instance parameters against the template's parameter schema.

        Args:
            params: The parameters to validate.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors: list[str] = []
        schema = self.parameters_schema
        if not schema:
            return errors  # No schema = no validation

        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required fields
        for field_name in required:
            if field_name not in params:
                errors.append(f"Missing required parameter: '{field_name}'")

        # Check types (basic validation without jsonschema dependency)
        for field_name, field_value in params.items():
            if field_name in properties:
                expected_type = properties[field_name].get("type")
                if expected_type and not self._check_type(
                    field_value, expected_type
                ):
                    errors.append(
                        f"Parameter '{field_name}' expected type '{expected_type}', "
                        f"got '{type(field_value).__name__}'"
                    )

        return errors

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """Check if a value matches a JSON Schema type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True  # Unknown type — permissive
        return isinstance(value, expected)

    def render(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Render the template body with the given parameters.

        Substitutes parameter placeholders in the template_body and returns
        the fully resolved execution plan.

        Args:
            params: Parameter values to substitute.

        Returns:
            The resolved template body ready for execution.
        """
        body = self.template_body
        if not body:
            return {}

        rendered = json.loads(json.dumps(body))  # Deep copy
        self._render_recursive(rendered, params)
        return rendered

    @staticmethod
    def _render_recursive(obj: Any, params: dict[str, Any]) -> None:
        """Recursively substitute ${param} placeholders in template body."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                    param_name = value[2:-1]
                    if param_name in params:
                        obj[key] = params[param_name]
                else:
                    UPTPTemplate._render_recursive(value, params)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str) and item.startswith("${") and item.endswith("}"):
                    param_name = item[2:-1]
                    if param_name in params:
                        obj[i] = params[param_name]
                else:
                    UPTPTemplate._render_recursive(item, params)


# =============================================================================
# UPTP Instance Model
# =============================================================================


class UPTPInstance(TenantModel, UUIDModel):
    """
    An execution instance of a UPTP template.

    Represents a concrete run of a template with specific parameter values.
    Tracks execution status, result, and error state.
    """

    class Status(models.TextChoices):
        """Instance execution status."""

        PENDING = "pending", "Pending"
        VALIDATING = "validating", "Validating"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        TIMEOUT = "timeout", "Timeout"

    template = models.ForeignKey(
        UPTPTemplate,
        on_delete=models.CASCADE,
        related_name="instances",
        help_text="The template this instance was created from",
    )
    parameters = models.JSONField(
        default=dict,
        help_text="Parameter values used for this execution",
    )
    rendered_body = models.JSONField(
        default=dict,
        blank=True,
        help_text="The fully rendered template body (after parameter substitution)",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    result = models.JSONField(
        null=True,
        blank=True,
        help_text="Execution result data (null while running)",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error message if the execution failed",
    )
    workflow_instance_id = models.CharField(
        max_length=255,
        blank=True,
        default="",
        db_index=True,
        help_text="Temporal workflow instance ID for async executions",
    )
    execution_urn = models.CharField(
        max_length=512,
        blank=True,
        default="",
        help_text="UPTP execution URN (e.g. urn:voyant:job:tenant:template:uuid)",
    )
    execution_category = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="The execution category at time of creation",
    )
    duration_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Execution duration in milliseconds",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution started",
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution finished",
    )
    trigger_source = models.CharField(
        max_length=128,
        blank=True,
        default="api",
        help_text="What triggered this instance (api, scheduler, event, agent)",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (session ID, agent context, etc.)",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_uptp_instance"
        verbose_name = "UPTP Instance"
        verbose_name_plural = "UPTP Instances"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "-created_at"]),
            models.Index(fields=["template", "-created_at"]),
            models.Index(fields=["tenant_id", "execution_category", "-created_at"]),
            models.Index(fields=["workflow_instance_id"]),
            models.Index(fields=["execution_urn"]),
        ]

    def __str__(self) -> str:
        return (
            f"UPTPInstance({self.id} template={self.template_id} "
            f"[{self.status}])"
        )

    def mark_running(self) -> None:
        """Transition to running status."""
        from django.utils import timezone

        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def mark_succeeded(self, result: dict[str, Any]) -> None:
        """Mark execution as successful with result data."""
        from django.utils import timezone

        now = timezone.now()
        self.status = self.Status.SUCCEEDED
        self.result = result
        self.finished_at = now
        if self.started_at:
            self.duration_ms = int(
                (now - self.started_at).total_seconds() * 1000
            )
        self.save(
            update_fields=[
                "status",
                "result",
                "finished_at",
                "duration_ms",
                "updated_at",
            ]
        )

    def mark_failed(self, error: str) -> None:
        """Mark execution as failed with error message."""
        from django.utils import timezone

        now = timezone.now()
        self.status = self.Status.FAILED
        self.error_message = error
        self.finished_at = now
        if self.started_at:
            self.duration_ms = int(
                (now - self.started_at).total_seconds() * 1000
            )
        self.save(
            update_fields=[
                "status",
                "error_message",
                "finished_at",
                "duration_ms",
                "updated_at",
            ]
        )

    def mark_cancelled(self) -> None:
        """Mark execution as cancelled."""
        from django.utils import timezone

        self.status = self.Status.CANCELLED
        self.finished_at = timezone.now()
        self.save(
            update_fields=["status", "finished_at", "updated_at"]
        )
