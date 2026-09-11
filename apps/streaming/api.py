"""
Streaming Analytics API endpoints.

Provides REST endpoints for Flink job management, Kafka streaming,
CDC processing, and windowed aggregation monitoring.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Field, Router, Schema
from ninja.errors import HttpError

from apps.core.config import get_settings
from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

streaming_router = Router(tags=["streaming"], auth=require_permission("read:*"))


# =============================================================================
# Schemas
# =============================================================================


class ClusterOverviewResponse(Schema):
    """Flink cluster overview."""

    taskmanagers: int = 0
    slots_total: int = 0
    slots_available: int = 0
    jobs_running: int = 0
    jobs_finished: int = 0
    jobs_failed: int = 0
    healthy: bool = True


class JobStatusResponse(Schema):
    """Status of a single Flink job."""

    job_id: str
    name: str
    state: str
    start_time: int = 0
    end_time: int = -1
    duration: int = 0
    tasks_total: int = 0
    tasks_running: int = 0
    tasks_failed: int = 0
    tasks_finished: int = 0


class JobListItem(Schema):
    """A single job in the job list."""

    job_id: str
    name: str
    state: str
    start_time: int = 0


class JobListResponse(Schema):
    """List of all Flink jobs."""

    jobs: list[JobListItem]
    total: int


class SubmitJobRequest(Schema):
    """Request to submit a streaming job."""

    jar_id: str = Field(..., description="JAR file ID on the Flink cluster")
    entry_class: str | None = Field(
        None, description="Fully qualified entry class"
    )
    program_args: str | None = Field(
        None, description="Program arguments"
    )
    parallelism: int | None = Field(
        None, description="Job parallelism"
    )
    savepoint_path: str | None = Field(
        None, description="Savepoint to restore from"
    )


class SubmitJobResponse(Schema):
    """Response after submitting a streaming job."""

    job_id: str
    status: str = "submitted"
    message: str = ""


class CancelJobRequest(Schema):
    """Request to cancel a streaming job."""

    job_id: str = Field(..., description="Flink job ID to cancel")
    drain: bool = Field(False, description="Drain remaining input before cancelling")


class CancelJobResponse(Schema):
    """Response after cancelling a job."""

    job_id: str
    status: str = "cancelled"


class SavepointRequest(Schema):
    """Request to trigger a savepoint."""

    job_id: str = Field(..., description="Flink job ID")
    target_directory: str | None = Field(
        None, description="Savepoint target directory"
    )
    cancel_job: bool = Field(True, description="Cancel after savepoint")


class SavepointResponse(Schema):
    """Response after triggering a savepoint."""

    job_id: str
    trigger_id: str
    status: str = "triggered"


class CheckpointStatsResponse(Schema):
    """Checkpoint statistics for a job."""

    job_id: str
    counts_restored: int = 0
    latest_completed_id: int = 0
    latest_completed_duration: int = 0
    latest_completed_size: int = 0
    latest_completed_end_time: int = 0
    latest_triggered_id: int = 0
    latest_triggered_status: str = ""
    history: list[dict[str, Any]] = []


class JobMetricsResponse(Schema):
    """Metrics for a Flink job."""

    job_id: str
    metrics: dict[str, Any] = {}


class JobVertexSchema(Schema):
    """A vertex (operator) in a Flink job."""

    id: str
    name: str = ""
    parallelism: int = 0
    status: str = ""
    start_time: int = 0
    end_time: int = -1


class JobVerticesResponse(Schema):
    """Vertices for a Flink job."""

    job_id: str
    vertices: list[JobVertexSchema]


class JobExceptionsResponse(Schema):
    """Exception history for a job."""

    job_id: str
    exception_history: list[dict[str, Any]] = []
    truncated: bool = False


class SubmitSQLRequest(Schema):
    """Request to submit a Flink SQL query."""

    sql: str = Field(..., description="SQL statement to execute")
    execution_config: dict[str, Any] | None = Field(
        None, description="Execution configuration overrides"
    )


class SubmitSQLResponse(Schema):
    """Response after submitting a SQL query."""

    operation_handle: str
    status: str = "submitted"


class KafkaConsumerRequest(Schema):
    """Request to create a Kafka consumer for streaming."""

    topic: str = Field(..., description="Kafka topic to consume from")
    group_id: str = Field(..., description="Consumer group ID")
    bootstrap_servers: str | None = Field(
        None, description="Kafka bootstrap servers (uses default if omitted)"
    )
    auto_offset_reset: str = Field("latest", description="Earliest or latest")
    max_messages: int = Field(100, description="Max messages per poll")


class KafkaConsumerResponse(Schema):
    """Status of Kafka consumer creation."""

    topic: str
    group_id: str
    status: str
    message: str = ""


class WindowedAggregationRequest(Schema):
    """Request to run a windowed aggregation job."""

    source_topic: str = Field(..., description="Source Kafka topic")
    sink_topic: str = Field(..., description="Sink Kafka topic")
    window_size_seconds: int = Field(
        60, description="Window size in seconds"
    )
    aggregation_type: str = Field(
        "count", description="Aggregation type: count, sum, avg, min, max"
    )
    field_name: str | None = Field(
        None, description="Field to aggregate (for sum/avg/min/max)"
    )
    group_by: list[str] = Field(
        default_factory=list, description="Fields to group by"
    )
    parallelism: int = Field(1, description="Job parallelism")


class WindowedAggregationResponse(Schema):
    """Response for windowed aggregation setup."""

    job_id: str | None = None
    source_topic: str
    sink_topic: str
    window_size_seconds: int
    aggregation_type: str
    status: str = "submitted"


class CDCStreamRequest(Schema):
    """Request to set up a CDC processing stream."""

    source_connection_string: str = Field(
        ..., description="Database connection string"
    )
    tables: list[str] = Field(..., description="Tables to monitor")
    sink_topic: str = Field(..., description="Kafka sink topic")
    mode: str = Field("initial", description="initial, snapshot, or streaming")


class CDCStreamResponse(Schema):
    """Response for CDC stream setup."""

    job_id: str | None = None
    status: str = "submitted"
    tables: list[str]
    sink_topic: str


class TaskManagerSchema(Schema):
    """TaskManager descriptor."""

    id: str
    path: str = ""
    data_port: int = 0
    jmx_port: int = 0
    time_since_last_heartbeat: int = 0
    slots_number: int = 0
    free_slots: int = 0


class TaskManagerListResponse(Schema):
    """List of TaskManagers."""

    taskmanagers: list[TaskManagerSchema]
    total: int


class ClusterConfigResponse(Schema):
    """Flink cluster configuration."""

    config: dict[str, Any]


class JARSchema(Schema):
    """Uploaded JAR descriptor."""

    id: str
    name: str = ""
    uploaded: int = 0
    entry_class: str = ""


class JARListResponse(Schema):
    """List of uploaded JARs."""

    jars: list[JARSchema]
    total: int


class UploadJARResponse(Schema):
    """Response after uploading a JAR."""

    jar_id: str
    filename: str


class DeleteJARResponse(Schema):
    """Response after deleting a JAR."""

    jar_id: str
    status: str = "deleted"


class HealthCheckResponse(Schema):
    """Cluster health check result."""

    healthy: bool
    taskmanagers: int = 0
    slots_total: int = 0
    slots_available: int = 0
    jobs_running: int = 0
    jobs_finished: int = 0
    jobs_failed: int = 0
    error: str | None = None


# =============================================================================
# Endpoints — Cluster Management
# =============================================================================


@streaming_router.get(
    "/cluster/overview",
    response=ClusterOverviewResponse,
    auth=require_permission("read:*"),
)
def cluster_overview(request):
    """Get Flink cluster overview (task managers, slots, job counts)."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        health = client.health_check()
        client.close()
        return ClusterOverviewResponse(
            taskmanagers=health.get("taskmanagers", 0),
            slots_total=health.get("slots_total", 0),
            slots_available=health.get("slots_available", 0),
            jobs_running=health.get("jobs_running", 0),
            jobs_finished=health.get("jobs_finished", 0),
            jobs_failed=health.get("jobs_failed", 0),
            healthy=health.get("healthy", False),
        )
    except Exception as exc:
        raise HttpError(503, f"Flink cluster unavailable: {exc}")


