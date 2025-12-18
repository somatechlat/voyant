import os

from fastapi.testclient import TestClient

os.environ["UDB_DISABLE_RATE_LIMIT"] = "1"

from voyant.api.app import app  # noqa: E402

client = TestClient(app)

def test_sql_select_allowed():
    r = client.post('/sql', json={'sql': 'select 1 as x'}, headers={'X-UDB-Role': 'analyst'})
    assert r.status_code == 200
    data = r.json()
    assert data['rows'][0][0] == 1


def test_sql_insert_blocked():
    r = client.post('/sql', json={'sql': 'insert into t values (1)'}, headers={'X-UDB-Role': 'analyst'})
    assert r.status_code == 422 or r.status_code == 400
