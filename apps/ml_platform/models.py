"""
ML Platform — Django ORM Models.

MLflow-compatible models for experiment tracking, model registry,
and model serving. Part of Voyant v4.0 Phase 3.
"""

from __future__ import annotations

import uuid

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class Experiment(TenantModel, UUIDModel):
    """MLflow-compatible experiment for tracking ML runs."""

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    tags = models.JSONField(default=dict, blank=True)
    artifact_location = models.CharField(max_length=512, blank=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_experiment"
        unique_together = [("tenant_id", "name")]

    def __str__(self) -> str:
        return f"Experiment({self.name})"


class Run(TenantModel, UUIDModel):
    """Individual ML experiment run."""

    STATUS_RUNNING = "running"
    STATUS_FINISHED = "finished"
    STATUS_FAILED = "failed"
    STATUS_KILLED = "killed"
    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_FINISHED, "Finished"),
        (STATUS_FAILED, "Failed"),
        (STATUS_KILLED, "Killed"),
    ]

    experiment = models.ForeignKey(
        Experiment, on_delete=models.CASCADE, related_name="runs"
    )
    name = models.CharField(max_length=255, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_RUNNING, db_index=True
    )
    params = models.JSONField(default=dict, blank=True, help_text="Hyperparameters")
    metrics = models.JSONField(default=dict, blank=True, help_text="Evaluation metrics")
    tags = models.JSONField(default=dict, blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_run"
        indexes = [
            models.Index(fields=["experiment_id", "status"]),
            models.Index(fields=["tenant_id", "-started_at"]),
        ]

    def __str__(self) -> str:
        return f"Run({self.name or self.id} [{self.status}])"


class RunArtifact(UUIDModel):
    """File artifact produced by a run."""

    run = models.ForeignKey(Run, on_delete=models.CASCADE, related_name="artifacts")
    name = models.CharField(max_length=255)
    artifact_type = models.CharField(
        max_length=50,
        choices=[
            ("model", "Model"),
            ("dataset", "Dataset"),
            ("image", "Image"),
            ("metric", "Metric"),
            ("log", "Log"),
            ("other", "Other"),
        ],
    )
    storage_path = models.CharField(max_length=512)
    size_bytes = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ml_run_artifact"

    def __str__(self) -> str:
        return f"Artifact({self.name} [{self.artifact_type}])"


class RegisteredModel(TenantModel, UUIDModel):
    """Model registry entry."""

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    tags = models.JSONField(default=dict, blank=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_registered_model"
        unique_together = [("tenant_id", "name")]

    def __str__(self) -> str:
        return f"Model({self.name})"


class ModelVersion(TenantModel, UUIDModel):
    """Versioned model in the registry."""

    STAGE_NONE = "none"
    STAGE_STAGING = "staging"
    STAGE_PRODUCTION = "production"
    STAGE_ARCHIVED = "archived"
    STAGE_CHOICES = [
        (STAGE_NONE, "None"),
        (STAGE_STAGING, "Staging"),
        (STAGE_PRODUCTION, "Production"),
        (STAGE_ARCHIVED, "Archived"),
    ]

    registered_model = models.ForeignKey(
        RegisteredModel, on_delete=models.CASCADE, related_name="versions"
    )
    version = models.PositiveIntegerField()
    stage = models.CharField(
        max_length=20, choices=STAGE_CHOICES, default=STAGE_NONE, db_index=True
    )
    status = models.CharField(max_length=20, default="ready")
    run = models.ForeignKey(Run, on_delete=models.SET_NULL, null=True, blank=True)
    storage_path = models.CharField(max_length=512, blank=True)
    metrics = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True, default="")

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_model_version"
        unique_together = [("registered_model_id", "version")]

    def __str__(self) -> str:
        return f"ModelVersion({self.registered_model.name} v{self.version} [{self.stage}])"


class ModelEndpoint(TenantModel, UUIDModel):
    """Real-time model serving endpoint."""

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    name = models.CharField(max_length=255, db_index=True)
    model_version = models.ForeignKey(
        ModelVersion, on_delete=models.SET_NULL, null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_INACTIVE, db_index=True
    )
    config = models.JSONField(
        default=dict, blank=True,
        help_text='Endpoint config: {"timeout_ms": 5000, "max_batch_size": 32}',
    )
    endpoint_path = models.CharField(max_length=255, blank=True)
    invocation_count = models.PositiveIntegerField(default=0)
    avg_latency_ms = models.FloatField(default=0.0)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_model_endpoint"

    def __str__(self) -> str:
        return f"Endpoint({self.name} [{self.status}])"