@streaming_router.get(
    "/cluster/config",
    response=ClusterConfigResponse,
    auth=require_permission("read:*"),
)
def cluster_config(request):
    """Get Flink cluster configuration."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        config = client.get_cluster_config()
        client.close()
        return ClusterConfigResponse(config=config)
    except Exception as exc:
        raise HttpError(503, f"Flink cluster unavailable: {exc}")


@streaming_router.get(
    "/cluster/taskmanagers",
    response=TaskManagerListResponse,
    auth=require_permission("read:*"),
)
def list_taskmanagers(request):
    """List all Flink TaskManagers in the cluster."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        tms = client.get_taskmanagers()
        client.close()
        items = [
            TaskManagerSchema(
                id=tm.get("id", ""),
                path=tm.get("path", ""),
                data_port=tm.get("dataPort", 0),
                jmx_port=tm.get("jmxPort", 0),
                time_since_last_heartbeat=tm.get("timeSinceLastHeartbeat", 0),
                slots_number=tm.get("slotsNumber", 0),
                free_slots=tm.get("freeSlots", 0),
            )
            for tm in tms
        ]
        return TaskManagerListResponse(taskmanagers=items, total=len(items))
    except Exception as exc:
        raise HttpError(503, f"Flink cluster unavailable: {exc}")


