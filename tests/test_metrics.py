from fastapi.testclient import TestClient
from udb_api.app import app

def test_metrics_endpoint():
    client = TestClient(app)
    r = client.get('/metrics')
    assert r.status_code == 200
    assert b'udb_jobs_total' in r.content
