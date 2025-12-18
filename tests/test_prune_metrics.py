import os
import tempfile
import time
import uuid

from fastapi.testclient import TestClient

# Use a temp directory for artifacts to avoid read-only / permission issues
TEMP_ART_ROOT = tempfile.mkdtemp(prefix="udb_artifacts_")
os.environ["UDB_ARTIFACTS_ROOT"] = TEMP_ART_ROOT  # must be set before app import

from voyant.api.app import ARTIFACTS_ROOT, app  # noqa: E402
from udb_api.metrics import artifacts_pruned  # noqa: E402

client = TestClient(app)


def _make_old_dir(age_days: int = 10):
    job_dir = os.path.join(ARTIFACTS_ROOT, f"old_{uuid.uuid4().hex[:8]}")
    os.makedirs(job_dir, exist_ok=True)
    old_time = time.time() - age_days * 86400
    os.utime(job_dir, (old_time, old_time))
    return job_dir


def test_prune_metrics(monkeypatch):
    # Set retention to 1 day so our 10 day old dir is pruned
    monkeypatch.setenv("UDB_ARTIFACT_RETENTION_DAYS", "1")
    old_dir = _make_old_dir()
    assert os.path.isdir(old_dir)

    before = artifacts_pruned._value.get() if hasattr(artifacts_pruned, "_value") else None

    # Need admin role header
    resp = client.post("/admin/prune", headers={"X-UDB-Role": "admin"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["removed"] >= 1

    assert not os.path.isdir(old_dir)

    after = artifacts_pruned._value.get() if hasattr(artifacts_pruned, "_value") else None
    if before is not None and after is not None:
        assert after >= before + 1
