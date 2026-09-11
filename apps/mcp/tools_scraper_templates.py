"""
Voyant MCP — scraper template tools (8 tools).

Agent-accessible template operations:
  - List, get, search, create, validate, run, generate, export templates.
"""

import json
import logging

from django_mcp import mcp_app

from apps.core.config import get_settings
from apps.mcp.tools_core import _tenant

logger = logging.getLogger(__name__)
settings = get_settings()


@mcp_app.tool(name="voyant.scraper.templates.list")
def tool_templates_list(category: str = "", tenant_id=None):
    """List all scraper templates, optionally filtered by category."""
    from apps.scraper.models import ScrapeTemplate

    qs = ScrapeTemplate.objects.filter(status="active")
    if category:
        qs = qs.filter(category=category)
    templates = qs.order_by("category", "name")[:100]
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "category": t.category,
            "site_pattern": t.site_pattern,
            "description": t.description,
            "engine": t.engine,
            "use_count": t.use_count,
            "success_rate": t.success_rate,
        }
        for t in templates
    ]


@mcp_app.tool(name="voyant.scraper.templates.get")
def tool_templates_get(template_id: str, tenant_id=None):
    """Get full template details including selectors, workflow, and parameters."""
    from apps.scraper.models import ScrapeTemplate

    t = ScrapeTemplate.objects.filter(id=template_id).first()
    if not t:
        return {"error": "Template not found"}
    return {
        "id": str(t.id),
        "name": t.name,
        "category": t.category,
        "site_pattern": t.site_pattern,
        "description": t.description,
        "engine": t.engine,
        "language": getattr(t, "language", "en"),
        "status": t.status,
        "selectors": t.selectors,
        "workflow": t.workflow,
        "parameters": t.parameters,
        "output_fields": t.output_fields,
        "use_count": t.use_count,
        "success_rate": t.success_rate,
    }


@mcp_app.tool(name="voyant.scraper.templates.search")
def tool_templates_search(query: str, tenant_id=None):
    """Search templates by name, description, or site pattern."""
    from django.db.models import Q

    from apps.scraper.models import ScrapeTemplate

    templates = ScrapeTemplate.objects.filter(
        status="active",
    ).filter(
        Q(name__icontains=query)
        | Q(description__icontains=query)
        | Q(site_pattern__icontains=query)
    )[:20]
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "category": t.category,
            "site_pattern": t.site_pattern,
            "description": t.description,
        }
        for t in templates
    ]


@mcp_app.tool(name="voyant.scraper.templates.create")
def tool_templates_create(
    name: str,
    category: str,
    site_pattern: str,
    workflow: list,
    selectors: dict = None,  # type: ignore[reportArgumentType]
    parameters: list = None,  # type: ignore[reportArgumentType]
    description: str = "",
    engine: str = "playwright",
    output_fields: list = None,  # type: ignore[reportArgumentType]
    tenant_id=None,
):
    """Create a new scraper template programmatically. Agents use this to register new templates."""
    from apps.scraper.models import ScrapeTemplate
    from apps.scraper.template_sdk import validate_template

    template_data = {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "category": category,
        "workflow": workflow,
    }
    errors = validate_template(template_data)
    if errors:
        return {"errors": errors}

    t = ScrapeTemplate.objects.create(
        tenant_id=_tenant(tenant_id),
        name=name,
        category=category,
        site_pattern=site_pattern,
        description=description,
        engine=engine,
        selectors=selectors or {},
        workflow=workflow,
        parameters=parameters or [],
        output_fields=output_fields or [],
        status="active",
    )
    return {"id": str(t.id), "name": t.name, "status": "created"}


@mcp_app.tool(name="voyant.scraper.templates.validate")
def tool_templates_validate(template: dict, tenant_id=None):
    """Validate a template definition against the schema. Returns list of errors."""
    from apps.scraper.template_sdk import validate_template

    errors = validate_template(template)
    return {"valid": len(errors) == 0, "errors": errors}


@mcp_app.tool(name="voyant.scraper.templates.run")
def tool_templates_run(template_id: str, parameters: dict = None, tenant_id=None):  # type: ignore[reportArgumentType]
    """Run a scraper template with the given parameters. Returns job ID."""
    from apps.scraper.models import ScrapeTemplate

    t = ScrapeTemplate.objects.filter(id=template_id).first()
    if not t:
        return {"error": "Template not found"}

    # Substitute parameters into workflow
    workflow = t.workflow or []
    params = parameters or {}
    resolved_workflow = []
    for step in workflow:
        resolved = {}
        for key, value in step.items():
            if isinstance(value, str):
                for param_name, param_value in params.items():
                    value = value.replace(f"{{{{{param_name}}}}}", str(param_value))
            resolved[key] = value
        resolved_workflow.append(resolved)

    # Update use count
    t.use_count = (t.use_count or 0) + 1
    t.save(update_fields=["use_count"])

    return {
        "template": t.name,
        "workflow": resolved_workflow,
        "status": "dispatched",
        "message": "Template workflow resolved. Use scrape.start to execute.",
    }


