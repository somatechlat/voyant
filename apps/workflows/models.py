from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class Job(TenantModel, UUIDModel):
    """
    Represents an asynchronous background job.
    """

    job_type = models.CharField(max_length=64, db_index=True)
    source_id = models.CharField(max_length=36, null=True, blank=True)
    soma_session_id = models.CharField(max_length=128, null=True, blank=True)

    status = models.CharField(max_length=64, default="queued")
    progress = models.IntegerField(default=0)
    parameters = models.JSONField(default=dict)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    result_summary = models.JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "voyant_job"
        ordering = ["-created_at"]

    @property
    def job_id(self) -> str:
        """Compatibility alias used across API responses and integrations."""
        return str(self.id)


class Artifact(TenantModel):
    """
    Represents a file or data artifact produced by a job.
    """

    artifact_id = models.CharField(max_length=512, primary_key=True)
    job_id = models.CharField(max_length=36, db_index=True)

    artifact_type = models.CharField(max_length=128)
    format = models.CharField(max_length=32)
    storage_path = models.CharField(max_length=512)
    size_bytes = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "voyant_artifact"


class PresetJob(TenantModel, UUIDModel):
    """
    Template for a job configuration.
    """

    preset_name = models.CharField(max_length=255, db_index=True)
    source_id = models.CharField(max_length=36)
    parameters = models.JSONField(default=dict)
    status = models.CharField(max_length=64, default="queued")

    class Meta:
        db_table = "voyant_preset_job"

    @property
    def job_id(self) -> str:
        """Compatibility alias used across API responses and integrations."""
        return str(self.id)
