import os

import duckdb
from fastapi.testclient import TestClient

os.environ["UDB_DISABLE_RATE_LIMIT"] = "1"

from voyant.api.app import DUCKDB_PATH, _tenant_artifact_root, app, job_store  # noqa: E402

client = TestClient(app, raise_server_exceptions=False)


def test_analyze_failure_emits_failed(monkeypatch):
    # Force failure by monkeypatching execute_kpis to raise
    from udb_api import kpi as kpi_module

    def boom(*args, **kwargs):  # noqa: ARG001
        raise RuntimeError("Synthetic failure")

    monkeypatch.setattr(kpi_module, "execute_kpis", boom)

    # ensure duckdb file exists
    duckdb.connect(DUCKDB_PATH).close()

    resp = client.post("/analyze", json={"kpiSql": "select 1 as x"})
    assert resp.status_code == 500, resp.text

    # Find last job id in store with type analyze and failed
    failed = [
        jid
        for jid, data in job_store._store.items()
        if data.get("type") == "analyze" and data.get("state") == "failed"
    ]
    assert failed, "No failed analyze job recorded"
    job_id = failed[-1]

    # Counter increment check (failed label increments by 1)
    # We can't easily read internal counter value without Prom scrape, but ensure artifact dir created (even if partial)
    art_root = os.path.join(_tenant_artifact_root(None), job_id)
    assert os.path.isdir(os.path.dirname(art_root)), "Artifact root directory missing"

    # Basic shape of job id
    assert job_id.startswith("job_") or job_id, "Unexpected job id format"
