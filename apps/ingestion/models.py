"""Data ingestion models."""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel


class Source(TenantModel, UUIDModel):
    """
    Represents an external data source that Voyant can connect to.

    A Source can be a database, API, file storage, or any other data provider.
    """

    class SourceType(models.TextChoices):
        """Supported data source types."""

        POSTGRES = "postgres", "PostgreSQL"
        MYSQL = "mysql", "MySQL"
        MONGODB = "mongodb", "MongoDB"
        REST_API = "rest_api", "REST API"
        GRAPHQL = "graphql", "GraphQL"
        CSV = "csv", "CSV File"
        JSON = "json", "JSON File"
        PARQUET = "parquet", "Parquet File"
        S3 = "s3", "Amazon S3"
        SNOWFLAKE = "snowflake", "Snowflake"
        BIGQUERY = "bigquery", "BigQuery"
        REDSHIFT = "redshift", "Redshift"
        UNKNOWN = "unknown", "Unknown"

    class Status(models.TextChoices):
        """Source connection status."""

        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        ERROR = "error", "Error"
        TESTING = "testing", "Testing"

    source_type = models.CharField(
        max_length=32,
        choices=SourceType.choices,
        default=SourceType.UNKNOWN,
        db_index=True,
        help_text="Type of data source",
    )
    name = models.CharField(
        max_length=255,
        help_text="Human-readable name for the source",
    )
    config = models.JSONField(
        default=dict,
        help_text="Source-specific configuration (connection strings, credentials, etc.)",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
        help_text="Current status of the source",
    )
    last_connected_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last successful connection",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if connection failed",
    )
    metadata = models.JSONField(
        default=dict,
        help_text="Additional metadata about the source",
    )

    class Meta:
        db_table = "voyant_source"
        verbose_name = "Data Source"
        verbose_name_plural = "Data Sources"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "source_type", "-created_at"]),
            models.Index(fields=["tenant_id", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                name="unique_source_name_per_tenant",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.source_type})"


class IngestionJob(TenantModel, UUIDModel):
    """
    Represents a data ingestion job that loads data from a Source.

    Tracks the progress and status of data ingestion operations.
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
        Source,
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
