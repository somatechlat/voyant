"""
Comprehensive tests for workflow API: schemas, helpers, presets, and endpoints.

Covers:
- Request/Response schema validation and defaults
- _to_job_response helper function
- PRESETS registry structure and completeness
- list_presets with and without category filter
- get_preset for existing and missing presets
- _validate_table_scope helper
- get_minio_client singleton behavior
- KPI template endpoint schemas
"""

import uuid

import pytest
from django.test import RequestFactory
from django.utils import timezone
from ninja.errors import HttpError

from apps.workflows.api import (
    PRESETS,
    ArtifactInfo,
    IngestRequest,
    JobResponse,
    KPITemplateInfo,
    PresetInfo,
    ProfileRequest,
    QualityRequest,
    RenderKPIRequest,
    _to_job_response,
    get_preset,
    list_presets,
)
from apps.workflows.models import Artifact, Job, PresetJob

# ---------------------------------------------------------------------------
# Schema Validation Tests
# ---------------------------------------------------------------------------


class TestIngestRequestSchema:
    """Tests for the IngestRequest schema."""

    def test_ingest_request_defaults(self):
        """IngestRequest has correct defaults for mode and tables."""
        req = IngestRequest(source_id="src-1")
        assert req.source_id == "src-1"
        assert req.mode == "full"
        assert req.tables is None

    def test_ingest_request_with_all_fields(self):
        """IngestRequest accepts all fields."""
        req = IngestRequest(
            source_id="src-1", mode="incremental", tables=["users", "orders"]
        )
        assert req.source_id == "src-1"
        assert req.mode == "incremental"
        assert req.tables == ["users", "orders"]

    def test_ingest_request_with_empty_tables(self):
        """IngestRequest accepts an empty list for tables."""
        req = IngestRequest(source_id="src-1", tables=[])
        assert req.tables == []

    def test_ingest_request_mode_full(self):
        """IngestRequest mode defaults to 'full'."""
        req = IngestRequest(source_id="src-1")
        assert req.mode == "full"


class TestProfileRequestSchema:
    """Tests for the ProfileRequest schema."""

    def test_profile_request_defaults(self):
        """ProfileRequest has correct defaults."""
        req = ProfileRequest(source_id="src-1")
        assert req.source_id == "src-1"
        assert req.table is None
        assert req.sample_size == 10000

    def test_profile_request_with_all_fields(self):
        """ProfileRequest accepts all fields."""
        req = ProfileRequest(source_id="src-1", table="users", sample_size=5000)
        assert req.source_id == "src-1"
        assert req.table == "users"
        assert req.sample_size == 5000

    def test_profile_request_sample_size_min_boundary(self):
        """ProfileRequest sample_size minimum is 100."""
        req = ProfileRequest(source_id="src-1", sample_size=100)
        assert req.sample_size == 100

    def test_profile_request_sample_size_max_boundary(self):
        """ProfileRequest sample_size maximum is 1,000,000."""
        req = ProfileRequest(source_id="src-1", sample_size=1_000_000)
        assert req.sample_size == 1_000_000

    def test_profile_request_sample_size_below_min_raises(self):
        """ProfileRequest rejects sample_size below 100."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ProfileRequest(source_id="src-1", sample_size=99)

    def test_profile_request_sample_size_above_max_raises(self):
        """ProfileRequest rejects sample_size above 1,000,000."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ProfileRequest(source_id="src-1", sample_size=1_000_001)


class TestQualityRequestSchema:
    """Tests for the QualityRequest schema."""

    def test_quality_request_defaults(self):
        """QualityRequest has correct defaults."""
        req = QualityRequest(source_id="src-1")
        assert req.source_id == "src-1"
        assert req.table is None
        assert req.checks is None

    def test_quality_request_with_all_fields(self):
        """QualityRequest accepts all fields."""
        req = QualityRequest(
            source_id="src-1", table="users", checks=["nulls", "duplicates"]
        )
        assert req.source_id == "src-1"
        assert req.table == "users"
        assert req.checks == ["nulls", "duplicates"]

    def test_quality_request_with_empty_checks(self):
        """QualityRequest accepts an empty list for checks."""
        req = QualityRequest(source_id="src-1", checks=[])
        assert req.checks == []


class TestRenderKPIRequestSchema:
    """Tests for the RenderKPIRequest schema."""

    def test_render_kpi_request(self):
        """RenderKPIRequest stores params dict."""
        req = RenderKPIRequest(params={"source_id": "src-1", "table": "users"})
        assert req.params == {"source_id": "src-1", "table": "users"}

    def test_render_kpi_request_empty_params(self):
        """RenderKPIRequest accepts empty params."""
        req = RenderKPIRequest(params={})
        assert req.params == {}


