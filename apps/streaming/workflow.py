"""
Streaming Workflow for Voyant.

Orchestrates submission and monitoring of Apache Flink streaming jobs.
Triggered by the Voyant API when continuous analytics are requested on a data stream.
Follows the Temporal Orchestrator pattern: all side-effect operations are delegated
to activities, with no inter-run state, ensuring idempotency and fault tolerance.

Implements Functional Requirement FR-21 (Streaming Analytics — Apache Flink) from SRS.md.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from apps.streaming.activities import FlinkJobResult


logger = logging.getLogger(__name__)


@dataclass
class StreamingJobInput:
    """
    Input parameters for a streaming job workflow.

    Attributes:
        job_name: Human-readable name for the streaming job.
        job_type: Type of streaming job (e.g., "kpi_aggregation", "anomaly_detection").
        source_topic: Kafka topic to consume from.
        sink_topic: Kafka topic to produce results to (optional).
        config: Additional job-specific configuration.
    """

    job_name: str
    job_type: str
    source_topic: str
    sink_topic: str | None = None
    config: dict[str, Any] | None = None


@workflow.defn
class StreamingJobWorkflow:
    """
    Temporal Workflow for managing Flink streaming jobs.

    This workflow:
    1. Validates the Flink cluster is healthy.
    2. Submits the requested streaming job.
    3. Returns the result to the caller.

    Future enhancements may include periodic health checks on long-running jobs.
    """

    @workflow.run
    async def run(self, input: StreamingJobInput) -> FlinkJobResult:
        """
        Execute the streaming job workflow.

        Args:
            input: StreamingJobInput containing job parameters.

        Returns:
            FlinkJobResult with the outcome of job submission.
        """
        workflow.logger.info(f"Starting StreamingJobWorkflow for: {input.job_name}")

        # Step 1: Health check - verify cluster is reachable
        try:
            overview = await workflow.execute_activity(
                "get_cluster_overview",
                start_to_close_timeout=timedelta(seconds=30),
            )
            workflow.logger.info(f"Flink cluster healthy: {overview}")
        except Exception as e:
            workflow.logger.error(f"Flink cluster health check failed: {e}")
            return FlinkJobResult(
                success=False,
                message=f"Cluster health check failed: {e}",
            )

        # Step 2: Submit the streaming job
        job_config = {
            "job_type": input.job_type,
            "source_topic": input.source_topic,
            "sink_topic": input.sink_topic,
            **(input.config or {}),
        }

        result = await workflow.execute_activity(
            "submit_streaming_job",
            args=[input.job_name, job_config],
            start_to_close_timeout=timedelta(minutes=5),
        )

        workflow.logger.info(f"Streaming job result: {result}")
        return result
