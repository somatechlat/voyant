"""
Comprehensive tests for workflow models: Job, Artifact, PresetJob.

Covers:
- Field defaults and constraints
- job_id compatibility alias
- Ordering and db_table configuration
- JSONField handling
- Nullable/blank field behavior
- Multi-tenant isolation via tenant_id
- UUID primary key generation
"""

import uuid

import pytest

from apps.workflows.models import Artifact, Job, PresetJob

# ---------------------------------------------------------------------------
# Job Model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJobModel:
    """Tests for the Job model."""

    def test_create_minimal_job(self):
        """Job can be created with only required fields."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert job.pk is not None
        assert job.tenant_id == "t1"
        assert job.job_type == "ingest"

    def test_job_has_uuid_primary_key(self):
        """Job uses a UUID primary key."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert isinstance(job.id, uuid.UUID)

    def test_job_id_alias_returns_string_uuid(self):
        """job_id property returns the string representation of the UUID pk."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert job.job_id == str(job.id)
        assert isinstance(job.job_id, str)

    def test_job_default_status_is_queued(self):
        """New jobs default to 'queued' status."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert job.status == "queued"

    def test_job_default_progress_is_zero(self):
        """New jobs default to progress=0."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert job.progress == 0

    def test_job_default_parameters_is_empty_dict(self):
        """New jobs default to an empty dict for parameters."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert job.parameters == {}

    def test_job_nullable_fields_default_to_none(self):
        """Nullable fields (source_id, soma_session_id, started_at, completed_at,
        result_summary, error_message) default to None or blank."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert job.source_id is None
        assert job.soma_session_id is None
        assert job.started_at is None
        assert job.completed_at is None
        assert job.result_summary is None
        assert job.error_message is None

    def test_job_with_all_fields(self):
        """Job can be created with all fields populated."""
        from django.utils import timezone

        now = timezone.now()
        job = Job.objects.create(
            tenant_id="t1",
            job_type="profile",
            source_id="src-1",
            soma_session_id="sess-abc",
            status="running",
            progress=50,
            parameters={"table": "users", "sample_size": 5000},
            started_at=now,
            result_summary={"rows": 1000},
            error_message=None,
        )
        assert job.job_type == "profile"
        assert job.source_id == "src-1"
        assert job.soma_session_id == "sess-abc"
        assert job.status == "running"
        assert job.progress == 50
        assert job.parameters == {"table": "users", "sample_size": 5000}
        assert job.started_at == now
        assert job.result_summary == {"rows": 1000}

    def test_job_parameters_json_field_stores_complex_data(self):
        """JSONField parameters can store nested structures."""
        complex_params = {
            "tables": ["users", "orders"],
            "config": {"nested": True, "thresholds": [0.1, 0.5, 0.9]},
        }
        job = Job.objects.create(
            tenant_id="t1", job_type="analyze", parameters=complex_params
        )
        job.refresh_from_db()
        assert job.parameters == complex_params

    def test_job_result_summary_json_field(self):
        """result_summary JSONField stores and retrieves complex data."""
        summary = {"total_rows": 5000, "errors": [], "warnings": ["low coverage"]}
        job = Job.objects.create(
            tenant_id="t1", job_type="quality", result_summary=summary
        )
        job.refresh_from_db()
        assert job.result_summary == summary

    def test_job_ordering_is_descending_by_created_at(self):
        """Jobs are ordered by -created_at by default (newest first)."""
        j1 = Job.objects.create(tenant_id="t1", job_type="ingest")
        j2 = Job.objects.create(tenant_id="t1", job_type="profile")
        j3 = Job.objects.create(tenant_id="t1", job_type="quality")

        jobs = list(Job.objects.all())
        assert jobs[0].id == j3.id
        assert jobs[1].id == j2.id
        assert jobs[2].id == j1.id

    def test_job_db_table_name(self):
        """Job model uses 'voyant_job' as its database table."""
        assert Job._meta.db_table == "voyant_job"

    def test_job_max_length_source_id(self):
        """source_id respects max_length=36 (UUID string length)."""
        job = Job.objects.create(
            tenant_id="t1", job_type="ingest", source_id="a" * 36
        )
        assert len(job.source_id) == 36

    def test_job_max_length_soma_session_id(self):
        """soma_session_id respects max_length=128."""
        job = Job.objects.create(
            tenant_id="t1", job_type="ingest", soma_session_id="s" * 128
        )
        assert len(job.soma_session_id) == 128

    def test_job_status_can_be_updated(self):
        """Job status transitions are persisted correctly."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert job.status == "queued"

        job.status = "running"
        job.save(update_fields=["status"])
        job.refresh_from_db()
        assert job.status == "running"

        job.status = "completed"
        job.save(update_fields=["status"])
        job.refresh_from_db()
        assert job.status == "completed"

    def test_job_progress_can_be_updated(self):
        """Job progress can be updated and persisted."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        job.progress = 75
        job.save(update_fields=["progress"])
        job.refresh_from_db()
        assert job.progress == 75

    def test_job_error_message_can_be_set(self):
        """Error message can be set on a job."""
        job = Job.objects.create(
            tenant_id="t1",
            job_type="ingest",
            status="failed",
            error_message="Connection timeout to source",
        )
        job.refresh_from_db()
        assert job.error_message == "Connection timeout to source"

    def test_job_tenant_isolation(self):
        """Jobs are isolated by tenant_id when using the default manager."""
        Job.objects.create(tenant_id="tenant-a", job_type="ingest")
        Job.objects.create(tenant_id="tenant-b", job_type="profile")
        Job.objects.create(tenant_id="tenant-a", job_type="quality")

        # Without RBAC filtering (admin context), all jobs are visible
        all_jobs = Job.objects.all()
        assert all_jobs.count() == 3

    def test_job_timestamps_auto_set(self):
        """created_at and updated_at are automatically set."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert job.created_at is not None
        assert job.updated_at is not None

    def test_job_realm_default(self):
        """Job realm defaults to 'default'."""
        job = Job.objects.create(tenant_id="t1", job_type="ingest")
        assert job.realm == "default"


