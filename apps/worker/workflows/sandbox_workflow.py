"""
Sandbox Orchestrator Workflow

Routes raw analytical scripts into the Python Sandbox Node,
coordinating strict input data mapping and physical output generation.
Security Auditor Mandate: Isolated environment with zero external inputs natively.
"""

import logging
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities.sandbox_activities import SandboxActivities

logger = logging.getLogger(__name__)


@workflow.defn(name="SandboxWorkflow")
class SandboxWorkflow:
    """Orchestrates mathematical operations mapped to Docker Nodes."""

    @workflow.run
    async def run(self, params: dict):
        """
        Executes the pure mathematical script securely inside Docker.
        """
        script = params.get("script")
        tenant_id = params.get("tenant_id")
        job_id = params.get("job_id")
        dependencies = params.get("dependencies", [])

        if not script:
            raise ValueError("SandboxWorkflow requires a 'script' payload to evaluate.")

        workflow.logger.info(
            f"Sandbox Workflow initialized for {tenant_id}, Job: {job_id}"
        )

        # Real physical execution block via Temporal Activities
        start_to_close_timeout = timedelta(hours=1)

        activity_params = {
            "script": script,
            "tenant_id": tenant_id,
            "dependencies": dependencies,
            "job_id": job_id,
        }

        result = await workflow.execute_activity(
            SandboxActivities.run_python_sandbox,
            activity_params,
            start_to_close_timeout=start_to_close_timeout,
            retry_policy=None,  # Security: Do not silently retry malicious or faulty compute
        )

        workflow.logger.info("Sandbox Workflow execution strictly completed.")
        return result
