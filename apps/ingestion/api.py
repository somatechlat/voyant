"""Data ingestion REST API endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.core.api_utils import run_async
from apps.core.config import get_settings
from apps.core.middleware import get_tenant_id
from apps.core.lib.temporal_client import get_temporal_client
from apps.discovery.models import Source
from apps.ingestion.models import IngestionJob
from apps.worker.workflows.ingest_workflow import IngestDataWorkflow

logger = logging.getLogger(__name__)
settings = get_settings()

router = Router(tags=["Data Ingestion"])


class IngestRequest(Schema):
    """Request schema for starting a data ingestion job."""

    source_id: str = Field(..., description="The ID of the data source to ingest from")
    mode: str = Field(default="full", description="Ingestion mode: full|incremental")
    tables: Optional[List[str]] = Field(
        default=None,
        description="Optional list of table names to ingest",
    )


class JobResponse(Schema):
    """Response schema representing a job's status and details."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    progress: float = Field(..., description="Job progress (0.0 to 1.0)")
    stage: str = Field(..., description="Current execution stage")
    created_at: str = Field(..., description="Creation timestamp")


@router.post("/ingest", response=JobResponse, summary="Trigger a Data Ingestion Job")
def trigger_ingest(request: HttpRequest, payload: IngestRequest) -> JobResponse:
    """Start a data ingestion job for an existing Source."""
    tenant_id = get_tenant_id(request)

    try:
        source = Source.objects.get(id=payload.source_id, tenant_id=tenant_id)
    except Source.DoesNotExist as exc:
        raise HttpError(404, f"Source {payload.source_id} not found") from exc

    workflow_id = f"ingest-{uuid.uuid4()}"
    job = IngestionJob.objects.create(
        tenant_id=tenant_id,
        source=source,
        workflow_instance_id=workflow_id,
        status=IngestionJob.Status.PENDING,
        params={"mode": payload.mode, "tables": payload.tables or []},
    )

    try:
        client = run_async(get_temporal_client)
        run_async(
            client.start_workflow,
            IngestDataWorkflow.run,
            {
                "job_id": str(job.id),
                "source_id": str(source.id),
                "tenant_id": tenant_id,
                "mode": payload.mode,
                "tables": payload.tables,
            },
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )

        job.status = IngestionJob.Status.QUEUED
        job.save(update_fields=["status"])
        logger.info("Started ingestion job %s for source %s", job.id, source.id)

    except Exception as exc:
        logger.error("Failed to start ingestion workflow: %s", exc)
        job.status = IngestionJob.Status.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message"])
        raise HttpError(500, f"Failed to start ingestion: {exc}") from exc

    return JobResponse(
        job_id=str(job.id),
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        created_at=job.created_at.isoformat(),
    )


@router.get("/jobs", response=List[JobResponse], summary="List Ingestion Jobs")
def list_jobs(
    request: HttpRequest,
    source_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> List[JobResponse]:
    """List ingestion jobs for the current tenant."""
    tenant_id = get_tenant_id(request)

    jobs = IngestionJob.objects.filter(tenant_id=tenant_id)

    if source_id:
        jobs = jobs.filter(source_id=source_id)

    if status:
        jobs = jobs.filter(status=status)

    jobs = jobs.order_by("-created_at")[:limit]

    return [
        JobResponse(
            job_id=str(job.id),
            status=job.status,
            progress=job.progress,
            stage=job.stage,
            created_at=job.created_at.isoformat(),
        )
        for job in jobs
    ]


@router.get("/jobs/{job_id}", response=JobResponse, summary="Get Ingestion Job Status")
def get_job(request: HttpRequest, job_id: str) -> JobResponse:
    """Retrieve status of a specific ingestion job."""
    tenant_id = get_tenant_id(request)

    try:
        job = IngestionJob.objects.get(id=job_id, tenant_id=tenant_id)
    except IngestionJob.DoesNotExist as exc:
        raise HttpError(404, f"Job {job_id} not found") from exc

    return JobResponse(
        job_id=str(job.id),
        status=job.status,
        progress=job.progress,
        stage=job.stage,
        created_at=job.created_at.isoformat(),
    )


@router.post(
    "/jobs/{job_id}/cancel",
    response={200: Dict[str, str]},
    summary="Cancel Ingestion Job",
)
def cancel_job(request: HttpRequest, job_id: str) -> Dict[str, str]:
    """Cancel a running ingestion job."""
    tenant_id = get_tenant_id(request)

    try:
        job = IngestionJob.objects.get(id=job_id, tenant_id=tenant_id)
    except IngestionJob.DoesNotExist as exc:
        raise HttpError(404, f"Job {job_id} not found") from exc

    if job.status not in {
        IngestionJob.Status.PENDING,
        IngestionJob.Status.QUEUED,
        IngestionJob.Status.RUNNING,
    }:
        raise HttpError(400, f"Job {job_id} cannot be cancelled (status: {job.status})")

    try:
        client = run_async(get_temporal_client)
        handle = client.get_workflow_handle(job.workflow_instance_id)
        run_async(handle.cancel)

        job.status = IngestionJob.Status.CANCELLED
        job.save(update_fields=["status"])
        logger.info("Cancelled ingestion job %s", job_id)

    except Exception as exc:
        logger.error("Failed to cancel workflow: %s", exc)
        raise HttpError(500, f"Failed to cancel job: {exc}") from exc

    return {"message": f"Job {job_id} cancelled successfully"}
