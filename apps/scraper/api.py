"""Voyant Scraper REST API endpoints."""

import logging
from typing import Any

from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from apps.core.api_utils import run_async
from apps.core.config import get_settings
from apps.core.events import publish_scraper_event
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

# Lazy imports - avoid importing Django models at module level
# This prevents AppRegistryNotReady errors when module is loaded
# Models are imported inside functions that use them

settings = get_settings()
scrape_router = Router(tags=["scrape"], auth=require_permission("read:*"))


# ============================================================================
# Schemas (Pure Execution - No LLM)
# ============================================================================


class ScrapeStartSchema(Schema):
    """Request schema for starting a scrape job."""

    urls: list[str]
    selectors: dict[str, Any] | None = None  # Agent-provided selectors
    options: dict[str, Any] | None = None


class ScrapeExtractSchema(Schema):
    """Request schema for extracting data from HTML."""

    html: str
    selectors: dict[str, Any]  # Agent-provided CSS/XPath


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
    wait_for: str | None = None
    scroll: bool = False
    timeout: int = settings.scraper_default_timeout_seconds
    wait_until: str | None = None
    settle_ms: int | None = None
    block_resources: bool | None = None
    capture_json: bool = False
    capture_url_contains: list[str] | None = None
    capture_max_bytes: int | None = None
    capture_max_items: int | None = None


class ScrapeDeepArchiveSchema(Schema):
    """Request schema for generic deep archival scraping."""

    url: str
    interaction_selectors: list[str] = []
    download_patterns: list[str] = []
    target_dir: str
    wait_settle_ms: int = 2000
    timeout_ms: int = 60000


class ScrapeJobSchema(Schema):
    """Response schema for scrape job."""

    job_id: str
    status: str
    pages_fetched: int
    bytes_processed: int
    artifact_count: int
    error_count: int
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None


class ScrapeArtifactSchema(Schema):
    """Response schema for scrape artifact."""

    artifact_id: str
    artifact_type: str
    format: str
    storage_path: str
    size_bytes: int | None = None
    content_hash: str | None = None


class ScrapeResultSchema(Schema):
    """Response schema for scrape results."""

    job_id: str
    status: str
    artifacts: list[ScrapeArtifactSchema]


# ============================================================================
# Helper Functions (Lazy Imports)
# ============================================================================


def _get_models():
    from .models import ScrapeArtifact, ScrapeJob

    return ScrapeJob, ScrapeArtifact


def _get_security():
    from .security import SSRFError, validate_url, validate_urls

    return validate_url, validate_urls, SSRFError


