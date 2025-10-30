import os
from fastapi.testclient import TestClient
from udb_api.app import app


def test_metrics_select_core_filters_high_cardinality():
    os.environ["UDB_DISABLE_RATE_LIMIT"] = "1"
    client = TestClient(app)
    # Trigger analyze to create artifact size metric
    r = client.post("/analyze", json={})
    assert r.status_code == 200
    full = client.get("/metrics").text
    assert "udb_artifact_size_bytes" in full
    core = client.get("/metrics/select?mode=core").text
    assert "udb_artifact_size_bytes" not in core
    # core should still have jobs_total
    assert "udb_jobs_total" in core