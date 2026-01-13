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
    Unit tests should mock the FlinkClient. Integration tests MUST run against
    a live Flink cluster (voyant_flink_jobmanager) to verify real behavior.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

from temporalio import activity

from voyant.core.config import get_settings
from voyant.streaming.flink_client import FlinkClient, FlinkClientError

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

        This ensures we always use the correct URL from settings and
        allows for easy mocking in unit tests.
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

        Note (PhD Developer):
            This is a placeholder for PyFlink job submission. Full implementation
            requires either:
            1. Uploading a JAR and submitting via REST API (for Java/Scala jobs).
            2. Using the Flink Table API remotely (for PyFlink jobs).
            3. Invoking `flink run` via subprocess (for CLI-based submission).

            For the current phase, we return a placeholder result and log the intent.

        Args:
            job_name: Human-readable name for the job.
            job_config: Configuration dictionary (entry class, parallelism, etc.).

        Returns:
            FlinkJobResult with submission status.
        """
        logger.info(f"Submitting streaming job: {job_name}")
        logger.info(f"Job config: {job_config}")

        # Phase 2.2: Placeholder - actual submission logic TBD based on job type
        # For now, we verify the cluster is reachable and return a pending result.
        client = self._get_client()
        try:
            overview = client.get_overview()
            if overview.get("slots-available", 0) == 0:
                return FlinkJobResult(
                    success=False,
                    message="No available slots in the Flink cluster.",
                    details=overview,
                )

            # TODO: Implement actual job submission (JAR upload or PyFlink CLI)
            return FlinkJobResult(
                success=True,
                job_id="pending-implementation",
                message=f"Job '{job_name}' submission logic is pending implementation.",
                details={"cluster_status": overview},
            )
        except FlinkClientError as e:
            return FlinkJobResult(
                success=False,
                message=f"Failed to connect to Flink cluster: {e}",
            )
