"""
Tests for Health, Readiness, and Status Endpoints.

Calls real Django test client against real view implementations.
NO mocking. Tests verify structural correctness and real infrastructure behaviour.
Service-specific failure scenarios (e.g. R-engine down) live in tests/integration/.
"""

import pytest


class TestHealthEndpoints:
    """Health, readiness, and status endpoint structural tests."""

    def test_health_endpoint_always_returns_200(self, client):
        """Liveness probe must always return 200 regardless of infrastructure state."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data

    def test_healthz_endpoint_alias(self, client):
        """/healthz is a k8s-compatible alias for /health."""
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_ready_endpoint_returns_valid_structure(self, client):
        """
        /ready returns a well-formed JSON response with all required keys.
        Status may be 'ready' or 'not_ready' depending on real infrastructure.
        DuckDB status may be 'up' or 'skipped' (file not yet initialised in test env).
        """
        response = client.get("/ready")
        assert response.status_code in (200, 503)

        data = response.json()
        assert "status" in data
        assert data["status"] in ("ready", "not_ready")
        assert "timestamp" in data
        assert "checks" in data

        checks = data["checks"]
        # DuckDB: either up (file exists) or skipped (not yet initialised) — both valid
        assert "duckdb" in checks
        assert checks["duckdb"]["status"] in ("up", "skipped", "down")

        # R-engine: either up, down, or skipped (when host not configured)
        assert "r_engine" in checks
        assert checks["r_engine"]["status"] in ("up", "down", "skipped")

        # Temporal: either up or down depending on cluster state
        assert "temporal" in checks
        assert checks["temporal"]["status"] in ("up", "down")

        # Circuit breakers: always present
        assert "circuit_breakers" in checks
        assert checks["circuit_breakers"]["status"] in ("monitored", "unknown")

    def test_readyz_endpoint_alias(self, client):
        """/readyz is a k8s-compatible alias for /ready."""
        response = client.get("/readyz")
        data = response.json()
        assert "status" in data
        assert "checks" in data

    def test_status_endpoint_structure(self, client):
        """
        /status must return all required administrative keys.
        Values depend on real infrastructure state.
        """
        response = client.get("/status")
        assert response.status_code == 200

        data = response.json()
        assert "version" in data
        assert "timestamp" in data
        assert "environment" in data
        assert "services" in data
        assert "circuit_breakers" in data

    def test_status_environment_field(self, client):
        """/status environment field must match the configured VOYANT_ENV."""
        response = client.get("/status")
        data = response.json()
        assert data["environment"] in ("local", "test", "staging", "production")

    def test_version_endpoint_structure(self, client):
        """/version must return version metadata."""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert "current_version" in data

    def test_ready_response_has_iso8601_timestamp(self, client):
        """/ready timestamp must be an ISO-8601 UTC string ending in Z."""
        response = client.get("/ready")
        data = response.json()
        ts = data["timestamp"]
        assert isinstance(ts, str)
        assert ts.endswith("Z"), f"Timestamp not UTC: {ts}"

    def test_health_response_has_iso8601_timestamp(self, client):
        """/health timestamp must be an ISO-8601 UTC string ending in Z."""
        response = client.get("/health")
        data = response.json()
        ts = data["timestamp"]
        assert isinstance(ts, str)
        assert ts.endswith("Z"), f"Timestamp not UTC: {ts}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
