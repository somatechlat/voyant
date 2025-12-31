"""
Analyze Workflow

Orchestrates end-to-end analysis: profile, analyzers, KPI, generators.
"""
from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from voyant.activities.profile_activities import ProfileActivities
    from voyant.activities.analysis_activities import AnalysisActivities
    from voyant.activities.generation_activities import GenerationActivities
    from voyant.activities.kpi_activities import KPIActivities


@workflow.defn
class AnalyzeWorkflow:
    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run end-to-end analysis.

        Params:
            source_id: str
            table: str
            tables: list[str]
            sample_size: int
            kpis: list[dict]
            analyzers: list[str]
            analyzer_context: dict
            profile: bool
            run_analyzers: bool
            generate_artifacts: bool
            job_id: str
            tenant_id: str
        """
        table = params.get("table") or params.get("source_id")
        if not table:
            raise workflow.ApplicationError("table or source_id is required")

        profile_summary = None
        analyzer_results: Dict[str, Any] = {}
        kpi_results: List[Dict[str, Any]] = []
        generator_results: Dict[str, Any] = {}

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

        if params.get("kpis"):
            kpi_results = await workflow.execute_activity(
                KPIActivities.run_kpis,
                {"kpis": params.get("kpis")},
                start_to_close_timeout=timedelta(minutes=10),
            )

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

        summary = {
            "table": table,
            "kpi_count": len(kpi_results),
            "analyzer_count": len(analyzer_results) if analyzer_results else 0,
        }

        return {
            "summary": summary,
            "profile": profile_summary,
            "kpis": kpi_results,
            "analyzers": analyzer_results,
            "generators": generator_results,
        }