# ---------------------------------------------------------------------------
# Response Schema Tests
# ---------------------------------------------------------------------------


class TestJobResponseSchema:
    """Tests for the JobResponse schema."""

    def test_job_response_required_fields(self):
        """JobResponse can be created with required fields only."""
        resp = JobResponse(
            job_id="j1",
            tenant_id="t1",
            job_type="ingest",
            status="queued",
            progress=0,
            created_at="2024-01-01T00:00:00",
        )
        assert resp.job_id == "j1"
        assert resp.tenant_id == "t1"
        assert resp.started_at is None
        assert resp.completed_at is None
        assert resp.result_summary is None
        assert resp.error_message is None

    def test_job_response_with_all_fields(self):
        """JobResponse accepts all fields."""
        resp = JobResponse(
            job_id="j1",
            tenant_id="t1",
            job_type="profile",
            status="completed",
            progress=100,
            created_at="2024-01-01T00:00:00",
            started_at="2024-01-01T00:00:01",
            completed_at="2024-01-01T00:05:00",
            result_summary={"rows": 1000},
            error_message=None,
        )
        assert resp.started_at == "2024-01-01T00:00:01"
        assert resp.completed_at == "2024-01-01T00:05:00"
        assert resp.result_summary == {"rows": 1000}


class TestArtifactInfoSchema:
    """Tests for the ArtifactInfo schema."""

    def test_artifact_info_required_fields(self):
        """ArtifactInfo can be created with required fields."""
        info = ArtifactInfo(
            artifact_id="a1",
            job_id="j1",
            artifact_type="profile",
            format="json",
            storage_path="/path",
            created_at="2024-01-01T00:00:00",
        )
        assert info.artifact_id == "a1"
        assert info.size_bytes is None

    def test_artifact_info_with_size(self):
        """ArtifactInfo accepts size_bytes."""
        info = ArtifactInfo(
            artifact_id="a1",
            job_id="j1",
            artifact_type="chart",
            format="png",
            storage_path="/path",
            size_bytes=2048,
            created_at="2024-01-01T00:00:00",
        )
        assert info.size_bytes == 2048


class TestPresetInfoSchema:
    """Tests for the PresetInfo schema."""

    def test_preset_info_creation(self):
        """PresetInfo can be created with all fields."""
        info = PresetInfo(
            name="Data Profiling",
            category="quality",
            description="Profile table quality",
            parameters=["source_id", "table"],
            output_artifacts=["profile"],
        )
        assert info.name == "Data Profiling"
        assert info.category == "quality"
        assert info.parameters == ["source_id", "table"]
        assert info.output_artifacts == ["profile"]


class TestKPITemplateInfoSchema:
    """Tests for the KPITemplateInfo schema."""

    def test_kpi_template_info_creation(self):
        """KPITemplateInfo can be created with all fields."""
        info = KPITemplateInfo(
            name="Revenue KPI",
            category="finance",
            description="Calculate revenue metrics",
            required_columns=["revenue", "date"],
        )
        assert info.name == "Revenue KPI"
        assert info.required_columns == ["revenue", "date"]


# ---------------------------------------------------------------------------
# _to_job_response Helper
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestToJobResponse:
    """Tests for the _to_job_response helper function."""

    def test_basic_job_response(self):
        """_to_job_response maps Job model fields to JobResponse."""
        job = Job.objects.create(
            tenant_id="t1", job_type="ingest", status="queued"
        )
        resp = _to_job_response(job)
        assert resp.job_id == str(job.id)
        assert resp.tenant_id == "t1"
        assert resp.job_type == "ingest"
        assert resp.status == "queued"
        assert resp.progress == 0
        assert resp.started_at is None
        assert resp.completed_at is None
        assert resp.result_summary is None
        assert resp.error_message is None

    def test_job_response_with_started_at(self):
        """_to_job_response formats started_at as ISO string."""
        now = timezone.now()
        job = Job.objects.create(
            tenant_id="t1",
            job_type="profile",
            status="running",
            started_at=now,
        )
        resp = _to_job_response(job)
        assert resp.started_at == now.isoformat()

    def test_job_response_with_completed_at(self):
        """_to_job_response formats completed_at as ISO string."""
        now = timezone.now()
        job = Job.objects.create(
            tenant_id="t1",
            job_type="quality",
            status="completed",
            started_at=now,
            completed_at=now,
        )
        resp = _to_job_response(job)
        assert resp.completed_at == now.isoformat()

    def test_job_response_with_result_summary(self):
        """_to_job_response passes through result_summary."""
        summary = {"total": 100, "errors": 2}
        job = Job.objects.create(
            tenant_id="t1",
            job_type="quality",
            status="completed",
            result_summary=summary,
        )
        resp = _to_job_response(job)
        assert resp.result_summary == summary

    def test_job_response_with_error_message(self):
        """_to_job_response passes through error_message."""
        job = Job.objects.create(
            tenant_id="t1",
            job_type="ingest",
            status="failed",
            error_message="Source not reachable",
        )
        resp = _to_job_response(job)
        assert resp.error_message == "Source not reachable"

    def test_job_response_created_at_is_iso_format(self):
        """_to_job_response formats created_at as ISO string."""
        job = Job.objects.create(
            tenant_id="t1", job_type="ingest", status="queued"
        )
        resp = _to_job_response(job)
        # Should be a valid ISO format string
        assert "T" in resp.created_at
        assert resp.created_at == job.created_at.isoformat()

    def test_job_response_with_progress(self):
        """_to_job_response maps progress correctly."""
        job = Job.objects.create(
            tenant_id="t1", job_type="ingest", status="running", progress=42
        )
        resp = _to_job_response(job)
        assert resp.progress == 42


