"""
Test suite for enhanced health check endpoints.

Tests comprehensive health and readiness probes including:
- Liveness checks
- Readiness checks with dependency validation
- Circuit breaker status integration
- Detailed status endpoint

Adheres to VIBE Coding Rules: Real dependency checks, proper status codes.

Security Auditor: No sensitive data in health responses
Performance Engineer: Fast liveness checks
SRE: Proper HTTP status codes for orchestration
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    """Create test client."""
    from voyant.api.app import app
    return TestClient(app)


class TestHealthEndpoints:
    """Test suite for health check endpoints."""
    
    def test_health_endpoint_always_returns_200(self, client):
        """Test that /health always returns 200 (liveness probe)."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
    
    def test_healthz_endpoint_alias(self, client):
        """Test Kubernetes-style /healthz endpoint."""
        response = client.get("/healthz")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    @patch("voyant.api.routes.health.get_duckdb_connection")
    @patch("voyant.api.routes.health.REngine")
    @patch("voyant.api.routes.health.get_temporal_client")
    def test_ready_endpoint_all_services_up(
        self,
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client
    ):
        """Test /ready returns 200 when all services are up."""
        # Mock all services as healthy
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value = mock_db_conn
        
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
    
    @patch("voyant.api.routes.health.get_duckdb_connection")
    @patch("voyant.api.routes.health.REngine")
    @patch("voyant.api.routes.health.get_temporal_client")
    def test_ready_endpoint_r_engine_down(
        self,
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client
    ):
        """Test /ready returns 503 when R engine is down."""
        # Mock DuckDB and Temporal as healthy
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value = mock_db_conn
        
        mock_temporal.return_value = MagicMock()
        
        # Mock R engine as down
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = False
        mock_r_engine.return_value = mock_r
        
        response = client.get("/ready")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["r_engine"]["status"] == "down"
    
    @patch("voyant.api.routes.health.get_duckdb_connection")
    @patch("voyant.api.routes.health.REngine")
    @patch("voyant.api.routes.health.get_temporal_client")
    def test_ready_endpoint_duckdb_error(
        self,
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client
    ):
        """Test /ready returns 503 when DuckDB connection fails."""
        # Mock DuckDB as failing
        mock_duckdb.side_effect = Exception("Database connection failed")
        
        # Mock other services as healthy
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
    
    @patch("voyant.api.routes.health.get_duckdb_connection")
    @patch("voyant.api.routes.health.REngine")
    @patch("voyant.api.routes.health.get_temporal_client")
    def test_ready_endpoint_temporal_error(
        self,
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client
    ):
        """Test /ready returns 503 when Temporal connection fails."""
        # Mock Temporal as failing
        mock_temporal.side_effect = Exception("Temporal connection failed")
        
        # Mock other services as healthy
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value = mock_db_conn
        
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r
        
        response = client.get("/ready")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["temporal"]["status"] == "down"
    
    def test_readyz_endpoint_alias(self, client):
        """Test Kubernetes-style /readyz endpoint."""
        response = client.get("/readyz")
        
        # Should return same structure as /ready
        assert "status" in response.json()
        assert "checks" in response.json()
    
    @patch("voyant.api.routes.health.REngine")
    @patch("voyant.api.routes.health._circuit_breakers", {})
    def test_status_endpoint_structure(self, mock_r_engine, client):
        """Test /status endpoint returns proper structure."""
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r.host = "localhost"
        mock_r.port = 6311
        mock_r_engine.return_value = mock_r
        
        response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "version" in data
        assert "timestamp" in data
        assert "environment" in data
        assert "services" in data
        assert "circuit_breakers" in data
    
    @patch("voyant.api.routes.health.REngine")
    @patch("voyant.api.routes.health._circuit_breakers")
    def test_status_endpoint_circuit_breaker_metrics(
        self,
        mock_cb_registry,
        mock_r_engine,
        client
    ):
        """Test /status includes circuit breaker metrics."""
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r.host = "localhost"
        mock_r.port = 6311
        mock_r_engine.return_value = mock_r
        
        # Mock circuit breaker
        mock_cb = MagicMock()
        mock_cb.get_metrics.return_value = {
            "name": "rserve",
            "state": "closed",
            "failure_count": 0,
            "success_count": 10
        }
        mock_cb_registry.items.return_value = [("rserve", mock_cb)]
        
        response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "rserve" in data["circuit_breakers"]
        assert data["circuit_breakers"]["rserve"]["state"] == "closed"
    
    @patch("voyant.api.routes.health.get_duckdb_connection")
    @patch("voyant.api.routes.health.REngine")
    @patch("voyant.api.routes.health.get_temporal_client")
    @patch("voyant.api.routes.health._circuit_breakers")
    def test_ready_circuit_breaker_open_critical_service(
        self,
        mock_cb_registry,
        mock_temporal,
        mock_r_engine,
        mock_duckdb,
        client
    ):
        """Test /ready returns 503 when critical circuit breaker is open."""
        # Mock all services as healthy
        mock_db_conn = MagicMock()
        mock_db_conn.execute.return_value.fetchone.return_value = (1,)
        mock_duckdb.return_value = mock_db_conn
        
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r
        
        mock_temporal.return_value = MagicMock()
        
        # Mock circuit breaker as OPEN for critical service
        from voyant.core.circuit_breaker import CircuitState
        mock_cb = MagicMock()
        mock_cb.get_state.return_value = CircuitState.OPEN
        mock_cb_registry.items.return_value = [("rserve", mock_cb)]
        
        response = client.get("/ready")
        
        # Should return not ready because critical circuit is open
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["circuit_breakers"]["states"]["rserve"] == "open"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
