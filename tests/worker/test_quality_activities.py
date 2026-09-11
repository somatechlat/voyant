"""
Tests for QualityActivities.

Tests fetch_sample and run_quality_checks with real DuckDB, real pandas,
and real quality rules engine. No mocking.
"""

import duckdb
import pytest
from temporalio.exceptions import ApplicationError

from apps.worker.activities.quality_activities import QualityActivities


@pytest.fixture(scope="module")
def activities():
    """Real QualityActivities instance."""
    return QualityActivities()


@pytest.fixture()
def quality_duckdb(tmp_path):
    """Create a temporary DuckDB with quality test data."""
    db_path = str(tmp_path / "quality_test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE quality_table AS
        SELECT
            i AS id,
            CASE WHEN i % 10 = 0 THEN NULL ELSE i * 10 END AS value,
            CASE WHEN i % 7 = 0 THEN NULL ELSE 'cat_' || (i % 3) END AS category
        FROM generate_series(1, 100) t(i)
    """)
    conn.close()
    return db_path


class TestQualityFetchSample:
    """Tests for the fetch_sample activity."""

    def test_fetch_sample_missing_table(self, activities):
        """Missing table and source_id raises non-retryable error."""
        with pytest.raises(ApplicationError, match="table or source_id is required"):
            activities.fetch_sample({})

    def test_fetch_sample_with_table(self, activities, quality_duckdb, monkeypatch):
        """Successful fetch returns list of dicts."""
        monkeypatch.setattr(activities.settings, "duckdb_path", quality_duckdb)
        result = activities.fetch_sample({"table": "quality_table", "sample_size": 50})
        assert isinstance(result, list)
        assert len(result) <= 50
        assert len(result) > 0

    def test_fetch_sample_with_source_id(self, activities, quality_duckdb, monkeypatch):
        """source_id is used as fallback when table is not provided."""
        monkeypatch.setattr(activities.settings, "duckdb_path", quality_duckdb)
        result = activities.fetch_sample({"source_id": "quality_table", "sample_size": 20})
        assert isinstance(result, list)
        assert len(result) <= 20

    def test_fetch_sample_default_size(self, activities, quality_duckdb, monkeypatch):
        """Default sample_size is 5000."""
        monkeypatch.setattr(activities.settings, "duckdb_path", quality_duckdb)
        result = activities.fetch_sample({"table": "quality_table"})
        assert len(result) == 100  # table has 100 rows

    def test_fetch_sample_nonexistent_table(self, activities, monkeypatch):
        """Non-existent table raises retryable ApplicationError."""
        monkeypatch.setattr(
            activities.settings, "duckdb_path", "/tmp/nonexistent_quality.duckdb"
        )
        with pytest.raises(ApplicationError, match="Failed to sample data"):
            activities.fetch_sample({"table": "no_such_table"})


class TestRunQualityChecks:
    """Tests for the run_quality_checks activity."""

    def test_empty_data(self, activities):
        """Empty data returns valid with zero checks."""
        result = activities.run_quality_checks({"data": [], "checks": []})
        assert result["is_valid"] is True
        assert result["total_checks"] == 0
        assert result["passed"] == 0
        assert result["failed"] == 0
        assert result["results"] == []
        assert result["rows_analyzed"] == 0

    def test_no_data_key(self, activities):
        """Missing data key defaults to empty list."""
        result = activities.run_quality_checks({})
        assert result["is_valid"] is True
        assert result["rows_analyzed"] == 0

    def test_default_rules_null_check(self, activities):
        """Default rules apply null checks to all columns."""
        data = [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": None},
            {"id": 3, "name": "Charlie"},
        ]
        result = activities.run_quality_checks({"data": data})
        assert result["total_checks"] > 0
        assert result["rows_analyzed"] == 3
        # id column has no nulls, name has 1/3 nulls
        assert result["passed"] > 0

    def test_default_rules_unique_check_on_id_columns(self, activities):
        """Default rules add UniqueCheck for id-like columns."""
        data = [
            {"user_id": 1, "value": 100},
            {"user_id": 2, "value": 200},
            {"user_id": 3, "value": 300},
        ]
        result = activities.run_quality_checks({"data": data})
        # Should have null checks + unique check for user_id
        check_names = [r["rule"] for r in result["results"]]
        assert any("UniqueCheck" in name and "user_id" in name for name in check_names)

    def test_default_rules_duplicate_id_fails(self, activities):
        """Duplicate IDs fail the unique check."""
        data = [
            {"id": 1, "value": 100},
            {"id": 1, "value": 200},
            {"id": 3, "value": 300},
        ]
        result = activities.run_quality_checks({"data": data})
        assert result["is_valid"] is False
        assert result["failed"] > 0

    def test_custom_null_check(self, activities):
        """Custom null check with specific threshold."""
        data = [
            {"name": "Alice"},
            {"name": None},
            {"name": "Charlie"},
            {"name": None},
            {"name": "Eve"},
        ]
        checks = [{"type": "null", "column": "name", "max_null_pct": 0.5}]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["total_checks"] == 1
        # 2/5 = 0.4 null rate, threshold is 0.5, so passes
        assert result["is_valid"] is True

    def test_custom_null_check_fails(self, activities):
        """Null check fails when threshold is exceeded."""
        data = [{"val": None}, {"val": None}, {"val": 1}]
        checks = [{"type": "null", "column": "val", "max_null_pct": 0.1}]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["is_valid"] is False

    def test_custom_range_check_pass(self, activities):
        """Range check passes when all values are within bounds."""
        data = [{"score": 50}, {"score": 75}, {"score": 100}]
        checks = [{"type": "range", "column": "score", "min": 0, "max": 100}]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["is_valid"] is True

    def test_custom_range_check_fail(self, activities):
        """Range check fails when values are out of bounds."""
        data = [{"score": 50}, {"score": 150}, {"score": -10}]
        checks = [{"type": "range", "column": "score", "min": 0, "max": 100}]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["is_valid"] is False

    def test_custom_unique_check_pass(self, activities):
        """Unique check passes with no duplicates."""
        data = [{"email": "a@b.com"}, {"email": "c@d.com"}, {"email": "e@f.com"}]
        checks = [{"type": "unique", "column": "email"}]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["is_valid"] is True

    def test_custom_unique_check_fail(self, activities):
        """Unique check fails with duplicates."""
        data = [{"email": "a@b.com"}, {"email": "a@b.com"}, {"email": "c@d.com"}]
        checks = [{"type": "unique", "column": "email"}]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["is_valid"] is False

    def test_multiple_checks(self, activities):
        """Multiple checks run together."""
        data = [
            {"id": 1, "age": 25, "email": "a@b.com"},
            {"id": 2, "age": 30, "email": "c@d.com"},
            {"id": 3, "age": 200, "email": "e@f.com"},
        ]
        checks = [
            {"type": "unique", "column": "id"},
            {"type": "range", "column": "age", "min": 0, "max": 150},
            {"type": "null", "column": "email", "max_null_pct": 0.0},
        ]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["total_checks"] == 3
        # age=200 exceeds max=150, so not all pass
        assert result["is_valid"] is False

    def test_invalid_check_spec_not_dict(self, activities):
        """Non-dict check specs are skipped with a warning."""
        data = [{"val": 1}]
        checks = ["not_a_dict", 42]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        # No valid checks, so zero checks run
        assert result["total_checks"] == 0

    def test_invalid_check_spec_missing_fields(self, activities):
        """Check specs missing type or column are skipped."""
        data = [{"val": 1}]
        checks = [
            {"type": "null"},  # missing column
            {"column": "val"},  # missing type
        ]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["total_checks"] == 0

    def test_unknown_check_type(self, activities):
        """Unknown check types are skipped."""
        data = [{"val": 1}]
        checks = [{"type": "unknown_type", "column": "val"}]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["total_checks"] == 0

    def test_build_rules_with_range_no_bounds(self, activities):
        """Range check with no min/max still creates a rule."""
        data = [{"val": 1}, {"val": 2}, {"val": 3}]
        checks = [{"type": "range", "column": "val"}]
        result = activities.run_quality_checks({"data": data, "checks": checks})
        assert result["total_checks"] == 1
        assert result["is_valid"] is True
