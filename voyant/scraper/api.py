
"""Voyant Scraper - API Endpoints.

This module defines the REST API endpoints for the web scraping service,
built using Django Ninja. The API exposes "pure execution" tools that
are controlled by an external intelligent agent, following an Agent-Tool Architecture.
"""


from typing import Any, Dict, List, Optional

from asgiref.sync import async_to_sync
from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from voyant.core.config import get_settings

# Lazy imports - avoid importing Django models at module level
# This prevents AppRegistryNotReady errors when module is loaded
# Models are imported inside functions that use them

settings = get_settings()
scrape_router = Router(tags=["scrape"])


# ============================================================================
# Schemas (Pure Execution - No LLM)
# ============================================================================


class ScrapeStartSchema(Schema):
    """Request schema for starting a scrape job."""

    urls: List[str]
    selectors: Optional[Dict[str, Any]] = None  # Agent-provided selectors
    options: Optional[Dict[str, Any]] = None


class ScrapeExtractSchema(Schema):
    """Request schema for extracting data from HTML."""

    html: str
    selectors: Dict[str, Any]  # Agent-provided CSS/XPath


class ScrapeOcrSchema(Schema):
    """Request schema for OCR processing."""

    image_url: str
    language: str = settings.scraper_default_ocr_language


class ScrapePdfSchema(Schema):
    """Request schema for PDF parsing."""

    pdf_url: str
    extract_tables: bool = False


class ScrapeTranscribeSchema(Schema):
    """Request schema for audio transcription."""

    media_url: str
    language: str = settings.scraper_default_transcribe_language


class ScrapeFetchSchema(Schema):
    """Request schema for fetching a web page."""

    url: str
    engine: str = settings.scraper_default_engine
    wait_for: Optional[str] = None
    scroll: bool = False
    timeout: int = settings.scraper_default_timeout_seconds
    wait_until: Optional[str] = None
    settle_ms: Optional[int] = None
    block_resources: Optional[bool] = None
    capture_json: bool = False
    capture_url_contains: Optional[List[str]] = None
    capture_max_bytes: Optional[int] = None
    capture_max_items: Optional[int] = None


class ScrapeJobSchema(Schema):
    """Response schema for scrape job."""

    job_id: str
    status: str
    pages_fetched: int
    bytes_processed: int
    artifact_count: int
    error_count: int
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
    content_hash: Optional[str] = None


class ScrapeResultSchema(Schema):
    """Response schema for scrape results."""

    job_id: str
    status: str
    artifacts: List[ScrapeArtifactSchema]


# ============================================================================
# Helper Functions (Lazy Imports)
# ============================================================================


def _get_models():
    """Lazy import of Django models to avoid AppRegistryNotReady."""
    from .models import ScrapeArtifact, ScrapeJob

    return ScrapeJob, ScrapeArtifact


def _get_security():
    """Lazy import of security module."""
    from .security import SSRFError, validate_url, validate_urls

    return validate_url, validate_urls, SSRFError


def _run_async(func, *args, **kwargs):
    """Run async function synchronously."""
    return async_to_sync(func)(*args, **kwargs)


def _start_scrape_workflow(
    job_id: str,
    urls: List[str],
    selectors: Optional[Dict],
    options: dict,
    tenant_id: str,
):
    """Start Temporal workflow for scraping (pure execution)."""
    from voyant.core.temporal_client import get_temporal_client

    from .workflow import ScrapeWorkflow

    client = _run_async(get_temporal_client)
    _run_async(
        client.start_workflow,
        ScrapeWorkflow.run,
        {
            "job_id": job_id,
            "urls": urls,
            "selectors": selectors,  # Agent-provided, not LLM-generated
            "options": options,
            "tenant_id": tenant_id,
        },
        id=f"scrape-{job_id}",
        task_queue=settings.temporal_task_queue,
    )


# ============================================================================
# Endpoints (Pure Execution Tools)
# ============================================================================


@scrape_router.post("/start", response={202: ScrapeJobSchema})
def start_scrape(request, payload: ScrapeStartSchema):
    """
    Start a new web scraping job.

    Pure execution - Agent provides URLs and optional selectors.

    Options:
    - engine: playwright | scrapy | httpx (default: playwright)
    - timeout: seconds (default: 30)
    - scroll: true/false - Scroll page before capture
    - wait_for: CSS selector to wait for
    - ocr: true/false - Enable OCR for images found
    - transcribe: true/false - Enable transcription for media
    """
    ScrapeJob, _ = _get_models()
    validate_url, validate_urls, SSRFError = _get_security()

    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)

    # Validate all URLs (SSRF protection - Security Auditor)
    try:
        validated_urls = validate_urls(payload.urls)
    except SSRFError as e:
        return 400, {"error": str(e)}

    job = ScrapeJob.objects.create(
        tenant_id=tenant_id,
        urls=validated_urls,
        selectors=payload.selectors,
        options=payload.options or {},
    )

    # Start Temporal workflow
    try:
        _start_scrape_workflow(
            job_id=str(job.job_id),
            urls=validated_urls,
            selectors=payload.selectors,
            options=payload.options or {},
            tenant_id=tenant_id,
        )
        job.status = ScrapeJob.Status.RUNNING
        job.save(update_fields=["status"])
    except Exception as e:
        job.status = ScrapeJob.Status.FAILED
        job.error_message = str(e)
        job.save(update_fields=["status", "error_message"])

    return 202, {
        "job_id": str(job.job_id),
        "status": job.status,
        "pages_fetched": 0,
        "bytes_processed": 0,
        "artifact_count": 0,
        "error_count": 0,
        "created_at": job.created_at.isoformat(),
    }


