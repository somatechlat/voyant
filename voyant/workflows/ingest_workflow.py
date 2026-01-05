"""
Ingestion Workflow: Orchestrates End-to-End Data Ingestion.

This Temporal workflow defines the automated process for bringing data
from a specified source into the Voyant platform. It ensures that data
is validated against contracts, ingested reliably, and that its lineage
is properly recorded for governance and auditability.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

# This context manager is necessary to allow importing non-workflow/activity
# modules within the workflow definition. It passes control to the Python
# import system directly, bypassing Temporal's default import handling.
with workflow.unsafe.imports_passed_through():
    from voyant.activities.ingest_activities import IngestActivities


@workflow.defn
class IngestDataWorkflow:
    """
    Temporal workflow for orchestrating the data ingestion pipeline.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the data ingestion workflow based on provided parameters.

        This method coordinates activities for contract validation, data
        ingestion, and lineage recording.

        Args:
            params: A dictionary containing the ingestion configuration:
                - `job_id` (str): Unique identifier for the ingestion job.
                - `source_id` (str): Identifier of the data source.
                - `tenant_id` (str): Identifier of the tenant.
                - `mode` (str): Ingestion mode ("full" or "incremental").
                - `tables` (Optional[List[str]]): List of tables to ingest.

        Returns:
            A dictionary containing the result of the ingestion, typically
            including status and any relevant metadata from the ingestion activity.
        """
        workflow.logger.info(f"IngestWorkflow started for job {params.get('job_id')}")

        # Define a standard retry policy for activities within this workflow.
        # This policy balances resilience against transient failures with
        # preventing indefinite retries on permanent issues.
        retry_policy = workflow.RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=3,
            non_retryable_error_types=[
                "ValidationError",
                "AuthenticationError",
                "AuthorizationError",
                "ApplicationError",
            ],
        )

        # 1. Validate Data Contract (Governance P5)
        # This activity ensures that the incoming data adheres to predefined
        # schema and quality contracts before actual ingestion proceeds.
        validation = await workflow.execute_activity(
            IngestActivities.validate_contract_activity,
            params,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
        )

        if not validation.get("valid", True):
            # If contract validation fails, raise an ApplicationError to halt
            # the workflow and signal a business-level failure.
            raise workflow.ApplicationError(f"Contract validation failed: {validation}")

        # 2. Execute Data Ingestion
        # This activity performs the actual data transfer from the source to
        # the designated storage location (e.g., DuckDB, Iceberg).
        result = await workflow.execute_activity(
            IngestActivities.run_ingestion,
            params,
            start_to_close_timeout=timedelta(minutes=10),
            retry_policy=retry_policy,
        )

        # 3. Record Data Lineage (Governance P5)
        # This activity records the provenance of the ingested data, linking
        # it back to its source and the ingestion job for auditability.
        await workflow.execute_activity(
            IngestActivities.record_lineage_activity,
            params,
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=retry_policy,
        )

        workflow.logger.info(f"IngestWorkflow completed for job {params.get('job_id')}")
        return result
