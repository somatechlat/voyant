"""Pipeline Builder — Django ORM models.

Provides Pipeline, PipelineStep, and PipelineRun models for building,
scheduling, and tracking multi-step data pipelines.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class Pipeline(TenantModel, UUIDModel):
    """
    A reusable data pipeline definition.

    Pipelines are composed of ordered steps and can be scheduled for
    recurring execution via cron expressions.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ARCHIVED = "archived", "Archived"

    name = models.CharField(
        max_length=255,
        help_text="Pipeline name (unique per tenant)",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        help_text="Pipeline lifecycle status",
    )
    schedule = models.CharField(
        max_length=128,
        blank=True,
        default="",
        help_text="Cron expression for scheduled execution (empty = manual only)",
    )
    schedule_timezone = models.CharField(
        max_length=64,
        default="UTC",
        help_text="Timezone for the schedule expression",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Global pipeline configuration (default params, retry policy, etc.)",
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Auto-incrementing version for pipeline changes",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Soft-deletion timestamp (null = active)",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_pipeline"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_pipeline_name_active",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="idx_pipe_tenant_status"),
            models.Index(
                fields=["tenant_id", "-created_at"], name="idx_pipe_tenant_created"
            ),
        ]

    def __str__(self) -> str:
        return f"Pipeline({self.name} [{self.status}])"


class PipelineStep(UUIDModel):
    """
    An individual step within a pipeline.

    Steps define the type of operation (ingest, transform, quality check,
    export, etc.) and its configuration. Steps execute in order.
    """

    class StepType(models.TextChoices):
        INGEST = "ingest", "Ingest"
        TRANSFORM = "transform", "Transform"
        QUALITY_CHECK = "quality_check", "Quality Check"
        PROFILE = "profile", "Profile"
        EXPORT = "export", "Export"
        SCRAPE = "scrape", "Scrape"
        SQL_QUERY = "sql_query", "SQL Query"
        CUSTOM = "custom", "Custom"

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name="steps",
        help_text="Parent pipeline",
    )
    step_type = models.CharField(
        max_length=32,
        choices=StepType.choices,
        help_text="Type of operation this step performs",
    )
    name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Human-readable step name",
    )
    order = models.PositiveIntegerField(
        default=0,
        help_text="Execution order (lower runs first)",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="Step-specific configuration (parameters, selectors, queries, etc.)",
    )
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of retries on failure",
    )
    timeout_seconds = models.PositiveIntegerField(
        default=300,
        help_text="Maximum execution time in seconds",
    )
    depends_on = models.ManyToManyField(
        "self",
        blank=True,
        symmetrical=False,
        related_name="dependents",
        help_text="Steps that must complete before this one starts",
    )

    class Meta(UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_pipeline_step"
        ordering = ["order"]
        indexes = [
            models.Index(
                fields=["pipeline_id", "order"], name="idx_step_pipeline_order"
            ),
        ]

    def __str__(self) -> str:
        label = self.name or f"Step {self.order}"
        return f"{self.pipeline.name}::{label} ({self.step_type})"


class PipelineRun(TenantModel, UUIDModel):
    """
    A single execution of a pipeline.

    Tracks the overall status, timing, and logs for a pipeline execution.
    Individual step results are stored in PipelineStepRun.
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        TIMEOUT = "timeout", "Timeout"

    pipeline = models.ForeignKey(
        Pipeline,
        on_delete=models.CASCADE,
        related_name="runs",
        help_text="Pipeline being executed",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED,
        db_index=True,
        help_text="Run status",
    )
    triggered_by = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="User or system that triggered this run",
    )
    trigger_type = models.CharField(
        max_length=32,
        choices=[
            ("manual", "Manual"),
            ("schedule", "Schedule"),
            ("api", "API"),
        ],
        default="manual",
        help_text="How this run was triggered",
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        help_text="Runtime parameters for this execution",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution started",
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When execution completed (success or failure)",
    )
    logs = models.TextField(
        blank=True,
        default="",
        help_text="Aggregated execution logs",
    )
    result_summary = models.JSONField(
        default=dict,
        blank=True,
        help_text="Summary of execution results (rows processed, errors, etc.)",
    )
    error_message = models.TextField(
        blank=True,
        default="",
        help_text="Error message if the run failed",
    )
    steps_completed = models.PositiveIntegerField(
        default=0,
        help_text="Number of steps completed",
    )
    steps_total = models.PositiveIntegerField(
        default=0,
        help_text="Total number of steps in the pipeline",
    )
    temporal_workflow_id = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="Temporal workflow ID for tracking",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_pipeline_run"
        indexes = [
            models.Index(
                fields=["pipeline_id", "-created_at"], name="idx_run_pipeline_created"
            ),
            models.Index(fields=["tenant_id", "status"], name="idx_run_tenant_status"),
        ]

    def __str__(self) -> str:
        return f"Run({self.pipeline.name} [{self.status}] {self.id})"


class PipelineStepRun(UUIDModel):
    """
    Execution record for an individual step within a pipeline run.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    pipeline_run = models.ForeignKey(
        PipelineRun,
        on_delete=models.CASCADE,
        related_name="step_runs",
        help_text="Parent pipeline run",
    )
    step = models.ForeignKey(
        PipelineStep,
        on_delete=models.CASCADE,
        related_name="runs",
        help_text="Pipeline step being executed",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    output_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Step output (result data, artifact references, etc.)",
    )
    logs = models.TextField(blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    attempt = models.PositiveIntegerField(
        default=1,
        help_text="Execution attempt number (incremented on retry)",
    )

    class Meta(UUIDModel.Meta):  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_pipeline_step_run"
        indexes = [
            models.Index(
                fields=["pipeline_run_id", "step_id"], name="idx_steprun_run_step"
            ),
        ]

    def __str__(self) -> str:
        return f"StepRun({self.step} [{self.status}])"
