"""
Profile Workflow: Orchestrates Data Profiling Jobs.

This Temporal workflow defines the automated process for generating comprehensive
profiles of datasets. It delegates the actual profiling work to specialized
activities, ensuring that statistical summaries and insights about data quality
and distribution are generated efficiently.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

from apps.core.lib.retry_config import EXTERNAL_SERVICE_RETRY

# This context manager is necessary to allow importing non-workflow/activity
# modules within the workflow definition. It passes control to the Python
# import system directly, bypassing Temporal's default import handling.
with workflow.unsafe.imports_passed_through():
    from apps.worker.activities.profile_activities import ProfileActivities


@workflow.defn
class ProfileWorkflow:
    """
    Temporal workflow for orchestrating the data profiling pipeline.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the data profiling workflow based on provided parameters.

        This method coordinates activities to generate a statistical profile
        of a specified dataset.

        Args:
            params: A dictionary containing the profiling configuration:
                - `source_id` (str): Identifier of the data source.
                - `table` (str): The name of the table to profile.
                - `sample_size` (int): Number of rows to sample for profiling.
                - `job_id` (str): Unique identifier for the profiling job.
                - `tenant_id` (str): Identifier of the tenant.

        Returns:
            A dictionary containing the profile result, typically a statistical
            summary of the dataset.
        """
        workflow.logger.info(f"ProfileWorkflow started for {params.get('job_id')}")

        # Execute the data profiling activity.
        # This activity performs the heavy lifting of calculating statistics
        # and generating the profile summary. It uses a retry policy suitable
        # for external service calls, as data access can be flaky.
        profile_result = await workflow.execute_activity(
            ProfileActivities.profile_data,
            params,
            start_to_close_timeout=timedelta(
                minutes=15
            ),  # Allow sufficient time for profiling.
            retry_policy=EXTERNAL_SERVICE_RETRY,
        )

        workflow.logger.info(f"ProfileWorkflow completed for {params.get('job_id')}")
        return profile_result