@mcp_app.tool(name="voyant.scraper.templates.generate")
def tool_templates_generate(url: str, name: str = "", tenant_id=None):
    """Generate a template from a URL using auto-detect. Agent creates templates automatically."""
    import httpx

    from apps.scraper.visual.auto_detect import AutoDetectEngine

    try:
        response = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
        )
        html = response.text
    except Exception as exc:
        return {"error": f"Failed to fetch URL: {exc}"}

    engine = AutoDetectEngine()
    detected = engine.detect(html, url)

    # Build workflow from detected patterns
    workflow = [{"action": "navigate", "url": url}]

    # If we found a list, extract from it
    if detected.get("lists"):
        main_list = detected["lists"][0]
        selectors = {}
        for f in main_list.get("fields", []):
            selectors[f["name"]] = f["selector"]
        workflow.append({"action": "extract", "selectors": selectors})  # type: ignore[reportArgumentType]

    # If we found pagination, add it
    if detected.get("pagination"):
        pag = detected["pagination"][0]
        if pag["type"] == "next_button":
            workflow.append({"action": "click", "selector": pag["selector"]})
            workflow.append({"action": "extract"})

    from urllib.parse import urlparse

    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "")

    template_name = name or f"{domain} Extract"
    category = "universal"

    # Auto-categorize
    social_domains = [
        "facebook.com",
        "instagram.com",
        "twitter.com",
        "tiktok.com",
        "linkedin.com",
    ]
    ecommerce_domains = ["amazon.com", "ebay.com", "walmart.com", "etsy.com"]
    if any(d in domain for d in social_domains):
        category = "social"
    elif any(d in domain for d in ecommerce_domains):
        category = "ecommerce"

    return {
        "name": template_name,
        "category": category,
        "site_pattern": domain,
        "workflow": workflow,
        "detected": {
            "lists": len(detected.get("lists", [])),
            "tables": len(detected.get("tables", [])),
            "pagination": len(detected.get("pagination", [])),
            "forms": len(detected.get("forms", [])),
        },
        "message": "Template generated. Use voyant.scraper.templates.create to save it.",
    }


@mcp_app.tool(name="voyant.scraper.templates.export")
def tool_templates_export(template_id: str, format: str = "json", tenant_id=None):
    """Export a template in the specified format (json, python)."""
    from apps.scraper.models import ScrapeTemplate

    t = ScrapeTemplate.objects.filter(id=template_id).first()
    if not t:
        return {"error": "Template not found"}

    template = {
        "id": str(t.id),
        "name": t.name,
        "category": t.category,
        "site_pattern": t.site_pattern,
        "description": t.description,
        "engine": t.engine,
        "selectors": t.selectors,
        "workflow": t.workflow,
        "parameters": t.parameters,
        "output_fields": t.output_fields,
    }

    if format == "json":
        return {"format": "json", "content": json.dumps(template, indent=2)}
    elif format == "python":
        # Generate TemplateBuilder code
        code_lines = [
            "from apps.scraper.template_sdk import TemplateBuilder",
            "",
            "template = (",
        ]
        code_lines.append(f'    TemplateBuilder("{t.name}")')
        code_lines.append(f'    .category("{t.category}")')
        code_lines.append(f'    .site("{t.site_pattern}")')
        code_lines.append(f'    .description("{t.description}")')
        code_lines.append(f'    .engine("{t.engine}")')

        for p in t.parameters or []:
            code_lines.append(
                f'    .param("{p["name"]}", type="{p.get("type", "string")}", required={p.get("required", False)})'
            )

        for step in t.workflow or []:
            action = step.get("action", "")
            if action == "navigate":
                code_lines.append(f'    .navigate("{step.get("url", "")}")')
            elif action == "click":
                code_lines.append(f'    .click("{step.get("selector", "")}")')
            elif action == "scroll":
                code_lines.append(f"    .scroll(times={step.get('times', 3)})")
            elif action == "extract":
                sels = step.get("selectors", {})
                args = ", ".join(f'{k}="{v}"' for k, v in sels.items())
                code_lines.append(f"    .extract({args})")

        code_lines.append("    .build()")
        code_lines.append(")")
        return {"format": "python", "content": "\n".join(code_lines)}

    return {"error": f"Unsupported format: {format}"}
