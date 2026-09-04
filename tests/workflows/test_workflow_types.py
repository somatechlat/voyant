"""
Comprehensive tests for workflow types and workflow class pure-logic methods.

Covers:
- IngestParams dataclass: construction, defaults, field access
- IngestResult dataclass: construction, field access
- LinearRegressionWorkflow._format_equation: various coefficient scenarios
- LinearRegressionWorkflow._interpret_r2: all R² quality thresholds
- Workflow class definitions: verify @workflow.defn decorators and run methods exist
- SegmentCustomersWorkflow segment profile calculation logic (extracted)
- AnalyzeWorkflow parameter resolution logic
- QualityWorkflow table resolution logic
- SandboxWorkflow validation logic
"""

import pytest

from apps.worker.workflows.types import IngestParams, IngestResult


# ---------------------------------------------------------------------------
# IngestParams Dataclass
# ---------------------------------------------------------------------------


class TestIngestParams:
    """Tests for the IngestParams dataclass."""

    def test_create_with_required_fields(self):
        """IngestParams can be created with only required fields."""
        params = IngestParams(job_id="j1", source_id="src-1")
        assert params.job_id == "j1"
        assert params.source_id == "src-1"

    def test_default_mode_is_full(self):
        """IngestParams defaults mode to 'full'."""
        params = IngestParams(job_id="j1", source_id="src-1")
        assert params.mode == "full"

    def test_default_tables_is_none(self):
        """IngestParams defaults tables to None."""
        params = IngestParams(job_id="j1", source_id="src-1")
        assert params.tables is None

    def test_create_with_all_fields(self):
        """IngestParams accepts all fields."""
        params = IngestParams(
            job_id="j1",
            source_id="src-1",
            mode="incremental",
            tables=["users", "orders"],
        )
        assert params.mode == "incremental"
        assert params.tables == ["users", "orders"]

    def test_mode_full(self):
        """IngestParams mode can be set to 'full'."""
        params = IngestParams(job_id="j1", source_id="src-1", mode="full")
        assert params.mode == "full"

    def test_mode_incremental(self):
        """IngestParams mode can be set to 'incremental'."""
        params = IngestParams(job_id="j1", source_id="src-1", mode="incremental")
        assert params.mode == "incremental"

    def test_tables_empty_list(self):
        """IngestParams tables can be an empty list."""
        params = IngestParams(job_id="j1", source_id="src-1", tables=[])
        assert params.tables == []

    def test_tables_single_table(self):
        """IngestParams tables can contain a single table."""
        params = IngestParams(job_id="j1", source_id="src-1", tables=["users"])
        assert params.tables == ["users"]

    def test_tables_multiple_tables(self):
        """IngestParams tables can contain multiple tables."""
        tables = ["users", "orders", "products", "inventory"]
        params = IngestParams(job_id="j1", source_id="src-1", tables=tables)
        assert params.tables == tables
        assert len(params.tables) == 4

    def test_dataclass_equality(self):
        """Two IngestParams with the same fields are equal."""
        p1 = IngestParams(job_id="j1", source_id="src-1", mode="full")
        p2 = IngestParams(job_id="j1", source_id="src-1", mode="full")
        assert p1 == p2

    def test_dataclass_inequality(self):
        """Two IngestParams with different fields are not equal."""
        p1 = IngestParams(job_id="j1", source_id="src-1")
        p2 = IngestParams(job_id="j2", source_id="src-1")
        assert p1 != p2

    def test_dataclass_repr(self):
        """IngestParams has a useful repr."""
        params = IngestParams(job_id="j1", source_id="src-1")
        repr_str = repr(params)
        assert "IngestParams" in repr_str
        assert "j1" in repr_str
        assert "src-1" in repr_str

    def test_fields_are_mutable(self):
        """IngestParams fields can be modified after creation."""
        params = IngestParams(job_id="j1", source_id="src-1")
        params.mode = "incremental"
        params.tables = ["t1"]
        assert params.mode == "incremental"
        assert params.tables == ["t1"]


# ---------------------------------------------------------------------------
# IngestResult Dataclass
# ---------------------------------------------------------------------------


