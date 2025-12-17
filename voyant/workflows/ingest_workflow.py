"""
Ingestion Workflow

Orchestrates the data ingestion process.
"""
from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

# Import activity definition (for type hints only if available, or use string names)
with workflow.unsafe.imports_passed_through():
    from voyant.activities.ingest_activities import IngestActivities

@workflow.defn
class IngestDataWorkflow:
    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the ingestion workflow.
        
        Args:
            params: Dictionary containing job_id, source_id, etc.
        """
        workflow.logger.info(f"IngestWorkflow started for job {params.get('job_id')}")
        
        # Retry policy
        retry_policy = workflow.RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=3,
        )
        
        # 1. Validate Contract (Governance P5)
        # ---------------------------------------------------------
        validation = await workflow.execute_activity(
            IngestActivities.validate_contract_activity,
            params,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
        )
        
        if not validation.get("valid", True):
             # Blocking validation failure
             raise workflow.ApplicationError(f"Contract validation failed: {validation}")

        # 2. Execute Ingestion
        # ---------------------------------------------------------
        result = await workflow.execute_activity(
            IngestActivities.run_ingestion,
            params,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=retry_policy,
        )
        
        # 3. Record Lineage (Governance P5)
        # ---------------------------------------------------------
        await workflow.execute_activity(
            IngestActivities.record_lineage_activity,
            params,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
        )
        
        workflow.logger.info(f"IngestWorkflow completed for job {params.get('job_id')}")
        return result