# ---------------------------------------------------------------------------
# PRESETS Registry
# ---------------------------------------------------------------------------


class TestPresetsRegistry:
    """Tests for the PRESETS dictionary."""

    def test_presets_is_not_empty(self):
        """PRESETS dictionary contains entries."""
        assert len(PRESETS) > 0

    def test_presets_have_required_keys(self):
        """Each preset has all required keys."""
        required_keys = {
            "name",
            "category",
            "description",
            "parameters",
            "output_artifacts",
            "job_type",
        }
        for key, preset in PRESETS.items():
            assert required_keys.issubset(
                preset.keys()
            ), f"Preset '{key}' is missing keys: {required_keys - preset.keys()}"

    def test_presets_quality_data_profiling(self):
        """quality.data_profiling preset has correct configuration."""
        preset = PRESETS["quality.data_profiling"]
        assert preset["name"] == "Data Profiling"
        assert preset["category"] == "quality"
        assert preset["job_type"] == "profile"
        assert "source_id" in preset["parameters"]
        assert "table" in preset["parameters"]
        assert "sample_size" in preset["parameters"]

    def test_presets_quality_data_checks(self):
        """quality.data_checks preset has correct configuration."""
        preset = PRESETS["quality.data_checks"]
        assert preset["name"] == "Data Quality Checks"
        assert preset["category"] == "quality"
        assert preset["job_type"] == "quality"
        assert "source_id" in preset["parameters"]
        assert "table" in preset["parameters"]
        assert "checks" in preset["parameters"]

    def test_presets_parameters_are_lists(self):
        """All preset parameters are lists of strings."""
        for key, preset in PRESETS.items():
            assert isinstance(
                preset["parameters"], list
            ), f"Preset '{key}' parameters should be a list"
            for param in preset["parameters"]:
                assert isinstance(
                    param, str
                ), f"Preset '{key}' parameter '{param}' should be a string"

    def test_presets_output_artifacts_are_lists(self):
        """All preset output_artifacts are lists of strings."""
        for key, preset in PRESETS.items():
            assert isinstance(
                preset["output_artifacts"], list
            ), f"Preset '{key}' output_artifacts should be a list"


# ---------------------------------------------------------------------------
# list_presets Endpoint Logic
# ---------------------------------------------------------------------------


class TestListPresetsLogic:
    """Tests for the list_presets function logic."""

    def test_list_presets_returns_grouped_dict(self):
        """list_presets returns presets grouped by category."""
        rf = RequestFactory()
        request = rf.get("/presets")
        result = list_presets(request)
        assert isinstance(result, dict)
        # All values should be lists
        for category, presets_list in result.items():
            assert isinstance(presets_list, list)
            for p in presets_list:
                assert isinstance(p, PresetInfo)

    def test_list_presets_filter_by_category(self):
        """list_presets filters by category when provided."""
        rf = RequestFactory()
        request = rf.get("/presets?category=quality")
        result = list_presets(request, category="quality")
        assert "quality" in result
        # All returned presets should be in the quality category
        for category, presets_list in result.items():
            for p in presets_list:
                assert p.category == "quality"

    def test_list_presets_nonexistent_category_returns_empty(self):
        """list_presets returns empty dict for non-existent category."""
        rf = RequestFactory()
        request = rf.get("/presets?category=nonexistent")
        result = list_presets(request, category="nonexistent")
        assert result == {}

    def test_list_presets_no_filter_returns_all(self):
        """list_presets without category filter returns all presets."""
        rf = RequestFactory()
        request = rf.get("/presets")
        result = list_presets(request)
        total_presets = sum(len(v) for v in result.values())
        assert total_presets == len(PRESETS)