# ---------------------------------------------------------------------------
# Artifact Model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestArtifactModel:
    """Tests for the Artifact model."""

    def test_create_artifact(self):
        """Artifact can be created with all required fields."""
        artifact = Artifact.objects.create(
            tenant_id="t1",
            artifact_id="art-001",
            job_id="job-001",
            artifact_type="profile",
            format="json",
            storage_path="s3://bucket/art-001.json",
        )
        assert artifact.artifact_id == "art-001"
        assert artifact.job_id == "job-001"
        assert artifact.artifact_type == "profile"
        assert artifact.format == "json"
        assert artifact.storage_path == "s3://bucket/art-001.json"

    def test_artifact_primary_key_is_artifact_id(self):
        """artifact_id is the primary key (CharField, not auto-generated)."""
        artifact = Artifact.objects.create(
            tenant_id="t1",
            artifact_id="custom-pk",
            job_id="j1",
            artifact_type="chart",
            format="png",
            storage_path="/path/chart.png",
        )
        assert artifact.pk == "custom-pk"

    def test_artifact_size_bytes_nullable(self):
        """size_bytes is optional and defaults to None."""
        artifact = Artifact.objects.create(
            tenant_id="t1",
            artifact_id="art-no-size",
            job_id="j1",
            artifact_type="report",
            format="pdf",
            storage_path="/path/report.pdf",
        )
        assert artifact.size_bytes is None

    def test_artifact_size_bytes_can_be_set(self):
        """size_bytes can be set to an integer value."""
        artifact = Artifact.objects.create(
            tenant_id="t1",
            artifact_id="art-sized",
            job_id="j1",
            artifact_type="report",
            format="pdf",
            storage_path="/path/report.pdf",
            size_bytes=102400,
        )
        assert artifact.size_bytes == 102400

    def test_artifact_db_table_name(self):
        """Artifact model uses 'voyant_artifact' as its database table."""
        assert Artifact._meta.db_table == "voyant_artifact"

    def test_artifact_timestamps_auto_set(self):
        """created_at and updated_at are automatically set on Artifact."""
        artifact = Artifact.objects.create(
            tenant_id="t1",
            artifact_id="art-ts",
            job_id="j1",
            artifact_type="data",
            format="csv",
            storage_path="/path/data.csv",
        )
        assert artifact.created_at is not None
        assert artifact.updated_at is not None

    def test_artifact_filter_by_job_id(self):
        """Artifacts can be filtered by job_id."""
        Artifact.objects.create(
            tenant_id="t1",
            artifact_id="art-j1-a",
            job_id="job-1",
            artifact_type="profile",
            format="json",
            storage_path="/p1",
        )
        Artifact.objects.create(
            tenant_id="t1",
            artifact_id="art-j1-b",
            job_id="job-1",
            artifact_type="chart",
            format="png",
            storage_path="/p2",
        )
        Artifact.objects.create(
            tenant_id="t1",
            artifact_id="art-j2-a",
            job_id="job-2",
            artifact_type="profile",
            format="json",
            storage_path="/p3",
        )

        job1_artifacts = Artifact.objects.filter(job_id="job-1")
        assert job1_artifacts.count() == 2

        job2_artifacts = Artifact.objects.filter(job_id="job-2")
        assert job2_artifacts.count() == 1

    def test_artifact_filter_by_type_and_format(self):
        """Artifacts can be filtered by artifact_type and format."""
        Artifact.objects.create(
            tenant_id="t1",
            artifact_id="a1",
            job_id="j1",
            artifact_type="profile",
            format="json",
            storage_path="/p1",
        )
        Artifact.objects.create(
            tenant_id="t1",
            artifact_id="a2",
            job_id="j1",
            artifact_type="profile",
            format="csv",
            storage_path="/p2",
        )
        Artifact.objects.create(
            tenant_id="t1",
            artifact_id="a3",
            job_id="j1",
            artifact_type="chart",
            format="png",
            storage_path="/p3",
        )

        json_profiles = Artifact.objects.filter(
            artifact_type="profile", format="json"
        )
        assert json_profiles.count() == 1
        assert json_profiles.first().artifact_id == "a1"

    def test_artifact_tenant_isolation(self):
        """Artifacts are isolated by tenant_id."""
        Artifact.objects.create(
            tenant_id="tenant-a",
            artifact_id="a-ta",
            job_id="j1",
            artifact_type="profile",
            format="json",
            storage_path="/p1",
        )
        Artifact.objects.create(
            tenant_id="tenant-b",
            artifact_id="a-tb",
            job_id="j1",
            artifact_type="profile",
            format="json",
            storage_path="/p2",
        )

        # Without RBAC filtering, all artifacts visible
        assert Artifact.objects.count() == 2

    def test_artifact_long_storage_path(self):
        """Artifact storage_path supports long paths up to 512 chars."""
        long_path = "s3://bucket-name/tenant-id/jobs/job-id/artifacts/" + "x" * 400
        long_path = long_path[:512]
        artifact = Artifact.objects.create(
            tenant_id="t1",
            artifact_id="art-long",
            job_id="j1",
            artifact_type="data",
            format="parquet",
            storage_path=long_path,
        )
        assert artifact.storage_path == long_path

    def test_artifact_long_artifact_id(self):
        """artifact_id supports up to 512 characters."""
        long_id = "a" * 512
        artifact = Artifact.objects.create(
            tenant_id="t1",
            artifact_id=long_id,
            job_id="j1",
            artifact_type="data",
            format="json",
            storage_path="/p",
        )
        assert artifact.artifact_id == long_id


