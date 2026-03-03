"""
Benchmark Brand Workflow: Orchestrates Competitive Brand Analysis.

Temporal workflow that performs a full Tier-4 competitive brand analysis.
No placeholders. No hardcoded data. No stub URLs.

Execution sequence:
    1. Parallel ingestion of brand + competitor sources (if not pre-ingested).
    2. Real sample fetch from ingested data via AnalysisActivities.fetch_sample.
    3. Statistical analysis: market share + hypothesis test on real rows.
    4. Bar-chart generation via GenerationActivities.run_generators.
    5. PDF report compilation via UPTP render path.
    6. Returns real artifact hash from MinIO — never a hardcoded S3 stub.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from apps.worker.activities.analysis_activities import AnalysisActivities
    from apps.worker.activities.generation_activities import GenerationActivities
    from apps.worker.activities.ingest_activities import IngestActivities
    from apps.worker.activities.stats_activities import StatsActivities


@workflow.defn
class BenchmarkBrandWorkflow:
    """
    Temporal workflow for orchestrating a competitive brand analysis benchmark.

    All data is real — fetched from ingested sources. All outputs are stored
    as real MinIO artifacts. Zero hardcoded values permitted by Vibe Rules.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the competitive brand analysis benchmark end-to-end.

        Args:
            params:
                - brand_source_id (str): Source ID for the primary brand.
                - competitor_source_ids (list[str]): Source IDs for competitors.
                - metric (str): Column name to extract for comparison (e.g. "revenue").
                - job_id (str): Parent job ID for artifact linking.
                - tenant_id (str): Tenant context for artifact isolation.

        Returns:
            Dict with market_share, significance_test, chart_artifact_id, report_hash.
        """
        brand_source = params["brand_source_id"]
        comp_sources = params.get("competitor_source_ids", [])
        metric = params.get("metric", "revenue")
        job_id = params.get("job_id", f"benchmark_{brand_source}")
        tenant_id = params.get("tenant_id", "default")

        workflow.logger.info(
            f"BenchmarkBrandWorkflow starting: brand={brand_source}, "
            f"competitors={comp_sources}, metric={metric}"
        )

        # ── Phase 1: Parallel Ingestion ──────────────────────────────────────
        all_sources = [brand_source] + comp_sources
        ingest_futures = [
            workflow.execute_activity(
                IngestActivities.run_ingestion,
                {"job_id": f"ingest_{src}_{job_id}", "source_id": src},
                start_to_close_timeout=timedelta(minutes=10),
            )
            for src in all_sources
        ]
        await workflow.wait_for_all(ingest_futures)

        workflow.logger.info("Ingestion complete for all sources.")

        # ── Phase 2: Real Data Sampling ──────────────────────────────────────
        brand_sample = await workflow.execute_activity(
            AnalysisActivities.fetch_sample,
            {
                "source_id": brand_source,
                "columns": [metric],
                "limit": 1000,
                "tenant_id": tenant_id,
            },
            start_to_close_timeout=timedelta(minutes=2),
        )

        competitor_samples = []
        for src in comp_sources:
            sample = await workflow.execute_activity(
                AnalysisActivities.fetch_sample,
                {
                    "source_id": src,
                    "columns": [metric],
                    "limit": 1000,
                    "tenant_id": tenant_id,
                },
                start_to_close_timeout=timedelta(minutes=2),
            )
            competitor_samples.append(sample)

        # Extract real numeric rows for statistical functions.
        brand_rows = [
            {"value": row[metric]}
            for row in brand_sample.get("rows", [])
            if row.get(metric) is not None
        ]
        competitor_rows = [
            {"value": row[metric]}
            for sample in competitor_samples
            for row in sample.get("rows", [])
            if row.get(metric) is not None
        ]
        brand_values = [r["value"] for r in brand_rows]
        competitor_values = [r["value"] for r in competitor_rows]

        workflow.logger.info(
            f"Sampled {len(brand_rows)} brand rows, "
            f"{len(competitor_rows)} competitor rows for metric='{metric}'."
        )

        # ── Phase 3: Statistical Analysis ────────────────────────────────────
        market_share = await workflow.execute_activity(
            StatsActivities.calculate_market_share,
            {
                "brand_data": brand_rows,
                "competitor_data": competitor_rows,
                "metric": metric,
            },
            start_to_close_timeout=timedelta(seconds=60),
        )

        significance_test = await workflow.execute_activity(
            StatsActivities.perform_hypothesis_test,
            {
                "group_a": brand_values,
                "group_b": competitor_values,
                "test_type": "t-test",
            },
            start_to_close_timeout=timedelta(seconds=60),
        )

        # ── Phase 4: Chart Generation ─────────────────────────────────────────
        chart_artifact = await workflow.execute_activity(
            GenerationActivities.run_generators,
            {
                "generator": "bar_comparison",
                "job_id": job_id,
                "tenant_id": tenant_id,
                "data": {
                    "brand": brand_rows,
                    "competitors": competitor_rows,
                    "metric": metric,
                    "title": f"Brand vs Competitors — {metric}",
                },
            },
            start_to_close_timeout=timedelta(minutes=2),
        )

        # ── Phase 5: PDF Report via UPTP Render ───────────────────────────────
        report_artifact = await workflow.execute_activity(
            GenerationActivities.run_generators,
            {
                "generator": "pdf_report",
                "job_id": job_id,
                "tenant_id": tenant_id,
                "template": "benchmark",
                "data": {
                    "brand_source_id": brand_source,
                    "competitor_source_ids": comp_sources,
                    "metric": metric,
                    "market_share": market_share,
                    "significance_test": significance_test,
                    "chart_artifact_id": chart_artifact.get("artifact_id"),
                },
            },
            start_to_close_timeout=timedelta(minutes=5),
        )

        result = {
            "status": "completed",
            "brand_source_id": brand_source,
            "competitor_source_ids": comp_sources,
            "metric": metric,
            "brand_sample_count": len(brand_rows),
            "competitor_sample_count": len(competitor_rows),
            "market_share": market_share,
            "significance_test": significance_test,
            "chart_artifact_id": chart_artifact.get("artifact_id"),
            "report_hash": report_artifact.get("artifact_hash"),
        }

        workflow.logger.info(
            f"BenchmarkBrandWorkflow completed. report_hash={result['report_hash']}"
        )
        return result