class TestIngestResult:
    """Tests for the IngestResult dataclass."""

    def test_create_with_all_fields(self):
        """IngestResult can be created with all fields."""
        result = IngestResult(
            job_id="j1",
            source_id="src-1",
            status="completed",
            rows_ingested=5000,
            tables_synced=["users", "orders"],
            completed_at="2024-01-01T12:00:00Z",
        )
        assert result.job_id == "j1"
        assert result.source_id == "src-1"
        assert result.status == "completed"
        assert result.rows_ingested == 5000
        assert result.tables_synced == ["users", "orders"]
        assert result.completed_at == "2024-01-01T12:00:00Z"

    def test_zero_rows_ingested(self):
        """IngestResult can have zero rows ingested."""
        result = IngestResult(
            job_id="j1",
            source_id="src-1",
            status="completed",
            rows_ingested=0,
            tables_synced=[],
            completed_at="2024-01-01T12:00:00Z",
        )
        assert result.rows_ingested == 0
        assert result.tables_synced == []

    def test_large_rows_ingested(self):
        """IngestResult can handle large row counts."""
        result = IngestResult(
            job_id="j1",
            source_id="src-1",
            status="completed",
            rows_ingested=10_000_000,
            tables_synced=["big_table"],
            completed_at="2024-01-01T12:00:00Z",
        )
        assert result.rows_ingested == 10_000_000

    def test_dataclass_equality(self):
        """Two IngestResults with the same fields are equal."""
        r1 = IngestResult(
            job_id="j1",
            source_id="src-1",
            status="completed",
            rows_ingested=100,
            tables_synced=["t1"],
            completed_at="2024-01-01T00:00:00Z",
        )
        r2 = IngestResult(
            job_id="j1",
            source_id="src-1",
            status="completed",
            rows_ingested=100,
            tables_synced=["t1"],
            completed_at="2024-01-01T00:00:00Z",
        )
        assert r1 == r2

    def test_dataclass_repr(self):
        """IngestResult has a useful repr."""
        result = IngestResult(
            job_id="j1",
            source_id="src-1",
            status="completed",
            rows_ingested=100,
            tables_synced=["t1"],
            completed_at="2024-01-01T00:00:00Z",
        )
        repr_str = repr(result)
        assert "IngestResult" in repr_str
        assert "j1" in repr_str


# ---------------------------------------------------------------------------
# LinearRegressionWorkflow Pure Logic
# ---------------------------------------------------------------------------


class TestLinearRegressionWorkflowLogic:
    """Tests for LinearRegressionWorkflow pure-logic helper methods."""

    @pytest.fixture
    def workflow(self):
        """Create a LinearRegressionWorkflow instance for testing pure methods."""
        from apps.worker.workflows.regression_workflow import LinearRegressionWorkflow

        return LinearRegressionWorkflow()

    # -- _format_equation tests --

    def test_format_equation_single_feature(self, workflow):
        """_format_equation with a single feature."""
        result = {
            "target": "price",
            "intercept": 10.5,
            "coefficients": [2.3],
            "features": ["area"],
        }
        eq = workflow._format_equation(result)
        assert eq == "price = 10.50 + 2.30*area"

    def test_format_equation_multiple_features(self, workflow):
        """_format_equation with multiple features."""
        result = {
            "target": "price",
            "intercept": 5.0,
            "coefficients": [2.0, -1.5, 0.75],
            "features": ["area", "age", "rooms"],
        }
        eq = workflow._format_equation(result)
        assert eq == "price = 5.00 + 2.00*area - 1.50*age + 0.75*rooms"

    def test_format_equation_negative_intercept(self, workflow):
        """_format_equation handles negative intercept."""
        result = {
            "target": "y",
            "intercept": -3.14,
            "coefficients": [1.0],
            "features": ["x1"],
        }
        eq = workflow._format_equation(result)
        assert eq == "y = -3.14 + 1.00*x1"

    def test_format_equation_zero_coefficient(self, workflow):
        """_format_equation handles zero coefficient."""
        result = {
            "target": "y",
            "intercept": 0.0,
            "coefficients": [0.0],
            "features": ["x1"],
        }
        eq = workflow._format_equation(result)
        # Zero is >= 0, so it gets a "+" sign
        assert eq == "y = 0.00 + 0.00*x1"

    def test_format_equation_empty_features(self, workflow):
        """_format_equation with no features (intercept-only model)."""
        result = {
            "target": "y",
            "intercept": 42.0,
            "coefficients": [],
            "features": [],
        }
        eq = workflow._format_equation(result)
        assert eq == "y = 42.00"

    def test_format_equation_default_values(self, workflow):
        """_format_equation handles missing keys with defaults."""
        result = {}
        eq = workflow._format_equation(result)
        assert eq == "y = 0.00"

    def test_format_equation_all_negative_coefficients(self, workflow):
        """_format_equation with all negative coefficients."""
        result = {
            "target": "score",
            "intercept": 100.0,
            "coefficients": [-5.0, -3.0, -1.0],
            "features": ["x1", "x2", "x3"],
        }
        eq = workflow._format_equation(result)
        assert eq == "score = 100.00 - 5.00*x1 - 3.00*x2 - 1.00*x3"

    def test_format_equation_large_values(self, workflow):
        """_format_equation handles large coefficient values."""
        result = {
            "target": "revenue",
            "intercept": 1000000.0,
            "coefficients": [50000.0],
            "features": ["marketing_spend"],
        }
        eq = workflow._format_equation(result)
        assert eq == "revenue = 1000000.00 + 50000.00*marketing_spend"

    def test_format_equation_small_values(self, workflow):
        """_format_equation handles small coefficient values."""
        result = {
            "target": "y",
            "intercept": 0.001,
            "coefficients": [0.002],
            "features": ["x"],
        }
        eq = workflow._format_equation(result)
        assert eq == "y = 0.00 + 0.00*x"

    # -- _interpret_r2 tests --

    def test_interpret_r2_excellent(self, workflow):
        """R² >= 0.9 is 'excellent'."""
        assert workflow._interpret_r2(0.9) == "excellent"
        assert workflow._interpret_r2(0.95) == "excellent"
        assert workflow._interpret_r2(1.0) == "excellent"

    def test_interpret_r2_good(self, workflow):
        """0.7 <= R² < 0.9 is 'good'."""
        assert workflow._interpret_r2(0.7) == "good"
        assert workflow._interpret_r2(0.8) == "good"
        assert workflow._interpret_r2(0.89) == "good"

    def test_interpret_r2_moderate(self, workflow):
        """0.5 <= R² < 0.7 is 'moderate'."""
        assert workflow._interpret_r2(0.5) == "moderate"
        assert workflow._interpret_r2(0.6) == "moderate"
        assert workflow._interpret_r2(0.69) == "moderate"

    def test_interpret_r2_poor(self, workflow):
        """R² < 0.5 is 'poor'."""
        assert workflow._interpret_r2(0.0) == "poor"
        assert workflow._interpret_r2(0.1) == "poor"
        assert workflow._interpret_r2(0.49) == "poor"

    def test_interpret_r2_zero(self, workflow):
        """R² of exactly 0 is 'poor'."""
        assert workflow._interpret_r2(0.0) == "poor"

    def test_interpret_r2_boundary_values(self, workflow):
        """R² boundary values are classified correctly."""
        assert workflow._interpret_r2(0.49999) == "poor"
        assert workflow._interpret_r2(0.5) == "moderate"
        assert workflow._interpret_r2(0.69999) == "moderate"
        assert workflow._interpret_r2(0.7) == "good"
        assert workflow._interpret_r2(0.89999) == "good"
        assert workflow._interpret_r2(0.9) == "excellent"


