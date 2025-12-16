"""
Jobs API Routes

Endpoints for job management (ingest, profile, quality, etc.)
"""
from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from voyant.api.middleware import get_tenant_id
from voyant.core.temporal import get_temporal_client
from voyant.workflows.ingest_workflow import IngestWorkflow
from voyant.workflows.types import IngestParams

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/jobs")


# =============================================================================
# Models
# =============================================================================

class IngestRequest(BaseModel):
    source_id: str
    mode: str = Field(default="full", description="full or incremental")
    tables: Optional[List[str]] = None


class ProfileRequest(BaseModel):
    source_id: str
    table: Optional[str] = None
    sample_size: int = Field(default=10000, ge=100, le=1000000)


class QualityRequest(BaseModel):
    source_id: str
    table: Optional[str] = None
    checks: Optional[List[str]] = None


class JobResponse(BaseModel):
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


# =============================================================================
# In-memory store (will be PostgreSQL + Celery)
# =============================================================================

_jobs: Dict[str, Dict[str, Any]] = {}


def _create_job(job_type: str, source_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new job record."""
    job_id = str(uuid.uuid4())
    tenant_id = get_tenant_id()
    now = datetime.utcnow().isoformat()
    
    job = {
        "job_id": job_id,
        "tenant_id": tenant_id,
        "job_type": job_type,
        "source_id": source_id,
        "status": "queued",
        "progress": 0,
        "parameters": params,
        "created_at": now,
    }
    
    _jobs[job_id] = job
    logger.info(f"Created {job_type} job {job_id} for source {source_id}")
    return job


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/ingest", response_model=JobResponse)
async def trigger_ingest(request: IngestRequest, background_tasks: BackgroundTasks):
    """Trigger data ingestion via Apache Beam/Airbyte."""
    job = _create_job("ingest", request.source_id, {
        "mode": request.mode,
        "tables": request.tables,
    })
    
    # Trigger Temporal Workflow
    try:
        client = await get_temporal_client()
        await client.start_workflow(
            IngestWorkflow.run,
            IngestParams(
                job_id=job["job_id"],
                source_id=request.source_id,
                mode=request.mode,
                tables=request.tables
            ),
            id=f"ingest-{job['job_id']}",
            task_queue="voyant-tasks",
        )
        job["status"] = "running" # Optimistic update
    except Exception as e:
        logger.error(f"Failed to start workflow: {e}")
        job["status"] = "failed"
        job["error_message"] = str(e)

    return JobResponse(
        job_id=job["job_id"],
        tenant_id=job["tenant_id"],
        job_type=job["job_type"],
        status=job["status"],
        progress=job["progress"],
        created_at=job["created_at"],
    )


@router.post("/profile", response_model=JobResponse)
async def trigger_profile(request: ProfileRequest, background_tasks: BackgroundTasks):
    """Trigger data profiling via ydata-profiling."""
    job = _create_job("profile", request.source_id, {
        "table": request.table,
        "sample_size": request.sample_size,
    })
    
    return JobResponse(
        job_id=job["job_id"],
        tenant_id=job["tenant_id"],
        job_type=job["job_type"],
        status=job["status"],
        progress=job["progress"],
        created_at=job["created_at"],
    )


@router.post("/quality", response_model=JobResponse)
async def trigger_quality(request: QualityRequest, background_tasks: BackgroundTasks):
    """Trigger data quality checks via Great Expectations."""
    job = _create_job("quality", request.source_id, {
        "table": request.table,
        "checks": request.checks,
    })
    
    return JobResponse(
        job_id=job["job_id"],
        tenant_id=job["tenant_id"],
        job_type=job["job_type"],
        status=job["status"],
        progress=job["progress"],
        created_at=job["created_at"],
    )


@router.get("", response_model=List[JobResponse])
async def list_jobs(status: Optional[str] = None, job_type: Optional[str] = None, limit: int = 50):
    """List jobs for current tenant."""
    tenant_id = get_tenant_id()
    jobs = [j for j in _jobs.values() if j["tenant_id"] == tenant_id]
    
    if status:
        jobs = [j for j in jobs if j["status"] == status]
    if job_type:
        jobs = [j for j in jobs if j["job_type"] == job_type]
    
    jobs.sort(key=lambda x: x["created_at"], reverse=True)
    
    return [
        JobResponse(
            job_id=j["job_id"],
            tenant_id=j["tenant_id"],
            job_type=j["job_type"],
            status=j["status"],
            progress=j["progress"],
            created_at=j["created_at"],
            started_at=j.get("started_at"),
            completed_at=j.get("completed_at"),
            result_summary=j.get("result_summary"),
            error_message=j.get("error_message"),
        )
        for j in jobs[:limit]
    ]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get job status by ID."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    j = _jobs[job_id]
    tenant_id = get_tenant_id()
    
    if j["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return JobResponse(
        job_id=j["job_id"],
        tenant_id=j["tenant_id"],
        job_type=j["job_type"],
        status=j["status"],
        progress=j["progress"],
        created_at=j["created_at"],
        started_at=j.get("started_at"),
        completed_at=j.get("completed_at"),
        result_summary=j.get("result_summary"),
        error_message=j.get("error_message"),
    )


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel a running job."""
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    j = _jobs[job_id]
    tenant_id = get_tenant_id()
    
    if j["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if j["status"] not in ("queued", "running"):
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")
    
    j["status"] = "cancelled"
    j["completed_at"] = datetime.utcnow().isoformat()
    
    logger.info(f"Cancelled job {job_id}")
    return {"status": "cancelled", "job_id": job_id}
