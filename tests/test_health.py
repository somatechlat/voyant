"""
Tests for Basic Health Endpoints.

This module contains basic tests for the `/healthz` and `/readyz` endpoints.
While functional, these tests are largely superseded by the more comprehensive
checks in `tests/test_health_endpoints.py`. This module may be deprecated
or removed in future iterations.
"""


def test_healthz(client):
    """
    Verifies that the /healthz endpoint returns a 200 OK status and a healthy status.
    """
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readyz(client):
    """
    Verifies that the /readyz endpoint returns either a 200 OK or 503 Service Unavailable
    status, and contains a 'status' field in its JSON response.
    """
    response = client.get("/readyz")
    assert response.status_code in (200, 503)
    assert "status" in response.json()
