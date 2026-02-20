"""Data ingestion REST API endpoints."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, List, Optional

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError
from pydantic import Field

from apps.ingestion.models import IngestionJob, Source
from apps.core.middleware import get_tenant_id
from apps.core.lib.temporal_client import get_temporal_client
from apps.workflows.ingest_workflow import IngestDataWorkflow
from apps.worker.workflows.types import IngestParams

logger = logging.getLogger(__name__)

# Router for ingestion endpoints
router = Router(tags=["Data Ingestion"])


# =============================================================================
# Request/Response Schemas
# =============================================================================


class DiscoverRequest(Schema):
    """Request schema for discovering a data source type from a hint."""

    hint: str = Field(..., description="URL, connection string, or file path hint")


class DiscoverResponse(Schema):
    """Response schema after discovering a data source."""

    source_type: str = Field(..., description="Detected source type")
    confidence: float = Field(..., description="Confidence score (0.0 to 1.0)")
    suggested_config: Dict[str, Any] = Field(..., description="Suggested configuration")


class CreateSourceRequest(Schema):
    """Request schema for creating a new data source."""

    name: str = Field(..., description="Human-readable name for the source")
    source_type: str = Field(..., description="Type of data source")
    config: Dict[str, Any] = Field(..., description="Source configuration")


class SourceResponse(Schema):
    """Response schema representing a data source resource."""

    source_id: str = Field(..., description="Unique source identifier")
    name: str = Field(..., description="Source name")
    source_type: str = Field(..., description="Source type")
    status: str = Field(..., description="Connection status")
    created_at: str = Field(..., description="Creation timestamp")


class IngestRequest(Schema):
    """Request schema for starting a data ingestion job."""

    source_id: str = Field(..., description="The ID of the data source to ingest from")
    params: Optional[Dict[str, Any]] = Field(
        default=None, description="Ingestion parameters"
    )


class JobResponse(Schema):
    """Response schema representing a job's status and details."""

    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Job status")
    progress: float = Field(..., description="Job progress (0.0 to 1.0)")
    stage: str = Field(..., description="Current execution stage")
    created_at: str = Field(..., description="Creation timestamp")


# =============================================================================
# Helper Functions
# =============================================================================


def _detect_source_type(hint: str) -> Dict[str, Any]:
    """
    Detect data source type from a hint string.

    Args:
        hint: URL, connection string, or file path

    Returns:
        Dictionary with source_type, confidence, and suggested_config
    """
    hint_lower = hint.lower()

    # PostgreSQL detection
    if "postgresql://" in hint_lower or "postgres://" in hint_lower:
        return {
            "source_type": "postgres",
            "confidence": 0.95,
            "suggested_config": {"connection_string": hint},
        }

    # MySQL detection
    if "mysql://" in hint_lower:
        return {
            "source_type": "mysql",
            "confidence": 0.95,
            "suggested_config": {"connection_string": hint},
        }

    # MongoDB detection
    if "mongodb://" in hint_lower or "mongodb+srv://" in hint_lower:
        return {
            "source_type": "mongodb",
            "confidence": 0.95,
            "suggested_config": {"connection_string": hint},
        }

    # REST API detection
    if hint_lower.startswith("http://") or hint_lower.startswith("https://"):
        return {
            "source_type": "rest_api",
            "confidence": 0.7,
            "suggested_config": {"base_url": hint},
        }

    # File detection
    if hint_lower.endswith(".csv"):
        return {
            "source_type": "csv",
            "confidence": 0.9,
            "suggested_config": {"file_path": hint},
        }

    if hint_lower.endswith(".json"):
        return {
            "source_type": "json",
            "confidence": 0.9,
            "suggested_config": {"file_path": hint},
        }

    if hint_lower.endswith(".parquet"):
        return {
            "source_type": "parquet",
            "confidence": 0.9,
            "suggested_config": {"file_path": hint},
        }

    # S3 detection
    if "s3://" in hint_lower or "s3a://" in hint_lower:
        return {
            "source_type": "s3",
            "confidence": 0.9,
            "suggested_config": {"s3_path": hint},
        }

    # Unknown
    return {
        "source_type": "unknown",
        "confidence": 0.0,
        "suggested_config": {},
    }


# =============================================================================
# API Endpoints
# =============================================================================


@router.post(
    "/discover", response=DiscoverResponse, summary="Discover Data Source Type"
)
def discover_source(request: HttpRequest, payload: DiscoverRequest) -> DiscoverResponse:
    """
    Analyze a hint string to detect the data source type.

    This endpoint helps agents automatically identify the type of data source
    from a URL, connection string, or file path.
    """
    result = _detect_source_type(payload.hint)
    return DiscoverResponse(**result)


@router.post("", response={201: SourceResponse}, summary="Create a New Data Source")
def create_source(
    request: HttpRequest, payload: CreateSourceRequest
) -> tuple[int, SourceResponse]:
    """
    Register a new data source in Voyant.

    Creates a Source record that can be used for ingestion operations.
    """
    tenant_id = get_tenant_id(request)

    # Create source
    source = Source.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        source_type=payload.source_type,
        config=payload.config,
        status=Source.Status.ACTIVE,
    )

    logger.info(f"Created source {source.id} for tenant {tenant_id}")

    return 201, SourceResponse(
        source_id=str(source.id),
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        created_at=source.created_at.isoformat(),
    )


