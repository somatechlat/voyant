import os

from fastapi.testclient import TestClient
from udb_api.app import app


def test_admin_prune_endpoint():
    os.environ["UDB_DISABLE_RATE_LIMIT"] = "1"
    client = TestClient(app)
    # Role header required for admin
    resp = client.post("/admin/prune", headers={"X-Role": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert "removed" in data and "retentionDays" in data
    assert isinstance(data["removed"], int)
    assert isinstance(data["retentionDays"], int)