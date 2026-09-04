"""
Tests for KPIActivities.

Tests the run_kpis activity. Since KPI execution depends on Trino (external service),
we test parameter validation, empty input handling, and error propagation.
"""

import pytest
from temporalio.exceptions import ApplicationError

from apps.worker.activities.kpi_activities import KPIActivities


@pytest.fixture(scope="module")
def activities():
    """Real KPIActivities instance."""
    return KPIActivities()


class TestRunKPIs:
    """Tests for the run_kpis activity."""

    def test_empty_kpis_returns_empty_list(self, activities):
        """No KPIs provided returns empty list."""
        result = activities.run_kpis({"kpis": []})
        assert result == []

    def test_missing_kpis_key_returns_empty_list(self, activities):
        """Missing kpis key returns empty list."""
        result = activities.run_kpis({})
        assert result == []

    def test_kpi_missing_sql_raises(self, activities):
        """KPI without SQL raises non-retryable ApplicationError."""
        kpis = [{"name": "test_kpi"}]  # no 'sql' key
        with pytest.raises(ApplicationError, match="missing a SQL query"):
            activities.run_kpis({"kpis": kpis})

    def test_kpi_empty_sql_raises(self, activities):
        """KPI with empty SQL string raises non-retryable ApplicationError."""
        kpis = [{"name": "test_kpi", "sql": ""}]
        with pytest.raises(ApplicationError, match="missing a SQL query"):
            activities.run_kpis({"kpis": kpis})

    def test_kpi_none_sql_raises(self, activities):
        """KPI with None SQL raises non-retryable ApplicationError."""
        kpis = [{"name": "test_kpi", "sql": None}]
        with pytest.raises(ApplicationError, match="missing a SQL query"):
            activities.run_kpis({"kpis": kpis})

    def test_kpi_unnamed_defaults(self, activities):
        """KPI without name uses 'kpi_unnamed' default — still fails on missing SQL."""
        kpis = [{"sql": None}]
        with pytest.raises(ApplicationError, match="kpi_unnamed"):
            activities.run_kpis({"kpis": kpis})

    def test_multiple_kpis_first_missing_sql_halts(self, activities):
        """First KPI with missing SQL halts execution before second KPI."""
        kpis = [
            {"name": "bad_kpi", "sql": ""},
            {"name": "good_kpi", "sql": "SELECT 1"},
        ]
        with pytest.raises(ApplicationError, match="bad_kpi"):
            activities.run_kpis({"kpis": kpis})
