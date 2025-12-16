from datetime import timedelta
from temporalio import workflow
from .types import IngestParams, IngestResult

# Import activity interface (stub) - actual implementation is in activities/
with workflow.unsafe.imports_passed_through():
    from voyant.activities.ingest_activities import IngestActivities

@workflow.defn
class IngestWorkflow:
    @workflow.run
    async def run(self, params: IngestParams) -> IngestResult:
        workflow.logger.info(f"Starting Ingest Workflow for job {params.job_id}")
        
        # Configure activities options
        activities = workflow.new_activity_stub(
            IngestActivities,
            start_to_close_timeout=timedelta(hours=1),
            retry_policy=workflow.RetryPolicy(
                initial_interval=timedelta(seconds=5),
                maximum_interval=timedelta(minutes=5),
                maximum_attempts=5
            )
        )

        # Step 1: Validate Source & Configuration
        # (This could be a separate activity if it takes time/IO)
        workflow.logger.info("Validating source connection...")
        
        # Step 2: Execute Ingestion
        # This calls the activity which handles Airbyte/Beam logic
        result = await activities.run_ingestion(params)
        
        workflow.logger.info(f"Ingestion completed: {result}")
        
        # Step 3: Register Lineage (Optional step, can be part of ingestion or separate)
        # await activities.register_lineage(result)
        
        return result
