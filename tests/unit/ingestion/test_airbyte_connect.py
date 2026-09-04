"""
Unit tests for Airbyte Client connect/provision methods.

Tests the connect_source and provision_destination methods of AirbyteClient
using mocked HTTP responses. No real Airbyte instance required.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from apps.ingestion.lib.airbyte_client import (
    AirbyteClient,
    AirbyteClientConfig,
)


@pytest.fixture
def client():
    """Create an AirbyteClient with test configuration."""
    config = AirbyteClientConfig(base_url="http://test-airbyte:8001/api/v1")
    return AirbyteClient(config)


@pytest.fixture
def mock_response():
    """Create a mock httpx response factory."""

    def _make(json_data, status_code=200):
        mock = AsyncMock()
        mock.status_code = status_code
        mock.content = True
        mock.json.return_value = json_data
        mock.raise_for_status = AsyncMock()
        return mock

    return _make


class TestConnectSource:
    """Tests for AirbyteClient.connect_source."""

    @pytest.mark.asyncio
    async def test_connect_source_returns_source_details(self, client, mock_response):
        """connect_source should return source_id and metadata on success."""
        expected_response = {
            "sourceId": "src-abc-123",
            "name": "My Postgres Source",
            "workspaceId": "ws-1",
        }

        with patch.object(
            client, "_request", new_callable=AsyncMock, return_value=expected_response
        ) as mock_req:
            result = await client.connect_source(
                workspace_id="ws-1",
                source_definition_id="def-postgres",
                name="My Postgres Source",
                connection_config={"host": "localhost", "port": 5432, "database": "test"},
            )

        assert result["source_id"] == "src-abc-123"
        assert result["name"] == "My Postgres Source"
        assert result["workspace_id"] == "ws-1"
        assert result["source_definition_id"] == "def-postgres"
        assert result["status"] == "provisioned"

        mock_req.assert_called_once_with(
            "POST",
            "/sources",
            json_data={
                "workspaceId": "ws-1",
                "sourceDefinitionId": "def-postgres",
                "name": "My Postgres Source",
                "connectionConfiguration": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "test",
                },
            },
        )

    @pytest.mark.asyncio
    async def test_connect_source_with_empty_response(self, client):
        """connect_source should handle empty sourceId gracefully."""
        with patch.object(
            client, "_request", new_callable=AsyncMock, return_value={}
        ):
            result = await client.connect_source(
                workspace_id="ws-1",
                source_definition_id="def-mysql",
                name="Empty Source",
                connection_config={},
            )

        assert result["source_id"] == ""
        assert result["status"] == "provisioned"

    @pytest.mark.asyncio
    async def test_connect_source_propagates_service_error(self, client):
        """connect_source should propagate ExternalServiceError from _request."""
        from apps.core.lib.errors import ExternalServiceError

        with patch.object(
            client,
            "_request",
            new_callable=AsyncMock,
            side_effect=ExternalServiceError(
                code="VYNT-6001", message="Airbyte HTTP error: 400"
            ),
        ):
            with pytest.raises(ExternalServiceError, match="Airbyte HTTP error"):
                await client.connect_source(
                    workspace_id="ws-1",
                    source_definition_id="def-bad",
                    name="Bad Source",
                    connection_config={},
                )


class TestProvisionDestination:
    """Tests for AirbyteClient.provision_destination."""

    @pytest.mark.asyncio
    async def test_provision_destination_returns_details(self, client):
        """provision_destination should return destination_id and metadata."""
        expected_response = {
            "destinationId": "dst-xyz-789",
            "name": "DuckDB Destination",
        }

        with patch.object(
            client, "_request", new_callable=AsyncMock, return_value=expected_response
        ) as mock_req:
            result = await client.provision_destination(
                workspace_id="ws-1",
                destination_definition_id="def-duckdb",
                name="DuckDB Destination",
                connection_config={"path": "/data/warehouse.duckdb"},
            )

        assert result["destination_id"] == "dst-xyz-789"
        assert result["name"] == "DuckDB Destination"
        assert result["workspace_id"] == "ws-1"
        assert result["destination_definition_id"] == "def-duckdb"
        assert result["status"] == "provisioned"

        mock_req.assert_called_once_with(
            "POST",
            "/destinations",
            json_data={
                "workspaceId": "ws-1",
                "destinationDefinitionId": "def-duckdb",
                "name": "DuckDB Destination",
                "connectionConfiguration": {"path": "/data/warehouse.duckdb"},
            },
        )

    @pytest.mark.asyncio
    async def test_provision_destination_postgres(self, client):
        """provision_destination should work for Postgres destinations."""
        expected_response = {
            "destinationId": "dst-pg-456",
            "name": "Postgres Warehouse",
        }

        with patch.object(
            client, "_request", new_callable=AsyncMock, return_value=expected_response
        ):
            result = await client.provision_destination(
                workspace_id="ws-1",
                destination_definition_id="def-postgres-dest",
                name="Postgres Warehouse",
                connection_config={
                    "host": "pg-host",
                    "port": 5432,
                    "database": "warehouse",
                    "username": "admin",
                    "password": "secret",
                },
            )

        assert result["destination_id"] == "dst-pg-456"
        assert result["status"] == "provisioned"

    @pytest.mark.asyncio
    async def test_provision_destination_empty_response(self, client):
        """provision_destination should handle empty response gracefully."""
        with patch.object(
            client, "_request", new_callable=AsyncMock, return_value={}
        ):
            result = await client.provision_destination(
                workspace_id="ws-1",
                destination_definition_id="def-test",
                name="Test Dest",
                connection_config={},
            )

        assert result["destination_id"] == ""
        assert result["status"] == "provisioned"


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.mark.asyncio
    async def test_connect_airbyte_source_convenience(self):
        """connect_airbyte_source convenience function delegates to client."""
        from apps.ingestion.lib.airbyte_client import connect_airbyte_source

        mock_result = {"source_id": "src-1", "status": "provisioned"}

        with patch(
            "apps.ingestion.lib.airbyte_client.get_airbyte_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.connect_source.return_value = mock_result
            mock_get_client.return_value = mock_client

            result = await connect_airbyte_source(
                workspace_id="ws-1",
                source_definition_id="def-pg",
                name="Test",
                connection_config={"host": "localhost"},
            )

        assert result["source_id"] == "src-1"
        mock_client.connect_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_provision_airbyte_destination_convenience(self):
        """provision_airbyte_destination convenience function delegates to client."""
        from apps.ingestion.lib.airbyte_client import provision_airbyte_destination

        mock_result = {"destination_id": "dst-1", "status": "provisioned"}

        with patch(
            "apps.ingestion.lib.airbyte_client.get_airbyte_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.provision_destination.return_value = mock_result
            mock_get_client.return_value = mock_client

            result = await provision_airbyte_destination(
                workspace_id="ws-1",
                destination_definition_id="def-duckdb",
                name="Test Dest",
                connection_config={"path": "/tmp/test.duckdb"},
            )

        assert result["destination_id"] == "dst-1"
        mock_client.provision_destination.assert_called_once()