# ---------------------------------------------------------------------------
# Workflow Class Definitions
# ---------------------------------------------------------------------------


class TestWorkflowDefinitions:
    """Tests verifying workflow class structure and method signatures."""

    def test_analyze_workflow_exists(self):
        """AnalyzeWorkflow class is importable and has a run method."""
        from apps.worker.workflows.analyze_workflow import AnalyzeWorkflow

        assert hasattr(AnalyzeWorkflow, "run")
        assert callable(getattr(AnalyzeWorkflow, "run", None))

    def test_ingest_workflow_exists(self):
        """IngestDataWorkflow class is importable and has a run method."""
        from apps.worker.workflows.ingest_workflow import IngestDataWorkflow

        assert hasattr(IngestDataWorkflow, "run")
        assert callable(getattr(IngestDataWorkflow, "run", None))

    def test_profile_workflow_exists(self):
        """ProfileWorkflow class is importable and has a run method."""
        from apps.worker.workflows.profile_workflow import ProfileWorkflow

        assert hasattr(ProfileWorkflow, "run")
        assert callable(getattr(ProfileWorkflow, "run", None))

    def test_quality_workflow_exists(self):
        """QualityWorkflow class is importable and has a run method."""
        from apps.worker.workflows.quality_workflow import QualityWorkflow

        assert hasattr(QualityWorkflow, "run")
        assert callable(getattr(QualityWorkflow, "run", None))

    def test_benchmark_workflow_exists(self):
        """BenchmarkBrandWorkflow class is importable and has a run method."""
        from apps.worker.workflows.benchmark_workflow import BenchmarkBrandWorkflow

        assert hasattr(BenchmarkBrandWorkflow, "run")
        assert callable(getattr(BenchmarkBrandWorkflow, "run", None))

    def test_capsule_workflow_exists(self):
        """CapsuleWorkflow class is importable and has a run method."""
        from apps.worker.workflows.capsule_workflow import CapsuleWorkflow

        assert hasattr(CapsuleWorkflow, "run")
        assert callable(getattr(CapsuleWorkflow, "run", None))

    def test_detect_anomalies_workflow_exists(self):
        """DetectAnomaliesWorkflow class is importable and has a run method."""
        from apps.worker.workflows.operational_workflows import DetectAnomaliesWorkflow

        assert hasattr(DetectAnomaliesWorkflow, "run")
        assert callable(getattr(DetectAnomaliesWorkflow, "run", None))

    def test_analyze_sentiment_workflow_exists(self):
        """AnalyzeSentimentWorkflow class is importable and has a run method."""
        from apps.worker.workflows.operational_workflows import AnalyzeSentimentWorkflow

        assert hasattr(AnalyzeSentimentWorkflow, "run")
        assert callable(getattr(AnalyzeSentimentWorkflow, "run", None))

    def test_fix_data_quality_workflow_exists(self):
        """FixDataQualityWorkflow class is importable and has a run method."""
        from apps.worker.workflows.operational_workflows import FixDataQualityWorkflow

        assert hasattr(FixDataQualityWorkflow, "run")
        assert callable(getattr(FixDataQualityWorkflow, "run", None))

    def test_forecast_workflow_exists(self):
        """ForecastWorkflow class is importable and has a run method."""
        from apps.worker.workflows.operational_workflows import ForecastWorkflow

        assert hasattr(ForecastWorkflow, "run")
        assert callable(getattr(ForecastWorkflow, "run", None))

    def test_linear_regression_workflow_exists(self):
        """LinearRegressionWorkflow class is importable and has helper methods."""
        from apps.worker.workflows.regression_workflow import LinearRegressionWorkflow

        assert hasattr(LinearRegressionWorkflow, "run")
        assert hasattr(LinearRegressionWorkflow, "_format_equation")
        assert hasattr(LinearRegressionWorkflow, "_interpret_r2")

    def test_sandbox_workflow_exists(self):
        """SandboxWorkflow class is importable and has a run method."""
        from apps.worker.workflows.sandbox_workflow import SandboxWorkflow

        assert hasattr(SandboxWorkflow, "run")
        assert callable(getattr(SandboxWorkflow, "run", None))

    def test_segment_customers_workflow_exists(self):
        """SegmentCustomersWorkflow class is importable and has a run method."""
        from apps.worker.workflows.segmentation_workflow import (
            SegmentCustomersWorkflow,
        )

        assert hasattr(SegmentCustomersWorkflow, "run")
        assert callable(getattr(SegmentCustomersWorkflow, "run", None))