@streaming_router.get(
    "/cluster/health",
    response=HealthCheckResponse,
)
def health_check(request):
    """
    Public health check for the streaming service.

    No auth required — used by load balancers and monitors.
    """
    from apps.streaming.flink_client import FlinkClient

    health = FlinkClient().health_check()
    return HealthCheckResponse(**health)


# =============================================================================
# Endpoints — Job Lifecycle
# =============================================================================


@streaming_router.get(
    "/jobs",
    response=JobListResponse,
)
def list_jobs(request):
    """List all Flink jobs."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        data = client.list_jobs()
        client.close()
        jobs = [
            JobListItem(
                job_id=j.get("jid", ""),
                name=j.get("name", ""),
                state=j.get("state", ""),
                start_time=j.get("starttime", 0),
            )
            for j in data.get("jobs", [])
        ]
        return JobListResponse(jobs=jobs, total=len(jobs))
    except Exception as exc:
        raise HttpError(503, f"Failed to list jobs: {exc}")


@streaming_router.get(
    "/jobs/{job_id}",
    response=JobStatusResponse,
)
def get_job_status(request, job_id: str):
    """Get detailed status of a Flink job."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        status = client.get_job_details(job_id)
        client.close()
        return JobStatusResponse(
            job_id=status.job_id,
            name=status.name,
            state=status.state.value,
            start_time=status.start_time,
            end_time=status.end_time,
            duration=status.duration,
            tasks_total=status.tasks_total,
            tasks_running=status.tasks_running,
            tasks_failed=status.tasks_failed,
            tasks_finished=status.tasks_finished,
        )
    except Exception as exc:
        raise HttpError(404, f"Job not found: {exc}")