@scrape_router.post("/extract")
def extract_data(request, payload: ScrapeExtractSchema):
    """
    Extract data from HTML using agent-provided selectors.

    Pure execution - no LLM, just CSS/XPath parsing.
    """
    from lxml import html as lxml_html
    from lxml.cssselect import CSSSelector

    try:
        tree = lxml_html.fromstring(payload.html)
    except Exception as e:
        return 400, {"error": f"Invalid HTML: {e}"}

    result = {}
    for field, selector in payload.selectors.items():
        try:
            if isinstance(selector, str):
                if selector.startswith("//"):
                    # XPath
                    result[field] = tree.xpath(selector)
                else:
                    # CSS
                    sel = CSSSelector(selector)
                    elements = sel(tree)
                    result[field] = [el.text_content().strip() for el in elements]
        except Exception as e:
            result[field] = {"error": str(e)}

    return result


@scrape_router.post("/fetch")
def fetch_page(request, payload: ScrapeFetchSchema):
    """Fetch a page using a selected engine with SSRF validation."""
    from .activities import ScrapeActivities

    activity_runner = ScrapeActivities()
    return _run_async(
        activity_runner.fetch_page,
        {
            "url": payload.url,
            "engine": payload.engine,
            "wait_for": payload.wait_for,
            "scroll": payload.scroll,
            "timeout": payload.timeout,
            "wait_until": payload.wait_until,
            "settle_ms": payload.settle_ms,
            "block_resources": payload.block_resources,
            "capture_json": payload.capture_json,
            "capture_url_contains": payload.capture_url_contains,
            "capture_max_bytes": payload.capture_max_bytes,
            "capture_max_items": payload.capture_max_items,
        },
    )


@scrape_router.post("/ocr")
def process_ocr(request, payload: ScrapeOcrSchema):
    """Run OCR for a single image URL or path."""
    from .activities import ScrapeActivities

    activity_runner = ScrapeActivities()
    return _run_async(
        activity_runner.process_ocr,
        {"images": [payload.image_url], "language": payload.language},
    )


@scrape_router.post("/parse_pdf")
def parse_pdf(request, payload: ScrapePdfSchema):
    """Extract text and optional tables from a PDF."""
    from .activities import ScrapeActivities

    activity_runner = ScrapeActivities()
    return _run_async(
        activity_runner.parse_pdf,
        {"pdf_url": payload.pdf_url, "extract_tables": payload.extract_tables},
    )


@scrape_router.post("/transcribe")
def transcribe_media(request, payload: ScrapeTranscribeSchema):
    """Transcribe one media URL and return text segments."""
    from .activities import ScrapeActivities

    if not settings.scraper_enable_transcribe:
        return 503, {"error_code": "TRANSCRIPTION_DISABLED"}

    activity_runner = ScrapeActivities()
    return _run_async(
        activity_runner.transcribe_media,
        {"media_urls": [payload.media_url], "language": payload.language},
    )


@scrape_router.get("/status/{job_id}", response=ScrapeJobSchema)
def get_scrape_status(request, job_id: str):
    """Get status of a scraping job."""
    ScrapeJob, _ = _get_models()
    job = get_object_or_404(ScrapeJob, job_id=job_id)

    return {
        "job_id": str(job.job_id),
        "status": job.status,
        "pages_fetched": job.pages_fetched,
        "bytes_processed": job.bytes_processed,
        "artifact_count": job.artifact_count,
        "error_count": job.error_count,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        "error_message": job.error_message or None,
    }


@scrape_router.post("/cancel")
def cancel_scrape(request, job_id: str):
    """Cancel a running scrape job."""
    ScrapeJob, _ = _get_models()
    job = get_object_or_404(ScrapeJob, job_id=job_id)

    # Cancel workflow execution when a running scrape is stopped.
    try:
        from voyant.core.temporal_client import get_temporal_client

        client = _run_async(get_temporal_client)
        handle = client.get_workflow_handle(f"scrape-{job_id}")
        _run_async(handle.cancel)
    except Exception:
        # Keep cancellation idempotent even if workflow handle is already closed/missing.
        pass

    job.status = ScrapeJob.Status.CANCELLED
    job.save()

    return {"status": "cancelled", "job_id": str(job.job_id)}


@scrape_router.get("/result/{job_id}", response=ScrapeResultSchema)
def get_scrape_result(request, job_id: str):
    """Get results of a completed scrape job."""
    ScrapeJob, ScrapeArtifact = _get_models()
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
                "content_hash": a.content_hash,
            }
            for a in artifacts
        ],
    }


@scrape_router.get("/metrics/{job_id}")
def get_scrape_metrics(request, job_id: str):
    """Get metrics for a scrape job."""
    ScrapeJob, _ = _get_models()
    job = get_object_or_404(ScrapeJob, job_id=job_id)

    return {
        "job_id": str(job.job_id),
        "pages_fetched": job.pages_fetched,
        "bytes_processed": job.bytes_processed,
        "artifact_count": job.artifact_count,
        "error_count": job.error_count,
        "retry_count": job.retry_count,
    }