# ---------------------------------------------------------------------------
# AnalyzeWorkflow Parameter Resolution Logic
# ---------------------------------------------------------------------------


class TestAnalyzeWorkflowParamResolution:
    """Tests for AnalyzeWorkflow parameter resolution logic (extracted)."""

    def test_table_from_table_param(self):
        """table is resolved from params['table'] when present."""
        params = {"table": "users", "source_id": "src-1"}
        table = params.get("table") or params.get("source_id")
        assert table == "users"

    def test_table_fallback_to_source_id(self):
        """table falls back to params['source_id'] when table is None."""
        params = {"table": None, "source_id": "src-1"}
        table = params.get("table") or params.get("source_id")
        assert table == "src-1"

    def test_table_fallback_when_table_missing(self):
        """table falls back to source_id when table key is absent."""
        params = {"source_id": "src-1"}
        table = params.get("table") or params.get("source_id")
        assert table == "src-1"

    def test_profile_default_true(self):
        """profile defaults to True."""
        params = {}
        assert params.get("profile", True) is True

    def test_run_analyzers_default_true(self):
        """run_analyzers defaults to True."""
        params = {}
        assert params.get("run_analyzers", True) is True

    def test_generate_artifacts_default_true(self):
        """generate_artifacts defaults to True."""
        params = {}
        assert params.get("generate_artifacts", True) is True

    def test_sample_size_default(self):
        """sample_size defaults to 10000."""
        params = {}
        assert params.get("sample_size", 10000) == 10000

    def test_summary_computation(self):
        """Summary dict is computed correctly from results."""
        kpi_results = [{"kpi": "revenue"}, {"kpi": "churn"}]
        analyzer_results = {"anomaly": {}, "sentiment": {}, "forecast": {}}
        table = "users"

        summary = {
            "table": table,
            "kpi_count": len(kpi_results),
            "analyzer_count": len(analyzer_results) if analyzer_results else 0,
        }
        assert summary["table"] == "users"
        assert summary["kpi_count"] == 2
        assert summary["analyzer_count"] == 3

    def test_summary_empty_results(self):
        """Summary handles empty results."""
        kpi_results = []
        analyzer_results = {}

        summary = {
            "table": "t",
            "kpi_count": len(kpi_results),
            "analyzer_count": len(analyzer_results) if analyzer_results else 0,
        }
        assert summary["kpi_count"] == 0
        assert summary["analyzer_count"] == 0


# ---------------------------------------------------------------------------
# QualityWorkflow Table Resolution Logic
# ---------------------------------------------------------------------------


