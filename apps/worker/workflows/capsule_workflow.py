"""
Capsule Workflow — Temporal orchestration for multi-step capsule execution.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities.capsule_activities import CapsuleActivities


@workflow.defn(name="CapsuleWorkflow")
class CapsuleWorkflow:
    """
    Temporal workflow that executes a Capsule's execution_graph step by step.
    Supports parallel steps, conditions, retries, and artifact generation.
    """

    @workflow.run
    async def run(
        self,
        capsule_id: str,
        parameter_values: Dict[str, Any],
        tenant_id: str,
        instance_id: str,
    ) -> Dict[str, Any]:
        # Load capsule definition
        capsule = await workflow.execute_activity(
            CapsuleActivities.load_capsule,
            {"capsule_id": capsule_id, "tenant_id": tenant_id},
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=workflow.RetryPolicy(maximum_attempts=3),
        )

        graph = capsule.get("execution_graph", [])
        step_results: Dict[str, Any] = {}

        # Identify parallel groups (steps with no interdependencies)
        for step in graph:
            # Check condition
            if step.get("condition"):
                condition_met = await workflow.execute_activity(
                    CapsuleActivities.eval_condition,
                    {"condition": step["condition"], "steps": step_results},
                    start_to_close_timeout=timedelta(seconds=10),
                )
                if not condition_met:
                    continue

            # Substitute parameters
            resolved_params = await workflow.execute_activity(
                CapsuleActivities.substitute_params,
                {
                    "params": step.get("params", {}),
                    "parameter_values": parameter_values,
                    "step_results": step_results,
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            # Execute step
            timeout = step.get("timeout_seconds", 60)
            retry = step.get("retry_policy", {"max_attempts": 3})

            result = await workflow.execute_activity(
                CapsuleActivities.execute_step,
                {
                    "action": step["action"],
                    "params": resolved_params,
                    "tenant_id": tenant_id,
                },
                start_to_close_timeout=timedelta(seconds=timeout),
                retry_policy=workflow.RetryPolicy(
                    maximum_attempts=retry.get("max_attempts", 3),
                    initial_interval=timedelta(seconds=retry.get("backoff_seconds", 5)),
                ),
            )

            step_results[step["step_id"]] = result

        # Cross-validate if configured
        if capsule.get("body", {}).get("cross_validate"):
            validated = await workflow.execute_activity(
                CapsuleActivities.cross_validate,
                {"findings": step_results, "tenant_id": tenant_id},
                start_to_close_timeout=timedelta(seconds=60),
            )
            step_results["_validated"] = validated

        # Generate artifacts
        artifacts = await workflow.execute_activity(
            CapsuleActivities.generate_artifacts,
            {
                "capsule_id": capsule_id,
                "results": step_results,
                "tenant_id": tenant_id,
                "instance_id": instance_id,
            },
            start_to_close_timeout=timedelta(seconds=120),
        )

        # Store final report
        await workflow.execute_activity(
            CapsuleActivities.store_report,
            {
                "capsule_id": capsule_id,
                "results": step_results,
                "artifacts": artifacts,
                "tenant_id": tenant_id,
                "instance_id": instance_id,
            },
            start_to_close_timeout=timedelta(seconds=60),
        )

        job_urn = f"urn:voyant:job:{tenant_id}:{capsule.get('name', 'unknown')}:{workflow.info().run_id}"
        return {"job_urn": job_urn, "artifacts": artifacts, "status": "completed"}
