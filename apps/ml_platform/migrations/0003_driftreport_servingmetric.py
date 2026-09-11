# Generated migration for DriftReport and ServingMetric models.

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ml_platform", "0002_agentdefinition_agentevaluation"),
    ]

    operations = [
        migrations.CreateModel(
            name="DriftReport",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "tenant_id",
                    models.CharField(
                        db_index=True,
                        help_text="Tenant identifier for multi-tenancy isolation",
                        max_length=128,
                    ),
                ),
                (
                    "feature_name",
                    models.CharField(
                        db_index=True,
                        help_text="Name of the feature being tested for drift",
                        max_length=255,
                    ),
                ),
                (
                    "drift_metric",
                    models.CharField(
                        help_text="Statistical test used: ks_statistic, chi_square, or psi",
                        max_length=50,
                    ),
                ),
                (
                    "drift_value",
                    models.FloatField(
                        help_text="Computed drift metric value",
                    ),
                ),
                (
                    "threshold",
                    models.FloatField(
                        help_text="Threshold above which drift is flagged",
                    ),
                ),
                (
                    "is_drifted",
                    models.BooleanField(
                        db_index=True,
                        default=False,
                        help_text="True if drift_value exceeds threshold",
                    ),
                ),
                (
                    "details",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Additional details: p-values, bin counts, sample sizes, etc.",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        auto_now_add=True,
                        db_index=True,
                    ),
                ),
                (
                    "deployment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="drift_reports",
                        to="ml_platform.modelendpoint",
                    ),
                ),
            ],
            options={
                "db_table": "ml_drift_report",
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["deployment", "-timestamp"],
                        name="idx_drift_deploy_time",
                    ),
                    models.Index(
                        fields=["tenant_id", "is_drifted"],
                        name="idx_drift_tenant_flag",
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name="ServingMetric",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="Unique identifier (UUID)",
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(
                        db_index=True,
                        help_text="Start of the aggregation bucket (minute granularity)",
                    ),
                ),
                (
                    "latency_p50",
                    models.FloatField(
                        default=0.0,
                        help_text="Median latency in milliseconds",
                    ),
                ),
                (
                    "latency_p95",
                    models.FloatField(
                        default=0.0,
                        help_text="95th percentile latency in milliseconds",
                    ),
                ),
                (
                    "latency_p99",
                    models.FloatField(
                        default=0.0,
                        help_text="99th percentile latency in milliseconds",
                    ),
                ),
                (
                    "throughput_rps",
                    models.FloatField(
                        default=0.0,
                        help_text="Requests per second in this bucket",
                    ),
                ),
                (
                    "error_rate",
                    models.FloatField(
                        default=0.0,
                        help_text="Fraction of requests that errored (0.0\u20131.0)",
                    ),
                ),
                (
                    "request_count",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Total requests in this bucket",
                    ),
                ),
                (
                    "deployment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="serving_metrics",
                        to="ml_platform.modelendpoint",
                    ),
                ),
            ],
            options={
                "db_table": "ml_serving_metric",
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["deployment", "-timestamp"],
                        name="idx_serving_deploy_time",
                    ),
                ],
            },
        ),
    ]
