import os
import tempfile
from fastapi.testclient import TestClient

# Isolate storage paths for this test
_tmp = tempfile.mkdtemp(prefix="udb_analyze_")
os.environ["UDB_DUCKDB_PATH"] = os.path.join(_tmp, "warehouse.duckdb")
os.environ["UDB_ARTIFACTS_ROOT"] = os.path.join(_tmp, "artifacts")

from udb_api.app import app  # noqa: E402

client = TestClient(app)

def test_analyze_empty_env_creates_job():
    r = client.post('/analyze', json={})
    assert r.status_code == 200
    job_id = r.json()['jobId']
    # Artifact may or may not exist if no tables; ensure no crash
    # Not asserting artifact existence because no data tables in blank env.
    assert job_id