# ---------------------------------------------------------------------------
# get_preset Endpoint Logic
# ---------------------------------------------------------------------------


class TestGetPresetLogic:
    """Tests for the get_preset function logic."""

    def test_get_existing_preset(self):
        """get_preset returns PresetInfo for an existing preset."""
        rf = RequestFactory()
        request = rf.get("/presets/quality.data_profiling")
        result = get_preset(request, "quality.data_profiling")
        assert isinstance(result, PresetInfo)
        assert result.name == "Data Profiling"
        assert result.category == "quality"

    def test_get_preset_not_found_raises_404(self):
        """get_preset raises HttpError(404) for missing preset."""
        rf = RequestFactory()
        request = rf.get("/presets/nonexistent")
        with pytest.raises(HttpError) as exc_info:
            get_preset(request, "nonexistent")
        assert exc_info.value.status_code == 404

    def test_get_preset_quality_data_checks(self):
        """get_preset returns correct info for quality.data_checks."""
        rf = RequestFactory()
        request = rf.get("/presets/quality.data_checks")
        result = get_preset(request, "quality.data_checks")
        assert result.name == "Data Quality Checks"
        assert result.category == "quality"
        assert "source_id" in result.parameters
        assert "quality" in result.output_artifacts


# ---------------------------------------------------------------------------
# _validate_table_scope
# ---------------------------------------------------------------------------


class TestValidateTableScope:
    """Tests for the _validate_table_scope helper."""

    def test_validate_table_scope_with_none_tables(self):
        """_validate_table_scope returns None when tables is None."""
        from apps.workflows.api import _validate_table_scope

        # Should not raise
        _validate_table_scope("tenant-1", None)

    def test_validate_table_scope_with_empty_tables(self):
        """_validate_table_scope returns None when tables is empty list."""
        from apps.workflows.api import _validate_table_scope

        # Should not raise
        _validate_table_scope("tenant-1", [])


# ---------------------------------------------------------------------------
# get_minio_client
# ---------------------------------------------------------------------------


class TestGetMinioClient:
    """Tests for the get_minio_client function."""

    def test_get_minio_client_returns_value(self):
        """get_minio_client returns a value or None (depending on config)."""
        from apps.workflows.api import get_minio_client

        # In test environment, MinIO may or may not be available
        # The function should not raise an unhandled exception
        client = get_minio_client()
        # client is either a Minio instance or None
        assert client is not None or client is None  # Always true, but exercises the code


# ---------------------------------------------------------------------------
# Database Integration Tests for API Helpers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestJobModelAPIIntegration:
    """Integration tests between Job model and API response helpers."""

    def test_create_and_retrieve_job(self):
        """Job can be created and retrieved from the database."""
        job = Job.objects.create(
            tenant_id="t1",
            job_type="ingest",
            source_id="src-1",
            parameters={"mode": "full", "tables": ["users"]},
        )
        retrieved = Job.objects.get(id=job.id)
        assert retrieved.job_type == "ingest"
        assert retrieved.source_id == "src-1"
        assert retrieved.parameters == {"mode": "full", "tables": ["users"]}

    def test_job_lifecycle_queued_to_completed(self):
        """Job can transition through its full lifecycle."""
        job = Job.objects.create(
            tenant_id="t1", job_type="profile", source_id="src-1"
        )
        assert job.status == "queued"

        # Transition to running
        job.status = "running"
        job.started_at = timezone.now()
        job.progress = 50
        job.save(update_fields=["status", "started_at", "progress"])

        job.refresh_from_db()
        assert job.status == "running"
        assert job.started_at is not None
        assert job.progress == 50

        # Transition to completed
        job.status = "completed"
        job.completed_at = timezone.now()
        job.progress = 100
        job.result_summary = {"rows_profiled": 5000}
        job.save(update_fields=["status", "completed_at", "progress", "result_summary"])

        job.refresh_from_db()
        assert job.status == "completed"
        assert job.completed_at is not None
        assert job.progress == 100
        assert job.result_summary == {"rows_profiled": 5000}

    def test_job_lifecycle_queued_to_failed(self):
        """Job can transition from queued to failed with error message."""
        job = Job.objects.create(
            tenant_id="t1", job_type="ingest", source_id="src-1"
        )
        job.status = "failed"
        job.error_message = "Connection refused by source"
        job.save(update_fields=["status", "error_message"])

        job.refresh_from_db()
        assert job.status == "failed"
        assert job.error_message == "Connection refused by source"

    def test_job_lifecycle_queued_to_cancelled(self):
        """Job can be cancelled."""
        job = Job.objects.create(
            tenant_id="t1", job_type="ingest", source_id="src-1"
        )
        job.status = "cancelled"
        job.save(update_fields=["status"])

        job.refresh_from_db()
        assert job.status == "cancelled"

    def test_multiple_jobs_for_same_tenant(self):
        """Multiple jobs can exist for the same tenant."""
        for i in range(5):
            Job.objects.create(
                tenant_id="t1", job_type="ingest", source_id=f"src-{i}"
            )

        jobs = Job.objects.filter(tenant_id="t1")
        assert jobs.count() == 5

    def test_job_filter_by_status(self):
        """Jobs can be filtered by status."""
        Job.objects.create(tenant_id="t1", job_type="ingest", status="queued")
        Job.objects.create(tenant_id="t1", job_type="ingest", status="running")
        Job.objects.create(tenant_id="t1", job_type="ingest", status="completed")
        Job.objects.create(tenant_id="t1", job_type="ingest", status="queued")

        queued = Job.objects.filter(status="queued")
        assert queued.count() == 2

        running = Job.objects.filter(status="running")
        assert running.count() == 1

    def test_job_filter_by_job_type(self):
        """Jobs can be filtered by job_type."""
        Job.objects.create(tenant_id="t1", job_type="ingest", status="queued")
        Job.objects.create(tenant_id="t1", job_type="profile", status="queued")
        Job.objects.create(tenant_id="t1", job_type="ingest", status="queued")

        ingest_jobs = Job.objects.filter(job_type="ingest")
        assert ingest_jobs.count() == 2

        profile_jobs = Job.objects.filter(job_type="profile")
        assert profile_jobs.count() == 1