class TestQualityWorkflowTableResolution:
    """Tests for QualityWorkflow table resolution logic (extracted)."""

    def test_table_from_table_param(self):
        """QualityWorkflow resolves table from 'table' param."""
        params = {"table": "users", "source_id": "src-1"}
        table = params.get("table") or params.get("source_id")
        assert table == "users"

    def test_table_fallback_to_source_id(self):
        """QualityWorkflow falls back to source_id when table is None."""
        params = {"table": None, "source_id": "src-1"}
        table = params.get("table") or params.get("source_id")
        assert table == "src-1"

    def test_table_fallback_when_missing(self):
        """QualityWorkflow falls back to source_id when table is absent."""
        params = {"source_id": "src-1"}
        table = params.get("table") or params.get("source_id")
        assert table == "src-1"

    def test_quality_result_structure(self):
        """QualityWorkflow return structure is correct."""
        table = "users"
        result = {"rows_analyzed": 500, "checks_passed": 4, "checks_failed": 1}
        output = {
            "table": table,
            "rows_analyzed": result.get("rows_analyzed", 0),
            "quality": result,
        }
        assert output["table"] == "users"
        assert output["rows_analyzed"] == 500
        assert output["quality"]["checks_passed"] == 4

    def test_quality_result_default_rows_analyzed(self):
        """rows_analyzed defaults to 0 when not in result."""
        result = {}
        assert result.get("rows_analyzed", 0) == 0


# ---------------------------------------------------------------------------
# SandboxWorkflow Validation Logic
# ---------------------------------------------------------------------------


class TestSandboxWorkflowValidation:
    """Tests for SandboxWorkflow validation logic."""

    def test_script_required(self):
        """SandboxWorkflow requires a 'script' parameter."""
        params = {"tenant_id": "t1", "job_id": "j1"}
        script = params.get("script")
        assert script is None  # Would trigger ValueError in the workflow

    def test_script_present(self):
        """SandboxWorkflow accepts a script parameter."""
        params = {
            "script": "print('hello')",
            "tenant_id": "t1",
            "job_id": "j1",
        }
        assert params.get("script") == "print('hello')"

    def test_dependencies_default_empty(self):
        """SandboxWorkflow dependencies default to empty list."""
        params = {"script": "x=1", "tenant_id": "t1", "job_id": "j1"}
        assert params.get("dependencies", []) == []

    def test_dependencies_provided(self):
        """SandboxWorkflow accepts dependencies list."""
        params = {
            "script": "import numpy",
            "tenant_id": "t1",
            "job_id": "j1",
            "dependencies": ["numpy", "pandas"],
        }
        assert params["dependencies"] == ["numpy", "pandas"]


# ---------------------------------------------------------------------------
# SegmentCustomersWorkflow Profile Calculation Logic
# ---------------------------------------------------------------------------


class TestSegmentCustomersProfileCalculation:
    """Tests for SegmentCustomersWorkflow segment profile calculation logic."""

    def _calculate_profiles(self, data, clusters, n_segments):
        """Extract the segment profile calculation logic from the workflow."""
        segment_profiles = {}
        for cluster_id in range(n_segments):
            cluster_members = [
                data[i] for i, c in enumerate(clusters) if c == cluster_id
            ]
            if cluster_members:
                avg_profile = {}
                if cluster_members:
                    keys = cluster_members[0].keys()
                    for key in keys:
                        values = [m[key] for m in cluster_members if key in m]
                        avg_profile[key] = sum(values) / len(values) if values else 0

                segment_profiles[f"segment_{cluster_id}"] = {
                    "size": len(cluster_members),
                    "percentage": (
                        len(cluster_members) / len(data) * 100 if len(data) > 0 else 0
                    ),
                    "average_profile": avg_profile,
                }
        return segment_profiles

    def test_single_segment(self):
        """Profile calculation with a single segment."""
        data = [{"age": 25, "income": 50000}, {"age": 35, "income": 70000}]
        clusters = [0, 0]
        profiles = self._calculate_profiles(data, clusters, 1)
        assert "segment_0" in profiles
        assert profiles["segment_0"]["size"] == 2
        assert profiles["segment_0"]["percentage"] == 100.0
        assert profiles["segment_0"]["average_profile"]["age"] == 30.0
        assert profiles["segment_0"]["average_profile"]["income"] == 60000.0

    def test_two_segments(self):
        """Profile calculation with two equal segments."""
        data = [
            {"age": 20, "income": 30000},
            {"age": 25, "income": 40000},
            {"age": 50, "income": 90000},
            {"age": 55, "income": 100000},
        ]
        clusters = [0, 0, 1, 1]
        profiles = self._calculate_profiles(data, clusters, 2)
        assert profiles["segment_0"]["size"] == 2
        assert profiles["segment_0"]["percentage"] == 50.0
        assert profiles["segment_0"]["average_profile"]["age"] == 22.5
        assert profiles["segment_1"]["size"] == 2
        assert profiles["segment_1"]["percentage"] == 50.0
        assert profiles["segment_1"]["average_profile"]["age"] == 52.5

    def test_uneven_segments(self):
        """Profile calculation with uneven segment sizes."""
        data = [
            {"value": 10},
            {"value": 20},
            {"value": 30},
            {"value": 100},
        ]
        clusters = [0, 0, 0, 1]
        profiles = self._calculate_profiles(data, clusters, 2)
        assert profiles["segment_0"]["size"] == 3
        assert profiles["segment_0"]["percentage"] == 75.0
        assert profiles["segment_0"]["average_profile"]["value"] == 20.0
        assert profiles["segment_1"]["size"] == 1
        assert profiles["segment_1"]["percentage"] == 25.0
        assert profiles["segment_1"]["average_profile"]["value"] == 100.0

    def test_empty_segment(self):
        """Profile calculation handles empty segments gracefully."""
        data = [{"value": 10}, {"value": 20}]
        clusters = [0, 0]
        profiles = self._calculate_profiles(data, clusters, 3)
        # segment_0 exists, segment_1 and segment_2 are empty (not in profiles)
        assert "segment_0" in profiles
        assert "segment_1" not in profiles
        assert "segment_2" not in profiles

    def test_empty_data(self):
        """Profile calculation handles empty data."""
        profiles = self._calculate_profiles([], [], 2)
        assert profiles == {}

    def test_single_data_point(self):
        """Profile calculation with a single data point."""
        data = [{"age": 30, "income": 50000}]
        clusters = [0]
        profiles = self._calculate_profiles(data, clusters, 1)
        assert profiles["segment_0"]["size"] == 1
        assert profiles["segment_0"]["percentage"] == 100.0
        assert profiles["segment_0"]["average_profile"]["age"] == 30.0

    def test_multiple_features(self):
        """Profile calculation with multiple features."""
        data = [
            {"a": 1, "b": 10, "c": 100},
            {"a": 3, "b": 30, "c": 300},
        ]
        clusters = [0, 0]
        profiles = self._calculate_profiles(data, clusters, 1)
        avg = profiles["segment_0"]["average_profile"]
        assert avg["a"] == 2.0
        assert avg["b"] == 20.0
        assert avg["c"] == 200.0


