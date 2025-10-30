import os

from fastapi.testclient import TestClient

os.environ["UDB_DISABLE_RATE_LIMIT"] = "1"

from udb_api.app import app  # noqa: E402

client = TestClient(app)

def test_sql_requires_role():
    r = client.post('/sql', json={'sql': 'SELECT 1'})
    assert r.status_code == 403
    r2 = client.post('/sql', headers={'X-UDB-Role':'analyst'}, json={'sql': 'SELECT 1'})
    assert r2.status_code != 403
