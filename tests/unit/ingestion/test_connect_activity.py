"""
Unit tests for the connect_airbyte_source Temporal activity.

Tests the activity logic using mocked Airbyte client calls.
No real Airbyte or Temporal instance required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from temporalio.exceptions import ApplicationError

from apps.worker.activities.ingest_activities import IngestActivities


@pytest.fixture
def activities():
    """Create an IngestActivities instance."""
    return IngestActivities()


class TestConnectAirbyteSourceActivity:
    """Tests for IngestActivities.connect_airbyte_source."""

    @pytest.mark.asyncio
    async def test_connect_source_only(self, activities):
        """Activity should provision source when no destination params given."""
        mock_client = AsyncMock()
        mock_client.connect_source.return_value = {
            "source_id": "airbyte-src-001",
            "name": "test-source",
            "status": "provisioned",
        }

        with patch(
            "apps.worker.activities.ingest_activities.IngestActivities.connect_airbyte_source.__wrapped__",
            create=True,
        ):
            pass

        with patch(
            "apps.ingestion.lib.airbyte_client.get_airbyte_client",
            return_value=mock_client,
        ):
            with patch(
                "temporalio.activity.heartbeat",
            ):
                with patch(
                    "temporalio.activity.logger",
                ):
                    result = await activities.connect_airbyte_source(
                        {
                            "source_id": "voyant-src-1",
                            "workspace_id": "tenant-1",
                            "source_definition_id": "def-postgres",
                            "source_name": "My Postgres",
                            "connection_config": {
                                "host": "pg.example.com",
                                "port": 5432,
                            },
                        }
                    )

        assert result["source_id"] == "voyant-src-1"
        assert result["airbyte_source_id"] == "airbyte-src-001"
        assert result["status"] == "connected"
        assert "airbyte_destination_id" not in result

        mock_client.connect_source.assert_called_once_with(
            workspace_id="tenant-1",
            source_definition_id="def-postgres",
            name="My Postgres",
            connection_config={"host": "pg.example.com", "port": 5432},
        )

    @pytest.mark.asyncio
    async def test_connect_source_with_destination(self, activities):
        """Activity should provision both source and destination when configured."""
        mock_client = AsyncMock()
        mock_client.connect_source.return_value = {
            "source_id": "airbyte-src-002",
            "name": "test-source",
            "status": "provisioned",
        }
        mock_client.provision_destination.return_value = {
            "destination_id": "airbyte-dst-002",
            "name": "test-dest",
            "status": "provisioned",
        }

        with patch(
            "apps.ingestion.lib.airbyte_client.get_airbyte_client",
            return_value=mock_client,
        ):
            with patch("temporalio.activity.heartbeat"):
                with patch("temporalio.activity.logger"):
                    result = await activities.connect_airbyte_source(
                        {
                            "source_id": "voyant-src-2",
                            "workspace_id": "tenant-2",
                            "source_definition_id": "def-mysql",
                            "source_name": "My MySQL",
                            "connection_config": {"host": "mysql.example.com"},
                            "destination_definition_id": "def-duckdb",
                            "destination_name": "DuckDB Warehouse",
                            "destination_config": {"path": "/data/warehouse.duckdb"},
                        }
                    )

        assert result["source_id"] == "voyant-src-2"
        assert result["airbyte_source_id"] == "airbyte-src-002"
        assert result["airbyte_destination_id"] == "airbyte-dst-002"
        assert result["destination_status"] == "provisioned"
        assert result["status"] == "connected"

        mock_client.provision_destination.assert_called_once_with(
            workspace_id="tenant-2",
            destination_definition_id="def-duckdb",
            name="DuckDB Warehouse",
            connection_config={"path": "/data/warehouse.duckdb"},
        )

    @pytest.mark.asyncio
    async def test_connect_source_missing_definition_id(self, activities):
        """Activity should raise ApplicationError when source_definition_id is missing."""
        with patch("temporalio.activity.heartbeat"):
            with patch("temporalio.activity.logger"):
                with pytest.raises(ApplicationError, match="source_definition_id is required"):
                    await activities.connect_airbyte_source(
                        {
                            "source_id": "voyant-src-3",
                            "workspace_id": "tenant-3",
                            # Missing source_definition_id
                        }
                    )

    @pytest.mark.asyncio
    async def test_connect_source_circuit_breaker_open(self, activities):
        """Activity should raise non-retryable ApplicationError when circuit breaker is open."""
        from apps.core.lib.circuit_breaker import CircuitBreakerOpenError

        mock_client = AsyncMock()
        mock_client.connect_source.side_effect = CircuitBreakerOpenError(
            "Airbyte circuit breaker is open"
        )

        with patch(
            "apps.ingestion.lib.airbyte_client.get_airbyte_client",
            return_value=mock_client,
        ):
            with patch("temporalio.activity.heartbeat"):
                with patch("temporalio.activity.logger"):
                    with pytest.raises(
                        ApplicationError, match="circuit breaker is open"
                    ) as exc_info:
                        await activities.connect_airbyte_source(
                            {
                                "source_id": "voyant-src-4",
                                "workspace_id": "tenant-4",
                                "source_definition_id": "def-pg",
                                "source_name": "Test",
                                "connection_config": {},
                            }
                        )

                    assert exc_info.value.non_retryable is True

    @pytest.mark.asyncio
    async def test_connect_source_default_workspace(self, activities):
        """Activity should default workspace_id to 'default' when not provided."""
        mock_client = AsyncMock()
        mock_client.connect_source.return_value = {
            "source_id": "airbyte-src-005",
            "name": "test",
            "status": "provisioned",
        }

        with patch(
            "apps.ingestion.lib.airbyte_client.get_airbyte_client",
            return_value=mock_client,
        ):
            with patch("temporalio.activity.heartbeat"):
                with patch("temporalio.activity.logger"):
                    await activities.connect_airbyte_source(
                        {
                            "source_id": "voyant-src-5",
                            "source_definition_id": "def-pg",
                            "source_name": "Test",
                            "connection_config": {},
                        }
                    )

        call_kwargs = mock_client.connect_source.call_args[1]
        assert call_kwargs["workspace_id"] == "default"

    @pytest.mark.asyncio
    async def test_connect_source_default_name(self, activities):
        """Activity should generate a default name from source_id when not provided."""
        mock_client = AsyncMock()
        mock_client.connect_source.return_value = {
            "source_id": "airbyte-src-006",
            "name": "source-voyant-src-6",
            "status": "provisioned",
        }

        with patch(
            "apps.ingestion.lib.airbyte_client.get_airbyte_client",
            return_value=mock_client,
        ):
            with patch("temporalio.activity.heartbeat"):
                with patch("temporalio.activity.logger"):
                    await activities.connect_airbyte_source(
                        {
                            "source_id": "voyant-src-6",
                            "source_definition_id": "def-pg",
                            "connection_config": {},
                        }
                    )

        call_kwargs = mock_client.connect_source.call_args[1]
        assert call_kwargs["name"] == "source-voyant-src-6"