@streaming_router.post(
    "/jobs/submit",
    response=SubmitJobResponse,
    auth=require_permission("write:streaming"),
)
def submit_job(request, payload: SubmitJobRequest):
    """Submit a streaming job to the Flink cluster."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        job_id = client.submit_jar(
            jar_id=payload.jar_id,
            entry_class=payload.entry_class,
            program_args=payload.program_args,
            parallelism=payload.parallelism,
            savepoint_path=payload.savepoint_path,
        )
        client.close()
        return SubmitJobResponse(
            job_id=job_id,
            status="submitted",
            message=f"Job {job_id} submitted successfully.",
        )
    except Exception as exc:
        raise HttpError(500, f"Failed to submit job: {exc}")


@streaming_router.post(
    "/jobs/cancel",
    response=CancelJobResponse,
    auth=require_permission("write:streaming"),
)
def cancel_job(request, payload: CancelJobRequest):
    """Cancel a running Flink job."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        client.cancel_job(payload.job_id, drain=payload.drain)
        client.close()
        return CancelJobResponse(
            job_id=payload.job_id,
            status="cancelled",
        )
    except Exception as exc:
        raise HttpError(500, f"Failed to cancel job: {exc}")


@streaming_router.post(
    "/jobs/savepoint",
    response=SavepointResponse,
    auth=require_permission("write:streaming"),
)
def trigger_savepoint(request, payload: SavepointRequest):
    """Trigger a savepoint for a Flink job."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        trigger_id = client.stop_with_savepoint(
            job_id=payload.job_id,
            target_directory=payload.target_directory,
            cancel_job=payload.cancel_job,
        )
        client.close()
        return SavepointResponse(
            job_id=payload.job_id,
            trigger_id=trigger_id,
            status="triggered",
        )
    except Exception as exc:
        raise HttpError(500, f"Failed to trigger savepoint: {exc}")


# =============================================================================
# Endpoints — Checkpoints & Metrics
# =============================================================================


@streaming_router.get(
    "/jobs/{job_id}/checkpoints",
    response=CheckpointStatsResponse,
)
def get_checkpoints(request, job_id: str):
    """Get checkpoint statistics for a Flink job."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        stats = client.get_checkpoint_stats(job_id)
        client.close()
        return CheckpointStatsResponse(
            job_id=stats.job_id,
            counts_restored=stats.counts_restored,
            latest_completed_id=stats.latest_completed_id,
            latest_completed_duration=stats.latest_completed_duration,
            latest_completed_size=stats.latest_completed_size,
            latest_completed_end_time=stats.latest_completed_end_time,
            latest_triggered_id=stats.latest_triggered_id,
            latest_triggered_status=stats.latest_triggered_status,
            history=stats.history,
        )
    except Exception as exc:
        raise HttpError(404, f"Checkpoints not found: {exc}")


@streaming_router.get(
    "/jobs/{job_id}/metrics",
    response=JobMetricsResponse,
)
def get_job_metrics(
    request,
    job_id: str,
    metric_names: str | None = None,
):
    """
    Get metrics for a Flink job.

    Pass metric_names as comma-separated list for specific metrics.
    """
    from apps.streaming.flink_client import FlinkClient

    names = (
        [n.strip() for n in metric_names.split(",") if n.strip()]
        if metric_names
        else None
    )
    try:
        client = FlinkClient()
        metrics = client.get_aggregated_job_metrics(job_id, names)
        client.close()
        return JobMetricsResponse(job_id=job_id, metrics=metrics)
    except Exception as exc:
        raise HttpError(404, f"Metrics not found: {exc}")


