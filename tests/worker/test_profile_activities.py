"""
Tests for ProfileActivities.

Tests the profile_data activity with real DuckDB and real adaptive sampling.
"""

import duckdb
import pytest
from temporalio.exceptions import ApplicationError

from apps.worker.activities.profile_activities import ProfileActivities


@pytest.fixture(scope="module")
def activities():
    """Real ProfileActivities instance."""
    return ProfileActivities()


@pytest.fixture()
def profile_duckdb(tmp_path):
    """Create a temporary DuckDB with profiling test data."""
    db_path = str(tmp_path / "profile_test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE profile_table AS
        SELECT
            i AS id,
            i * 1.5 AS revenue,
            CASE WHEN i % 5 = 0 THEN NULL ELSE 'cat_' || (i % 4) END AS category,
            CURRENT_DATE + (i % 30) * INTERVAL '1' day AS date_col
        FROM generate_series(1, 200) t(i)
    """)
    conn.close()
    return db_path


@pytest.fixture()
def small_duckdb(tmp_path):
    """Create a DuckDB with a small table (< 2x default sample size)."""
    db_path = str(tmp_path / "small_test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute(
        "CREATE TABLE small_table AS SELECT i AS id, i * 2 AS val FROM generate_series(1, 50) t(i)"
    )
    conn.close()
    return db_path


@pytest.fixture()
def empty_duckdb(tmp_path):
    """Create a DuckDB with an empty table."""
    db_path = str(tmp_path / "empty_test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("CREATE TABLE empty_table (id INTEGER, name VARCHAR)")
    conn.close()
    return db_path


class TestProfileData:
    """Tests for the profile_data activity."""

    def test_profile_basic(self, activities, profile_duckdb, monkeypatch):
        """Profile returns expected structure with column stats."""
        monkeypatch.setattr(activities.settings, "duckdb_path", profile_duckdb)
        result = activities.profile_data(
            {"source_id": "profile_table", "table": "profile_table", "sample_size": 100}
        )
        assert result["source_id"] == "profile_table"
        assert result["table"] == "profile_table"
        assert "profile" in result
        assert "generated_at" in result
        assert result["generated_at"].endswith("Z")

    def test_profile_column_stats(self, activities, profile_duckdb, monkeypatch):
        """Column stats include type, null_count, unique_count, and stats."""
        monkeypatch.setattr(activities.settings, "duckdb_path", profile_duckdb)
        result = activities.profile_data(
            {"source_id": "profile_table", "table": "profile_table", "sample_size": 200}
        )
        profile = result["profile"]
        assert "columns" in profile
        assert "id" in profile["columns"]
        assert "revenue" in profile["columns"]
        assert "category" in profile["columns"]

        id_col = profile["columns"]["id"]
        assert "type" in id_col
        assert "null_count" in id_col
        assert "unique_count" in id_col
        assert "stats" in id_col

    def test_profile_rows_analyzed(self, activities, profile_duckdb, monkeypatch):
        """rows_analyzed and total_rows_estimated are populated."""
        monkeypatch.setattr(activities.settings, "duckdb_path", profile_duckdb)
        result = activities.profile_data(
            {"source_id": "profile_table", "table": "profile_table", "sample_size": 50}
        )
        profile = result["profile"]
        assert profile["rows_analyzed"] > 0
        assert profile["total_rows_estimated"] == 200

    def test_profile_sampling_stats(self, activities, profile_duckdb, monkeypatch):
        """Sampling stats are included in the profile."""
        monkeypatch.setattr(activities.settings, "duckdb_path", profile_duckdb)
        result = activities.profile_data(
            {"source_id": "profile_table", "table": "profile_table", "sample_size": 50}
        )
        profile = result["profile"]
        assert "sampling_stats" in profile
        assert "strategy" in profile["sampling_stats"]

    def test_profile_small_table_full_fetch(self, activities, small_duckdb, monkeypatch):
        """Small tables are fetched in full (no SQL sampling)."""
        monkeypatch.setattr(activities.settings, "duckdb_path", small_duckdb)
        result = activities.profile_data(
            {"source_id": "small_table", "table": "small_table", "sample_size": 10000}
        )
        profile = result["profile"]
        assert profile["total_rows_estimated"] == 50

    def test_profile_empty_table(self, activities, empty_duckdb, monkeypatch):
        """Empty table returns profile with zero rows analyzed."""
        monkeypatch.setattr(activities.settings, "duckdb_path", empty_duckdb)
        result = activities.profile_data(
            {"source_id": "empty_table", "table": "empty_table", "sample_size": 100}
        )
        profile = result["profile"]
        assert profile["total_rows_estimated"] == 0
        assert profile["rows_analyzed"] == 0

    def test_profile_uses_source_id_as_table(self, activities, profile_duckdb, monkeypatch):
        """When table is not provided, source_id is used as table name."""
        monkeypatch.setattr(activities.settings, "duckdb_path", profile_duckdb)
        result = activities.profile_data(
            {"source_id": "profile_table", "sample_size": 50}
        )
        assert result["table"] == "profile_table"

    def test_profile_nonexistent_table_raises(self, activities, monkeypatch):
        """Non-existent table raises ApplicationError."""
        monkeypatch.setattr(
            activities.settings, "duckdb_path", "/tmp/nonexistent_voyant_test.duckdb"
        )
        with pytest.raises(ApplicationError, match="Profiling failed"):
            activities.profile_data(
                {"source_id": "no_such_table", "table": "no_such_table"}
            )

    def test_profile_null_counts(self, activities, profile_duckdb, monkeypatch):
        """Null counts are correctly reported for columns with NULLs."""
        monkeypatch.setattr(activities.settings, "duckdb_path", profile_duckdb)
        result = activities.profile_data(
            {"source_id": "profile_table", "table": "profile_table", "sample_size": 200}
        )
        category_stats = result["profile"]["columns"]["category"]
        # category has NULLs every 5th row (40 out of 200)
        assert category_stats["null_count"] > 0

    def test_profile_default_sample_size(self, activities, profile_duckdb, monkeypatch):
        """Default sample_size of 10000 is used when not specified."""
        monkeypatch.setattr(activities.settings, "duckdb_path", profile_duckdb)
        result = activities.profile_data({"source_id": "profile_table", "table": "profile_table"})
        assert result["profile"]["rows_analyzed"] > 0
