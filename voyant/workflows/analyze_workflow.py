"""
Analyze Workflow: Orchestrates End-to-End Data Analysis.

This Temporal workflow defines and executes the complete pipeline for a data
analysis request. It coordinates various activities including data profiling,
running registered analyzer plugins, calculating Key Performance Indicators (KPIs),
and generating data artifacts such as charts and reports.

The workflow is designed to be flexible, allowing different stages of the
analysis to be enabled or disabled based on the input parameters.
"""

from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow

# This context manager is necessary to allow importing non-workflow/activity
# modules within the workflow definition. It passes control to the Python
# import system directly, bypassing Temporal's default import handling.
with workflow.unsafe.imports_passed_through():
    from voyant.activities.profile_activities import ProfileActivities
    from voyant.activities.analysis_activities import AnalysisActivities
    from voyant.activities.generation_activities import GenerationActivities
    from voyant.activities.kpi_activities import KPIActivities


@workflow.defn
class AnalyzeWorkflow:
    """
    Temporal workflow for orchestrating a complete data analysis pipeline.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the end-to-end data analysis workflow based on provided parameters.

        This method orchestrates a sequence of activities to perform profiling,
        analysis, KPI calculation, and artifact generation.

        Args:
            params: A dictionary containing the analysis configuration:
                - `source_id` (str): The ID of the data source.
                - `table` (str): The specific table to analyze within the source.
                - `tables` (list[str]): A list of tables to analyze (if multiple).
                - `sample_size` (int): Number of rows to sample for analysis.
                - `kpis` (list[dict]): List of KPI queries to execute.
                - `analyzers` (list[str]): List of analyzer plugin names to run.
                - `analyzer_context` (dict): Context to pass to analyzers.
                - `profile` (bool): Whether to generate a data profile (default: True).
                - `run_analyzers` (bool): Whether to execute analyzer plugins (default: True).
                - `generate_artifacts` (bool): Whether to generate output artifacts (default: True).
                - `job_id` (str): The unique ID of the analysis job.
                - `tenant_id` (str): The ID of the tenant initiating the analysis.

        Returns:
            A dictionary containing a summary of the analysis, along with results
            from profiling, KPIs, analyzers, and generated artifacts.

        Raises:
            workflow.ApplicationError: If essential parameters are missing or invalid.
        """
        table = params.get("table") or params.get("source_id")
        if not table:
            raise workflow.ApplicationError("table or source_id is required")

        profile_summary = None
        analyzer_results: Dict[str, Any] = {}
        kpi_results: List[Dict[str, Any]] = []
        generator_results: Dict[str, Any] = {}

        # Stage 1: Data Profiling
        # Execute the ProfileActivities.profile_data to generate a statistical summary of the dataset.
        if params.get("profile", True):
            profile_summary = await workflow.execute_activity(
                ProfileActivities.profile_data,
                {
                    "source_id": params.get("source_id") or table,
                    "table": table,
                    "sample_size": params.get("sample_size", 10000),
                },
                start_to_close_timeout=timedelta(minutes=15),
            )

        # Stage 2: Run Analyzers
        # Fetch a sample of data, then execute configured analyzer plugins to extract insights.
        if params.get("run_analyzers", True):
            sample_data = await workflow.execute_activity(
                AnalysisActivities.fetch_sample,
                {
                    "table": table,
                    "sample_size": params.get("sample_size", 10000),
                },
                start_to_close_timeout=timedelta(minutes=5),
            )

            analyzer_results = await workflow.execute_activity(
                AnalysisActivities.run_analyzers,
                {
                    "data": sample_data,
                    "analyzers": params.get("analyzers"),
                    "context": params.get("analyzer_context", {}),
                },
                start_to_close_timeout=timedelta(minutes=10),
            )

        # Stage 3: Calculate KPIs
        # Execute custom KPI queries provided in the workflow parameters.
        if params.get("kpis"):
            kpi_results = await workflow.execute_activity(
                KPIActivities.run_kpis,
                {"kpis": params.get("kpis")},
                start_to_close_timeout=timedelta(minutes=10),
            )

        # Stage 4: Generate Artifacts
        # Create visual reports and other artifacts based on the analysis results.
        if params.get("generate_artifacts", True):
            generator_results = await workflow.execute_activity(
                GenerationActivities.run_generators,
                {
                    "table_name": table,
                    "tables": params.get("tables"),
                    "job_id": params.get("job_id"),
                    "tenant_id": params.get("tenant_id"),
                    "profile": profile_summary,
                    "kpis": kpi_results,
                    "analyzers": analyzer_results,
                },
                start_to_close_timeout=timedelta(minutes=10),
            )

        # Compile a summary of the analysis results.
        summary = {
            "table": table,
            "kpi_count": len(kpi_results),
            "analyzer_count": len(analyzer_results) if analyzer_results else 0,
        }

        # Return all compiled results.
        return {
            "summary": summary,
            "profile": profile_summary,
            "kpis": kpi_results,
            "analyzers": analyzer_results,
            "generators": generator_results,
        }
