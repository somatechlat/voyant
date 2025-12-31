"""
Voyant Scraper - Django Ninja API

REST API endpoints for web scraping operations.
Uses Temporal workflows for durable execution.
"""
from typing import List, Dict, Any, Optional
from ninja import Router, Schema
from django.shortcuts import get_object_or_404
from asgiref.sync import async_to_sync

from voyant.core.config import get_settings
from voyant.core.temporal_client import get_temporal_client

from .models import ScrapeJob, ScrapeArtifact
from .workflow import ScrapeWorkflow

settings = get_settings()
scrape_router = Router(tags=["scrape"])


# ============================================================================
# Schemas
# ============================================================================

class ScrapeStartSchema(Schema):
    """Request schema for starting a scrape job."""
    urls: List[str]
    llm_prompt: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class ScrapeJobSchema(Schema):
    """Response schema for scrape job."""
    job_id: str
    status: str
    pages_fetched: int
    bytes_processed: int
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error_message: Optional[str] = None


class ScrapeArtifactSchema(Schema):
    """Response schema for scrape artifact."""
    artifact_id: str
    artifact_type: str
    format: str
    storage_path: str
    size_bytes: Optional[int] = None


class ScrapeResultSchema(Schema):
    """Response schema for scrape results."""
    job_id: str
    status: str
    artifacts: List[ScrapeArtifactSchema]


# ============================================================================
# Helper Functions
# ============================================================================

def _run_async(func, *args, **kwargs):
    """Run async function synchronously."""
    return async_to_sync(func)(*args, **kwargs)


def _start_scrape_workflow(job_id: str, urls: List[str], llm_prompt: str, options: dict, tenant_id: str):
    """Start Temporal workflow for scraping."""
    client = _run_async(get_temporal_client)
    _run_async(
        client.start_workflow,
        ScrapeWorkflow.run,
        {
            "job_id": job_id,
            "urls": urls,
            "llm_prompt": llm_prompt,
            "options": options,
            "tenant_id": tenant_id,
        },
        id=f"scrape-{job_id}",
        task_queue=settings.temporal_task_queue,
    )


# ============================================================================
# Endpoints
# ============================================================================

@scrape_router.post("/scrape/start", response={202: ScrapeJobSchema})
def start_scrape(request, payload: ScrapeStartSchema):
    """
    Start a new web scraping job.
    
    Options:
    - engine: playwright | selenium | scrapy | beautifulsoup
    - ocr: true/false - Enable OCR for images
    - media: true/false - Extract media files
    - llm_selectors: true/false - Use LLM for selector generation
    """
    tenant_id = request.headers.get('X-Tenant-ID', 'default')
    
    job = ScrapeJob.objects.create(
        tenant_id=tenant_id,
        urls=payload.urls,
        llm_prompt=payload.llm_prompt or "",
        options=payload.options or {},
    )
    
    # Start Temporal workflow
    try:
        _start_scrape_workflow(
            job_id=str(job.job_id),
            urls=payload.urls,
            llm_prompt=payload.llm_prompt or "",
            options=payload.options or {},
            tenant_id=tenant_id,
        )
        job.status = ScrapeJob.Status.RUNNING
        job.save(update_fields=['status'])
    except Exception as e:
        job.status = ScrapeJob.Status.FAILED
        job.error_message = str(e)
        job.save(update_fields=['status', 'error_message'])
    
    return 202, {
        'job_id': str(job.job_id),
        'status': job.status,
        'pages_fetched': 0,
        'bytes_processed': 0,
        'created_at': job.created_at.isoformat(),
    }


@scrape_router.get("/scrape/status/{job_id}", response=ScrapeJobSchema)
def get_scrape_status(request, job_id: str):
    """Get status of a scraping job."""
    job = get_object_or_404(ScrapeJob, job_id=job_id)
    
    return {
        'job_id': str(job.job_id),
        'status': job.status,
        'pages_fetched': job.pages_fetched,
        'bytes_processed': job.bytes_processed,
        'created_at': job.created_at.isoformat(),
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'finished_at': job.finished_at.isoformat() if job.finished_at else None,
        'error_message': job.error_message or None,
    }


@scrape_router.post("/scrape/cancel")
def cancel_scrape(request, job_id: str):
    """Cancel a running scrape job."""
    job = get_object_or_404(ScrapeJob, job_id=job_id)
    job.status = ScrapeJob.Status.CANCELLED
    job.save()
    
    # TODO: Cancel Temporal workflow via client.cancel_workflow()
    
    return {"status": "cancelled", "job_id": str(job.job_id)}


@scrape_router.get("/scrape/result/{job_id}", response=ScrapeResultSchema)
def get_scrape_result(request, job_id: str, format: str = "json"):
    """Get results of a completed scrape job."""
    job = get_object_or_404(ScrapeJob, job_id=job_id)
    artifacts = ScrapeArtifact.objects.filter(job=job)
    
    return {
        "job_id": str(job.job_id),
        "status": job.status,
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "artifact_type": a.artifact_type,
                "format": a.format,
                "storage_path": a.storage_path,
                "size_bytes": a.size_bytes,
            }
            for a in artifacts
        ]
    }


@scrape_router.get("/scrape/metrics/{job_id}")
def get_scrape_metrics(request, job_id: str):
    """Get metrics for a scrape job."""
    job = get_object_or_404(ScrapeJob, job_id=job_id)
    
    return {
        "job_id": str(job.job_id),
        "pages_fetched": job.pages_fetched,
        "bytes_processed": job.bytes_processed,
        "ocr_success_rate": job.ocr_success_rate,
        "retry_count": job.retry_count,
    }
