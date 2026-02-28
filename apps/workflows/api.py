"""Workflow orchestration and artifact API endpoints."""

from __future__ import annotations

import io
import logging
from typing import Any, Dict, List, Optional

from django.http import StreamingHttpResponse
from ninja import Field, Router, Schema
from ninja.errors import HttpError

from apps.core.api_utils import apply_policy, run_async
from apps.core.config import get_settings
from apps.core.lib.kpi_templates import (
    get_categories as get_kpi_categories,
)
from apps.core.lib.kpi_templates import (
    get_template as get_kpi_template,
)
from apps.core.lib.kpi_templates import (
    list_templates as list_kpi_templates,
)
from apps.core.lib.kpi_templates import (
    render_template as render_kpi_template,
)
from apps.core.lib.namespace_analyzer import (
    NamespaceViolationError,
    validate_table_access,
)
from apps.core.lib.temporal_client import get_temporal_client
from apps.core.middleware import get_soma_session_id, get_tenant_id
from apps.integrations.soma import create_task_for_job, update_task_status
from apps.worker.workflows.ingest_workflow import IngestDataWorkflow
from apps.worker.workflows.profile_workflow import ProfileWorkflow
from apps.worker.workflows.quality_workflow import QualityWorkflow
from apps.worker.workflows.types import IngestParams
from apps.workflows.models import Artifact, Job, PresetJob

logger = logging.getLogger(__name__)
settings = get_settings()

jobs_router = Router(tags=["jobs"])
presets_router = Router(tags=["presets"])
artifacts_router = Router(tags=["artifacts"])

_minio_client = None


def get_minio_client():
    global _minio_client
    if _minio_client is None:
        try:
            from minio import Minio

            _minio_client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
        except ImportError:
            logger.warning("MinIO package not installed")
        except Exception as exc:
            logger.error("MinIO connection failed: %s", exc)
    return _minio_client


class IngestRequest(Schema):
    source_id: str
    mode: str = "full"
    tables: Optional[List[str]] = None


class ProfileRequest(Schema):
    source_id: str
    table: Optional[str] = None
    sample_size: int = Field(10000, ge=100, le=1_000_000)


class QualityRequest(Schema):
    source_id: str
    table: Optional[str] = None
    checks: Optional[List[str]] = None


class JobResponse(Schema):
    job_id: str
    tenant_id: str
    job_type: str
    status: str
    progress: int
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class ArtifactInfo(Schema):
    artifact_id: str
    job_id: str
    artifact_type: str
    format: str
    storage_path: str
    size_bytes: Optional[int] = None
    created_at: str


class PresetInfo(Schema):
    name: str
    category: str
    description: str
    parameters: List[str]
    output_artifacts: List[str]


class KPITemplateInfo(Schema):
    name: str
    category: str
    description: str
    required_columns: List[str]


class RenderKPIRequest(Schema):
    params: Dict[str, str]


def _to_job_response(job: Job) -> JobResponse:
    return JobResponse(
        job_id=str(job.job_id),
        tenant_id=job.tenant_id,
        job_type=job.job_type,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        result_summary=job.result_summary,
        error_message=job.error_message,
    )


def _create_job(request, job_type: str, source_id: str, params: Dict[str, Any]) -> Job:
    tenant_id = get_tenant_id(request)
    soma_session_id = get_soma_session_id() or None
    job = Job.objects.create(
        tenant_id=tenant_id,
        job_type=job_type,
        source_id=source_id,
        soma_session_id=soma_session_id,
        status="queued",
        progress=0,
        parameters=params,
    )
    return job


def _validate_table_scope(tenant_id: str, tables: Optional[List[str]]) -> None:
    if not tables:
        return
    for table in tables:
        validate_table_access(tenant_id, table)


@jobs_router.post("/ingest", response=JobResponse)
def trigger_ingest(request, payload: IngestRequest):
    tenant_id = get_tenant_id(request)
    try:
        _validate_table_scope(tenant_id, payload.tables)
    except NamespaceViolationError as exc:
        raise HttpError(403, str(exc)) from exc

    policy_prompt = (
        f"voyant ingest source_id={payload.source_id} mode={payload.mode} "
        f"tables={payload.tables or []}"
    )
    apply_policy("ingest", policy_prompt, {"source_id": payload.source_id})

    job = _create_job(
        request,
        "ingest",
        payload.source_id,
        {"mode": payload.mode, "tables": payload.tables},
    )

    soma_task_id = run_async(
        create_task_for_job,
        str(job.job_id),
        job.job_type,
        job.source_id,
        policy_prompt,
    )
    if soma_task_id:
        Job.objects.filter(id=job.id).update(soma_task_id=soma_task_id)

    try:
        client = run_async(get_temporal_client)
        run_async(
            client.start_workflow,
            IngestDataWorkflow.run,
            IngestParams(
                job_id=str(job.job_id),
                source_id=payload.source_id,
                mode=payload.mode,
                tables=payload.tables,
            ),
            id=f"ingest-{job.job_id}",
            task_queue=settings.temporal_task_queue,
        )
        job.status = "running"
        job.save(update_fields=["status"])
        if soma_task_id:
            run_async(update_task_status, soma_task_id, "running")
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        if soma_task_id:
            run_async(update_task_status, soma_task_id, "failed", reason=str(exc))

    return _to_job_response(job)


