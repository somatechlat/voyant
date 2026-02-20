"""
Benchmark Brand Workflow: Orchestrates Competitive Brand Analysis.

This Temporal workflow defines the automated process for performing a
"Tier 4 Preset: Competitive brand analysis." It orchestrates a sequence of
activities including parallel data ingestion, statistical analysis (e.g.,
market share calculation and hypothesis testing), and ultimately aims to
generate a comprehensive report comparing a brand against its competitors.

The workflow demonstrates coordination of multiple activities and handling
of results from analytical operations.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

# This context manager is necessary to allow importing non-workflow/activity
# modules within the workflow definition. It passes control to the Python
# import system directly, bypassing Temporal's default import handling.
with workflow.unsafe.imports_passed_through():
    from apps.worker.activities.ingest_activities import IngestActivities
    from apps.worker.activities.stats_activities import StatsActivities


@workflow.defn
class BenchmarkBrandWorkflow:
    """
    Temporal workflow for orchestrating a competitive brand analysis benchmark.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the competitive brand analysis benchmark workflow.

        This method orchestrates parallel data ingestion for the target brand
        and its competitors, followed by statistical analysis to derive insights
        such as market share and significance tests.

        Args:
            params: A dictionary containing the benchmark configuration:
                - `brand_source_id` (str): The ID of the data source for the primary brand.
                - `competitor_source_ids` (List[str]): A list of data source IDs for competitors.
                - `metric` (str): The metric to be used for comparison (e.g., "revenue").

        Returns:
            A dictionary containing the benchmark results, including market share
            figures, significance test outcomes, and a generated report URL.
        """
        brand_source = params["brand_source_id"]
        comp_sources = params.get("competitor_source_ids", [])

        workflow.logger.info(f"Starting BENCHMARK_MY_BRAND for {brand_source}")

        # 1. Ingest Data (Parallel)
        # In a real production scenario, these ingestions might be pre-existing
        # or triggered as separate workflows. Here, we demonstrate triggering
        # them as activities and waiting for all to complete in parallel.
        ingest_futures = []
        for src in [brand_source] + comp_sources:
            ingest_futures.append(
                workflow.execute_activity(
                    IngestActivities.run_ingestion,
                    {"job_id": f"ingest_{src}", "source_id": src},
                    start_to_close_timeout=timedelta(minutes=5),
                )
            )

        # Wait for all ingestion activities to complete.
        await workflow.wait_for_all(ingest_futures)

        # 2. Statistical Analysis (Market Share & Hypothesis Testing)
        # For demonstration purposes within this workflow, small example data
        # structures are passed directly. In a production system, activities
        # would typically fetch larger datasets based on source_id and table names
        # from an analytical database like DuckDB or Trino.

        # Calculate market share based on processed data.
        market_share = await workflow.execute_activity(
            StatsActivities.calculate_market_share,
            {
                "brand_data": [
                    {"value": 100},
                    {"value": 120},
                ],  # Example data for workflow demonstration
                "competitor_data": [{"value": 90}, {"value": 110}],
                "metric": params.get("metric", "revenue"),  # Use the metric from params
            },
            start_to_close_timeout=timedelta(seconds=30),
        )

        # Perform hypothesis testing (e.g., t-test) to assess significance.
        t_test = await workflow.execute_activity(
            StatsActivities.perform_hypothesis_test,
            {
                "group_a": [
                    100,
                    120,
                    130,
                    140,
                ],  # Example data for workflow demonstration
                "group_b": [90, 110, 115, 120],
                "test_type": "t-test",
            },
            start_to_close_timeout=timedelta(seconds=30),
        )

        result = {
            "status": "completed",
            "market_share": market_share,
            "significance_test": t_test,
            "report_url": "s3://artifacts/report_123.html",  # Placeholder: Actual report generation would be a separate activity.
        }

        workflow.logger.info("BENCHMARK_MY_BRAND completed.")
        return result
