"""
ML Platform — Django ORM Models.

MLflow-compatible models for experiment tracking, model registry,
and model serving. Part of Voyant v4.0 Phase 3.
"""

from __future__ import annotations

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

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
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
        return (
            f"ModelVersion({self.registered_model.name} v{self.version} [{self.stage}])"
        )


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
        default=dict,
        blank=True,
        help_text='Endpoint config: {"timeout_ms": 5000, "max_batch_size": 32}',
    )
    endpoint_path = models.CharField(max_length=255, blank=True)
    invocation_count = models.PositiveIntegerField(default=0)
    avg_latency_ms = models.FloatField(default=0.0)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_model_endpoint"

    def __str__(self) -> str:
        return f"Endpoint({self.name} [{self.status}])"


class AgentDefinition(TenantModel, UUIDModel):
    """AI agent definition with prompt, model, tools, and guardrails."""

    name = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=[("draft", "Draft"), ("active", "Active"), ("archived", "Archived")],
        default="draft",
        db_index=True,
    )

    system_prompt = models.TextField(help_text="System prompt for the agent")
    model_provider = models.CharField(
        max_length=100, default="groq", help_text="LLM provider"
    )
    model_name = models.CharField(
        max_length=255, default="openai/gpt-oss-120b", help_text="Model identifier"
    )
    temperature = models.FloatField(default=0.1)
    max_tokens = models.IntegerField(default=4096)

    tools = models.JSONField(
        default=list,
        blank=True,
        help_text='List of allowed MCP tools: ["voyant.sql", "voyant.search", ...]',
    )
    guardrails = models.JSONField(
        default=dict,
        blank=True,
        help_text='Safety rules: {"max_queries_per_session": 50, "blocked_tables": [], "require_approval": false}',
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_agent_definition"
        unique_together = [("tenant_id", "name")]

    def __str__(self) -> str:
        return f"Agent({self.name} [{self.status}])"


class AgentEvaluation(TenantModel, UUIDModel):
    """Test cases and scores for evaluating agent quality."""

    agent = models.ForeignKey(
        AgentDefinition, on_delete=models.CASCADE, related_name="evaluations"
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("running", "Running"),
            ("completed", "Completed"),
        ],
        default="pending",
        db_index=True,
    )

    test_cases = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"input": "query", "expected": "answer", "tools_used": ["voyant.sql"]}]',
    )
    results = models.JSONField(
        default=list,
        blank=True,
        help_text='[{"input": "...", "output": "...", "score": 0.95, "judge_notes": "..."}]',
    )
    overall_score = models.FloatField(
        null=True, blank=True, help_text="0.0-1.0 aggregate score"
    )
    judge_model = models.CharField(
        max_length=255, default="openai/gpt-oss-120b", help_text="AI judge model"
    )
    run_count = models.PositiveIntegerField(default=0)
    passed_count = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ml_agent_evaluation"

    def __str__(self) -> str:
        return f"Eval({self.name} [{self.status}] score={self.overall_score})"


# ── Serving & Drift Monitoring Models ────────────────────────────────────────


class DriftReport(UUIDModel):
    """
    Per-feature drift measurement for a deployed model.

    Stores the result of a statistical drift test (KS test, chi-square, or PSI)
    for a single feature at a point in time.
    """

    deployment = models.ForeignKey(
        ModelEndpoint,
        on_delete=models.CASCADE,
        related_name="drift_reports",
    )
    tenant_id = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Tenant identifier for multi-tenancy isolation",
    )
    feature_name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Name of the feature being tested for drift",
    )
    drift_metric = models.CharField(
        max_length=50,
        help_text="Statistical test used: ks_statistic, chi_square, or psi",
    )
    drift_value = models.FloatField(
        help_text="Computed drift metric value",
    )
    threshold = models.FloatField(
        help_text="Threshold above which drift is flagged",
    )
    is_drifted = models.BooleanField(
        default=False,
        db_index=True,
        help_text="True if drift_value exceeds threshold",
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional details: p-values, bin counts, sample sizes, etc.",
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "ml_drift_report"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(
                fields=["deployment", "-timestamp"],
                name="idx_drift_deploy_time",
            ),
            models.Index(
                fields=["tenant_id", "is_drifted"],
                name="idx_drift_tenant_flag",
            ),
        ]

    def __str__(self) -> str:
        status = "DRIFTED" if self.is_drifted else "ok"
        return f"Drift({self.feature_name} [{self.drift_metric}={self.drift_value:.4f}] {status})"


class ServingMetric(UUIDModel):
    """
    Aggregated serving performance metrics for a deployed model.

    Stored in per-minute time buckets. Tracks latency percentiles,
    throughput, error rate, and request count.
    """

    deployment = models.ForeignKey(
        ModelEndpoint,
        on_delete=models.CASCADE,
        related_name="serving_metrics",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="Start of the aggregation bucket (minute granularity)",
    )
    latency_p50 = models.FloatField(
        default=0.0,
        help_text="Median latency in milliseconds",
    )
    latency_p95 = models.FloatField(
        default=0.0,
        help_text="95th percentile latency in milliseconds",
    )
    latency_p99 = models.FloatField(
        default=0.0,
        help_text="99th percentile latency in milliseconds",
    )
    throughput_rps = models.FloatField(
        default=0.0,
        help_text="Requests per second in this bucket",
    )
    error_rate = models.FloatField(
        default=0.0,
        help_text="Fraction of requests that errored (0.0–1.0)",
    )
    request_count = models.PositiveIntegerField(
        default=0,
        help_text="Total requests in this bucket",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "ml_serving_metric"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(
                fields=["deployment", "-timestamp"],
                name="idx_serving_deploy_time",
            ),
        ]

    def __str__(self) -> str:
        return f"ServingMetric({self.deployment_id} @ {self.timestamp} rps={self.throughput_rps:.1f})"