@jobs_router.post("/profile", response=JobResponse)
def trigger_profile(request, payload: ProfileRequest):
    tenant_id = get_tenant_id(request)
    try:
        if payload.table:
            validate_table_access(tenant_id, payload.table)
    except NamespaceViolationError as exc:
        raise HttpError(403, str(exc)) from exc

    policy_prompt = (
        f"voyant profile source_id={payload.source_id} table={payload.table} "
        f"sample_size={payload.sample_size}"
    )
    apply_policy("profile", policy_prompt, {"source_id": payload.source_id})

    job = _create_job(
        request,
        "profile",
        payload.source_id,
        {"table": payload.table, "sample_size": payload.sample_size},
    )

    soma_task_id = run_async(
        create_task_for_job,
        str(job.job_id),
        job.job_type,
        job.source_id,
        policy_prompt,
    )
    if soma_task_id:
        Job.objects.filter(id=job.id).update(soma_task_id=soma_task_id)

    try:
        client = run_async(get_temporal_client)
        run_async(
            client.start_workflow,
            ProfileWorkflow.run,
            {
                "source_id": payload.source_id,
                "table": payload.table,
                "sample_size": payload.sample_size,
                "job_id": str(job.job_id),
                "tenant_id": tenant_id,
            },
            id=f"profile-{job.job_id}",
            task_queue=settings.temporal_task_queue,
        )
        job.status = "running"
        job.save(update_fields=["status"])
        if soma_task_id:
            run_async(update_task_status, soma_task_id, "running")
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        if soma_task_id:
            run_async(update_task_status, soma_task_id, "failed", reason=str(exc))

    return _to_job_response(job)


@jobs_router.post("/quality", response=JobResponse)
def trigger_quality(request, payload: QualityRequest):
    tenant_id = get_tenant_id(request)
    try:
        if payload.table:
            validate_table_access(tenant_id, payload.table)
    except NamespaceViolationError as exc:
        raise HttpError(403, str(exc)) from exc

    policy_prompt = (
        f"voyant quality source_id={payload.source_id} table={payload.table}"
    )
    apply_policy("quality", policy_prompt, {"source_id": payload.source_id})

    job = _create_job(
        request,
        "quality",
        payload.source_id,
        {"table": payload.table, "checks": payload.checks},
    )

    try:
        client = run_async(get_temporal_client)
        run_async(
            client.start_workflow,
            QualityWorkflow.run,
            {
                "source_id": payload.source_id,
                "table": payload.table,
                "checks": payload.checks,
                "job_id": str(job.job_id),
                "tenant_id": tenant_id,
            },
            id=f"quality-{job.job_id}",
            task_queue=settings.temporal_task_queue,
        )
        job.status = "running"
        job.save(update_fields=["status"])
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])

    return _to_job_response(job)


@jobs_router.get("", response=List[JobResponse])
def list_jobs(
    request,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50,
):
    tenant_id = get_tenant_id(request)
    query = Job.objects.filter(tenant_id=tenant_id)
    if status:
        query = query.filter(status=status)
    if job_type:
        query = query.filter(job_type=job_type)
    jobs = query.order_by("-created_at")[:limit]
    return [_to_job_response(job) for job in jobs]


@jobs_router.get("/{job_id}", response=JobResponse)
def get_job(request, job_id: str):
    tenant_id = get_tenant_id(request)
    job = Job.objects.filter(id=job_id, tenant_id=tenant_id).first()
    if not job:
        raise HttpError(404, "Job not found")
    return _to_job_response(job)


@jobs_router.post("/{job_id}/cancel", response=Dict[str, str])
def cancel_job(request, job_id: str):
    tenant_id = get_tenant_id(request)
    job = Job.objects.filter(id=job_id, tenant_id=tenant_id).first()
    if not job:
        raise HttpError(404, "Job not found")

    try:
        client = run_async(get_temporal_client)
        for prefix in ("ingest", "profile", "quality", "analyze"):
            try:
                handle = client.get_workflow_handle(f"{prefix}-{job_id}")
                run_async(handle.cancel)
                break
            except Exception:
                continue
    except Exception:
        pass

    job.status = "cancelled"
    job.save(update_fields=["status"])
    return {"status": "cancelled", "job_id": str(job.job_id)}