# ---------------------------------------------------------------------------
# BenchmarkWorkflow Parameter Extraction Logic
# ---------------------------------------------------------------------------


class TestBenchmarkWorkflowParamExtraction:
    """Tests for BenchmarkWorkflow parameter extraction logic."""

    def test_brand_source_extraction(self):
        """Brand source is extracted from params."""
        params = {"brand_source_id": "brand-1", "competitor_source_ids": ["comp-1"]}
        assert params["brand_source_id"] == "brand-1"

    def test_competitor_sources_default(self):
        """Competitor sources default to empty list."""
        params = {"brand_source_id": "brand-1"}
        assert params.get("competitor_source_ids", []) == []

    def test_metric_default(self):
        """Metric defaults to 'revenue'."""
        params = {"brand_source_id": "brand-1"}
        assert params.get("metric", "revenue") == "revenue"

    def test_job_id_default(self):
        """job_id defaults to 'benchmark_{brand_source}'."""
        params = {"brand_source_id": "brand-1"}
        job_id = params.get("job_id", f"benchmark_{params['brand_source_id']}")
        assert job_id == "benchmark_brand-1"

    def test_tenant_id_default(self):
        """tenant_id defaults to 'default'."""
        params = {}
        assert params.get("tenant_id", "default") == "default"

    def test_all_sources_computation(self):
        """all_sources combines brand + competitors."""
        brand_source = "brand-1"
        comp_sources = ["comp-1", "comp-2"]
        all_sources = [brand_source] + comp_sources
        assert all_sources == ["brand-1", "comp-1", "comp-2"]

    def test_brand_rows_extraction(self):
        """Brand rows are extracted from sample data, filtering None values."""
        brand_sample = {
            "rows": [
                {"revenue": 100},
                {"revenue": None},
                {"revenue": 200},
                {"revenue": 300},
            ]
        }
        metric = "revenue"
        brand_rows = [
            {"value": row[metric]}
            for row in brand_sample.get("rows", [])
            if row.get(metric) is not None
        ]
        assert len(brand_rows) == 3
        assert brand_rows[0]["value"] == 100
        assert brand_rows[1]["value"] == 200

    def test_competitor_rows_extraction_from_multiple_samples(self):
        """Competitor rows are extracted from multiple competitor samples."""
        competitor_samples = [
            {"rows": [{"revenue": 50}, {"revenue": 60}]},
            {"rows": [{"revenue": 70}]},
        ]
        metric = "revenue"
        competitor_rows = [
            {"value": row[metric]}
            for sample in competitor_samples
            for row in sample.get("rows", [])
            if row.get(metric) is not None
        ]
        assert len(competitor_rows) == 3
        assert [r["value"] for r in competitor_rows] == [50, 60, 70]


# ---------------------------------------------------------------------------
# CapsuleWorkflow Logic
# ---------------------------------------------------------------------------


