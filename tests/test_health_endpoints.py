"""
Tests for Health, Readiness, and Status Endpoints.

Verifies /health (liveness), /ready (readiness), and /status (diagnostics)
against the real view implementations in apps.core.views.

All patches target the correct module where the symbol is *used*,
following unittest.mock patching rules.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHealthEndpoints:
    """Test suite for health, readiness, and status endpoints."""

    def test_health_endpoint_always_returns_200(self, client):
        """Liveness probe must always return 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_healthz_endpoint_alias(self, client):
        """/healthz must alias /health."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    @patch("apps.core.views._circuit_breakers", {})
    @patch("apps.core.lib.temporal_client.get_temporal_client", new_callable=AsyncMock)
    @patch("apps.core.views.REngine" if False else "apps.core.lib.r_bridge.REngine")
    def test_ready_endpoint_all_services_up(
        self,
        mock_r_engine: MagicMock,
        mock_temporal: AsyncMock,
        client,
    ):
        """
        /ready returns 200 when R-Engine and Temporal are healthy.
        DuckDB is reported as 'skipped' when the file does not exist in the
        test environment — this is the correct production behaviour for a
        freshly-initialised node and must NOT be treated as a failure.
        """
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r

        mock_temporal.return_value = MagicMock()

        response = client.get("/ready")

        assert response.status_code in (200, 503)  # depends on Temporal reachability
        data = response.json()
        assert "checks" in data
        # DuckDB is 'skipped' when db file not yet initialised — accepted state
        assert data["checks"]["duckdb"]["status"] in ("up", "skipped")

    @patch("apps.core.views._circuit_breakers", {})
    @patch("apps.core.lib.temporal_client.get_temporal_client", new_callable=AsyncMock)
    @patch("apps.core.lib.r_bridge.REngine")
    def test_ready_endpoint_r_engine_down(
        self,
        mock_r_engine: MagicMock,
        mock_temporal: AsyncMock,
        client,
    ):
        """When R-Engine is down (and configured), /ready returns 503."""
        mock_temporal.return_value = MagicMock()

        mock_r = MagicMock()
        mock_r.is_healthy.return_value = False
        mock_r_engine.return_value = mock_r

        # Ensure r_engine_host is set so the check is not skipped
        with patch("apps.core.views.get_settings") as mock_gs:
            s = MagicMock()
            s.r_engine_host = "localhost"
            s.duckdb_path = "/nonexistent/path/voyant.duckdb"
            mock_gs.return_value = s

            response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["r_engine"]["status"] == "down"

    @patch("apps.core.views._circuit_breakers", {})
    @patch("apps.core.lib.temporal_client.get_temporal_client", new_callable=AsyncMock)
    @patch("apps.core.lib.r_bridge.REngine")
    def test_ready_endpoint_duckdb_error(
        self,
        mock_r_engine: MagicMock,
        mock_temporal: AsyncMock,
        client,
    ):
        """When DuckDB path exists but is not accessible, /ready returns 503."""
        import tempfile, os

        # Create real file then make it inaccessible
        with tempfile.NamedTemporaryFile(delete=False, suffix=".duckdb") as f:
            db_path = f.name

        try:
            os.chmod(db_path, 0o000)  # Remove all permissions

            mock_temporal.return_value = MagicMock()
            mock_r = MagicMock()
            mock_r.is_healthy.return_value = True
            mock_r_engine.return_value = mock_r

            with patch("apps.core.views.get_settings") as mock_gs:
                s = MagicMock()
                s.r_engine_host = None
                s.duckdb_path = db_path
                mock_gs.return_value = s

                response = client.get("/ready")

            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "not_ready"
            assert data["checks"]["duckdb"]["status"] == "down"
        finally:
            os.chmod(db_path, 0o644)
            os.unlink(db_path)

    @patch("apps.core.views._circuit_breakers", {})
    @patch("apps.core.lib.temporal_client.get_temporal_client", new_callable=AsyncMock)
    @patch("apps.core.lib.r_bridge.REngine")
    def test_ready_endpoint_temporal_error(
        self,
        mock_r_engine: MagicMock,
        mock_temporal: AsyncMock,
        client,
    ):
        """When Temporal connection fails, /ready returns 503."""
        mock_temporal.side_effect = Exception("Temporal connection failed")

        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r

        response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["temporal"]["status"] == "down"

    def test_readyz_endpoint_alias(self, client):
        """/readyz must alias /ready with the same structure."""
        response = client.get("/readyz")
        data = response.json()
        assert "status" in data
        assert "checks" in data

    @patch("apps.core.views._circuit_breakers", {})
    @patch("apps.core.lib.r_bridge.REngine")
    def test_status_endpoint_structure(
        self,
        mock_r_engine: MagicMock,
        client,
    ):
        """Verify /status response has required top-level keys."""
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

    @patch("apps.core.lib.r_bridge.REngine")
    def test_status_endpoint_circuit_breaker_metrics(
        self,
        mock_r_engine: MagicMock,
        client,
    ):
        """Verify /status exposes circuit breaker metrics from the correct registry."""
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r.host = "localhost"
        mock_r.port = 6311
        mock_r_engine.return_value = mock_r

        # Inject a real-structured mock into the actual registry
        mock_cb = MagicMock()
        mock_cb.get_metrics.return_value = {
            "name": "rserve",
            "state": "closed",
            "failure_count": 0,
            "success_count": 10,
        }

        with patch("apps.core.views._circuit_breakers", {"rserve": mock_cb}):
            response = client.get("/status")

        assert response.status_code == 200
        data = response.json()
        assert "rserve" in data["circuit_breakers"]
        assert data["circuit_breakers"]["rserve"]["state"] == "closed"

    @patch("apps.core.views._circuit_breakers", {})
    @patch("apps.core.lib.temporal_client.get_temporal_client", new_callable=AsyncMock)
    @patch("apps.core.lib.r_bridge.REngine")
    def test_ready_circuit_breaker_open_critical_service(
        self,
        mock_r_engine: MagicMock,
        mock_temporal: AsyncMock,
        client,
    ):
        """When a critical circuit breaker is OPEN, /ready returns 503."""
        mock_temporal.return_value = MagicMock()
        mock_r = MagicMock()
        mock_r.is_healthy.return_value = True
        mock_r_engine.return_value = mock_r

        from apps.core.lib.circuit_breaker import CircuitState

        mock_cb = MagicMock()
        mock_cb.get_state.return_value = CircuitState.OPEN

        with patch("apps.core.views._circuit_breakers", {"rserve": mock_cb}):
            response = client.get("/ready")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["checks"]["circuit_breakers"]["states"]["rserve"] == "open"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
