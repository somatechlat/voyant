import os
import pytest
from fastapi.testclient import TestClient
from udb_api.app import _RATE_BUCKETS, app

client = TestClient(app)

@pytest.mark.skipif(False, reason="always run")
def test_sql_rate_limit():
    os.environ["UDB_RATE_LIMIT"] = "2"
    os.environ["UDB_RATE_WINDOW"] = "60"
    # First two should succeed (may 400 if table absent but not 429)
    # Ensure rate limiting not disabled by other tests
    os.environ.pop("UDB_DISABLE_RATE_LIMIT", None)
    r1 = client.post("/sql", json={"sql": "SELECT 1 as a"}, headers={"X-UDB-Role": "analyst"})
    assert r1.status_code != 429
    r2 = client.post("/sql", json={"sql": "SELECT 2 as b"}, headers={"X-UDB-Role": "analyst"})
    assert r2.status_code != 429
    r3 = client.post("/sql", json={"sql": "SELECT 3 as c"}, headers={"X-UDB-Role": "analyst"})
    assert r3.status_code == 429
    # Reset buckets so subsequent tests are unaffected
    _RATE_BUCKETS.clear()
    # Re-disable rate limiting for other tests
    os.environ["UDB_DISABLE_RATE_LIMIT"] = "1"
