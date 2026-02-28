"""
Tests for Health, Readiness, and Status Endpoints.

This module contains comprehensive tests for the application's operational
status endpoints: `/health` (liveness), `/ready` (readiness), and `/status` (detailed diagnostics).
It verifies that these endpoints correctly report the application's state,
perform checks on critical dependencies (e.g., DuckDB, R-Engine, Temporal),
and expose relevant operational metrics like circuit breaker status.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHealthEndpoints:
    """
    Test suite for the application's health, readiness, and status endpoints.

    These tests ensure that the application correctly reports its operational
    state to external monitoring systems and orchestrators.
    """

    def test_health_endpoint_always_returns_200(self, client):
        """
        Verifies that the `/health` endpoint always returns a 200 OK status
        and reports "healthy", indicating the service is alive.
        """
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_healthz_endpoint_alias(self, client):
        """
        Ensures that `/healthz` acts as an alias for the `/health` endpoint,
        returning the same healthy status.
        """
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @patch("voyant.core.duckdb_pool.get_connection")
    @patch("voyant.core.r_bridge.REngine")
    @patch("voyant.core.temporal_client.get_temporal_client", new_callable=AsyncMock)
    def test_ready_endpoint_all_services_up(
        self,
        mock_temporal: AsyncMock,
        mock_r_engine: MagicMock,
        mock_duckdb: MagicMock,
        client,
    ):
        """
        Verifies that the `/ready` endpoint returns a 200 OK status when
        all critical internal and external services (DuckDB, R-Engine, Temporal) are healthy.
        """
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value.__enter__.return_value = mock_db_conn

        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r

        mock_temporal.return_value = MagicMock()

        response = client.get("/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert data["checks"]["duckdb"]["status"] == "up"
        assert data["checks"]["r_engine"]["status"] == "up"
        assert data["checks"]["temporal"]["status"] == "up"

    @patch("voyant.core.duckdb_pool.get_connection")
    @patch("voyant.core.r_bridge.REngine")
    @patch("voyant.core.temporal_client.get_temporal_client", new_callable=AsyncMock)
    def test_ready_endpoint_r_engine_down(
        self,
        mock_temporal: AsyncMock,
        mock_r_engine: MagicMock,
        mock_duckdb: MagicMock,
        client,
    ):
        """
        Tests that the `/ready` endpoint correctly reports a 503 Service Unavailable
        when the R-Engine dependency is unhealthy.
        """
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value.__enter__.return_value = mock_db_conn

        mock_temporal.return_value = MagicMock()

        mock_r = MagicMock()
        mock_r.is_healthy.return_value = False  # Simulate R-Engine being down.
        mock_r_engine.return_value = mock_r

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["r_engine"]["status"] == "down"

    @patch("voyant.core.duckdb_pool.get_connection")
    @patch("voyant.core.r_bridge.REngine")
    @patch("voyant.core.temporal_client.get_temporal_client", new_callable=AsyncMock)
    def test_ready_endpoint_duckdb_error(
        self,
        mock_temporal: AsyncMock,
        mock_r_engine: MagicMock,
        mock_duckdb: MagicMock,
        client,
    ):
        """
        Tests that the `/ready` endpoint correctly reports a 503 Service Unavailable
        when the DuckDB connection fails.
        """
        mock_duckdb.side_effect = Exception(
            "Database connection failed"
        )  # Simulate DuckDB error.

        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r

        mock_temporal.return_value = MagicMock()

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["duckdb"]["status"] == "down"
        assert "error" in data["checks"]["duckdb"]

    @patch("voyant.core.duckdb_pool.get_connection")
    @patch("voyant.core.r_bridge.REngine")
    @patch("voyant.core.temporal_client.get_temporal_client", new_callable=AsyncMock)
    def test_ready_endpoint_temporal_error(
        self,
        mock_temporal: AsyncMock,
        mock_r_engine: MagicMock,
        mock_duckdb: MagicMock,
        client,
    ):
        """
        Tests that the `/ready` endpoint correctly reports a 503 Service Unavailable
        when the Temporal client fails to connect.
        """
        mock_temporal.side_effect = Exception(
            "Temporal connection failed"
        )  # Simulate Temporal error.

        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value.__enter__.return_value = mock_db_conn

        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["temporal"]["status"] == "down"

    def test_readyz_endpoint_alias(self, client):
        """
        Ensures that `/readyz` acts as an alias for the `/ready` endpoint,
        returning the same status and checks structure.
        """
        response = client.get("/readyz")
        assert "status" in response.json()
        assert "checks" in response.json()

    @patch("voyant.core.r_bridge.REngine")
    @patch("voyant_project.urls._circuit_breakers", {})
    def test_status_endpoint_structure(
        self,
        mock_r_engine: MagicMock,
        client,
    ):
        """
        Tests the basic structure of the `/status` endpoint response,
        ensuring it contains expected top-level keys like version, timestamp,
        environment, services, and circuit breakers.
        """
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r.host = "localhost"
        mock_r.port = 6311
        mock_r_engine.return_value = mock_r

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert "version" in data
        assert "timestamp" in data
        assert "environment" in data
        assert "services" in data
        assert "circuit_breakers" in data

    @patch("voyant.core.r_bridge.REngine")
    @patch("voyant_project.urls._circuit_breakers")
    def test_status_endpoint_circuit_breaker_metrics(
        self,
        mock_cb_registry: MagicMock,
        mock_r_engine: MagicMock,
        client,
    ):
        """
        Verifies that the `/status` endpoint correctly reports circuit breaker metrics
        for registered services.
        """
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r.host = "localhost"
        mock_r.port = 6311
        mock_r_engine.return_value = mock_r

        # Simulate a circuit breaker being registered and having metrics.
        mock_cb = MagicMock()
        mock_cb.get_metrics.return_value = {
            "name": "rserve",
            "state": "closed",
            "failure_count": 0,
            "success_count": 10,
        }
        mock_cb_registry.items.return_value = [("rserve", mock_cb)]

        response = client.get("/status")

        assert response.status_code == 200
        data = response.json()

        assert "rserve" in data["circuit_breakers"]
        assert data["circuit_breakers"]["rserve"]["state"] == "closed"

    @patch("voyant.core.duckdb_pool.get_connection")
    @patch("voyant.core.r_bridge.REngine")
    @patch("voyant.core.temporal_client.get_temporal_client", new_callable=AsyncMock)
    @patch("voyant_project.urls._circuit_breakers")
    def test_ready_circuit_breaker_open_critical_service(
        self,
        mock_cb_registry: MagicMock,
        mock_temporal: AsyncMock,
        mock_r_engine: MagicMock,
        mock_duckdb: MagicMock,
        client,
    ):
        """
        Tests that the `/ready` endpoint correctly reports a 503 Service Unavailable
        when a critical service's circuit breaker is in an OPEN state.
        """
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value.__enter__.return_value = mock_db_conn

        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r

        mock_temporal.return_value = MagicMock()

        from apps.core.lib.circuit_breaker import CircuitState

        # Simulate a circuit breaker being open for a critical service.
        mock_cb = MagicMock()
        mock_cb.get_state.return_value = CircuitState.OPEN
        mock_cb_registry.items.return_value = [("rserve", mock_cb)]

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["circuit_breakers"]["states"]["rserve"] == "open"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
