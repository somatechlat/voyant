"""
Tests for AnalysisActivities.

Tests the analysis activity methods including fetch_sample and run_analyzers.
Uses real plugin registry and real data where possible. DuckDB-dependent tests
use an in-memory database.
"""

import os

import duckdb
import pytest
from temporalio.exceptions import ApplicationError

from apps.core.lib.plugin_registry import (
    AnalyzerPlugin,
    PluginCategory,
    register_plugin,
    reset_registry,
)
from apps.worker.activities.analysis_activities import AnalysisActivities


@pytest.fixture(scope="module")
def activities():
    """Real AnalysisActivities instance."""
    return AnalysisActivities()


@pytest.fixture()
def sample_duckdb(tmp_path):
    """Create a temporary DuckDB with test data and return its path."""
    db_path = str(tmp_path / "test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute(
        "CREATE TABLE test_table AS SELECT i AS id, i * 10 AS value, 'cat_' || (i % 3) AS category FROM generate_series(1, 100) t(i)"
    )
    conn.close()
    return db_path


class TestFeatureEnabled:
    """Tests for the _feature_enabled static method."""

    def test_feature_enabled_true_values(self):
        """All truthy env values should return True."""
        for val in ("1", "true", "TRUE", "True", "yes", "YES", "on", "ON"):
            os.environ["VOYANT_FEATURE_TEST_FLAG"] = val
            assert AnalysisActivities._feature_enabled("test_flag") is True
        del os.environ["VOYANT_FEATURE_TEST_FLAG"]

    def test_feature_enabled_false_values(self):
        """Non-truthy env values should return False."""
        for val in ("0", "false", "no", "off", "", "maybe", "random"):
            os.environ["VOYANT_FEATURE_TEST_FLAG"] = val
            assert AnalysisActivities._feature_enabled("test_flag") is False
        del os.environ["VOYANT_FEATURE_TEST_FLAG"]

    def test_feature_enabled_missing_env(self):
        """Missing env var should return False."""
        os.environ.pop("VOYANT_FEATURE_NONEXISTENT", None)
        assert AnalysisActivities._feature_enabled("nonexistent") is False

    def test_feature_enabled_case_insensitive_flag_name(self):
        """Flag name is uppercased to form the env key."""
        os.environ["VOYANT_FEATURE_MY_FLAG"] = "true"
        assert AnalysisActivities._feature_enabled("my_flag") is True
        assert AnalysisActivities._feature_enabled("MY_FLAG") is True
        assert AnalysisActivities._feature_enabled("My_Flag") is True
        del os.environ["VOYANT_FEATURE_MY_FLAG"]


class TestFetchSample:
    """Tests for the fetch_sample activity."""

    def test_fetch_sample_missing_table(self, activities):
        """Missing table param raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="table is required"):
            activities.fetch_sample({})

    def test_fetch_sample_empty_table(self, activities):
        """Empty string table param raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="table is required"):
            activities.fetch_sample({"table": ""})

    def test_fetch_sample_none_table(self, activities):
        """None table param raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="table is required"):
            activities.fetch_sample({"table": None})

    def test_fetch_sample_nonexistent_table(self, activities):
        """Non-existent table raises retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Failed to fetch sample"):
            activities.fetch_sample({"table": "nonexistent_xyz_table"})

    def test_fetch_sample_with_duckdb(self, activities, sample_duckdb, monkeypatch):
        """Successful sample fetch returns list of dicts."""
        monkeypatch.setattr(activities.settings, "duckdb_path", sample_duckdb)
        result = activities.fetch_sample({"table": "test_table", "sample_size": 10})
        assert isinstance(result, list)
        assert len(result) <= 10
        assert len(result) > 0
        assert "id" in result[0]
        assert "value" in result[0]
        assert "category" in result[0]

    def test_fetch_sample_default_size(self, activities, sample_duckdb, monkeypatch):
        """Default sample_size of 10000 is used when not specified."""
        monkeypatch.setattr(activities.settings, "duckdb_path", sample_duckdb)
        result = activities.fetch_sample({"table": "test_table"})
        assert isinstance(result, list)
        # Our test table has 100 rows, so we get all 100
        assert len(result) == 100

    def test_fetch_sample_small_limit(self, activities, sample_duckdb, monkeypatch):
        """Sample respects the requested limit."""
        monkeypatch.setattr(activities.settings, "duckdb_path", sample_duckdb)
        result = activities.fetch_sample({"table": "test_table", "sample_size": 5})
        assert len(result) == 5


