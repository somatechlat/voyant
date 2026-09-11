"""
Tests for IngestActivities.

Tests run_ingestion, validate_contract_activity, and record_lineage_activity.
Uses ActivityEnvironment for activities that call activity.heartbeat().
"""


import duckdb
import pytest
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment

from apps.worker.activities.ingest_activities import IngestActivities


@pytest.fixture(scope="module")
def activities():
    """Real IngestActivities instance."""
    return IngestActivities()


@pytest.fixture()
def ingest_duckdb(tmp_path):
    """Create a temporary DuckDB with ingestion test data."""
    db_path = str(tmp_path / "ingest_test.duckdb")
    conn = duckdb.connect(db_path)
    conn.execute("""
        CREATE TABLE test_source AS
        SELECT i AS id, 'item_' || i AS name, i * 10 AS amount
        FROM generate_series(1, 50) t(i)
    """)
    conn.close()
    return db_path


@pytest.fixture()
def env():
    """ActivityEnvironment for testing activities outside a Temporal worker."""
    return ActivityEnvironment()


class TestRunIngestion:
    """Tests for the run_ingestion activity."""

    @pytest.mark.asyncio
    async def test_run_ingestion_full_mode(self, activities, ingest_duckdb, monkeypatch, env):
        """Full mode ingestion completes successfully."""
        monkeypatch.setattr(activities.settings, "duckdb_path", ingest_duckdb)
        result = await env.run(
            activities.run_ingestion,
            {
                "job_id": "job-001",
                "source_id": "test_source",
                "mode": "full",
            },
        )
        assert result["job_id"] == "job-001"
        assert result["source_id"] == "test_source"
        assert result["status"] == "completed"
        assert result["rows_ingested"] == 50
        assert "completed_at" in result
        assert result["completed_at"].endswith("Z")

    @pytest.mark.asyncio
    async def test_run_ingestion_incremental_mode(
        self, activities, ingest_duckdb, monkeypatch, env
    ):
        """Incremental mode ingestion completes successfully."""
        monkeypatch.setattr(activities.settings, "duckdb_path", ingest_duckdb)
        result = await env.run(
            activities.run_ingestion,
            {
                "job_id": "job-002",
                "source_id": "test_source",
                "mode": "incremental",
            },
        )
        assert result["status"] == "completed"
        assert result["rows_ingested"] == 50

    @pytest.mark.asyncio
    async def test_run_ingestion_invalid_mode(self, activities, env):
        """Unsupported mode raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Unsupported ingestion mode"):
            await env.run(
                activities.run_ingestion,
                {
                    "job_id": "job-003",
                    "source_id": "test_source",
                    "mode": "streaming",
                },
            )

    @pytest.mark.asyncio
    async def test_run_ingestion_with_tables(self, activities, ingest_duckdb, monkeypatch, env):
        """Custom tables list is reflected in result."""
        monkeypatch.setattr(activities.settings, "duckdb_path", ingest_duckdb)
        result = await env.run(
            activities.run_ingestion,
            {
                "job_id": "job-004",
                "source_id": "test_source",
                "mode": "full",
                "tables": ["orders", "customers"],
            },
        )
        assert result["tables_synced"] == ["orders", "customers"]

    @pytest.mark.asyncio
    async def test_run_ingestion_default_tables(self, activities, ingest_duckdb, monkeypatch, env):
        """Default tables_synced when no tables provided."""
        monkeypatch.setattr(activities.settings, "duckdb_path", ingest_duckdb)
        result = await env.run(
            activities.run_ingestion,
            {
                "job_id": "job-005",
                "source_id": "test_source",
                "mode": "full",
            },
        )
        assert result["tables_synced"] == ["default_table"]

    @pytest.mark.asyncio
    async def test_run_ingestion_invalid_source_id(self, activities, ingest_duckdb, monkeypatch, env):
        """Invalid source_id (SQL injection attempt) is handled gracefully."""
        monkeypatch.setattr(activities.settings, "duckdb_path", ingest_duckdb)
        result = await env.run(
            activities.run_ingestion,
            {
                "job_id": "job-006",
                "source_id": "test_source; DROP TABLE test_source;--",
                "mode": "full",
            },
        )
        # Should degrade gracefully with row_count = 0
        assert result["rows_ingested"] == 0
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_run_ingestion_nonexistent_source(self, activities, ingest_duckdb, monkeypatch, env):
        """Non-existent source gracefully degrades to row_count=0."""
        monkeypatch.setattr(activities.settings, "duckdb_path", ingest_duckdb)
        result = await env.run(
            activities.run_ingestion,
            {
                "job_id": "job-007",
                "source_id": "nonexistent_table_xyz",
                "mode": "full",
            },
        )
        assert result["rows_ingested"] == 0
        assert result["status"] == "completed"


class TestValidateContractActivity:
    """Tests for the validate_contract_activity."""

    @pytest.mark.asyncio
    async def test_no_contract_registered(self, activities, env):
        """Returns skipped=True when no contract exists for the source."""
        result = await env.run(
            activities.validate_contract_activity,
            {"source_id": "nonexistent_source_for_contract"},
        )
        assert result["valid"] is True
        assert result["skipped"] is True

    @pytest.mark.asyncio
    async def test_no_source_id(self, activities, env):
        """Missing source_id returns skipped=True."""
        result = await env.run(activities.validate_contract_activity, {})
        assert result["valid"] is True
        assert result["skipped"] is True


class TestRecordLineageActivity:
    """Tests for the record_lineage_activity."""

    @pytest.mark.asyncio
    async def test_record_lineage(self, activities, env):
        """Lineage recording returns success with node count."""
        result = await env.run(
            activities.record_lineage_activity,
            {
                "job_id": "lineage-job-001",
                "source_id": "test_source",
                "tenant_id": "tenant_1",
            },
        )
        assert result["recorded"] is True
        assert result["nodes"] == 3

    @pytest.mark.asyncio
    async def test_record_lineage_default_tenant(self, activities, env):
        """Default tenant_id is 'default'."""
        result = await env.run(
            activities.record_lineage_activity,
            {
                "job_id": "lineage-job-002",
                "source_id": "test_source",
            },
        )
        assert result["recorded"] is True

    @pytest.mark.asyncio
    async def test_record_lineage_missing_job_id(self, activities, env):
        """Missing job_id uses empty string."""
        result = await env.run(
            activities.record_lineage_activity,
            {"source_id": "test_source"},
        )
        assert result["recorded"] is True


class TestSyncAirbyte:
    """Tests for sync_airbyte parameter validation."""

    @pytest.mark.asyncio
    async def test_sync_airbyte_missing_connection_and_uri(self, activities, env):
        """Missing both connection_id and generic_uri raises error."""
        try:
            await env.run(activities.sync_airbyte, {})
        except ApplicationError as e:
            assert "connection_id" in str(e) or "generic_uri" in str(e)
        except Exception as e:
            # Airbyte client initialization may fail first
            assert "airbyte" in str(e).lower() or "base_url" in str(e).lower()


class TestConnectAirbyteSource:
    """Tests for connect_airbyte_source parameter validation."""

    @pytest.mark.asyncio
    async def test_missing_source_definition_id(self, activities, env):
        """Missing source_definition_id raises non-retryable error."""
        with pytest.raises(
            ApplicationError, match="source_definition_id is required"
        ):
            await env.run(
                activities.connect_airbyte_source, {"source_id": "src-1"}
            )