@router.get("", response=List[SourceResponse], summary="List All Data Sources")
def list_sources(request: HttpRequest) -> List[SourceResponse]:
    """
    List all data sources for the current tenant.

    Returns all registered data sources with their current status.
    """
    tenant_id = get_tenant_id(request)

    sources = Source.objects.filter(tenant_id=tenant_id).order_by("-created_at")

    return [
        SourceResponse(
            source_id=str(source.id),
            name=source.name,
            source_type=source.source_type,
            status=source.status,
            created_at=source.created_at.isoformat(),
        )
        for source in sources
    ]


@router.get(
    "/{source_id}", response=SourceResponse, summary="Get a Specific Data Source"
)
def get_source(request: HttpRequest, source_id: str) -> SourceResponse:
    """
    Retrieve details of a specific data source.

    Returns the source configuration and current status.
    """
    tenant_id = get_tenant_id(request)

    try:
        source = Source.objects.get(id=source_id, tenant_id=tenant_id)
    except Source.DoesNotExist:
        raise HttpError(404, f"Source {source_id} not found")

    return SourceResponse(
        source_id=str(source.id),
        name=source.name,
        source_type=source.source_type,
        status=source.status,
        created_at=source.created_at.isoformat(),
    )


@router.delete(
    "/{source_id}", response={200: Dict[str, str]}, summary="Delete a Data Source"
)
def delete_source(request: HttpRequest, source_id: str) -> Dict[str, str]:
    """
    Delete a data source.

    Removes the source and all associated ingestion jobs.
    """
    tenant_id = get_tenant_id(request)

    try:
        source = Source.objects.get(id=source_id, tenant_id=tenant_id)
    except Source.DoesNotExist:
        raise HttpError(404, f"Source {source_id} not found")

    source.delete()
    logger.info(f"Deleted source {source_id} for tenant {tenant_id}")

    return {"message": f"Source {source_id} deleted successfully"}


@router.post("/ingest", response=JobResponse, summary="Trigger a Data Ingestion Job")
def trigger_ingest(request: HttpRequest, payload: IngestRequest) -> JobResponse:
    """
    Start a data ingestion job for a specific source.

    Creates an ingestion job and triggers a Temporal workflow to execute it.
    The endpoint returns immediately with the job ID.
    """
    tenant_id = get_tenant_id(request)

    # Validate source exists
    try:
        source = Source.objects.get(id=payload.source_id, tenant_id=tenant_id)
    except Source.DoesNotExist:
        raise HttpError(404, f"Source {payload.source_id} not found")

    # Create job record
    workflow_id = f"ingest-{uuid.uuid4()}"
    job = IngestionJob.objects.create(
        tenant_id=tenant_id,
        source=source,
        workflow_instance_id=workflow_id,
        status=IngestionJob.Status.PENDING,
        params=payload.params or {},
    )

    # Trigger Temporal workflow
    try:
        client = get_temporal_client()
        params = IngestParams(
            source_id=str(source.id),
            tenant_id=tenant_id,
            job_id=str(job.id),
            config=source.config,
            params=payload.params or {},
        )

        client.start_workflow(
            IngestDataWorkflow.run,
            params,
            id=workflow_id,
            task_queue="voyant-workflows",
        )

        job.status = IngestionJob.Status.QUEUED
        job.save()

        logger.info(f"Started ingestion job {job.id} for source {source.id}")

    except Exception as e:
        logger.error(f"Failed to start ingestion workflow: {e}")
        job.status = IngestionJob.Status.FAILED
        job.error_message = str(e)
        job.save()
        raise HttpError(500, f"Failed to start ingestion: {e}")

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
    """
    List ingestion jobs for the current tenant.

    Optionally filter by source ID and status.
    """
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
    """
    Retrieve the status of a specific ingestion job.

    Returns current progress, stage, and execution details.
    """
    tenant_id = get_tenant_id(request)

    try:
        job = IngestionJob.objects.get(id=job_id, tenant_id=tenant_id)
    except IngestionJob.DoesNotExist:
        raise HttpError(404, f"Job {job_id} not found")

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
    """
    Cancel a running ingestion job.

    Sends a cancellation signal to the Temporal workflow.
    """
    tenant_id = get_tenant_id(request)

    try:
        job = IngestionJob.objects.get(id=job_id, tenant_id=tenant_id)
    except IngestionJob.DoesNotExist:
        raise HttpError(404, f"Job {job_id} not found")

    if job.status not in [
        IngestionJob.Status.PENDING,
        IngestionJob.Status.QUEUED,
        IngestionJob.Status.RUNNING,
    ]:
        raise HttpError(400, f"Job {job_id} cannot be cancelled (status: {job.status})")

    # Cancel Temporal workflow
    try:
        client = get_temporal_client()
        client.cancel_workflow(job.workflow_instance_id)

        job.status = IngestionJob.Status.CANCELLED
        job.save()

        logger.info(f"Cancelled ingestion job {job_id}")

    except Exception as e:
        logger.error(f"Failed to cancel workflow: {e}")
        raise HttpError(500, f"Failed to cancel job: {e}")

    return {"message": f"Job {job_id} cancelled successfully"}
