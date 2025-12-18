import os
import re

from fastapi.testclient import TestClient
from voyant.api.app import app


def test_recent_events_and_artifact_metric():
    os.environ["UDB_DISABLE_RATE_LIMIT"] = "1"
    os.environ["UDB_ENABLE_EVENTS"] = "1"
    client = TestClient(app)
    # Trigger analyze
    r = client.post("/analyze", json={})
    assert r.status_code == 200
    job_id = r.json()["jobId"]
    # Fetch recent events
    ev = client.get("/events/recent")
    assert ev.status_code == 200
    data = ev.json()
    assert "events" in data
    assert any(e.get("jobId") == job_id for e in data["events"])
    # Scrape metrics for artifact size and queue length
    m = client.get("/metrics")
    assert m.status_code == 200
    body = m.text
    # artifact size metric should appear with this job id label
    assert f"udb_artifact_size_bytes{{jobId=\"{job_id}\"" in body
    # duckdb queue length gauge present
    assert re.search(r"udb_duckdb_queue_length \d+", body)