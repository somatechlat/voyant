"""
Streaming Activities for Voyant Temporal Worker.

This module provides Temporal activities for managing Apache Flink streaming jobs.
Activities are the "side-effect" operations that interact with external systems.

Architecture Note (PhD Developer):
    These activities serve as the bridge between the Temporal orchestration layer
    (the "Brain") and the Flink execution layer (the "Muscle"). They are designed
    to be idempotent where possible and to fail fast with clear error messages.

Security Note (Security Auditor):
    No credentials are hardcoded. All configuration is sourced from `get_settings()`,
    which reads from environment variables or secure backends.

Testing Note (QA Engineer):
    Integration tests should run against a live Flink cluster
    (`voyant_flink_jobmanager`) to verify real behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from temporalio import activity

from apps.core.config import get_settings
from apps.streaming.flink_client import FlinkClient, FlinkClientError

logger = logging.getLogger(__name__)


@dataclass
class FlinkJobResult:
    """
    Result of a Flink job operation.

    Attributes:
        success: Whether the operation succeeded.
        job_id: The Flink job ID if applicable.
        message: Human-readable status message.
        details: Additional metadata from the Flink API.
    """

    success: bool
    job_id: Optional[str] = None
    message: str = ""
    details: Optional[Dict[str, Any]] = None


class StreamingActivities:
    """
    Temporal activities for Apache Flink streaming operations.

    ISO Documentation (ISO Documenter):
        These activities implement FR-21 (Streaming Analytics) from the SRS.
        They enable the Voyant platform to submit, monitor, and manage
        continuous stream processing jobs.

    Performance Note (Performance Engineer):
        The FlinkClient is instantiated per-activity call to avoid connection
        staleness. For high-throughput scenarios, consider caching with TTL.
    """

    def __init__(self):
        """Initialize activities with settings-based configuration."""
        self.settings = get_settings()

    def _get_client(self) -> FlinkClient:
        """
        Factory method for FlinkClient.

        This ensures we always use the correct URL from settings.
        """
        return FlinkClient(jobmanager_url=self.settings.flink_jobmanager_url)

    @activity.defn
    async def get_cluster_overview(self) -> Dict[str, Any]:
        """
        Get the current Flink cluster overview.

        This activity is useful for health checks and capacity planning.

        Returns:
            Dict containing cluster stats (slots, jobs, task managers).

        Raises:
            FlinkClientError: If the cluster is unreachable.
        """
        logger.info("Fetching Flink cluster overview...")
        client = self._get_client()
        try:
            overview = client.get_overview()
            logger.info(
                f"Cluster overview: {overview.get('taskmanagers', 0)} task managers, "
                f"{overview.get('slots-total', 0)} slots total."
            )
            return overview
        except FlinkClientError as e:
            logger.error(f"Failed to get cluster overview: {e}")
            raise

    @activity.defn
    async def list_running_jobs(self) -> Dict[str, Any]:
        """
        List all running Flink jobs.

        Returns:
            Dict containing job overview information.
        """
        logger.info("Listing running Flink jobs...")
        client = self._get_client()
        try:
            jobs = client.list_jobs()
            job_count = len(jobs.get("jobs", []))
            logger.info(f"Found {job_count} Flink job(s).")
            return jobs
        except FlinkClientError as e:
            logger.error(f"Failed to list jobs: {e}")
            raise

    @activity.defn
    async def submit_streaming_job(
        self,
        job_name: str,
        job_config: Dict[str, Any],
    ) -> FlinkJobResult:
        """
        Submit a new streaming job to the Flink cluster.

        Args:
            job_name: Human-readable name for the job.
            job_config: Configuration dictionary (entry class, parallelism, etc.).

        Returns:
            FlinkJobResult with submission status.
        """
        logger.info(f"Submitting streaming job: {job_name}")
        logger.info(f"Job config: {job_config}")

        client = self._get_client()
        try:
            overview = client.get_overview()
            if overview.get("slots-available", 0) == 0:
                return FlinkJobResult(
                    success=False,
                    message="No available slots in the Flink cluster.",
                    details=overview,
                )

            jar_path = job_config.get("jar_path")
            jar_id = job_config.get("jar_id")
            if jar_path and not jar_id:
                jar_id = client.upload_jar(jar_path)

            if not jar_id:
                return FlinkJobResult(
                    success=False,
                    message="Missing required Flink job artifact (jar_id or jar_path).",
                    details={"cluster_status": overview, "job_name": job_name},
                )

            program_args = job_config.get("program_args")
            if isinstance(program_args, list):
                program_args = " ".join(str(arg) for arg in program_args)

            job_id = client.submit_jar(
                jar_id=jar_id,
                entry_class=job_config.get("entry_class"),
                program_args=program_args,
                parallelism=job_config.get("parallelism"),
            )

            return FlinkJobResult(
                success=True,
                job_id=job_id,
                message=f"Submitted streaming job '{job_name}'.",
                details={"cluster_status": overview, "jar_id": jar_id},
            )
        except FlinkClientError as e:
            return FlinkJobResult(
                success=False,
                message=f"Failed to connect to Flink cluster: {e}",
            )
