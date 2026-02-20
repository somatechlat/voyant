"""Data ingestion models."""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class IngestionJob(TenantModel, UUIDModel):
    """
    Represents a data ingestion job that loads data from a canonical Source.

    Source ownership lives in apps.discovery.models.Source.
    """

    class Status(models.TextChoices):
        """Job execution status."""

        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        PARTIAL = "partial", "Partial Success"

    source = models.ForeignKey(
        "discovery.Source",
        on_delete=models.CASCADE,
        related_name="ingestion_jobs",
        help_text="Source to ingest data from",
    )
    workflow_instance_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Temporal workflow instance ID",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        help_text="Current job status",
    )
    progress = models.FloatField(
        default=0.0,
        help_text="Job progress (0.0 to 1.0)",
    )
    stage = models.CharField(
        max_length=64,
        blank=True,
        help_text="Current execution stage",
    )
    params = models.JSONField(
        default=dict,
        help_text="Job parameters and configuration",
    )
    result = models.JSONField(
        null=True,
        blank=True,
        help_text="Job result data",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if job failed",
    )
    rows_ingested = models.BigIntegerField(
        default=0,
        help_text="Number of rows successfully ingested",
    )
    bytes_processed = models.BigIntegerField(
        default=0,
        help_text="Number of bytes processed",
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when job started execution",
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when job finished",
    )

    class Meta:
        db_table = "voyant_ingestion_job"
        verbose_name = "Ingestion Job"
        verbose_name_plural = "Ingestion Jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "-created_at"]),
            models.Index(fields=["source", "-created_at"]),
            models.Index(fields=["workflow_instance_id"]),
        ]

    def __str__(self) -> str:
        return f"Ingestion Job {self.id} ({self.status})"