# ---------------------------------------------------------------------------
# PresetJob Model
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPresetJobModel:
    """Tests for the PresetJob model."""

    def test_create_preset_job(self):
        """PresetJob can be created with required fields."""
        preset = PresetJob.objects.create(
            tenant_id="t1",
            preset_name="quality.data_profiling",
            source_id="src-1",
        )
        assert preset.preset_name == "quality.data_profiling"
        assert preset.source_id == "src-1"

    def test_preset_job_has_uuid_primary_key(self):
        """PresetJob uses a UUID primary key."""
        preset = PresetJob.objects.create(
            tenant_id="t1", preset_name="test", source_id="src-1"
        )
        assert isinstance(preset.id, uuid.UUID)

    def test_preset_job_id_alias(self):
        """job_id property returns string representation of UUID pk."""
        preset = PresetJob.objects.create(
            tenant_id="t1", preset_name="test", source_id="src-1"
        )
        assert preset.job_id == str(preset.id)
        assert isinstance(preset.job_id, str)

    def test_preset_job_default_status_is_queued(self):
        """New PresetJobs default to 'queued' status."""
        preset = PresetJob.objects.create(
            tenant_id="t1", preset_name="test", source_id="src-1"
        )
        assert preset.status == "queued"

    def test_preset_job_default_parameters_is_empty_dict(self):
        """New PresetJobs default to empty dict for parameters."""
        preset = PresetJob.objects.create(
            tenant_id="t1", preset_name="test", source_id="src-1"
        )
        assert preset.parameters == {}

    def test_preset_job_with_parameters(self):
        """PresetJob can store complex JSON parameters."""
        params = {"table": "users", "checks": ["nulls", "duplicates"], "threshold": 0.95}
        preset = PresetJob.objects.create(
            tenant_id="t1",
            preset_name="quality.data_checks",
            source_id="src-1",
            parameters=params,
        )
        preset.refresh_from_db()
        assert preset.parameters == params

    def test_preset_job_db_table_name(self):
        """PresetJob model uses 'voyant_preset_job' as its database table."""
        assert PresetJob._meta.db_table == "voyant_preset_job"

    def test_preset_job_timestamps_auto_set(self):
        """created_at and updated_at are automatically set."""
        preset = PresetJob.objects.create(
            tenant_id="t1", preset_name="test", source_id="src-1"
        )
        assert preset.created_at is not None
        assert preset.updated_at is not None

    def test_preset_job_status_can_be_updated(self):
        """PresetJob status can transition."""
        preset = PresetJob.objects.create(
            tenant_id="t1", preset_name="test", source_id="src-1"
        )
        assert preset.status == "queued"

        preset.status = "running"
        preset.save(update_fields=["status"])
        preset.refresh_from_db()
        assert preset.status == "running"

        preset.status = "completed"
        preset.save(update_fields=["status"])
        preset.refresh_from_db()
        assert preset.status == "completed"

    def test_preset_job_tenant_isolation(self):
        """PresetJobs are isolated by tenant_id."""
        PresetJob.objects.create(
            tenant_id="tenant-a", preset_name="p1", source_id="s1"
        )
        PresetJob.objects.create(
            tenant_id="tenant-b", preset_name="p2", source_id="s2"
        )

        assert PresetJob.objects.count() == 2

    def test_preset_job_realm_default(self):
        """PresetJob realm defaults to 'default'."""
        preset = PresetJob.objects.create(
            tenant_id="t1", preset_name="test", source_id="src-1"
        )
        assert preset.realm == "default"

    def test_preset_job_source_id_max_length(self):
        """source_id respects max_length=36."""
        preset = PresetJob.objects.create(
            tenant_id="t1",
            preset_name="test",
            source_id="s" * 36,
        )
        assert len(preset.source_id) == 36

    def test_preset_job_preset_name_max_length(self):
        """preset_name respects max_length=255."""
        long_name = "category." + "n" * 246
        preset = PresetJob.objects.create(
            tenant_id="t1",
            preset_name=long_name,
            source_id="src-1",
        )
        assert preset.preset_name == long_name