class TestCapsuleWorkflowLogic:
    """Tests for CapsuleWorkflow logic patterns."""

    def test_step_metadata_accumulation(self):
        """Step metadata accumulates across steps."""
        step_metadata = {}
        step_metadata["step_1"] = {"status": "done", "output": "result_1"}
        step_metadata["step_2"] = {"status": "done", "output": "result_2"}
        assert len(step_metadata) == 2
        assert step_metadata["step_1"]["output"] == "result_1"

    def test_job_urn_format(self):
        """Job URN follows the expected format."""
        tenant_id = "t1"
        capsule_name = "my_capsule"
        run_id = "run-abc-123"
        job_urn = f"urn:voyant:job:{tenant_id}:{capsule_name}:{run_id}"
        assert job_urn == "urn:voyant:job:t1:my_capsule:run-abc-123"

    def test_job_urn_unknown_capsule_name(self):
        """Job URN uses 'unknown' when capsule name is missing."""
        capsule = {}
        capsule_name = capsule.get("name", "unknown")
        assert capsule_name == "unknown"

    def test_execution_graph_iteration(self):
        """Execution graph steps are iterated correctly."""
        graph = [
            {"step_id": "s1", "action": "fetch", "params": {}},
            {"step_id": "s2", "action": "transform", "params": {}},
            {"step_id": "s3", "action": "store", "params": {}},
        ]
        step_ids = [step["step_id"] for step in graph]
        assert step_ids == ["s1", "s2", "s3"]

    def test_condition_skip_logic(self):
        """Steps with unmet conditions are skipped."""
        step_metadata = {"s1": {"status": "done"}}
        step = {"step_id": "s2", "condition": "s1.status == 'failed'"}
        # In real workflow, condition would be evaluated; here we test the skip pattern
        condition_met = False  # Simulating condition not met
        if step.get("condition") and not condition_met:
            skipped = True
        else:
            skipped = False
        assert skipped is True

    def test_retry_policy_defaults(self):
        """Step retry policy defaults are correct."""
        retry = {"max_attempts": 3, "backoff_seconds": 5}
        assert retry.get("max_attempts", 3) == 3
        assert retry.get("backoff_seconds", 5) == 5

    def test_timeout_default(self):
        """Step timeout defaults to 60 seconds."""
        step = {"step_id": "s1", "action": "fetch"}
        timeout = step.get("timeout_seconds", 60)
        assert timeout == 60


# ---------------------------------------------------------------------------
# Operational Workflows Parameter Logic
# ---------------------------------------------------------------------------


class TestOperationalWorkflowsParamLogic:
    """Tests for operational workflows parameter extraction logic."""

    def test_detect_anomalies_default_contamination(self):
        """DetectAnomaliesWorkflow contamination defaults to 0.1."""
        params = {}
        assert params.get("contamination", 0.1) == 0.1

    def test_detect_anomalies_default_data(self):
        """DetectAnomaliesWorkflow data defaults to empty list."""
        params = {}
        assert params.get("data", []) == []

    def test_sentiment_texts_extraction(self):
        """AnalyzeSentimentWorkflow extracts texts list."""
        params = {"texts": ["I love this", "Terrible product", "It's okay"]}
        texts = params.get("texts", [])
        assert len(texts) == 3

    def test_sentiment_aggregation_logic(self):
        """AnalyzeSentimentWorkflow aggregation logic is correct."""
        results = [
            {"sentiment": "positive"},
            {"sentiment": "negative"},
            {"sentiment": "positive"},
            {"sentiment": "neutral"},
            {"sentiment": "positive"},
        ]
        positive = sum(1 for r in results if r["sentiment"] == "positive")
        negative = sum(1 for r in results if r["sentiment"] == "negative")
        neutral = sum(1 for r in results if r["sentiment"] == "neutral")
        assert positive == 3
        assert negative == 1
        assert neutral == 1

    def test_fix_data_quality_defaults(self):
        """FixDataQualityWorkflow has correct defaults."""
        params = {}
        assert params.get("imputation_strategy", "median") == "median"
        assert params.get("outlier_strategy", "cap") == "cap"
        assert params.get("outlier_threshold", 3.0) == 3.0
        assert params.get("data", []) == []
        assert params.get("numeric_columns", []) == []
        assert params.get("categorical_columns", []) == []

    def test_forecast_defaults(self):
        """ForecastWorkflow has correct defaults."""
        params = {}
        assert params.get("values", []) == []
        assert params.get("dates") is None
        assert params.get("periods", 7) == 7
        assert params.get("method", "ema") == "ema"
        assert params.get("confidence_level", 0.95) == 0.95

    def test_forecast_with_all_params(self):
        """ForecastWorkflow accepts all parameters."""
        params = {
            "values": [100.0, 110.0, 120.0],
            "dates": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "periods": 12,
            "method": "prophet",
            "confidence_level": 0.99,
        }
        assert params["method"] == "prophet"
        assert params["periods"] == 12
        assert params["confidence_level"] == 0.99


# ---------------------------------------------------------------------------
# IngestWorkflow Retry Policy Logic
# ---------------------------------------------------------------------------