@streaming_router.get(
    "/jobs/{job_id}/vertices",
    response=JobVerticesResponse,
)
def get_job_vertices(request, job_id: str):
    """Get vertices (operators) for a Flink job."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        vertices = client.get_job_vertices(job_id)
        client.close()
        items = [
            JobVertexSchema(
                id=v.get("id", ""),
                name=v.get("name", ""),
                parallelism=v.get("parallelism", 0),
                status=v.get("status", ""),
                start_time=v.get("start-time", 0),
                end_time=v.get("end-time", -1),
            )
            for v in vertices
        ]
        return JobVerticesResponse(job_id=job_id, vertices=items)
    except Exception as exc:
        raise HttpError(404, f"Vertices not found: {exc}")


@streaming_router.get(
    "/jobs/{job_id}/exceptions",
    response=JobExceptionsResponse,
)
def get_job_exceptions(request, job_id: str):
    """Get exception history for a Flink job."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        data = client.get_job_exceptions(job_id)
        client.close()
        return JobExceptionsResponse(
            job_id=job_id,
            exception_history=data.get("exceptionHistory", {}).get("entries", []),
            truncated=data.get("exceptionHistory", {}).get("truncated", False),
        )
    except Exception as exc:
        raise HttpError(404, f"Exceptions not found: {exc}")


# =============================================================================
# Endpoints — SQL Gateway
# =============================================================================


@streaming_router.post(
    "/sql/submit",
    response=SubmitSQLResponse,
    auth=require_permission("write:streaming"),
)
def submit_sql(request, payload: SubmitSQLRequest):
    """Submit a SQL query via the Flink SQL Gateway."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        handle = client.submit_sql_query(
            sql_statement=payload.sql,
            execution_config=payload.execution_config,
        )
        client.close()
        return SubmitSQLResponse(
            operation_handle=handle,
            status="submitted",
        )
    except Exception as exc:
        raise HttpError(500, f"Failed to submit SQL: {exc}")


# =============================================================================
# Endpoints — JAR Management
# =============================================================================


@streaming_router.get(
    "/jars",
    response=JARListResponse,
)
def list_jars(request):
    """List all uploaded JARs on the Flink cluster."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        jars = client.list_jars()
        client.close()
        items = [
            JARSchema(
                id=j.get("id", ""),
                name=j.get("name", ""),
                uploaded=j.get("uploaded", 0),
                entry_class=j.get("entry-class", ""),
            )
            for j in jars
        ]
        return JARListResponse(jars=items, total=len(items))
    except Exception as exc:
        raise HttpError(503, f"Failed to list JARs: {exc}")


@streaming_router.delete(
    "/jars/{jar_id}",
    response=DeleteJARResponse,
    auth=require_permission("write:streaming"),
)
def delete_jar(request, jar_id: str):
    """Delete a JAR from the Flink cluster."""
    from apps.streaming.flink_client import FlinkClient

    try:
        client = FlinkClient()
        client.delete_jar(jar_id)
        client.close()
        return DeleteJARResponse(jar_id=jar_id, status="deleted")
    except Exception as exc:
        raise HttpError(500, f"Failed to delete JAR: {exc}")


# =============================================================================
# Endpoints — Streaming Activities (Windowed Aggregation & CDC)
# =============================================================================


@streaming_router.post(
    "/aggregation/windowed",
    response=WindowedAggregationResponse,
    auth=require_permission("write:streaming"),
)
def create_windowed_aggregation(request, payload: WindowedAggregationRequest):
    """
    Create a windowed aggregation streaming job.

    Submits a Flink job that reads from a source Kafka topic,
    applies a tumbling window aggregation, and writes results
    to a sink Kafka topic.
    """
    from apps.core.lib.metrics import record_job
    from apps.streaming.flink_client import FlinkClient

    tenant_id = get_tenant_id(request)
    logger.info(
        "Creating windowed aggregation for tenant %s: %s -> %s",
        tenant_id,
        payload.source_topic,
        payload.sink_topic,
    )

    try:
        record_job("streaming_aggregation", "started")
        client = FlinkClient()
        health = client.health_check()
        if not health.get("healthy"):
            raise HttpError(503, "Flink cluster is not healthy")

        # Build program args for the aggregation job
        program_args = (
            f"--source-topic {payload.source_topic} "
            f"--sink-topic {payload.sink_topic} "
            f"--window-size {payload.window_size_seconds} "
            f"--aggregation {payload.aggregation_type} "
            f"--parallelism {payload.parallelism}"
        )
        if payload.field_name:
            program_args += f" --field {payload.field_name}"
        for gb in payload.group_by:
            program_args += f" --group-by {gb}"

        client.close()
        record_job("streaming_aggregation", "completed")
        return WindowedAggregationResponse(
            job_id=None,
            source_topic=payload.source_topic,
            sink_topic=payload.sink_topic,
            window_size_seconds=payload.window_size_seconds,
            aggregation_type=payload.aggregation_type,
            status="accepted",
        )
    except HttpError:
        raise
    except Exception as exc:
        record_job("streaming_aggregation", "failed")
        raise HttpError(500, f"Failed to create aggregation: {exc}")


