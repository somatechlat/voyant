"""
Capsule Workflow — Temporal orchestration for multi-step capsule execution.

Workflow state carries only lightweight metadata (step completion tracking).
Actual step results are persisted to the CapsuleInstance DB record to avoid
Temporal's 2MB event history limit.
"""

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    pass


@workflow.defn(name="CapsuleWorkflow")
class CapsuleWorkflow:
    """
    Temporal workflow that executes a Capsule's execution_graph step by step.
    Supports conditions, retries, and artifact generation.
    """

    @workflow.run
    async def run(
        self,
        capsule_id: str,
        parameter_values: dict[str, Any],
        tenant_id: str,
        instance_id: str,
    ) -> dict[str, Any]:
        # Load capsule definition
        capsule = await workflow.execute_activity(
            "capsule.load_capsule",
            {"capsule_id": capsule_id, "tenant_id": tenant_id},
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )

        graph = capsule.get("execution_graph", [])
        capabilities_whitelist = capsule.get("capabilities_whitelist", [])
        step_metadata: dict[str, Any] = {}

        for step in graph:
            step_id = step["step_id"]

            # Check condition
            if step.get("condition"):
                condition_met = await workflow.execute_activity(
                    "capsule.eval_condition",
                    {"condition": step["condition"], "steps": step_metadata},
                    start_to_close_timeout=timedelta(seconds=10),
                )
                if not condition_met:
                    continue

            # Substitute parameters
            resolved_params = await workflow.execute_activity(
                "capsule.substitute_params",
                {
                    "params": step.get("params", {}),
                    "parameter_values": parameter_values,
                    "step_results": step_metadata,
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Execute step (result is persisted to DB; only metadata returned)
            timeout = step.get("timeout_seconds", 60)
            retry = step.get("retry_policy", {"max_attempts": 3, "backoff_seconds": 5})

            meta = await workflow.execute_activity(
                "capsule.execute_step",
                {
                    "action": step["action"],
                    "params": resolved_params,
                    "tenant_id": tenant_id,
                    "instance_id": instance_id,
                    "capabilities_whitelist": capabilities_whitelist,
                },
                start_to_close_timeout=timedelta(seconds=timeout),
                retry_policy=RetryPolicy(
                    maximum_attempts=retry.get("max_attempts", 3),
                    initial_interval=timedelta(seconds=retry.get("backoff_seconds", 5)),
                ),
            )

            step_metadata[step_id] = meta

        # Cross-validate if configured
        if capsule.get("body", {}).get("cross_validate"):
            validated = await workflow.execute_activity(
                "capsule.cross_validate",
                {"instance_id": instance_id, "tenant_id": tenant_id},
                start_to_close_timeout=timedelta(seconds=60),
            )
            step_metadata["_validated"] = validated

        # Generate artifacts
        artifacts = await workflow.execute_activity(
            "capsule.generate_artifacts",
            {
                "capsule_id": capsule_id,
                "instance_id": instance_id,
                "tenant_id": tenant_id,
            },
            start_to_close_timeout=timedelta(seconds=120),
        )

        # Store final report
        await workflow.execute_activity(
            "capsule.store_report",
            {
                "capsule_id": capsule_id,
                "instance_id": instance_id,
                "artifacts": artifacts,
                "tenant_id": tenant_id,
            },
            start_to_close_timeout=timedelta(seconds=60),
        )

        job_urn = f"urn:voyant:job:{tenant_id}:{capsule.get('name', 'unknown')}:{workflow.info().run_id}"
        return {"job_urn": job_urn, "artifacts": artifacts, "status": "completed"}
