"""
Quality Workflow: Runs data quality validation.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities.quality_activities import QualityActivities


@workflow.defn
class QualityWorkflow:
    """
    Temporal workflow for running quality checks on a dataset.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute sampling and quality validation.
        """
        table = params.get("table") or params.get("source_id")
        if not table:
            raise workflow.ApplicationError(
                "table or source_id is required for quality workflow"
            )

        retry_policy = workflow.RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
        )

        sample = await workflow.execute_activity(
            QualityActivities.fetch_sample,
            params,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )

        result = await workflow.execute_activity(
            QualityActivities.run_quality_checks,
            {"data": sample, "checks": params.get("checks")},
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=retry_policy,
        )

        return {
            "table": table,
            "rows_analyzed": result.get("rows_analyzed", 0),
            "quality": result,
        }
