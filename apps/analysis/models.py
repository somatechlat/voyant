"""Statistical analysis models."""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class AnalysisJob(TenantModel, UUIDModel):
    """Analysis job execution tracking."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    workflow_instance_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    progress = models.FloatField(default=0.0)
    stage = models.CharField(max_length=64, blank=True)
    params = models.JSONField(default=dict)
    result = models.JSONField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    data_quality_score = models.FloatField(null=True, blank=True)
    rows_analyzed = models.BigIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "voyant_analysis_job"
        verbose_name = "Analysis Job"
        verbose_name_plural = "Analysis Jobs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "-created_at"]),
            models.Index(fields=["workflow_instance_id"]),
        ]

    def __str__(self) -> str:
        return f"Analysis Job {self.id} ({self.status})"
