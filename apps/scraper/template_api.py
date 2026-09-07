"""Scraper v4.0 — Template API endpoints. All operations are real, not mocked."""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.scraper.models import ScrapeTemplate


class RunTemplatePayload(Schema):
    parameters: dict[str, Any] = {}

logger = logging.getLogger(__name__)

template_router = Router(tags=["scraper-templates"], auth=require_permission("read:*"))


@template_router.get("/templates")
def list_templates(
    request,
    category: str | None = None,
    status: str | None = None,
    limit: int = 100,
):
    """List all scraping templates."""
    qs = ScrapeTemplate.objects.filter(status="active")
    if category:
        qs = qs.filter(category=category)
    if status:
        qs = qs.filter(status=status)

    return [
        {
            "id": str(t.id),
            "name": t.name,
            "site_pattern": t.site_pattern,
            "category": t.category,
            "description": t.description,
            "engine": t.engine,
            "language": t.language,
            "parameters": t.parameters,
            "output_fields": t.output_fields,
            "use_count": t.use_count,
            "success_rate": t.success_rate,
        }
        for t in qs[:limit]
    ]


@template_router.get("/templates/categories")
def list_categories(request):
    """List all template categories with counts."""
    from django.db.models import Count

    categories = (
        ScrapeTemplate.objects.filter(status="active")
        .values("category")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    return [
        {"category": c["category"], "count": c["count"]}
        for c in categories
    ]


@template_router.get("/templates/{template_id}")
def get_template(request, template_id: str):
    """Get template details including selectors and workflow."""
    t = ScrapeTemplate.objects.filter(id=template_id).first()
    if not t:
        raise HttpError(404, "Template not found")

    return {
        "id": str(t.id),
        "name": t.name,
        "site_pattern": t.site_pattern,
        "category": t.category,
        "description": t.description,
        "engine": t.engine,
        "language": t.language,
        "selectors": t.selectors,
        "workflow": t.workflow,
        "options": t.options,
        "parameters": t.parameters,
        "output_fields": t.output_fields,
        "use_count": t.use_count,
        "success_rate": t.success_rate,
        "created_at": t.created_at.isoformat(),
    }


@template_router.post("/templates/{template_id}/run", auth=require_permission("write:jobs"))
def run_template(request, template_id: str, payload: RunTemplatePayload):
    """Execute a template with parameter substitution. Starts a real Temporal workflow."""
    from apps.scraper.models import ScrapeJob
    from apps.scraper.security import SSRFError, validate_urls

    t = ScrapeTemplate.objects.filter(id=template_id, status="active").first()
    if not t:
        raise HttpError(404, "Template not found")

    tenant_id = get_tenant_id(request) or "default"
    params = payload.parameters or {}

    # Substitute parameters into workflow
    workflow = _substitute_workflow(t.workflow or [], params)
    url = _extract_url(workflow)

    if not url:
        raise HttpError(400, "Template workflow has no navigable URL")

    # SSRF validation
    try:
        validated_urls = validate_urls([url])
    except (SSRFError, Exception) as e:
        raise HttpError(400, f"URL validation failed: {e}")

    # Build selectors from template
    selectors = t.selectors or {}
    for step in workflow:
        if step.get("action") == "extract" and step.get("selectors"):
            selectors.update(step["selectors"])

    # Build options from template + workflow
    options = dict(t.options or {})
    options["engine"] = t.engine or "playwright"
    options["workflow"] = workflow

    # Anti-bot settings from template
    for step in workflow:
        if step.get("action") == "anti_bot":
            options.update(step)

    # Create the job
    job = ScrapeJob.objects.create(
        tenant_id=tenant_id,
        urls=validated_urls,
        selectors=selectors,
        options=options,
    )

    # Start Temporal workflow for real execution
    try:
        from apps.core.config import get_settings
        from apps.worker.workflows.scrape_workflow import ScrapeWorkflow

        settings = get_settings()
        _start_workflow_sync(
            ScrapeWorkflow.run,
            {
                "job_id": str(job.job_id),
                "urls": validated_urls,
                "selectors": selectors,
                "options": options,
                "tenant_id": tenant_id,
            },
            workflow_id=f"scrape-{job.job_id}",
            task_queue=settings.temporal_task_queue,
        )
        job.status = ScrapeJob.Status.RUNNING
        job.save(update_fields=["status"])
    except Exception as exc:
        logger.warning("Temporal workflow start failed, running inline: %s", exc)
        # Fallback: run inline if Temporal is unavailable
        _run_inline(job, validated_urls, selectors, options)

    # Update template stats
    t.use_count = (t.use_count or 0) + 1
    t.save(update_fields=["use_count"])

    return {
        "job_id": str(job.job_id),
        "template_id": str(t.id),
        "template_name": t.name,
        "status": job.status,
        "url": url,
        "selectors": selectors,
    }


@template_router.get("/templates/{template_id}/preview")
def preview_template(request, template_id: str, params: str = ""):
    """Preview what a template would extract without running it. Returns resolved workflow."""
    import json as json_mod

    t = ScrapeTemplate.objects.filter(id=template_id).first()
    if not t:
        raise HttpError(404, "Template not found")

    # Parse params from query string
    param_dict = {}
    if params:
        try:
            param_dict = json_mod.loads(params)
        except Exception:
            for pair in params.split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    param_dict[k] = v

    workflow = _substitute_workflow(t.workflow or [], param_dict)

    return {
        "template_id": str(t.id),
        "template_name": t.name,
        "resolved_workflow": workflow,
        "selectors": t.selectors,
        "parameters": t.parameters,
        "output_fields": t.output_fields,
    }


# ── Helpers ─────────────────────────────────────────────────────────────────


def _substitute_workflow(workflow: list[dict], params: dict[str, Any]) -> list[dict]:
    """Substitute {{param}} placeholders in workflow steps."""
    import json

    workflow_str = json.dumps(workflow)
    for key, value in params.items():
        workflow_str = workflow_str.replace(f"{{{{{key}}}}}", str(value))
    return json.loads(workflow_str)


def _extract_url(workflow: list[dict]) -> str:
    """Extract the first URL from a workflow."""
    for step in workflow:
        if step.get("action") == "navigate" and step.get("url"):
            return step["url"]
        if step.get("action") == "fetch" and step.get("url"):
            return step["url"]
    return ""


def _start_workflow_sync(workflow_run, args, workflow_id, task_queue):
    """Start a Temporal workflow synchronously using a background thread."""
    import concurrent.futures

    async def _start():
        from apps.core.lib.temporal_client import get_temporal_client
        client = await get_temporal_client()
        await client.start_workflow(
            workflow_run,
            args,
            id=workflow_id,
            task_queue=task_queue,
        )

    def _run():
        import asyncio
        asyncio.run(_start())

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(_run).result(timeout=15)


def _run_inline(job, urls, selectors, options):
    """Execute full workflow inline with Playwright. Runs in a thread. Full audit trail."""
    from apps.scraper.audit import create_audit_log
    from apps.scraper.models import ScrapeJob

    audit = create_audit_log(str(job.job_id))

    def _execute():
        scrape_result = {"status": "failed", "results": {}, "html": "", "bytes": 0, "error": ""}

        try:
            from playwright.sync_api import sync_playwright

            url = urls[0] if urls else ""
            if not url:
                scrape_result["error"] = "No URL"
                return scrape_result

            workflow_steps = options.get("workflow", [])
            timeout_ms = options.get("timeout", 30) * 1000

            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                )
                context = browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
                page = context.new_page()

                try:
                    # Execute workflow steps with audit tracking
                    if workflow_steps:
                        for step_def in workflow_steps:
                            action = step_def.get("action", "")
                            with audit.step(action, **{k: v for k, v in step_def.items() if k != "action"}) as s:
                                if action in ("navigate", "fetch"):
                                    step_url = step_def.get("url", url)
                                    page.goto(step_url, wait_until="domcontentloaded", timeout=timeout_ms)
                                    try:
                                        page.wait_for_load_state("networkidle", timeout=10000)
                                    except Exception:
                                        pass
                                    s.detail("page_title", page.title())
                                    s.detail("final_url", page.url)
                                elif action == "scroll":
                                    times = step_def.get("times", 3)
                                    for i in range(times):
                                        page.evaluate("window.scrollBy(0, window.innerHeight)")
                                        page.wait_for_timeout(step_def.get("wait_ms", 1500))
                                    s.detail("scroll_times", times)
                                    s.detail("scroll_position", page.evaluate("window.scrollY"))
                                elif action == "click":
                                    sel = step_def.get("selector", "")
                                    if sel:
                                        page.click(sel, timeout=5000)
                                        page.wait_for_timeout(1000)
                                        s.detail("clicked", sel)
                                elif action == "wait":
                                    page.wait_for_timeout(step_def.get("wait_ms", 2000))
                                elif action == "enter_text":
                                    sel, text = step_def.get("selector", ""), step_def.get("text", "")
                                    if sel and text:
                                        try:
                                            page.fill(sel, text, timeout=5000)
                                        except Exception:
                                            page.type(sel, text, delay=50)
                                        s.detail("field", sel)
                                elif action == "extract":
                                    pass  # Handled below
                    else:
                        with audit.step("navigate", url=url):
                            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                            try:
                                page.wait_for_load_state("networkidle", timeout=10000)
                            except Exception:
                                pass

                    # Get HTML
                    with audit.step("capture_html") as s:
                        html = page.content()
                        scrape_result["html"] = html
                        scrape_result["bytes"] = len(html.encode("utf-8"))
                        s.detail("html_bytes", scrape_result["bytes"])
                        s.detail("page_title", page.title())

                    # Extract data with audit
                    with audit.step("extract", selector_count=len(selectors)) as s:
                        if selectors:
                            results = {}
                            for field_name, selector in selectors.items():
                                try:
                                    if not selector:
                                        continue
                                    elements = page.query_selector_all(selector)
                                    if len(elements) == 1:
                                        text = elements[0].inner_text().strip()[:500]
                                        if not text:
                                            text = elements[0].get_attribute("href") or elements[0].get_attribute("src") or ""
                                        results[field_name] = text
                                    elif len(elements) > 1:
                                        results[field_name] = [el.inner_text().strip()[:200] for el in elements[:50]]
                                    else:
                                        results[field_name] = None
                                except Exception:
                                    results[field_name] = None
                            scrape_result["results"] = results
                            s.detail("fields", list(results.keys()))
                            s.detail("field_count", len(results))
                            s.detail("non_null_count", sum(1 for v in results.values() if v is not None))
                        else:
                            scrape_result["results"] = {"raw_html": html[:5000]}
                            s.detail("fields", ["raw_html"])

                    scrape_result["status"] = "succeeded"

                finally:
                    context.close()
                    browser.close()

        except Exception as exc:
            logger.exception("Playwright scrape failed")
            scrape_result["error"] = str(exc)[:500]

        return scrape_result

    # Phase 2: Save results to Django ORM (outside Playwright's event loop)
    result = _execute()

    if result["status"] == "succeeded":
        import json as json_mod

        job.status = ScrapeJob.Status.SUCCEEDED
        job.pages_fetched = 1
        job.bytes_processed = result["bytes"]
        job.save(update_fields=["status", "pages_fetched", "bytes_processed"])

        from apps.scraper.models import ScrapeArtifact

        ScrapeArtifact.objects.create(
            job=job,
            artifact_type="json",
            format="json",
            storage_path=f"scraper/{job.job_id}/result.json",
            source_url=urls[0] if urls else "",
            size_bytes=len(json_mod.dumps(result["results"]).encode()),
            metadata={"fields": list(result["results"].keys())},
        )
        logger.info("Inline scrape succeeded: %d fields", len(result["results"]))
    else:
        job.status = ScrapeJob.Status.FAILED
        job.error_message = result["error"]
        job.save(update_fields=["status", "error_message"])

    # Finalize audit log
    from apps.scraper.audit import finalize_audit_log

    audit_data = finalize_audit_log(str(job.job_id))
    if audit_data:
        job.options = {**(job.options or {}), "audit": audit_data}
        job.save(update_fields=["options"])


# ── Audit Log API ───────────────────────────────────────────────────────────


@template_router.get("/jobs/{job_id}/audit")
def get_job_audit(request, job_id: str):
    """Get the full audit trail for a scrape job — every step, timing, details."""
    from apps.scraper.audit import get_audit_log
    from apps.scraper.models import ScrapeJob

    # Check active logs first
    active_log = get_audit_log(job_id)
    if active_log:
        return active_log.to_dict()

    # Fall back to persisted log in job options
    job = ScrapeJob.objects.filter(job_id=job_id).first()
    if not job:
        raise HttpError(404, "Job not found")

    audit_data = (job.options or {}).get("audit")
    if audit_data:
        return audit_data

    return {"job_id": job_id, "steps": [], "message": "No audit data available"}


@template_router.get("/jobs/{job_id}/audit/live")
def get_job_audit_live(request, job_id: str):
    """Get live audit feed — human-readable step-by-step progress."""
    from apps.scraper.audit import get_audit_log

    log = get_audit_log(job_id)
    if not log:
        return {"job_id": job_id, "feed": [], "summary": {}}

    return {
        "job_id": job_id,
        "feed": log.to_live_feed(),
        "summary": log.summary(),
    }
