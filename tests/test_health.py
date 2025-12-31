def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_readyz(client):
    response = client.get("/readyz")
    assert response.status_code in (200, 503)
    assert "status" in response.json()