def _start_scrape_workflow(
    job_id: str,
    urls: list[str],
    selectors: dict | None,
    options: dict,
    tenant_id: str,
):
    """Start Temporal workflow for scraping (pure execution)."""
    from apps.core.lib.temporal_client import get_temporal_client

    from .workflow import ScrapeWorkflow

    client = run_async(get_temporal_client)
    run_async(
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


@scrape_router.post(
    "/start", response={202: ScrapeJobSchema}, auth=require_permission("write:jobs")
)
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
        publish_scraper_event(
            tenant_id, "scrape.started", data={"job_id": str(job.job_id)}
        )
    except Exception as e:
        job.status = ScrapeJob.Status.FAILED
        job.error_message = str(e)
        job.save(update_fields=["status", "error_message"])
        publish_scraper_event(
            tenant_id,
            "scrape.failed",
            data={"job_id": str(job.job_id), "error": str(e)},
        )

    return 202, {
        "job_id": str(job.job_id),
        "status": job.status,
        "pages_fetched": 0,
        "bytes_processed": 0,
        "artifact_count": 0,
        "error_count": 0,
        "created_at": job.created_at.isoformat(),
    }


@scrape_router.post("/extract", auth=require_permission("write:jobs"))
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


@scrape_router.post("/fetch", auth=require_permission("write:jobs"))
def fetch_page(request, payload: ScrapeFetchSchema):
    from .activities import ScrapeActivities

    activity_runner = ScrapeActivities()
    return run_async(
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


@scrape_router.post("/deep_archive", auth=require_permission("write:jobs"))
def deep_archive(request, payload: ScrapeDeepArchiveSchema):
    from .activities import ScrapeActivities

    activity_runner = ScrapeActivities()
    return run_async(
        activity_runner.deep_archive,
        {
            "url": payload.url,
            "interaction_selectors": payload.interaction_selectors,
            "download_patterns": payload.download_patterns,
            "target_dir": payload.target_dir,
            "wait_settle_ms": payload.wait_settle_ms,
            "timeout_ms": payload.timeout_ms,
        },
    )


@scrape_router.post("/ocr", auth=require_permission("write:jobs"))
def process_ocr(request, payload: ScrapeOcrSchema):
    from .activities import ScrapeActivities

    activity_runner = ScrapeActivities()
    return run_async(
        activity_runner.process_ocr,
        {"images": [payload.image_url], "language": payload.language},
    )


@scrape_router.post("/parse_pdf", auth=require_permission("write:jobs"))
def parse_pdf(request, payload: ScrapePdfSchema):
    from .activities import ScrapeActivities

    activity_runner = ScrapeActivities()
    return run_async(
        activity_runner.parse_pdf,
        {"pdf_url": payload.pdf_url, "extract_tables": payload.extract_tables},
    )


@scrape_router.post("/transcribe", auth=require_permission("write:jobs"))
def transcribe_media(request, payload: ScrapeTranscribeSchema):
    from .activities import ScrapeActivities

    if not settings.scraper_enable_transcribe:
        return 503, {"error_code": "TRANSCRIPTION_DISABLED"}

    activity_runner = ScrapeActivities()
    return run_async(
        activity_runner.transcribe_media,
        {"media_urls": [payload.media_url], "language": payload.language},
    )


@scrape_router.get("/status/{job_id}", response=ScrapeJobSchema)
def get_scrape_status(request, job_id: str):
    ScrapeJob, _ = _get_models()
    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
    job = get_object_or_404(ScrapeJob, job_id=job_id, tenant_id=tenant_id)

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


@scrape_router.post("/cancel", auth=require_permission("write:jobs"))
def cancel_scrape(request, job_id: str):
    ScrapeJob, _ = _get_models()
    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
    job = get_object_or_404(ScrapeJob, job_id=job_id, tenant_id=tenant_id)

    # Cancel workflow execution when a running scrape is stopped.
    try:
        from apps.core.lib.temporal_client import get_temporal_client

        client = run_async(get_temporal_client)
        handle = client.get_workflow_handle(f"scrape-{job_id}")
        run_async(handle.cancel)
    except Exception as exc:
        logger.warning(
            "Failed to cancel Temporal workflow for scrape-%s: %s", job_id, exc
        )

    job.status = ScrapeJob.Status.CANCELLED
    job.save()
    publish_scraper_event(tenant_id, "scrape.cancelled", data={"job_id": job_id})

    return {"status": "cancelled", "job_id": str(job.job_id)}


@scrape_router.get("/result/{job_id}", response=ScrapeResultSchema)
def get_scrape_result(request, job_id: str):
    ScrapeJob, ScrapeArtifact = _get_models()
    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
    job = get_object_or_404(ScrapeJob, job_id=job_id, tenant_id=tenant_id)
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
    ScrapeJob, _ = _get_models()
    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
    job = get_object_or_404(ScrapeJob, job_id=job_id, tenant_id=tenant_id)

    return {
        "job_id": str(job.job_id),
        "pages_fetched": job.pages_fetched,
        "bytes_processed": job.bytes_processed,
        "artifact_count": job.artifact_count,
        "error_count": job.error_count,
        "retry_count": job.retry_count,
    }


# ============================================================================
# CAPTCHA Solver Integration
# ============================================================================


class CaptchaTestSchema(Schema):
    """Request schema for testing the CAPTCHA solver."""

    captcha_type: str = (
        "recaptcha_v2"  # recaptcha_v2 | recaptcha_v3 | hcaptcha | turnstile
    )
    site_key: str
    page_url: str
    action: str | None = None
    min_score: float = 0.3


class CaptchaStatusSchema(Schema):
    """Response schema for CAPTCHA solver status."""

    configured: bool
    providers: dict[str, bool]
    provider_count: int


@scrape_router.post("/captcha/test", auth=require_permission("write:jobs"))
def test_captcha_solver(request, payload: CaptchaTestSchema):
    """
    Test the CAPTCHA solver by attempting to solve a challenge.

    Sends a solve request to the configured CAPTCHA provider chain.
    Useful for verifying that API keys are valid and the solver works.
    """
    from .services.captcha_solver import (
        CaptchaSolveError,
        MultiProviderCaptchaSolver,
    )

    try:
        solver = MultiProviderCaptchaSolver.from_settings()
    except CaptchaSolveError as e:
        return 503, {"error": str(e), "status": "no_providers_configured"}

    async def _solve():
        method_map = {
            "recaptcha_v2": solver.solve_recaptcha_v2,
            "recaptcha_v3": solver.solve_recaptcha_v3,
            "hcaptcha": solver.solve_hcaptcha,
            "turnstile": solver.solve_turnstile,
        }
        solve_fn = method_map.get(payload.captcha_type)
        if not solve_fn:
            return {
                "status": "error",
                "error": f"Unknown captcha_type: {payload.captcha_type}. "
                f"Must be one of: {', '.join(method_map.keys())}",
            }

        kwargs: dict = {}
        if payload.action:
            kwargs["action"] = payload.action
        if payload.captcha_type == "recaptcha_v3":
            kwargs["min_score"] = payload.min_score

        token = await solve_fn(payload.site_key, payload.page_url, **kwargs)
        return {
            "status": "solved",
            "captcha_type": payload.captcha_type,
            "token_length": len(token),
            "token_preview": (
                f"{token[:20]}...{token[-10:]}" if len(token) > 30 else token
            ),
        }

    try:
        result = run_async(_solve)
        return result
    except CaptchaSolveError as e:
        return 502, {"status": "solve_failed", "error": str(e)}
    except Exception as e:
        logger.exception("CAPTCHA test failed unexpectedly")
        return 500, {"status": "error", "error": str(e)}


@scrape_router.get("/captcha/status", response=CaptchaStatusSchema)
def get_captcha_status(request):
    """
    Get CAPTCHA solver configuration status.

    Returns which providers are configured (have API keys set)
    without exposing the actual key values.
    """
    providers = {
        "2captcha": bool(settings.captcha_2captcha_key),
        "anticaptcha": bool(settings.captcha_anticaptcha_key),
        "capsolver": bool(settings.captcha_capsolver_key),
    }
    configured_count = sum(1 for v in providers.values() if v)
    return {
        "configured": configured_count > 0,
        "providers": providers,
        "provider_count": configured_count,
    }


@scrape_router.get("/health")
def scraper_health(request):
    """
    Scraper service health check.

    Reports operational status of the scraper subsystem including
    CAPTCHA solver availability, default engine, and feature flags.
    """
    captcha_providers = {
        "2captcha": bool(settings.captcha_2captcha_key),
        "anticaptcha": bool(settings.captcha_anticaptcha_key),
        "capsolver": bool(settings.captcha_capsolver_key),
    }
    captcha_configured = any(captcha_providers.values())

    return {
        "status": "healthy",
        "service": "scraper",
        "captcha": {
            "configured": captcha_configured,
            "providers": captcha_providers,
            "provider_count": sum(1 for v in captcha_providers.values() if v),
        },
        "defaults": {
            "engine": settings.scraper_default_engine,
            "timeout_seconds": settings.scraper_default_timeout_seconds,
            "ocr_language": settings.scraper_default_ocr_language,
            "transcribe_language": settings.scraper_default_transcribe_language,
        },
        "features": {
            "ocr": True,
            "transcribe": settings.scraper_enable_transcribe,
            "pdf_parse": True,
            "deep_archive": True,
        },
    }


# ============================================================================
# v4.0 Scraper Octopus — New Endpoints
# ============================================================================

# New router for v4.0 scraper models
scraper_v2_router = Router(tags=["scraper-v2"], auth=require_permission("read:*"))


# ---------------------------------------------------------------------------
# ScrapeWorkflow Schemas & Endpoints
# ---------------------------------------------------------------------------


class WorkflowCreateSchema(Schema):
    name: str
    description: str = ""
    steps: list[dict[str, Any]] = []
    input_schema: dict[str, Any] = {}
    output_schema: dict[str, Any] = {}


class WorkflowUpdateSchema(Schema):
    name: str | None = None
    description: str | None = None
    steps: list[dict[str, Any]] | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None


class WorkflowResponseSchema(Schema):
    id: str
    name: str
    description: str
    steps: list[dict[str, Any]]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    tenant_id: str
    created_at: str
    updated_at: str


@scraper_v2_router.post(
    "/workflows",
    response={201: WorkflowResponseSchema},
    auth=require_permission("write:jobs"),
)
def create_workflow(request, payload: WorkflowCreateSchema):
    from .models import ScrapeWorkflow

    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
    wf = ScrapeWorkflow.objects.create(
        name=payload.name,
        description=payload.description,
        steps=payload.steps,
        input_schema=payload.input_schema,
        output_schema=payload.output_schema,
        tenant_id=tenant_id,
    )
    return 201, {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description,
        "steps": wf.steps,
        "input_schema": wf.input_schema,
        "output_schema": wf.output_schema,
        "tenant_id": wf.tenant_id,
        "created_at": wf.created_at.isoformat(),
        "updated_at": wf.updated_at.isoformat(),
    }


@scraper_v2_router.get("/workflows")
def list_workflows(request, limit: int = 100):
    from .models import ScrapeWorkflow

    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
    qs = ScrapeWorkflow.objects.filter(tenant_id=tenant_id)[:limit]
    return [
        {
            "id": str(wf.id),
            "name": wf.name,
            "description": wf.description,
            "steps": wf.steps,
            "input_schema": wf.input_schema,
            "output_schema": wf.output_schema,
            "tenant_id": wf.tenant_id,
            "created_at": wf.created_at.isoformat(),
            "updated_at": wf.updated_at.isoformat(),
        }
        for wf in qs
    ]


@scraper_v2_router.get("/workflows/{workflow_id}", response=WorkflowResponseSchema)
def get_workflow(request, workflow_id: str):
    from .models import ScrapeWorkflow

    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
    wf = get_object_or_404(ScrapeWorkflow, id=workflow_id, tenant_id=tenant_id)
    return {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description,
        "steps": wf.steps,
        "input_schema": wf.input_schema,
        "output_schema": wf.output_schema,
        "tenant_id": wf.tenant_id,
        "created_at": wf.created_at.isoformat(),
        "updated_at": wf.updated_at.isoformat(),
    }


@scraper_v2_router.put(
    "/workflows/{workflow_id}",
    response=WorkflowResponseSchema,
    auth=require_permission("write:jobs"),
)
def update_workflow(request, workflow_id: str, payload: WorkflowUpdateSchema):
    from .models import ScrapeWorkflow

    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
    wf = get_object_or_404(ScrapeWorkflow, id=workflow_id, tenant_id=tenant_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(wf, field, value)
    wf.save()
    return {
        "id": str(wf.id),
        "name": wf.name,
        "description": wf.description,
        "steps": wf.steps,
        "input_schema": wf.input_schema,
        "output_schema": wf.output_schema,
        "tenant_id": wf.tenant_id,
        "created_at": wf.created_at.isoformat(),
        "updated_at": wf.updated_at.isoformat(),
    }


@scraper_v2_router.delete(
    "/workflows/{workflow_id}",
    auth=require_permission("write:jobs"),
)
def delete_workflow(request, workflow_id: str):
    from .models import ScrapeWorkflow

    tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
    wf = get_object_or_404(ScrapeWorkflow, id=workflow_id, tenant_id=tenant_id)
    wf.delete()
    return {"deleted": True, "id": workflow_id}


# ---------------------------------------------------------------------------
# ScrapeStep Schemas & Endpoints
# ---------------------------------------------------------------------------


class StepCreateSchema(Schema):
    workflow_id: str
    order: int = 0
    step_type: str
    selector: str = ""
    action: str = ""
    wait_condition: str = ""
    options: dict[str, Any] = {}


class StepUpdateSchema(Schema):
    order: int | None = None
    step_type: str | None = None
    selector: str | None = None
    action: str | None = None
    wait_condition: str | None = None
    options: dict[str, Any] | None = None


class StepResponseSchema(Schema):
    id: str
    workflow_id: str
    order: int
    step_type: str
    selector: str
    action: str
    wait_condition: str
    options: dict[str, Any]


@scraper_v2_router.post(
    "/steps",
    response={201: StepResponseSchema},
    auth=require_permission("write:jobs"),
)
def create_step(request, payload: StepCreateSchema):
    from .models import ScrapeStep, ScrapeWorkflow

    wf = get_object_or_404(ScrapeWorkflow, id=payload.workflow_id)
    step = ScrapeStep.objects.create(
        workflow=wf,
        order=payload.order,
        step_type=payload.step_type,
        selector=payload.selector,
        action=payload.action,
        wait_condition=payload.wait_condition,
        options=payload.options,
    )
    return 201, {
        "id": str(step.id),
        "workflow_id": str(step.workflow_id),  # type: ignore[attr-defined]
        "order": step.order,
        "step_type": step.step_type,
        "selector": step.selector,
        "action": step.action,
        "wait_condition": step.wait_condition,
        "options": step.options,
    }


@scraper_v2_router.get("/workflows/{workflow_id}/steps")
def list_steps(request, workflow_id: str):
    from .models import ScrapeStep

    qs = ScrapeStep.objects.filter(workflow_id=workflow_id)
    return [
        {
            "id": str(s.id),
            "workflow_id": str(s.workflow_id),  # type: ignore[attr-defined]
            "order": s.order,
            "step_type": s.step_type,
            "selector": s.selector,
            "action": s.action,
            "wait_condition": s.wait_condition,
            "options": s.options,
        }
        for s in qs
    ]


@scraper_v2_router.put(
    "/steps/{step_id}",
    response=StepResponseSchema,
    auth=require_permission("write:jobs"),
)
def update_step(request, step_id: str, payload: StepUpdateSchema):
    from .models import ScrapeStep

    step = get_object_or_404(ScrapeStep, id=step_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(step, field, value)
    step.save()
    return {
        "id": str(step.id),
        "workflow_id": str(step.workflow_id),  # type: ignore[attr-defined]
        "order": step.order,
        "step_type": step.step_type,
        "selector": step.selector,
        "action": step.action,
        "wait_condition": step.wait_condition,
        "options": step.options,
    }


@scraper_v2_router.delete(
    "/steps/{step_id}",
    auth=require_permission("write:jobs"),
)
def delete_step(request, step_id: str):
    from .models import ScrapeStep

    step = get_object_or_404(ScrapeStep, id=step_id)
    step.delete()
    return {"deleted": True, "id": step_id}


# ---------------------------------------------------------------------------
# ScrapeSchedule Schemas & Endpoints
# ---------------------------------------------------------------------------


class ScheduleCreateSchema(Schema):
    task_id: str
    cron_expr: str
    timezone: str = "UTC"
    enabled: bool = True


class ScheduleUpdateSchema(Schema):
    cron_expr: str | None = None
    timezone: str | None = None
    enabled: bool | None = None


class ScheduleResponseSchema(Schema):
    id: str
    task_id: str
    cron_expr: str
    timezone: str
    enabled: bool
    created_at: str
    updated_at: str


@scraper_v2_router.post(
    "/schedules",
    response={201: ScheduleResponseSchema},
    auth=require_permission("write:jobs"),
)
def create_schedule(request, payload: ScheduleCreateSchema):
    from .models import ScrapeJob, ScrapeSchedule

    task = get_object_or_404(ScrapeJob, job_id=payload.task_id)
    schedule = ScrapeSchedule.objects.create(
        task=task,
        cron_expr=payload.cron_expr,
        timezone=payload.timezone,
        enabled=payload.enabled,
    )
    return 201, {
        "id": str(schedule.id),
        "task_id": str(schedule.task_id),  # type: ignore[attr-defined]
        "cron_expr": schedule.cron_expr,
        "timezone": schedule.timezone,
        "enabled": schedule.enabled,
        "created_at": schedule.created_at.isoformat(),
        "updated_at": schedule.updated_at.isoformat(),
    }


@scraper_v2_router.get("/schedules")
def list_schedules(request, enabled: bool | None = None, limit: int = 100):
    from .models import ScrapeSchedule

    qs = ScrapeSchedule.objects.all()
    if enabled is not None:
        qs = qs.filter(enabled=enabled)
    return [
        {
            "id": str(s.id),
            "task_id": str(s.task_id),  # type: ignore[attr-defined]
            "cron_expr": s.cron_expr,
            "timezone": s.timezone,
            "enabled": s.enabled,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in qs[:limit]
    ]


@scraper_v2_router.get("/schedules/{schedule_id}", response=ScheduleResponseSchema)
def get_schedule(request, schedule_id: str):
    from .models import ScrapeSchedule

    schedule = get_object_or_404(ScrapeSchedule, id=schedule_id)
    return {
        "id": str(schedule.id),
        "task_id": str(schedule.task_id),  # type: ignore[attr-defined]
        "cron_expr": schedule.cron_expr,
        "timezone": schedule.timezone,
        "enabled": schedule.enabled,
        "created_at": schedule.created_at.isoformat(),
        "updated_at": schedule.updated_at.isoformat(),
    }


@scraper_v2_router.put(
    "/schedules/{schedule_id}",
    response=ScheduleResponseSchema,
    auth=require_permission("write:jobs"),
)
def update_schedule(request, schedule_id: str, payload: ScheduleUpdateSchema):
    from .models import ScrapeSchedule

    schedule = get_object_or_404(ScrapeSchedule, id=schedule_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)
    schedule.save()
    return {
        "id": str(schedule.id),
        "task_id": str(schedule.task_id),  # type: ignore[attr-defined]
        "cron_expr": schedule.cron_expr,
        "timezone": schedule.timezone,
        "enabled": schedule.enabled,
        "created_at": schedule.created_at.isoformat(),
        "updated_at": schedule.updated_at.isoformat(),
    }


@scraper_v2_router.delete(
    "/schedules/{schedule_id}",
    auth=require_permission("write:jobs"),
)
def delete_schedule(request, schedule_id: str):
    from .models import ScrapeSchedule

    schedule = get_object_or_404(ScrapeSchedule, id=schedule_id)
    schedule.delete()
    return {"deleted": True, "id": schedule_id}


# ---------------------------------------------------------------------------
# ScrapeExport Schemas & Endpoints
# ---------------------------------------------------------------------------


class ExportCreateSchema(Schema):
    task_id: str
    format: str = "json"
    destination: str
    auto_export: bool = False


class ExportUpdateSchema(Schema):
    format: str | None = None
    destination: str | None = None
    auto_export: bool | None = None


class ExportResponseSchema(Schema):
    id: str
    task_id: str
    format: str
    destination: str
    auto_export: bool
    created_at: str
    updated_at: str


@scraper_v2_router.post(
    "/exports",
    response={201: ExportResponseSchema},
    auth=require_permission("write:jobs"),
)
def create_export(request, payload: ExportCreateSchema):
    from .models import ScrapeExport, ScrapeJob

    task = get_object_or_404(ScrapeJob, job_id=payload.task_id)
    export = ScrapeExport.objects.create(
        task=task,
        format=payload.format,
        destination=payload.destination,
        auto_export=payload.auto_export,
    )
    return 201, {
        "id": str(export.id),
        "task_id": str(export.task_id),  # type: ignore[attr-defined]
        "format": export.format,
        "destination": export.destination,
        "auto_export": export.auto_export,
        "created_at": export.created_at.isoformat(),
        "updated_at": export.updated_at.isoformat(),
    }


@scraper_v2_router.get("/exports")
def list_exports(request, task_id: str | None = None, limit: int = 100):
    from .models import ScrapeExport

    qs = ScrapeExport.objects.all()
    if task_id:
        qs = qs.filter(task_id=task_id)
    return [
        {
            "id": str(e.id),
            "task_id": str(e.task_id),  # type: ignore[attr-defined]
            "format": e.format,
            "destination": e.destination,
            "auto_export": e.auto_export,
            "created_at": e.created_at.isoformat(),
            "updated_at": e.updated_at.isoformat(),
        }
        for e in qs[:limit]
    ]


@scraper_v2_router.get("/exports/{export_id}", response=ExportResponseSchema)
def get_export(request, export_id: str):
    from .models import ScrapeExport

    export = get_object_or_404(ScrapeExport, id=export_id)
    return {
        "id": str(export.id),
        "task_id": str(export.task_id),  # type: ignore[attr-defined]
        "format": export.format,
        "destination": export.destination,
        "auto_export": export.auto_export,
        "created_at": export.created_at.isoformat(),
        "updated_at": export.updated_at.isoformat(),
    }


@scraper_v2_router.put(
    "/exports/{export_id}",
    response=ExportResponseSchema,
    auth=require_permission("write:jobs"),
)
def update_export(request, export_id: str, payload: ExportUpdateSchema):
    from .models import ScrapeExport

    export = get_object_or_404(ScrapeExport, id=export_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(export, field, value)
    export.save()
    return {
        "id": str(export.id),
        "task_id": str(export.task_id),  # type: ignore[attr-defined]
        "format": export.format,
        "destination": export.destination,
        "auto_export": export.auto_export,
        "created_at": export.created_at.isoformat(),
        "updated_at": export.updated_at.isoformat(),
    }


@scraper_v2_router.delete(
    "/exports/{export_id}",
    auth=require_permission("write:jobs"),
)
def delete_export(request, export_id: str):
    from .models import ScrapeExport

    export = get_object_or_404(ScrapeExport, id=export_id)
    export.delete()
    return {"deleted": True, "id": export_id}


# ---------------------------------------------------------------------------
# ScrapeRun Schemas & Endpoints
# ---------------------------------------------------------------------------


class RunCreateSchema(Schema):
    task_id: str
    trace_id: str = ""


class RunResponseSchema(Schema):
    id: str
    task_id: str
    status: str
    rows_extracted: int
    duration_ms: int | None = None
    trace_id: str
    started_at: str | None = None
    completed_at: str | None = None
    created_at: str
    updated_at: str


@scraper_v2_router.post(
    "/runs",
    response={201: RunResponseSchema},
    auth=require_permission("write:jobs"),
)
def create_run(request, payload: RunCreateSchema):
    from .models import ScrapeJob, ScrapeRun

    task = get_object_or_404(ScrapeJob, job_id=payload.task_id)
    run = ScrapeRun.objects.create(
        task=task,
        trace_id=payload.trace_id,
    )
    return 201, {
        "id": str(run.id),
        "task_id": str(run.task_id),  # type: ignore[attr-defined]
        "status": run.status,
        "rows_extracted": run.rows_extracted,
        "duration_ms": run.duration_ms,
        "trace_id": run.trace_id,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }


@scraper_v2_router.get("/runs")
def list_runs(
    request,
    task_id: str | None = None,
    status: str | None = None,
    limit: int = 100,
):
    from .models import ScrapeRun

    qs = ScrapeRun.objects.all()
    if task_id:
        qs = qs.filter(task_id=task_id)
    if status:
        qs = qs.filter(status=status)
    return [
        {
            "id": str(r.id),
            "task_id": str(r.task_id),  # type: ignore[attr-defined]
            "status": r.status,
            "rows_extracted": r.rows_extracted,
            "duration_ms": r.duration_ms,
            "trace_id": r.trace_id,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "created_at": r.created_at.isoformat(),
            "updated_at": r.updated_at.isoformat(),
        }
        for r in qs[:limit]
    ]


@scraper_v2_router.get("/runs/{run_id}", response=RunResponseSchema)
def get_run(request, run_id: str):
    from .models import ScrapeRun

    run = get_object_or_404(ScrapeRun, id=run_id)
    return {
        "id": str(run.id),
        "task_id": str(run.task_id),  # type: ignore[attr-defined]
        "status": run.status,
        "rows_extracted": run.rows_extracted,
        "duration_ms": run.duration_ms,
        "trace_id": run.trace_id,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }


@scraper_v2_router.patch(
    "/runs/{run_id}",
    response=RunResponseSchema,
    auth=require_permission("write:jobs"),
)
def update_run(request, run_id: str, payload: dict[str, Any]):
    from django.utils import timezone as tz

    from .models import ScrapeRun

    run = get_object_or_404(ScrapeRun, id=run_id)
    allowed_fields = {
        "status",
        "rows_extracted",
        "duration_ms",
        "trace_id",
        "started_at",
        "completed_at",
    }
    for field, value in payload.items():
        if field in allowed_fields:
            setattr(run, field, value)
    # Auto-set timestamps based on status transitions
    if payload.get("status") == ScrapeRun.Status.RUNNING and not run.started_at:
        run.started_at = tz.now()
    if (
        payload.get("status")
        in (
            ScrapeRun.Status.SUCCEEDED,
            ScrapeRun.Status.FAILED,
            ScrapeRun.Status.CANCELLED,
            ScrapeRun.Status.TIMEOUT,
        )
        and not run.completed_at
    ):
        run.completed_at = tz.now()
        if run.started_at:
            run.duration_ms = int(
                (run.completed_at - run.started_at).total_seconds() * 1000
            )
    run.save()
    return {
        "id": str(run.id),
        "task_id": str(run.task_id),  # type: ignore[attr-defined]
        "status": run.status,
        "rows_extracted": run.rows_extracted,
        "duration_ms": run.duration_ms,
        "trace_id": run.trace_id,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }


@scraper_v2_router.delete(
    "/runs/{run_id}",
    auth=require_permission("write:jobs"),
)
def delete_run(request, run_id: str):
    from .models import ScrapeRun

    run = get_object_or_404(ScrapeRun, id=run_id)
    run.delete()
    return {"deleted": True, "id": run_id}


# ---------------------------------------------------------------------------
# ScrapeProxy Schemas & Endpoints
# ---------------------------------------------------------------------------


class ProxyCreateSchema(Schema):
    proxy_type: str = "residential"
    provider: str
    endpoints: list[str] = []
    rotation_strategy: str = "per_request"
    is_active: bool = True


class ProxyUpdateSchema(Schema):
    proxy_type: str | None = None
    provider: str | None = None
    endpoints: list[str] | None = None
    rotation_strategy: str | None = None
    is_active: bool | None = None


class ProxyResponseSchema(Schema):
    id: str
    proxy_type: str
    provider: str
    endpoints: list[str]
    rotation_strategy: str
    is_active: bool
    created_at: str
    updated_at: str


@scraper_v2_router.post(
    "/proxies",
    response={201: ProxyResponseSchema},
    auth=require_permission("write:jobs"),
)
def create_proxy(request, payload: ProxyCreateSchema):
    from .models import ScrapeProxy

    proxy = ScrapeProxy.objects.create(
        proxy_type=payload.proxy_type,
        provider=payload.provider,
        endpoints=payload.endpoints,
        rotation_strategy=payload.rotation_strategy,
        is_active=payload.is_active,
    )
    return 201, {
        "id": str(proxy.id),
        "proxy_type": proxy.proxy_type,
        "provider": proxy.provider,
        "endpoints": proxy.endpoints,
        "rotation_strategy": proxy.rotation_strategy,
        "is_active": proxy.is_active,
        "created_at": proxy.created_at.isoformat(),
        "updated_at": proxy.updated_at.isoformat(),
    }


@scraper_v2_router.get("/proxies")
def list_proxies(
    request,
    proxy_type: str | None = None,
    provider: str | None = None,
    is_active: bool | None = None,
    limit: int = 100,
):
    from .models import ScrapeProxy

    qs = ScrapeProxy.objects.all()
    if proxy_type:
        qs = qs.filter(proxy_type=proxy_type)
    if provider:
        qs = qs.filter(provider=provider)
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    return [
        {
            "id": str(p.id),
            "proxy_type": p.proxy_type,
            "provider": p.provider,
            "endpoints": p.endpoints,
            "rotation_strategy": p.rotation_strategy,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }
        for p in qs[:limit]
    ]


@scraper_v2_router.get("/proxies/{proxy_id}", response=ProxyResponseSchema)
def get_proxy(request, proxy_id: str):
    from .models import ScrapeProxy

    proxy = get_object_or_404(ScrapeProxy, id=proxy_id)
    return {
        "id": str(proxy.id),
        "proxy_type": proxy.proxy_type,
        "provider": proxy.provider,
        "endpoints": proxy.endpoints,
        "rotation_strategy": proxy.rotation_strategy,
        "is_active": proxy.is_active,
        "created_at": proxy.created_at.isoformat(),
        "updated_at": proxy.updated_at.isoformat(),
    }


@scraper_v2_router.put(
    "/proxies/{proxy_id}",
    response=ProxyResponseSchema,
    auth=require_permission("write:jobs"),
)
def update_proxy(request, proxy_id: str, payload: ProxyUpdateSchema):
    from .models import ScrapeProxy

    proxy = get_object_or_404(ScrapeProxy, id=proxy_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(proxy, field, value)
    proxy.save()
    return {
        "id": str(proxy.id),
        "proxy_type": proxy.proxy_type,
        "provider": proxy.provider,
        "endpoints": proxy.endpoints,
        "rotation_strategy": proxy.rotation_strategy,
        "is_active": proxy.is_active,
        "created_at": proxy.created_at.isoformat(),
        "updated_at": proxy.updated_at.isoformat(),
    }


@scraper_v2_router.delete(
    "/proxies/{proxy_id}",
    auth=require_permission("write:jobs"),
)
def delete_proxy(request, proxy_id: str):
    from .models import ScrapeProxy

    proxy = get_object_or_404(ScrapeProxy, id=proxy_id)
    proxy.delete()
    return {"deleted": True, "id": proxy_id}


# ---------------------------------------------------------------------------
# ScrapeFingerprint Schemas & Endpoints
# ---------------------------------------------------------------------------


class FingerprintCreateSchema(Schema):
    user_agent: str
    viewport_width: int = 1920
    viewport_height: int = 1080
    webgl_vendor: str = ""
    webgl_renderer: str = ""


class FingerprintUpdateSchema(Schema):
    user_agent: str | None = None
    viewport_width: int | None = None
    viewport_height: int | None = None
    webgl_vendor: str | None = None
    webgl_renderer: str | None = None


class FingerprintResponseSchema(Schema):
    id: str
    user_agent: str
    viewport_width: int
    viewport_height: int
    webgl_vendor: str
    webgl_renderer: str
    created_at: str
    updated_at: str


@scraper_v2_router.post(
    "/fingerprints",
    response={201: FingerprintResponseSchema},
    auth=require_permission("write:jobs"),
)
def create_fingerprint(request, payload: FingerprintCreateSchema):
    from .models import ScrapeFingerprint

    fp = ScrapeFingerprint.objects.create(
        user_agent=payload.user_agent,
        viewport_width=payload.viewport_width,
        viewport_height=payload.viewport_height,
        webgl_vendor=payload.webgl_vendor,
        webgl_renderer=payload.webgl_renderer,
    )
    return 201, {
        "id": str(fp.id),
        "user_agent": fp.user_agent,
        "viewport_width": fp.viewport_width,
        "viewport_height": fp.viewport_height,
        "webgl_vendor": fp.webgl_vendor,
        "webgl_renderer": fp.webgl_renderer,
        "created_at": fp.created_at.isoformat(),
        "updated_at": fp.updated_at.isoformat(),
    }


@scraper_v2_router.get("/fingerprints")
def list_fingerprints(request, limit: int = 100):
    from .models import ScrapeFingerprint

    qs = ScrapeFingerprint.objects.all()[:limit]
    return [
        {
            "id": str(fp.id),
            "user_agent": fp.user_agent,
            "viewport_width": fp.viewport_width,
            "viewport_height": fp.viewport_height,
            "webgl_vendor": fp.webgl_vendor,
            "webgl_renderer": fp.webgl_renderer,
            "created_at": fp.created_at.isoformat(),
            "updated_at": fp.updated_at.isoformat(),
        }
        for fp in qs
    ]


@scraper_v2_router.get(
    "/fingerprints/{fingerprint_id}",
    response=FingerprintResponseSchema,
)
def get_fingerprint(request, fingerprint_id: str):
    from .models import ScrapeFingerprint

    fp = get_object_or_404(ScrapeFingerprint, id=fingerprint_id)
    return {
        "id": str(fp.id),
        "user_agent": fp.user_agent,
        "viewport_width": fp.viewport_width,
        "viewport_height": fp.viewport_height,
        "webgl_vendor": fp.webgl_vendor,
        "webgl_renderer": fp.webgl_renderer,
        "created_at": fp.created_at.isoformat(),
        "updated_at": fp.updated_at.isoformat(),
    }


@scraper_v2_router.put(
    "/fingerprints/{fingerprint_id}",
    response=FingerprintResponseSchema,
    auth=require_permission("write:jobs"),
)
def update_fingerprint(request, fingerprint_id: str, payload: FingerprintUpdateSchema):
    from .models import ScrapeFingerprint

    fp = get_object_or_404(ScrapeFingerprint, id=fingerprint_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(fp, field, value)
    fp.save()
    return {
        "id": str(fp.id),
        "user_agent": fp.user_agent,
        "viewport_width": fp.viewport_width,
        "viewport_height": fp.viewport_height,
        "webgl_vendor": fp.webgl_vendor,
        "webgl_renderer": fp.webgl_renderer,
        "created_at": fp.created_at.isoformat(),
        "updated_at": fp.updated_at.isoformat(),
    }


@scraper_v2_router.delete(
    "/fingerprints/{fingerprint_id}",
    auth=require_permission("write:jobs"),
)
def delete_fingerprint(request, fingerprint_id: str):
    from .models import ScrapeFingerprint

    fp = get_object_or_404(ScrapeFingerprint, id=fingerprint_id)
    fp.delete()
    return {"deleted": True, "id": fingerprint_id}


@scraper_v2_router.post("/fingerprints/generate", auth=require_permission("write:jobs"))
def generate_fingerprint_endpoint(request):
    """Generate a random browser fingerprint and optionally persist it.

    Returns the full fingerprint data (user-agent, viewport, WebGL,
    canvas/audio noise seeds, etc.) using the BrowserFingerprint
    randomizer.  The fingerprint is also saved to the database.
    """
    from .services.fingerprint import BrowserFingerprint

    fp_obj = BrowserFingerprint.random()
    data = fp_obj.to_dict()

    # Persist to database
    from .models import ScrapeFingerprint

    db_fp = ScrapeFingerprint.objects.create(
        user_agent=data["user_agent"],
        viewport_width=data["viewport_width"],
        viewport_height=data["viewport_height"],
        webgl_vendor=data["webgl_vendor"],
        webgl_renderer=data["webgl_renderer"],
    )

    return 201, {
        "id": str(db_fp.id),
        **data,
        "created_at": db_fp.created_at.isoformat(),
        "updated_at": db_fp.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# AgentSkill Schemas & Endpoints
# ---------------------------------------------------------------------------


class AgentSkillCreateSchema(Schema):
    name: str
    description: str = ""
    steps: list[dict[str, Any]] = []
    tools: list[str] = []
    parameters: dict[str, Any] = {}


class AgentSkillUpdateSchema(Schema):
    name: str | None = None
    description: str | None = None
    steps: list[dict[str, Any]] | None = None
    tools: list[str] | None = None
    parameters: dict[str, Any] | None = None


class AgentSkillResponseSchema(Schema):
    id: str
    name: str
    description: str
    steps: list[dict[str, Any]]
    tools: list[str]
    parameters: dict[str, Any]
    created_at: str
    updated_at: str


@scraper_v2_router.post(
    "/agent-skills",
    response={201: AgentSkillResponseSchema},
    auth=require_permission("write:jobs"),
)
def create_agent_skill(request, payload: AgentSkillCreateSchema):
    from .models import AgentSkill

    skill = AgentSkill.objects.create(
        name=payload.name,
        description=payload.description,
        steps=payload.steps,
        tools=payload.tools,
        parameters=payload.parameters,
    )
    return 201, {
        "id": str(skill.id),
        "name": skill.name,
        "description": skill.description,
        "steps": skill.steps,
        "tools": skill.tools,
        "parameters": skill.parameters,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }


@scraper_v2_router.get("/agent-skills")
def list_agent_skills(request, limit: int = 100):
    from .models import AgentSkill

    qs = AgentSkill.objects.all()[:limit]
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "description": s.description,
            "steps": s.steps,
            "tools": s.tools,
            "parameters": s.parameters,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in qs
    ]


@scraper_v2_router.get(
    "/agent-skills/{skill_id}",
    response=AgentSkillResponseSchema,
)
def get_agent_skill(request, skill_id: str):
    from .models import AgentSkill

    skill = get_object_or_404(AgentSkill, id=skill_id)
    return {
        "id": str(skill.id),
        "name": skill.name,
        "description": skill.description,
        "steps": skill.steps,
        "tools": skill.tools,
        "parameters": skill.parameters,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }


@scraper_v2_router.put(
    "/agent-skills/{skill_id}",
    response=AgentSkillResponseSchema,
    auth=require_permission("write:jobs"),
)
def update_agent_skill(request, skill_id: str, payload: AgentSkillUpdateSchema):
    from .models import AgentSkill

    skill = get_object_or_404(AgentSkill, id=skill_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(skill, field, value)
    skill.save()
    return {
        "id": str(skill.id),
        "name": skill.name,
        "description": skill.description,
        "steps": skill.steps,
        "tools": skill.tools,
        "parameters": skill.parameters,
        "created_at": skill.created_at.isoformat(),
        "updated_at": skill.updated_at.isoformat(),
    }


@scraper_v2_router.delete(
    "/agent-skills/{skill_id}",
    auth=require_permission("write:jobs"),
)
def delete_agent_skill(request, skill_id: str):
    from .models import AgentSkill

    skill = get_object_or_404(AgentSkill, id=skill_id)
    skill.delete()
    return {"deleted": True, "id": skill_id}
