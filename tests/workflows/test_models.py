import pytest

from apps.workflows.models import Artifact, Job, PresetJob


@pytest.mark.django_db
class TestWorkflowModels:
    def test_job_id_alias(self):
        job = Job.objects.create(
            tenant_id="test-tenant", job_type="ingest", status="queued"
        )
        assert job.job_id == str(job.id)

    def test_artifact_creation(self):
        artifact = Artifact.objects.create(
            tenant_id="test-tenant",
            artifact_id="art-123",
            job_id="job-456",
            artifact_type="profile",
            format="json",
            storage_path="path/to/art",
        )
        assert artifact.artifact_id == "art-123"

    def test_preset_job_creation(self):
        preset = PresetJob.objects.create(
            tenant_id="test-tenant",
            preset_name="test-preset",
            source_id="src-789",
            parameters={"key": "value"},
        )
        assert preset.preset_name == "test-preset"
        assert preset.job_id == str(preset.id)
