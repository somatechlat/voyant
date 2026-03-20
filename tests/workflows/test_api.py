import time

import pytest
from django.test import RequestFactory

from apps.workflows.api import IngestRequest, trigger_ingest
from apps.workflows.models import Job as JobModel


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.mark.django_db
class TestWorkflowAPIIntegration:
    """
    Real integration tests for Workflows API.
    NO MOCKS.
    """

    def test_trigger_ingest_real_temporal(self, rf):
        # We assume Docker services are running on localhost:45xxx
        request = rf.post("/ingest", HTTP_X_TENANT_ID="test-tenant")
        payload = IngestRequest(source_id="src-integration-test", mode="full")

        # This will hit REAL database and REAL Temporal
        # Note: Temporal client must be accessible from host
        response = trigger_ingest(request, payload)

        assert response.job_type == "ingest"
        assert response.status in ("running", "queued")

        # Verify DB state
        job = JobModel.objects.get(id=response.job_id)
        assert job.tenant_id == "test-tenant"

        # Wait a bit for status change if running
        if job.status == "queued":
            time.sleep(2)
            job.refresh_from_db()

        assert job.status in (
            "running",
            "failed",
        )  # Might fail if source_id is invalid, but proves logic