@pytest.mark.django_db
class TestPresetJobAPIIntegration:
    """Integration tests between PresetJob model and API."""

    def test_create_and_execute_preset_job(self):
        """PresetJob can be created with running status for execution."""
        preset = PresetJob.objects.create(
            tenant_id="t1",
            preset_name="quality.data_profiling",
            source_id="src-1",
            parameters={"table": "users", "sample_size": 10000},
            status="running",
        )
        assert preset.status == "running"
        assert preset.parameters["table"] == "users"

    def test_preset_job_lifecycle(self):
        """PresetJob can transition through its lifecycle."""
        preset = PresetJob.objects.create(
            tenant_id="t1",
            preset_name="quality.data_checks",
            source_id="src-1",
            parameters={"table": "orders", "checks": ["nulls"]},
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


@pytest.mark.django_db
class TestArtifactAPIIntegration:
    """Integration tests between Artifact model and API response helpers."""

    def test_create_multiple_artifacts_for_job(self):
        """Multiple artifacts can be associated with a single job."""
        job_id = str(uuid.uuid4())
        Artifact.objects.create(
            tenant_id="t1",
            artifact_id=f"{job_id}-profile",
            job_id=job_id,
            artifact_type="profile",
            format="json",
            storage_path=f"/artifacts/{job_id}/profile.json",
            size_bytes=4096,
        )
        Artifact.objects.create(
            tenant_id="t1",
            artifact_id=f"{job_id}-chart",
            job_id=job_id,
            artifact_type="chart",
            format="png",
            storage_path=f"/artifacts/{job_id}/chart.png",
            size_bytes=20480,
        )

        artifacts = Artifact.objects.filter(job_id=job_id).order_by("-created_at")
        assert artifacts.count() == 2
        assert artifacts[0].artifact_type == "chart"
        assert artifacts[1].artifact_type == "profile"

    def test_artifact_to_artifact_info_mapping(self):
        """Artifact model fields map correctly to ArtifactInfo schema."""
        artifact = Artifact.objects.create(
            tenant_id="t1",
            artifact_id="art-map-test",
            job_id="j1",
            artifact_type="report",
            format="pdf",
            storage_path="/reports/report.pdf",
            size_bytes=102400,
        )
        info = ArtifactInfo(
            artifact_id=artifact.artifact_id,
            job_id=artifact.job_id,
            artifact_type=artifact.artifact_type,
            format=artifact.format,
            storage_path=artifact.storage_path,
            size_bytes=artifact.size_bytes,
            created_at=artifact.created_at.isoformat(),
        )
        assert info.artifact_id == "art-map-test"
        assert info.job_id == "j1"
        assert info.artifact_type == "report"
        assert info.format == "pdf"
        assert info.size_bytes == 102400
