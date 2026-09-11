"""Apache Flink REST API client with full job lifecycle management."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class FlinkClientError(Exception):
    """Base exception for Flink client errors."""


class FlinkJobNotFoundError(FlinkClientError):
    """Raised when a Flink job is not found."""


class FlinkClusterUnavailableError(FlinkClientError):
    """Raised when the Flink cluster is unreachable."""


# =============================================================================
# Enums & Dataclasses
# =============================================================================


class JobState(StrEnum):
    """Flink job lifecycle states."""

    INITIALIZING = "INITIALIZING"
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    FAILING = "FAILING"
    FAILED = "FAILED"
    CANCELLING = "CANCELLING"
    CANCELED = "CANCELED"
    FINISHED = "FINISHED"
    RESTARTING = "RESTARTING"
    SUSPENDED = "SUSPENDED"
    RECONCILING = "RECONCILING"


@dataclass
class FlinkJobStatus:
    """Structured representation of a Flink job status."""

    job_id: str
    name: str
    state: JobState
    start_time: int = 0
    end_time: int = -1
    duration: int = 0
    tasks_total: int = 0
    tasks_running: int = 0
    tasks_failed: int = 0
    tasks_canceling: int = 0
    tasks_canceled: int = 0
    tasks_finished: int = 0

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> FlinkJobStatus:
        """Construct from Flink REST API /jobs/{id} response."""
        tasks = data.get("tasks", {})
        return cls(
            job_id=data.get("jid", ""),
            name=data.get("name", ""),
            state=JobState(data.get("state", "CREATED")),
            start_time=data.get("start-time", 0),
            end_time=data.get("end-time", -1),
            duration=data.get("duration", 0),
            tasks_total=tasks.get("total", 0),
            tasks_running=tasks.get("RUNNING", 0),
            tasks_failed=tasks.get("FAILED", 0),
            tasks_canceling=tasks.get("CANCELING", 0),
            tasks_canceled=tasks.get("CANCELED", 0),
            tasks_finished=tasks.get("FINISHED", 0),
        )


@dataclass
class CheckpointStats:
    """Checkpoint statistics for a Flink job."""

    job_id: str
    counts_restored: int = 0
    latest_completed_id: int = 0
    latest_completed_duration: int = 0
    latest_completed_size: int = 0
    latest_completed_end_time: int = 0
    latest_triggered_id: int = 0
    latest_triggered_status: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_api(cls, job_id: str, data: dict[str, Any]) -> CheckpointStats:
        """Construct from Flink REST API /jobs/{id}/checkpoints response."""
        counts = data.get("counts", {})
        latest = data.get("latest", {})
        completed = latest.get("completed", {})
        triggered = data.get("latest", {}).get("triggered", {})
        history_raw = data.get("history", [])

        return cls(
            job_id=job_id,
            counts_restored=counts.get("restored", 0),
            latest_completed_id=completed.get("id", 0),
            latest_completed_duration=completed.get("duration", 0),
            latest_completed_size=completed.get("size", 0),
            latest_completed_end_time=completed.get("end-to-end-duration", 0),
            latest_triggered_id=triggered.get("id", 0),
            latest_triggered_status=triggered.get("status", ""),
            history=[
                {
                    "id": h.get("id", 0),
                    "status": h.get("status", ""),
                    "duration": h.get("duration", 0),
                    "end_to_end_duration": h.get("end-to-end-duration", 0),
                }
                for h in history_raw[:10]  # Keep last 10
            ],
        )


@dataclass
class JobMetrics:
    """Key metrics for a Flink job."""

    job_id: str
    metrics: dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Flink REST API Client
# =============================================================================


class FlinkClient:
    """
    Full-featured Apache Flink REST API client.

    Provides methods for job submission, cancellation, status monitoring,
    checkpoint tracking, metric retrieval, and cluster management.
    """

    def __init__(self, jobmanager_url: str | None = None):
        settings = get_settings()
        resolved_url = jobmanager_url or settings.flink_jobmanager_url
        if not resolved_url:
            raise ValueError("FLINK_JOBMANAGER_URL must be configured")
        self.base_url = resolved_url.rstrip("/")
        self._client = httpx.Client(timeout=10.0)

    # --------------------------------------------------------------------------
    # Internal helpers
    # --------------------------------------------------------------------------

    def _get(self, path: str, timeout: float = 10.0) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self._client.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError as e:
            raise FlinkClusterUnavailableError(
                f"Flink cluster unreachable at {self.base_url}: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise FlinkJobNotFoundError(f"Resource not found: {path}") from e
            raise FlinkClientError(f"Flink API error on {path}: {e}") from e
        except httpx.RequestError as e:
            raise FlinkClientError(f"Request failed on {path}: {e}") from e

    def _post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self._client.post(url, json=json, timeout=timeout)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.ConnectError as e:
            raise FlinkClusterUnavailableError(
                f"Flink cluster unreachable at {self.base_url}: {e}"
            ) from e
        except httpx.HTTPStatusError as e:
            raise FlinkClientError(f"Flink API error on POST {path}: {e}") from e
        except httpx.RequestError as e:
            raise FlinkClientError(f"Request failed on POST {path}: {e}") from e

    def _patch(self, path: str, timeout: float = 10.0) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self._client.patch(url, timeout=timeout)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.ConnectError as e:
            raise FlinkClusterUnavailableError(
                f"Flink cluster unreachable: {e}"
            ) from e
        except httpx.RequestError as e:
            raise FlinkClientError(f"PATCH failed on {path}: {e}") from e

    def _delete(self, path: str, timeout: float = 10.0) -> Any:
        url = f"{self.base_url}{path}"
        try:
            response = self._client.delete(url, timeout=timeout)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.ConnectError as e:
            raise FlinkClusterUnavailableError(
                f"Flink cluster unreachable: {e}"
            ) from e
        except httpx.RequestError as e:
            raise FlinkClientError(f"DELETE failed on {path}: {e}") from e

    # --------------------------------------------------------------------------
    # Cluster Management
    # --------------------------------------------------------------------------

    def get_overview(self) -> dict[str, Any]:
        """
        Get Flink cluster overview.

        Returns:
            Dict with cluster-level stats: taskmanagers, slots, jobs running, etc.
        """
        return self._get("/overview")

    def get_cluster_config(self) -> dict[str, Any]:
        """
        Get the Flink cluster configuration.

        Returns:
            Dict of cluster configuration key-value pairs.
        """
        return self._get("/config")

    def get_taskmanagers(self) -> list[dict[str, Any]]:
        """
        List all TaskManagers connected to the cluster.

        Returns:
            List of TaskManager descriptors.
        """
        data = self._get("/taskmanagers")
        return data.get("taskmanagers", [])

    def get_taskmanager_details(self, taskmanager_id: str) -> dict[str, Any]:
        """
        Get detailed info for a specific TaskManager.

        Args:
            taskmanager_id: The TaskManager ID.

        Returns:
            Detailed TaskManager metrics and config.
        """
        return self._get(f"/taskmanagers/{taskmanager_id}")

    # --------------------------------------------------------------------------
    # Job Lifecycle
    # --------------------------------------------------------------------------

    def list_jobs(self) -> dict[str, Any]:
        """
        List all jobs in the cluster.

        Returns:
            Dict with 'jobs' key containing job summaries.
        """
        return self._get("/jobs/overview")

    def get_job_details(self, job_id: str) -> FlinkJobStatus:
        """
        Get detailed status of a specific job.

        Args:
            job_id: The Flink job ID.

        Returns:
            FlinkJobStatus dataclass with full task breakdown.
        """
        data = self._get(f"/jobs/{job_id}")
        return FlinkJobStatus.from_api(data)

    def get_job_vertices(self, job_id: str) -> list[dict[str, Any]]:
        """
        Get all vertices (operators) of a running job.

        Args:
            job_id: The Flink job ID.

        Returns:
            List of vertex descriptors with operator names and parallelism.
        """
        data = self._get(f"/jobs/{job_id}/vertices")
        return data.get("vertices", [])

    def get_job_exceptions(self, job_id: str) -> dict[str, Any]:
        """
        Get exceptions that occurred during job execution.

        Args:
            job_id: The Flink job ID.

        Returns:
            Dict containing exception history.
        """
        return self._get(f"/jobs/{job_id}/exceptions")

    def cancel_job(self, job_id: str, drain: bool = False) -> bool:
        """
        Cancel a running Flink job.

        Args:
            job_id: The Flink job ID.
            drain: If True, drains remaining input before cancelling (Flink 1.12+).

        Returns:
            True if cancellation was triggered successfully.
        """
        endpoint = f"/jobs/{job_id}"
        if drain:
            endpoint += "?mode=cancel"
            # For drain, use savepoint trigger + stop
            try:
                self._patch(endpoint, timeout=30.0)
                return True
            except FlinkClientError:
                pass
        try:
            self._patch(f"/jobs/{job_id}", timeout=30.0)
            logger.info("Cancelled Flink job %s", job_id)
            return True
        except FlinkClientError as e:
            logger.error("Failed to cancel job %s: %s", job_id, e)
            raise

    def stop_with_savepoint(
        self,
        job_id: str,
        target_directory: str | None = None,
        cancel_job: bool = True,
    ) -> str:
        """
        Trigger a savepoint and optionally stop the job.

        Args:
            job_id: The Flink job ID.
            target_directory: Directory for savepoint files.
            cancel_job: Whether to cancel after the savepoint.

        Returns:
            Trigger ID for the savepoint operation.
        """
        payload: dict[str, Any] = {"cancelJob": cancel_job}
        if target_directory:
            payload["targetDirectory"] = target_directory

        result = self._post(f"/jobs/{job_id}/savepoints", json=payload)
        trigger_id = result.get("request-id", "")
        logger.info(
            "Savepoint triggered for job %s, trigger_id=%s", job_id, trigger_id
        )
        return trigger_id

    def get_savepoint_status(
        self, job_id: str, trigger_id: str
    ) -> dict[str, Any]:
        """
        Check the status of a savepoint operation.

        Args:
            job_id: The Flink job ID.
            trigger_id: The savepoint trigger ID.

        Returns:
            Savepoint operation status.
        """
        return self._get(f"/jobs/{job_id}/savepoints/{trigger_id}")

    # --------------------------------------------------------------------------
    # Checkpoint Management
    # --------------------------------------------------------------------------

    def get_checkpoint_stats(self, job_id: str) -> CheckpointStats:
        """
        Get checkpoint statistics for a job.

        Args:
            job_id: The Flink job ID.

        Returns:
            CheckpointStats dataclass with counts, latest, and history.
        """
        data = self._get(f"/jobs/{job_id}/checkpoints")
        return CheckpointStats.from_api(job_id, data)

    def get_checkpoint_config(self, job_id: str) -> dict[str, Any]:
        """
        Get the checkpoint configuration for a job.

        Args:
            job_id: The Flink job ID.

        Returns:
            Checkpoint configuration parameters.
        """
        return self._get(f"/jobs/{job_id}/checkpoints/config")

    def trigger_checkpoint(
        self, job_id: str, target_directory: str | None = None
    ) -> str:
        """
        Manually trigger a checkpoint for a job.

        Args:
            job_id: The Flink job ID.
            target_directory: Optional target directory.

        Returns:
            Trigger ID.
        """
        payload: dict[str, Any] = {}
        if target_directory:
            payload["targetDirectory"] = target_directory
        result = self._post(f"/jobs/{job_id}/checkpoints", json=payload)
        return result.get("request-id", "")

    # --------------------------------------------------------------------------
    # Metrics
    # --------------------------------------------------------------------------

    def get_job_metrics(
        self, job_id: str, metric_names: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Get metrics for a specific job.

        Args:
            job_id: The Flink job ID.
            metric_names: Optional list of specific metric names to fetch.
                          If None, returns all available metrics.

        Returns:
            List of metric name/value pairs.
        """
        path = f"/jobs/{job_id}/metrics"
        if metric_names:
            params = ",".join(metric_names)
            path += f"?get={params}"
        return self._get(path)

    def get_vertex_metrics(
        self, job_id: str, vertex_id: str, metric_names: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Get metrics for a specific job vertex.

        Args:
            job_id: The Flink job ID.
            vertex_id: The vertex ID.
            metric_names: Optional list of specific metric names.

        Returns:
            List of metric name/value pairs for the vertex.
        """
        path = f"/jobs/{job_id}/vertices/{vertex_id}/metrics"
        if metric_names:
            params = ",".join(metric_names)
            path += f"?get={params}"
        return self._get(path)

    def get_aggregated_job_metrics(
        self, job_id: str, metric_names: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Get aggregated metrics for a job across all subtasks.

        Args:
            job_id: The Flink job ID.
            metric_names: Optional list of specific metric names.

        Returns:
            Aggregated metrics data.
        """
        raw_metrics = self.get_job_metrics(job_id, metric_names)
        result: dict[str, Any] = {}
        for m in raw_metrics:
            result[m.get("id", "")] = m.get("value")
        return result

    # --------------------------------------------------------------------------
    # JAR & Job Submission
    # --------------------------------------------------------------------------

    def list_jars(self) -> list[dict[str, Any]]:
        """
        List all JARs uploaded to the cluster.

        Returns:
            List of JAR descriptors.
        """
        data = self._get("/jars")
        return data.get("files", [])

    def upload_jar(self, jar_path: str) -> str:
        """
        Upload a JAR file to the Flink cluster.

        Args:
            jar_path: Local filesystem path to the JAR file.

        Returns:
            The JAR ID on the Flink cluster.

        Raises:
            FlinkClientError: If upload fails.
        """
        path = Path(jar_path)
        if not path.exists() or not path.is_file():
            raise FlinkClientError(f"JAR file not found: {jar_path}")

        url = f"{self.base_url}/jars/upload"
        try:
            with path.open("rb") as file_obj:
                response = self._client.post(
                    url,
                    files={
                        "jarfile": (path.name, file_obj, "application/java-archive")
                    },
                    timeout=60.0,
                )
            response.raise_for_status()
            data = response.json()
            filename = data.get("filename", "")
            if not filename:
                raise FlinkClientError("Flink upload response missing filename.")
            return filename.rsplit("/", 1)[-1]
        except httpx.RequestError as e:
            raise FlinkClientError(f"Failed to upload JAR {jar_path}: {e}") from e

    def delete_jar(self, jar_id: str) -> bool:
        """
        Delete a JAR from the Flink cluster.

        Args:
            jar_id: The JAR ID to delete.

        Returns:
            True if deletion was successful.
        """
        try:
            self._delete(f"/jars/{jar_id}", timeout=10.0)
            logger.info("Deleted JAR %s from Flink cluster", jar_id)
            return True
        except FlinkClientError as e:
            logger.error("Failed to delete JAR %s: %s", jar_id, e)
            raise

    def submit_jar(
        self,
        jar_id: str,
        entry_class: str | None = None,
        program_args: str | None = None,
        parallelism: int | None = None,
        savepoint_path: str | None = None,
        allow_non_restored_state: bool = False,
    ) -> str:
        """
        Submit a JAR to run on the Flink cluster.

        Args:
            jar_id: The JAR ID (from upload_jar or list_jars).
            entry_class: Fully qualified entry class name.
            program_args: Program arguments as a single string.
            parallelism: Job parallelism (uses cluster default if None).
            savepoint_path: Optional savepoint path to restore from.
            allow_non_restored_state: Allow non-restored state.

        Returns:
            The Flink job ID.
        """
        payload: dict[str, Any] = {}
        if entry_class:
            payload["entryClass"] = entry_class
        if program_args:
            payload["programArgs"] = program_args
        if parallelism is not None:
            payload["parallelism"] = parallelism
        if savepoint_path:
            payload["savepointPath"] = savepoint_path
            payload["allowNonRestoredState"] = allow_non_restored_state

        url = f"/jars/{jar_id}/run"
        try:
            data = self._post(url, json=payload, timeout=30.0)
            job_id = data.get("jobid")
            if not job_id:
                raise FlinkClientError("Flink run response did not include jobid.")
            logger.info(
                "Submitted JAR %s as job %s (parallelism=%s)",
                jar_id,
                job_id,
                parallelism,
            )
            return job_id
        except FlinkClientError:
            raise
        except Exception as e:
            raise FlinkClientError(
                f"Failed to submit JAR {jar_id}: {e}"
            ) from e

    def submit_sql_query(
        self,
        sql_statement: str,
        execution_config: dict[str, Any] | None = None,
    ) -> str:
        """
        Submit a SQL query via the Flink SQL Gateway (1.16+).

        Args:
            sql_statement: The SQL statement to execute.
            execution_config: Optional execution configuration.

        Returns:
            The operation handle ID.
        """
        payload: dict[str, Any] = {"statement": sql_statement}
        if execution_config:
            payload["executionConfig"] = execution_config

        result = self._post("/sql/execute", json=payload)
        operation_handle = result.get("operationHandle", "")
        logger.info("Submitted SQL query, operation=%s", operation_handle)
        return operation_handle

    # --------------------------------------------------------------------------
    # Health
    # --------------------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        """
        Perform a health check on the Flink cluster.

        Returns:
            Dict with 'healthy' bool, 'overview', and 'config' if reachable.
        """
        try:
            overview = self.get_overview()
            return {
                "healthy": True,
                "taskmanagers": overview.get("taskmanagers", 0),
                "slots_total": overview.get("slots-total", 0),
                "slots_available": overview.get("slots-available", 0),
                "jobs_running": overview.get("jobs-running", 0),
                "jobs_finished": overview.get("jobs-finished", 0),
                "jobs_failed": overview.get("jobs-failed", 0),
            }
        except (FlinkClientError, FlinkClusterUnavailableError) as e:
            return {"healthy": False, "error": str(e)}

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> FlinkClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
