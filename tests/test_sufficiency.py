import json
import os
import os as _os
import tempfile

import duckdb
from fastapi.testclient import TestClient

# Use isolated duckdb & artifacts root for this test to avoid permission issues
_tmp_dir = tempfile.mkdtemp(prefix="udb_suff_")
_os.environ["UDB_DUCKDB_PATH"] = os.path.join(_tmp_dir, "warehouse.duckdb")
_os.environ["UDB_ARTIFACTS_ROOT"] = os.path.join(_tmp_dir, "artifacts")
_os.environ["UDB_DISABLE_RATE_LIMIT"] = "1"

from voyant.api.app import ARTIFACTS_ROOT, DUCKDB_PATH, app  # noqa: E402

client = TestClient(app)


def test_sufficiency_artifact_and_metric(monkeypatch):
    # Ensure minimal table exists
    con = duckdb.connect(DUCKDB_PATH)
    con.execute("CREATE OR REPLACE TABLE test_suff (id INTEGER, val INTEGER, updated_at TIMESTAMP)")
    con.execute("INSERT INTO test_suff VALUES (1, 10, CURRENT_TIMESTAMP), (2, 20, CURRENT_TIMESTAMP)")
    # Run analyze with no KPIs (allowed)
    resp = client.post("/analyze", json={})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    job_id = data["jobId"]
    # Check sufficiency artifact
    suff_path = os.path.join(ARTIFACTS_ROOT, job_id, "sufficiency.json")
    assert os.path.isfile(suff_path), "sufficiency.json not created"
    with open(suff_path) as f:
        suff = json.load(f)
    assert "score" in suff and "components" in suff and "needs" in suff
    assert 0 <= suff["score"] <= 1
    # Check metrics endpoint contains sufficiency metric name
    m = client.get("/metrics").text
    assert "udb_sufficiency_score" in m