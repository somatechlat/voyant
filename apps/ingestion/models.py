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

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
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


# =============================================================================
# CDC (Change Data Capture) Models
# =============================================================================


class CDCConnection(TenantModel, UUIDModel):
    """
    Represents an active CDC (Change Data Capture) stream from a source.

    Tracks the replication slot, publication, current status, and
    watermark (last processed LSN) for a PostgreSQL logical-replication
    based CDC session.
    """

    class Status(models.TextChoices):
        """CDC connection lifecycle states."""

        CREATED = "created", "Created"
        STARTING = "starting", "Starting"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        FAILED = "failed", "Failed"
        STOPPED = "stopped", "Stopped"

    source = models.ForeignKey(
        "discovery.Source",
        on_delete=models.CASCADE,
        related_name="cdc_connections",
        help_text="Source this CDC connection monitors",
    )
    workflow_instance_id = models.CharField(
        max_length=255,
        blank=True,
        db_index=True,
        help_text="Temporal workflow instance ID driving this CDC stream",
    )
    replication_slot = models.CharField(
        max_length=128,
        default="voyant_cdc_slot",
        help_text="PostgreSQL logical replication slot name",
    )
    publication_name = models.CharField(
        max_length=128,
        default="voyant_cdc_pub",
        help_text="PostgreSQL publication name",
    )
    tables = models.JSONField(
        default=list,
        blank=True,
        help_text="List of table names to monitor (empty = all tables)",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.CREATED,
        db_index=True,
        help_text="Current CDC connection status",
    )
    last_lsn = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="Last acknowledged WAL Log Sequence Number (watermark)",
    )
    last_sync_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last processed change event",
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if the CDC stream failed",
    )
    config = models.JSONField(
        default=dict,
        blank=True,
        help_text="CDC-specific configuration (connection string, batch size, etc.)",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_cdc_connection"
        verbose_name = "CDC Connection"
        verbose_name_plural = "CDC Connections"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "-created_at"]),
            models.Index(fields=["source", "status"]),
            models.Index(fields=["workflow_instance_id"]),
        ]

    def __str__(self) -> str:
        return f"CDC {self.source_id} [{self.status}]"


class CDCChangeEvent(TenantModel, UUIDModel):
    """
    A single change event captured by a CDC connection.

    Stores the normalized before/after row data, operation type, and
    WAL position for replay and auditability.
    """

    class Operation(models.TextChoices):
        """Type of change operation."""

        INSERT = "INSERT", "Insert"
        UPDATE = "UPDATE", "Update"
        DELETE = "DELETE", "Delete"

    connection = models.ForeignKey(
        CDCConnection,
        on_delete=models.CASCADE,
        related_name="change_events",
        help_text="CDC connection that captured this change",
    )
    operation = models.CharField(
        max_length=8,
        choices=Operation.choices,
        db_index=True,
        help_text="Type of change operation",
    )
    table_name = models.CharField(
        max_length=256,
        db_index=True,
        help_text="Source table that changed",
    )
    schema_name = models.CharField(
        max_length=128,
        default="public",
        help_text="Source schema name",
    )
    primary_key = models.JSONField(
        null=True,
        blank=True,
        help_text="Primary key value(s) of the affected row",
    )
    before_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Row data before the change (null for INSERTs)",
    )
    after_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Row data after the change (null for DELETEs)",
    )
    lsn = models.CharField(
        max_length=64,
        blank=True,
        default="",
        db_index=True,
        help_text="WAL Log Sequence Number of this change",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="When the change was captured (from the source)",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_cdc_change_event"
        verbose_name = "CDC Change Event"
        verbose_name_plural = "CDC Change Events"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["connection", "operation", "-timestamp"]),
            models.Index(fields=["tenant_id", "table_name", "-timestamp"]),
            models.Index(fields=["connection", "lsn"]),
        ]

    def __str__(self) -> str:
        return f"{self.operation} on {self.schema_name}.{self.table_name} @ {self.lsn}"
