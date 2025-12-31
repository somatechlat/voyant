"""
Test suite for health check endpoints.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHealthEndpoints:
    """Test suite for health check endpoints."""

    def test_health_endpoint_always_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_healthz_endpoint_alias(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @patch("voyant.core.duckdb_pool.get_connection")
    @patch("voyant.core.r_bridge.REngine")
    @patch("voyant.core.temporal_client.get_temporal_client", new_callable=AsyncMock)
    def test_ready_endpoint_all_services_up(
        self,
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client,
    ):
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
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client,
    ):
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value.__enter__.return_value = mock_db_conn

        mock_temporal.return_value = MagicMock()

        mock_r = MagicMock()
        mock_r.is_healthy.return_value = False
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
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client,
    ):
        mock_duckdb.side_effect = Exception("Database connection failed")

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
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client,
    ):
        mock_temporal.side_effect = Exception("Temporal connection failed")

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
        response = client.get("/readyz")
        assert "status" in response.json()
        assert "checks" in response.json()

    @patch("voyant.core.r_bridge.REngine")
    @patch("voyant_project.urls._circuit_breakers", {})
    def test_status_endpoint_structure(self, mock_r_engine, client):
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
        mock_cb_registry,
        mock_r_engine,
        client,
    ):
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r.host = "localhost"
        mock_r.port = 6311
        mock_r_engine.return_value = mock_r

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
        mock_cb_registry,
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client,
    ):
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value.__enter__.return_value = mock_db_conn

        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r

        mock_temporal.return_value = MagicMock()

        from voyant.core.circuit_breaker import CircuitState

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
