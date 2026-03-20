"""
Integration tests for Data Ingestion and Source Discovery.
No mocks - running against live Postgres and DuckDB.
"""

import os

import pytest

from apps.core.config import get_settings
from apps.discovery.models import Source
from apps.ingestion.lib.direct_utils import DirectFileIngester
from apps.ingestion.models import IngestionJob


@pytest.mark.django_db
class TestIngestionIntegration:
    """
    Verifies the ingestion pipeline using real infrastructure.
    """

    @pytest.fixture(autouse=True)
    def setup_system(self):
        self.settings = get_settings()
        self.tenant_id = "test-tenant-ingestion"
        # Reset DuckDB for test purity
        if (
            os.path.exists(self.settings.duckdb_path)
            and self.settings.duckdb_path != ":memory:"
        ):
            try:
                os.remove(self.settings.duckdb_path)
            except OSError:
                pass

    def test_source_registration(self):
        """Verify that Sources can be registered and retrieved from Postgres."""
        source = Source.objects.create(
            tenant_id=self.tenant_id,
            name="Test Local CSV",
            source_type="file",
            connection_config={"path": "/tmp/test.csv"},
            status="active",
        )

        assert source.id is not None
        retrieved = Source.objects.get(id=source.id)
        assert retrieved.name == "Test Local CSV"
        assert retrieved.tenant_id == self.tenant_id

    def test_direct_csv_ingestion(self, tmp_path):
        """Verify loading a real CSV file into DuckDB."""
        # 1. Create a dummy CSV
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300")

        # 2. Initialize Ingester with real settings
        ingester = DirectFileIngester(db_path=self.settings.duckdb_path)

        # 3. Perform ingestion
        table_name = "test_ingest_table"
        result = ingester.ingest_file(str(csv_file), table_name)

        # 4. Verify results
        assert result["status"] == "success"
        assert result["rows"] == 3
        assert result["table"] == table_name

        # 5. Verify data in DuckDB
        import duckdb

        conn = duckdb.connect(self.settings.duckdb_path)
        data = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        assert data == 3

        # Verify specific record
        alice_val = conn.execute(
            f"SELECT value FROM {table_name} WHERE name='Alice'"
        ).fetchone()[0]
        assert alice_val == 100
        conn.close()

    def test_ingestion_job_creation(self):
        """Verify that IngestionJobs correctly track state in Postgres."""
        source = Source.objects.create(
            tenant_id=self.tenant_id,
            name="Job Track Source",
            source_type="api",
            connection_config={"url": "http://api.example.com"},
            status="active",
        )

        job = IngestionJob.objects.create(
            tenant_id=self.tenant_id,
            source=source,
            workflow_instance_id=f"wf-{os.urandom(4).hex()}",
            status=IngestionJob.Status.PENDING,
            params={"mode": "full"},
        )

        assert job.id is not None
        assert job.status == IngestionJob.Status.PENDING

        # Update status
        job.status = IngestionJob.Status.RUNNING
        job.progress = 0.5
        job.save()

        retrieved = IngestionJob.objects.get(id=job.id)
        assert retrieved.status == IngestionJob.Status.RUNNING
        assert retrieved.progress == 0.5
