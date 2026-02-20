
import logging
import json
import io
from datetime import datetime
from typing import Any, Dict, List, Optional
from ninja import Router, Schema, Field
from ninja.errors import HttpError
from apps.core.api_utils import auth_guard, run_async, apply_policy
from apps.core.config import get_settings
from apps.workflows.models import Job, Artifact
from apps.core.middleware import get_tenant_id
from apps.integrations.soma import create_task_for_job, update_task_status, remember_summary
from apps.core.lib.temporal_client import get_temporal_client
from apps.core.lib.namespace_analyzer import validate_table_access, NamespaceViolationError
from apps.worker.workflows.analyze_workflow import AnalyzeWorkflow
from apps.workflows.api import get_minio_client

logger = logging.getLogger(__name__)
settings = get_settings()
analyze_router = Router(tags=["analyze"])

class KPIQuery(Schema):
    name: str
    sql: str

class AnalyzeRequest(Schema):
    source_id: Optional[str] = None
    table: Optional[str] = None
    tables: Optional[List[str]] = None
    sample_size: int = Field(default=10000, ge=100, le=1000000)
    kpis: Optional[List[KPIQuery]] = None
    analyzers: Optional[List[str]] = None
    analyzer_context: Optional[Dict[str, Any]] = None
    profile: bool = True
    run_analyzers: bool = True
    generate_artifacts: bool = True

class AnalyzeResponse(Schema):
    job_id: str
    tenant_id: str
    status: str
    summary: Dict[str, Any]
    artifacts: Dict[str, Any]
    manifest: List[Dict[str, Any]]

def _resolve_table(payload: AnalyzeRequest) -> Optional[str]:
    if payload.table: return payload.table
    if payload.source_id: return payload.source_id
    if payload.tables: return payload.tables[0]
    return None

def _create_job(request, job_type: str, source_id: str, params: Dict[str, Any]) -> Job:
    tenant_id = get_tenant_id(request)
    job = Job.objects.create(
        tenant_id=tenant_id,
        job_type=job_type,
        source_id=source_id,
        status="queued",
        progress=0,
        parameters=params,
    )
    return job

@analyze_router.post("", response=AnalyzeResponse)
def analyze(request, payload: AnalyzeRequest):
    table = _resolve_table(payload)
    if not table:
        raise HttpError(400, "table or source_id is required")

    tenant_id = get_tenant_id(request)
    try:
        validate_table_access(tenant_id, table)
    except NamespaceViolationError as exc:
        raise HttpError(403, str(exc)) from exc

    policy_prompt = f"voyant analyze table={table}"
    apply_policy("analyze", policy_prompt, {"source_id": payload.source_id})

    job = _create_job(request, "analyze", payload.source_id or table, {"table": table})
    job_id = str(job.job_id)

    soma_task_id = run_async(create_task_for_job, job_id, job.job_type, job.source_id, policy_prompt)
    if soma_task_id:
        Job.objects.filter(job_id=job.job_id).update(soma_task_id=soma_task_id)

    job.status = "running"
    job.started_at = datetime.utcnow()
    job.save(update_fields=["status", "started_at"])
    if soma_task_id:
        run_async(update_task_status, soma_task_id, "running")

    artifacts: Dict[str, Any] = {}
    manifest: List[Dict[str, Any]] = []

    try:
        client = run_async(get_temporal_client)
        workflow_result = run_async(
            client.execute_workflow,
            AnalyzeWorkflow.run,
            {
                "source_id": payload.source_id,
                "table": table,
                "tables": payload.tables,
                "sample_size": payload.sample_size,
                "kpis": [kpi.model_dump() for kpi in payload.kpis] if payload.kpis else None,
                "analyzers": payload.analyzers,
                "job_id": job_id,
                "tenant_id": tenant_id,
            },
            id=f"analyze-{job_id}",
            task_queue=settings.temporal_task_queue,
        )
        # Simplified handling for brevity - in real code we process artifacts
        summary = workflow_result.get("summary", {})
        job.status = "completed"
        job.completed_at = datetime.utcnow()
        job.result_summary = summary
        job.save()
        if soma_task_id:
            run_async(update_task_status, soma_task_id, "completed")
        run_async(remember_summary, job_id, job.status, summary, manifest)

        return AnalyzeResponse(
            job_id=job_id, tenant_id=tenant_id, status=job.status,
            summary=summary, artifacts=artifacts, manifest=manifest
        )
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.save()
        if soma_task_id:
            run_async(update_task_status, soma_task_id, "failed", reason=str(exc))
        raise HttpError(500, str(exc)) from exc