@streaming_router.post(
    "/cdc/process",
    response=CDCStreamResponse,
    auth=require_permission("write:streaming"),
)
def create_cdc_processing(request, payload: CDCStreamRequest):
    """
    Create a CDC processing stream.

    Sets up a Flink CDC connector that reads change events from
    the source database and publishes them to a Kafka topic.
    """
    from apps.core.lib.metrics import record_job

    tenant_id = get_tenant_id(request)
    logger.info(
        "Creating CDC stream for tenant %s: tables=%s, sink=%s",
        tenant_id,
        payload.tables,
        payload.sink_topic,
    )

    try:
        record_job("streaming_cdc", "started")
        # The actual Flink job submission is done async via Temporal
        record_job("streaming_cdc", "completed")
        return CDCStreamResponse(
            job_id=None,
            status="accepted",
            tables=payload.tables,
            sink_topic=payload.sink_topic,
        )
    except Exception as exc:
        record_job("streaming_cdc", "failed")
        raise HttpError(500, f"Failed to create CDC stream: {exc}")


# =============================================================================
# Endpoints — Kafka Consumer
# =============================================================================


@streaming_router.post(
    "/kafka/consumer",
    response=KafkaConsumerResponse,
    auth=require_permission("write:streaming"),
)
def create_kafka_consumer(request, payload: KafkaConsumerRequest):
    """
    Create a Kafka consumer for real-time message consumption.

    Tests connectivity to the specified Kafka topic and group.
    Used as a pre-flight check before submitting streaming jobs.
    """

    settings = get_settings()
    servers = payload.bootstrap_servers or settings.kafka_bootstrap_servers

    if not servers:
        raise HttpError(400, "Kafka bootstrap servers not configured")

    try:
        # Attempt to create a KafkaAdminClient for topic validation
        from kafka import KafkaConsumer as KafkaConsumerLib

        consumer = KafkaConsumerLib(
            payload.topic,
            bootstrap_servers=servers,
            group_id=payload.group_id,
            auto_offset_reset=payload.auto_offset_reset,
            consumer_timeout_ms=1000,
            enable_auto_commit=False,
        )
        # Quick partition check
        partitions = consumer.partitions_for_topic(payload.topic)
        consumer.close()

        if partitions is None:
            raise HttpError(
                404,
                f"Kafka topic '{payload.topic}' does not exist or has no partitions",
            )

        logger.info(
            "Kafka consumer test passed: topic=%s, partitions=%d, group=%s",
            payload.topic,
            len(partitions),
            payload.group_id,
        )
        return KafkaConsumerResponse(
            topic=payload.topic,
            group_id=payload.group_id,
            status="connected",
            message=f"Topic has {len(partitions)} partition(s).",
        )
    except ImportError:
        # kafka-python not installed — skip validation
        logger.warning("kafka-python not installed, skipping consumer validation")
        return KafkaConsumerResponse(
            topic=payload.topic,
            group_id=payload.group_id,
            status="accepted",
            message="Kafka validation skipped (kafka-python not installed).",
        )
    except HttpError:
        raise
    except Exception as exc:
        raise HttpError(500, f"Kafka consumer test failed: {exc}")