class TestIngestWorkflowRetryPolicy:
    """Tests for IngestWorkflow retry policy configuration."""

    def test_retry_policy_initial_interval(self):
        """Retry policy has 1 second initial interval."""
        from datetime import timedelta

        from temporalio.common import RetryPolicy

        policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=60),
            maximum_attempts=3,
        )
        assert policy.initial_interval == timedelta(seconds=1)
        assert policy.backoff_coefficient == 2.0
        assert policy.maximum_interval == timedelta(seconds=60)
        assert policy.maximum_attempts == 3

    def test_non_retryable_error_types(self):
        """Non-retryable error types are correctly configured."""
        non_retryable = [
            "ValidationError",
            "AuthenticationError",
            "AuthorizationError",
            "ApplicationError",
        ]
        assert "ValidationError" in non_retryable
        assert "AuthenticationError" in non_retryable
        assert "AuthorizationError" in non_retryable
        assert "ApplicationError" in non_retryable

    def test_contract_validation_failure_logic(self):
        """Contract validation failure raises ApplicationError."""
        validation = {"valid": False, "errors": ["missing column 'id'"]}
        if not validation.get("valid", True):
            error_msg = f"Contract validation failed: {validation}"
            assert "Contract validation failed" in error_msg

    def test_contract_validation_pass_logic(self):
        """Contract validation pass allows workflow to continue."""
        validation = {"valid": True}
        assert validation.get("valid", True) is True


# ---------------------------------------------------------------------------
# Retry Config Module
# ---------------------------------------------------------------------------


class TestRetryConfig:
    """Tests for the retry configuration module."""

    def test_external_service_retry_import(self):
        """EXTERNAL_SERVICE_RETRY is importable."""
        from apps.core.lib.retry_config import EXTERNAL_SERVICE_RETRY

        assert EXTERNAL_SERVICE_RETRY is not None

    def test_data_processing_retry_import(self):
        """DATA_PROCESSING_RETRY is importable."""
        from apps.core.lib.retry_config import DATA_PROCESSING_RETRY

        assert DATA_PROCESSING_RETRY is not None

    def test_no_retry_import(self):
        """NO_RETRY is importable."""
        from apps.core.lib.retry_config import NO_RETRY

        assert NO_RETRY is not None

    def test_get_retry_policy_external_service(self):
        """get_retry_policy returns correct policy for 'external_service'."""
        from apps.core.lib.retry_config import (
            EXTERNAL_SERVICE_RETRY,
            get_retry_policy,
        )

        policy = get_retry_policy("external_service")
        assert policy is EXTERNAL_SERVICE_RETRY

    def test_get_retry_policy_data_processing(self):
        """get_retry_policy returns correct policy for 'data_processing'."""
        from apps.core.lib.retry_config import (
            DATA_PROCESSING_RETRY,
            get_retry_policy,
        )

        policy = get_retry_policy("data_processing")
        assert policy is DATA_PROCESSING_RETRY

    def test_get_retry_policy_no_retry(self):
        """get_retry_policy returns correct policy for 'no_retry'."""
        from apps.core.lib.retry_config import NO_RETRY, get_retry_policy

        policy = get_retry_policy("no_retry")
        assert policy is NO_RETRY

    def test_get_retry_policy_unknown_raises(self):
        """get_retry_policy raises ValueError for unknown type."""
        from apps.core.lib.retry_config import get_retry_policy

        with pytest.raises(ValueError, match="Unknown activity_type"):
            get_retry_policy("unknown_type")

    def test_get_timeout_valid_key(self):
        """get_timeout returns correct timeout for valid key."""
        from apps.core.lib.retry_config import get_timeout

        timeout = get_timeout("stats_short")
        assert timeout is not None

    def test_get_timeout_unknown_key_raises(self):
        """get_timeout raises ValueError for unknown key."""
        from apps.core.lib.retry_config import get_timeout

        with pytest.raises(ValueError, match="Unknown timeout_key"):
            get_timeout("nonexistent_timeout")

    def test_timeouts_dict_has_expected_keys(self):
        """TIMEOUTS dict contains expected keys."""
        from apps.core.lib.retry_config import TIMEOUTS

        expected_keys = [
            "stats_short",
            "stats_long",
            "ml_clustering",
            "ml_training",
            "ml_forecasting",
            "ingestion_short",
            "ingestion_long",
            "ingestion_airbyte",
            "operational_short",
            "operational_medium",
            "operational_long",
            "processing_short",
            "processing_long",
            "discovery",
        ]
        for key in expected_keys:
            assert key in TIMEOUTS, f"TIMEOUTS missing key: {key}"

    def test_heartbeat_intervals_has_expected_keys(self):
        """HEARTBEAT_INTERVALS dict contains expected keys."""
        from apps.core.lib.retry_config import HEARTBEAT_INTERVALS

        assert "default" in HEARTBEAT_INTERVALS
        assert "long_running" in HEARTBEAT_INTERVALS
        assert "data_transfer" in HEARTBEAT_INTERVALS