@artifacts_router.get("/{job_id}", response=Dict[str, List[ArtifactInfo]])
def list_artifacts(request, job_id: str):
    tenant_id = get_tenant_id(request)
    apply_policy(
        "artifact_list", f"voyant artifact list job_id={job_id}", {"job_id": job_id}
    )
    rows = Artifact.objects.filter(job_id=job_id, tenant_id=tenant_id).order_by(
        "-created_at"
    )
    artifacts = [
        ArtifactInfo(
            artifact_id=row.artifact_id,
            job_id=row.job_id,
            artifact_type=row.artifact_type,
            format=row.format,
            storage_path=row.storage_path,
            size_bytes=row.size_bytes,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
    return {"artifacts": artifacts}


@artifacts_router.get("/{job_id}/{artifact_type}/download")
def download_artifact(request, job_id: str, artifact_type: str, format: str = "json"):
    tenant_id = get_tenant_id(request)
    row = Artifact.objects.filter(
        tenant_id=tenant_id,
        job_id=job_id,
        artifact_type=artifact_type,
        format=format,
    ).first()
    if not row:
        raise HttpError(404, "Artifact not found")

    client = get_minio_client()
    if not client:
        raise HttpError(503, "Storage unavailable")

    object_name = row.storage_path
    try:
        response = client.get_object(settings.minio_bucket_name, object_name)
        data = response.read()
        return StreamingHttpResponse(
            io.BytesIO(data),
            content_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={artifact_type}.{format}"
            },
        )
    except Exception as exc:
        raise HttpError(404, f"Artifact download failed: {exc}") from exc


PRESETS: Dict[str, Dict[str, Any]] = {
    "quality.data_profiling": {
        "name": "Data Profiling",
        "category": "quality",
        "description": "Profile table quality and distribution",
        "parameters": ["source_id", "table", "sample_size"],
        "output_artifacts": ["profile"],
        "job_type": "profile",
    },
    "quality.data_checks": {
        "name": "Data Quality Checks",
        "category": "quality",
        "description": "Run quality checks for a table",
        "parameters": ["source_id", "table", "checks"],
        "output_artifacts": ["quality"],
        "job_type": "quality",
    },
}


@presets_router.get("", response=Dict[str, List[PresetInfo]])
def list_presets(request, category: Optional[str] = None):
    grouped: Dict[str, List[PresetInfo]] = {}
    for preset in PRESETS.values():
        if category and preset["category"] != category:
            continue
        grouped.setdefault(preset["category"], []).append(
            PresetInfo(
                **{
                    "name": preset["name"],
                    "category": preset["category"],
                    "description": preset["description"],
                    "parameters": preset["parameters"],
                    "output_artifacts": preset["output_artifacts"],
                }
            )
        )
    return grouped


@presets_router.get("/{preset_name}", response=PresetInfo)
def get_preset(request, preset_name: str):
    preset = PRESETS.get(preset_name)
    if not preset:
        raise HttpError(404, "Preset not found")
    return PresetInfo(
        name=preset["name"],
        category=preset["category"],
        description=preset["description"],
        parameters=preset["parameters"],
        output_artifacts=preset["output_artifacts"],
    )


@presets_router.post("/{preset_name}/execute", response=Dict[str, str])
def execute_preset(request, preset_name: str, payload: Dict[str, Any]):
    preset = PRESETS.get(preset_name)
    if not preset:
        raise HttpError(404, "Preset not found")

    job = PresetJob.objects.create(
        tenant_id=get_tenant_id(request),
        preset_name=preset_name,
        source_id=payload.get("source_id", ""),
        parameters=payload,
        status="queued",
    )
    return {"job_id": str(job.job_id), "status": job.status}


@presets_router.get("/kpi-templates", response=List[KPITemplateInfo])
def list_kpi_templates_endpoint(request):
    return [
        KPITemplateInfo(
            name=t["name"],
            category=t["category"],
            description=t["description"],
            required_columns=t["required_columns"],
        )
        for t in list_kpi_templates()
    ]


@presets_router.get("/kpi-templates/categories", response=List[str])
def list_kpi_template_categories(request):
    return get_kpi_categories()


@presets_router.get("/kpi-templates/{template_name}", response=Dict[str, Any])
def get_kpi_template_endpoint(request, template_name: str):
    template = get_kpi_template(template_name)
    if not template:
        raise HttpError(404, "KPI template not found")
    return {
        "name": template.name,
        "category": template.category,
        "description": template.description,
        "required_columns": template.required_columns,
        "optional_columns": template.optional_columns,
        "output_columns": template.output_columns,
        "sql": template.sql,
    }


@presets_router.post("/kpi-templates/{template_name}/render", response=Dict[str, str])
def render_kpi_template_endpoint(
    request, template_name: str, payload: RenderKPIRequest
):
    try:
        return {"sql": render_kpi_template(template_name, payload.params)}
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