class TestRunAnalyzers:
    """Tests for the run_analyzers activity."""

    def test_run_analyzers_no_plugins_registered(self, activities):
        """Empty registry returns empty dict."""
        reset_registry()
        result = activities.run_analyzers({"data": [{"a": 1}]})
        assert result == {}

    def test_run_analyzers_with_test_analyzer(self, activities):
        """A registered analyzer plugin is invoked and its result captured."""
        reset_registry()

        @register_plugin(
            name="test_analyzer",
            category=PluginCategory.DATA_QUALITY,
            description="Test analyzer",
        )
        class TestAnalyzer(AnalyzerPlugin):
            def analyze(self, data, context):
                return {"row_count": len(data), "context_keys": list(context.keys())}

        try:
            result = activities.run_analyzers(
                {
                    "data": [{"a": 1}, {"a": 2}],
                    "context": {"extra": "value"},
                }
            )
            assert "test_analyzer" in result
            assert result["test_analyzer"]["row_count"] == 2
            assert "extra" in result["test_analyzer"]["context_keys"]
        finally:
            reset_registry()

    def test_run_analyzers_filter_by_name(self, activities):
        """Only selected analyzers run when target list is provided."""
        reset_registry()

        @register_plugin(
            name="analyzer_a",
            category=PluginCategory.DATA_QUALITY,
        )
        class AnalyzerA(AnalyzerPlugin):
            def analyze(self, data, context):
                return {"name": "A"}

        @register_plugin(
            name="analyzer_b",
            category=PluginCategory.DATA_QUALITY,
        )
        class AnalyzerB(AnalyzerPlugin):
            def analyze(self, data, context):
                return {"name": "B"}

        try:
            result = activities.run_analyzers(
                {"data": [{}], "analyzers": ["analyzer_a"]}
            )
            assert "analyzer_a" in result
            assert "analyzer_b" not in result
        finally:
            reset_registry()

    def test_run_analyzers_non_core_failure_continues(self, activities):
        """Non-core analyzer failure is captured in _errors, others continue."""
        reset_registry()

        @register_plugin(
            name="failing_analyzer",
            category=PluginCategory.DATA_QUALITY,
            is_core=False,
        )
        class FailingAnalyzer(AnalyzerPlugin):
            def analyze(self, data, context):
                raise RuntimeError("boom")

        @register_plugin(
            name="good_analyzer",
            category=PluginCategory.DATA_QUALITY,
        )
        class GoodAnalyzer(AnalyzerPlugin):
            def analyze(self, data, context):
                return {"status": "ok"}

        try:
            result = activities.run_analyzers({"data": [{}]})
            assert "good_analyzer" in result
            assert result["good_analyzer"]["status"] == "ok"
            assert "_errors" in result
            assert any("failing_analyzer" in e for e in result["_errors"])
        finally:
            reset_registry()

    def test_run_analyzers_core_failure_halts(self, activities):
        """Core analyzer failure raises ApplicationError immediately."""
        reset_registry()

        @register_plugin(
            name="core_failing",
            category=PluginCategory.DATA_QUALITY,
            is_core=True,
        )
        class CoreFailingAnalyzer(AnalyzerPlugin):
            def analyze(self, data, context):
                raise RuntimeError("critical failure")

        @register_plugin(
            name="after_core",
            category=PluginCategory.DATA_QUALITY,
        )
        class AfterCoreAnalyzer(AnalyzerPlugin):
            def analyze(self, data, context):
                return {"should": "not_run"}

        try:
            with pytest.raises(ApplicationError, match="Core analyzer failed"):
                activities.run_analyzers({"data": [{}]})
        finally:
            reset_registry()

    def test_run_analyzers_feature_flag_disabled(self, activities):
        """Analyzer with disabled feature flag is skipped."""
        reset_registry()
        os.environ.pop("VOYANT_FEATURE_GATED_ANALYZER", None)

        @register_plugin(
            name="gated_analyzer",
            category=PluginCategory.DATA_QUALITY,
            feature_flag="gated_analyzer",
        )
        class GatedAnalyzer(AnalyzerPlugin):
            def analyze(self, data, context):
                return {"should": "not_run"}

        try:
            result = activities.run_analyzers({"data": [{}]})
            assert "gated_analyzer" not in result
        finally:
            reset_registry()

    def test_run_analyzers_feature_flag_enabled(self, activities):
        """Analyzer with enabled feature flag runs normally."""
        reset_registry()
        os.environ["VOYANT_FEATURE_ENABLED_ANALYZER"] = "true"

        @register_plugin(
            name="enabled_analyzer",
            category=PluginCategory.DATA_QUALITY,
            feature_flag="enabled_analyzer",
        )
        class EnabledAnalyzer(AnalyzerPlugin):
            def analyze(self, data, context):
                return {"ran": True}

        try:
            result = activities.run_analyzers({"data": [{}]})
            assert "enabled_analyzer" in result
            assert result["enabled_analyzer"]["ran"] is True
        finally:
            os.environ.pop("VOYANT_FEATURE_ENABLED_ANALYZER", None)
            reset_registry()

    def test_run_analyzers_plugin_context_merge(self, activities):
        """Plugin-specific context is merged with shared context."""
        reset_registry()

        @register_plugin(
            name="ctx_analyzer",
            category=PluginCategory.DATA_QUALITY,
        )
        class CtxAnalyzer(AnalyzerPlugin):
            def analyze(self, data, context):
                return context

        try:
            result = activities.run_analyzers(
                {
                    "data": [{}],
                    "context": {
                        "shared_key": "shared_val",
                        "ctx_analyzer": {"plugin_key": "plugin_val"},
                    },
                }
            )
            ctx = result["ctx_analyzer"]
            assert ctx["shared_key"] == "shared_val"
            assert ctx["plugin_key"] == "plugin_val"
        finally:
            reset_registry()

    def test_run_analyzers_load_failure_skips(self, activities):
        """Plugin that fails to load is skipped gracefully."""
        reset_registry()

        # Register a plugin class that will fail to instantiate
        @register_plugin(
            name="broken_loader",
            category=PluginCategory.DATA_QUALITY,
        )
        class BrokenLoader(AnalyzerPlugin):
            def __init__(self):
                raise RuntimeError("cannot init")

            def analyze(self, data, context):
                return {}

        try:
            result = activities.run_analyzers({"data": [{}]})
            # Plugin fails to load, so it's not in results
            assert "broken_loader" not in result
        finally:
            reset_registry()
