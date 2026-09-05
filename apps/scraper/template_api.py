"""Scraper v4.0 — Template API endpoints."""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.scraper.models import ScrapeTemplate

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
def run_template(request, template_id: str, payload: dict[str, Any]):
    """Execute a template with parameter substitution."""
    from apps.core.lib.workflow_utils import dispatch_workflow
    from apps.worker.workflows.ingest_workflow import IngestDataWorkflow

    t = ScrapeTemplate.objects.filter(id=template_id, status="active").first()
    if not t:
        raise HttpError(404, "Template not found")

    # Substitute parameters in workflow
    params = payload.get("parameters", {})
    workflow = _substitute_workflow(t.workflow, params)

    # Create a scrape job
    from apps.scraper.models import ScrapeJob

    tenant_id = get_tenant_id(request) or "default"
    job = ScrapeJob.objects.create(
        tenant_id=tenant_id,
        urls=[_extract_url(workflow)],
        selectors=t.selectors,
        options=t.options,
    )

    # Update template stats
    t.use_count += 1
    t.save(update_fields=["use_count"])

    return {
        "job_id": str(job.job_id),
        "template_id": str(t.id),
        "template_name": t.name,
        "status": job.status,
    }


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
