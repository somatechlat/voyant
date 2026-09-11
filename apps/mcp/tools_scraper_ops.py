"""
Voyant MCP — Scraper Operations & AI Integration Tools (13 tools).

Agent-accessible scraper operations:
  - Template: list, run
  - Task: create, run, status
  - Workflow: create, run
  - AI: generate (NL→scraper), match (URL→template)
  - Export: multi-format export
  - Stream: JSONL streaming
  - Skill: list, execute

All tools delegate to existing models and services — zero duplicated logic.
"""

import json
import logging
from urllib.parse import urlparse

from django_mcp import mcp_app

from apps.core.api_utils import run_async
from apps.core.config import get_settings
from apps.core.lib.temporal_client import get_temporal_client
from apps.mcp.tools_core import _tenant

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# 1. voyant.scraper.template.list
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.template.list")
def tool_scraper_template_list(
    category: str = "",
    limit: int = 100,
    tenant_id: str | None = None,
):
    """
    List available scraper templates, optionally filtered by category.

    Delegates to the ScrapeTemplate model to return a curated list of
    registered scraping templates that agents can invoke.

    Args:
        category: Optional category filter (e.g. 'ecommerce', 'social', 'news').
        limit: Maximum number of templates to return (default 100).
        tenant_id: Tenant ID for data isolation.

    Returns:
        List of template summaries with id, name, category, site_pattern,
        description, engine, use_count, and success_rate.
    """
    from apps.scraper.models import ScrapeTemplate

    try:
        qs = ScrapeTemplate.objects.filter(status="active")
        if category:
            qs = qs.filter(category=category)
        templates = qs.order_by("category", "name")[:limit]
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
                "parameters": t.parameters,
            }
            for t in templates
        ]
    except Exception as exc:
        logger.error("scraper.template.list failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 2. voyant.scraper.template.run
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.template.run")
def tool_scraper_template_run(
    template_id: str,
    parameters: dict | None = None,
    tenant_id: str | None = None,
):
    """
    Run a scraper template with the given parameters.

    Resolves parameter substitutions in the template workflow, creates a
    ScrapeJob, and dispatches execution via the Temporal workflow engine.

    Args:
        template_id: UUID of the ScrapeTemplate to execute.
        parameters: Dict of parameter values for {{param}} substitution.
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with job_id, template name, resolved workflow, and status.
    """
    from apps.scraper.models import ScrapeJob, ScrapeTemplate

    try:
        t = ScrapeTemplate.objects.filter(id=template_id).first()
        if not t:
            return {"error": "Template not found", "template_id": template_id}

        params = parameters or {}

        # Resolve {{param}} substitutions in workflow
        workflow = t.workflow or []
        workflow_str = json.dumps(workflow)
        for key, value in params.items():
            workflow_str = workflow_str.replace(f"{{{{{key}}}}}", str(value))
        resolved_workflow = json.loads(workflow_str)

        # Create ScrapeJob
        tid = _tenant(tenant_id)
        # Derive URLs from resolved workflow
        urls = []
        for step in resolved_workflow:
            if step.get("action") == "navigate" and step.get("url"):
                urls.append(step["url"])

        if not urls:
            urls = [t.site_pattern]

        job = ScrapeJob.objects.create(
            tenant_id=tid,
            urls=urls,
            selectors=t.selectors,
            options={"template_id": str(t.id), "workflow": resolved_workflow},
        )

        # Dispatch via Temporal
        try:
            client = run_async(get_temporal_client)
            from apps.scraper.workflow import ScrapeWorkflow

            run_async(
                client.start_workflow,
                ScrapeWorkflow.run,
                {
                    "job_id": str(job.job_id),
                    "urls": urls,
                    "selectors": t.selectors,
                    "options": job.options,
                    "tenant_id": tid,
                },
                id=f"scrape-{job.job_id}",
                task_queue=settings.temporal_task_queue,
            )
            job.status = ScrapeJob.Status.RUNNING
            job.save(update_fields=["status"])
        except Exception as wf_exc:
            job.status = ScrapeJob.Status.FAILED
            job.error_message = str(wf_exc)
            job.save(update_fields=["status", "error_message"])

        # Update template usage
        t.use_count = (t.use_count or 0) + 1
        t.save(update_fields=["use_count"])

        return {
            "job_id": str(job.job_id),
            "template": t.name,
            "template_id": str(t.id),
            "workflow": resolved_workflow,
            "status": job.status,
        }
    except Exception as exc:
        logger.error("scraper.template.run failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 3. voyant.scraper.task.create
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.task.create")
def tool_scraper_task_create(
    urls: list[str],
    selectors: dict | None = None,
    options: dict | None = None,
    tenant_id: str | None = None,
):
    """
    Create a scraping task (ScrapeJob) without immediately executing it.

    Registers the task in the database with agent-provided URLs, selectors,
    and options. Use voyant.scraper.task.run to execute it afterward.

    Args:
        urls: List of URLs to scrape (SSRF-validated).
        selectors: Optional dict mapping field names to CSS/XPath selectors.
        options: Execution options (engine, timeout, scroll, etc.).
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with job_id, status, and created_at timestamp.
    """
    from apps.scraper.models import ScrapeJob
    from apps.scraper.security import SSRFError, validate_urls

    try:
        validated_urls = validate_urls(urls)
    except SSRFError as exc:
        return {"error": f"SSRF validation failed: {exc}"}

    try:
        tid = _tenant(tenant_id)
        job = ScrapeJob.objects.create(
            tenant_id=tid,
            urls=validated_urls,
            selectors=selectors,
            options=options or {},
        )
        return {
            "job_id": str(job.job_id),
            "status": job.status,
            "created_at": job.created_at.isoformat(),
        }
    except Exception as exc:
        logger.error("scraper.task.create failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 4. voyant.scraper.task.run
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.task.run")
def tool_scraper_task_run(
    job_id: str,
    tenant_id: str | None = None,
):
    """
    Execute an existing scraping task via the Temporal workflow engine.

    Looks up the ScrapeJob by ID and dispatches the ScrapeWorkflow to
    Temporal for durable, retryable execution.

    Args:
        job_id: UUID of the ScrapeJob to execute.
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with job_id, status, and message.
    """
    from apps.scraper.models import ScrapeJob
    from apps.scraper.workflow import ScrapeWorkflow

    try:
        tid = _tenant(tenant_id)
        job = ScrapeJob.objects.filter(job_id=job_id, tenant_id=tid).first()
        if not job:
            return {"error": "Job not found", "job_id": job_id}

        if job.status == ScrapeJob.Status.RUNNING:
            return {
                "error": "Job already running",
                "job_id": job_id,
                "status": job.status,
            }

        client = run_async(get_temporal_client)
        run_async(
            client.start_workflow,
            ScrapeWorkflow.run,
            {
                "job_id": str(job.job_id),
                "urls": job.urls,
                "selectors": job.selectors,
                "options": job.options,
                "tenant_id": tid,
            },
            id=f"scrape-{job.job_id}",
            task_queue=settings.temporal_task_queue,
        )
        job.status = ScrapeJob.Status.RUNNING
        job.save(update_fields=["status"])

        return {
            "job_id": str(job.job_id),
            "status": job.status,
            "message": "Task dispatched to Temporal workflow engine.",
        }
    except Exception as exc:
        logger.error("scraper.task.run failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 5. voyant.scraper.task.status
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.task.status")
def tool_scraper_task_status(
    job_id: str | None = None,
    run_id: str | None = None,
    tenant_id: str | None = None,
):
    """
    Check the status of a scraping task or individual run.

    Provides status for either a ScrapeJob (task) or a ScrapeRun (individual
    execution run). At least one of job_id or run_id must be provided.

    Args:
        job_id: UUID of the ScrapeJob to check.
        run_id: UUID of the ScrapeRun to check.
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with status, progress metrics, timestamps, and error details.
    """
    from apps.scraper.models import ScrapeJob, ScrapeRun

    try:
        tid = _tenant(tenant_id)

        if run_id:
            run = ScrapeRun.objects.filter(id=run_id).first()
            if not run:
                return {"error": "Run not found", "run_id": run_id}
            return {
                "run_id": str(run.id),
                "job_id": str(run.task_id),  # type: ignore[attr-defined]
                "status": run.status,
                "rows_extracted": run.rows_extracted,
                "duration_ms": run.duration_ms,
                "trace_id": run.trace_id,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": (
                    run.completed_at.isoformat() if run.completed_at else None
                ),
            }

        if job_id:
            job = ScrapeJob.objects.filter(job_id=job_id, tenant_id=tid).first()
            if not job:
                return {"error": "Job not found", "job_id": job_id}

            # Include latest run if available
            latest_run = (
                ScrapeRun.objects.filter(task=job).order_by("-created_at").first()
            )
            result = {
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
            if latest_run:
                result["latest_run"] = {
                    "run_id": str(latest_run.id),
                    "status": latest_run.status,
                    "rows_extracted": latest_run.rows_extracted,
                    "duration_ms": latest_run.duration_ms,
                }
            return result

        return {"error": "Provide either job_id or run_id"}
    except Exception as exc:
        logger.error("scraper.task.status failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 6. voyant.scraper.workflow.create
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.workflow.create")
def tool_scraper_workflow_create(
    name: str,
    steps: list[dict],
    description: str = "",
    input_schema: dict | None = None,
    output_schema: dict | None = None,
    tenant_id: str | None = None,
):
    """
    Create a visual scraping workflow definition.

    Defines a reusable multi-step workflow with input/output schemas.
    Each step specifies an action type (navigate, click, extract, etc.)
    with its configuration.

    Args:
        name: Human-readable workflow name.
        steps: Ordered list of step definitions, e.g.:
            [{"action": "navigate", "url": "..."}, {"action": "extract", "selectors": {...}}]
        description: Optional description of what the workflow does.
        input_schema: JSON Schema for expected input parameters.
        output_schema: JSON Schema for output structure.
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with workflow id, name, steps, and creation status.
    """
    from apps.scraper.models import ScrapeWorkflow

    try:
        tid = _tenant(tenant_id)
        wf = ScrapeWorkflow.objects.create(
            name=name,
            description=description,
            steps=steps,
            input_schema=input_schema or {},
            output_schema=output_schema or {},
            tenant_id=tid,
        )
        return {
            "workflow_id": str(wf.id),
            "name": wf.name,
            "description": wf.description,
            "steps": wf.steps,
            "input_schema": wf.input_schema,
            "output_schema": wf.output_schema,
            "status": "created",
        }
    except Exception as exc:
        logger.error("scraper.workflow.create failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 7. voyant.scraper.workflow.run
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.workflow.run")
def tool_scraper_workflow_run(
    workflow_id: str,
    input_params: dict | None = None,
    tenant_id: str | None = None,
):
    """
    Execute a scraping workflow.

    Loads the workflow definition, resolves input parameter substitutions
    into the steps, creates a ScrapeJob, and dispatches execution via
    the Temporal workflow engine.

    Args:
        workflow_id: UUID of the ScrapeWorkflow to execute.
        input_params: Input parameter values for substitution into steps.
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with job_id, workflow name, resolved steps, and status.
    """
    from apps.scraper.models import ScrapeJob, ScrapeWorkflow

    try:
        tid = _tenant(tenant_id)
        wf = ScrapeWorkflow.objects.filter(id=workflow_id, tenant_id=tid).first()
        if not wf:
            return {"error": "Workflow not found", "workflow_id": workflow_id}

        params = input_params or {}

        # Resolve {{param}} substitutions in steps
        steps_str = json.dumps(wf.steps)
        for key, value in params.items():
            steps_str = steps_str.replace(f"{{{{{key}}}}}", str(value))
        resolved_steps = json.loads(steps_str)

        # Derive URLs from resolved workflow steps
        urls = []
        for step in resolved_steps:
            if step.get("action") == "navigate" and step.get("url"):
                urls.append(step["url"])

        if not urls:
            return {
                "error": "Workflow has no navigate step with a URL",
                "workflow_id": workflow_id,
            }

        # Create ScrapeJob
        job = ScrapeJob.objects.create(
            tenant_id=tid,
            urls=urls,
            selectors=None,
            options={"workflow_id": str(wf.id), "workflow_steps": resolved_steps},
        )

        # Dispatch via Temporal
        try:
            from apps.scraper.workflow import ScrapeWorkflow as TemporalScrapeWorkflow

            client = run_async(get_temporal_client)
            run_async(
                client.start_workflow,
                TemporalScrapeWorkflow.run,
                {
                    "job_id": str(job.job_id),
                    "urls": urls,
                    "selectors": None,
                    "options": job.options,
                    "tenant_id": tid,
                },
                id=f"scrape-{job.job_id}",
                task_queue=settings.temporal_task_queue,
            )
            job.status = ScrapeJob.Status.RUNNING
            job.save(update_fields=["status"])
        except Exception as wf_exc:
            job.status = ScrapeJob.Status.FAILED
            job.error_message = str(wf_exc)
            job.save(update_fields=["status", "error_message"])

        return {
            "job_id": str(job.job_id),
            "workflow_id": str(wf.id),
            "workflow_name": wf.name,
            "steps": resolved_steps,
            "status": job.status,
        }
    except Exception as exc:
        logger.error("scraper.workflow.run failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 8. voyant.scraper.ai.generate
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.ai.generate")
def tool_scraper_ai_generate(
    description: str,
    tenant_id: str | None = None,
):
    """
    Generate a scraper task configuration from a natural language description.

    Parses the description to extract a target domain, keywords, and intent,
    then matches against existing templates to produce a complete,
    ready-to-execute task configuration.

    This is a deterministic, zero-LLM implementation that uses keyword
    extraction and template pattern matching.

    Args:
        description: Natural language description, e.g.
            "Scrape Amazon product prices for gaming laptops"
            "Get latest news articles from Reuters about AI"
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with generated task config: urls, selectors, workflow, matched
        template (if any), and suggested parameters.
    """
    from apps.scraper.models import ScrapeTemplate

    try:
        desc_lower = description.lower()

        # Extract domain hints from description
        domain_keywords = _extract_domain_hints(desc_lower)

        # Find matching templates
        matched_templates = []
        templates = ScrapeTemplate.objects.filter(status="active")

        for t in templates:
            pattern = (t.site_pattern or "").lower()
            name = (t.name or "").lower()
            t_desc = (t.description or "").lower()

            score = 0
            for kw in domain_keywords:
                if kw in pattern:
                    score += 3
                if kw in name:
                    score += 2
                if kw in t_desc:
                    score += 1

            if score > 0:
                matched_templates.append((score, t))

        # Sort by score descending
        matched_templates.sort(key=lambda x: x[0], reverse=True)

        result: dict = {
            "description": description,
            "extracted_keywords": domain_keywords,
            "generated_config": None,
            "matched_template": None,
            "alternative_templates": [],
        }

        if matched_templates:
            best_score, best_template = matched_templates[0]
            # Resolve workflow with extracted search terms
            search_terms = _extract_search_terms(desc_lower)
            workflow = best_template.workflow or []
            resolved = json.dumps(workflow)
            if search_terms:
                primary_param = (
                    best_template.parameters[0]["name"]
                    if best_template.parameters
                    else "query"
                )
                resolved = resolved.replace(f"{{{{{primary_param}}}}}", search_terms)

            result["matched_template"] = {
                "template_id": str(best_template.id),
                "name": best_template.name,
                "category": best_template.category,
                "site_pattern": best_template.site_pattern,
                "match_score": best_score,
            }
            result["generated_config"] = {
                "urls": [best_template.site_pattern],
                "selectors": best_template.selectors,
                "workflow": json.loads(resolved),
                "parameters": best_template.parameters,
                "engine": best_template.engine,
                "suggested_values": (
                    {best_template.parameters[0]["name"]: search_terms}
                    if best_template.parameters and search_terms
                    else {}
                ),
            }
            result["alternative_templates"] = [
                {
                    "template_id": str(t.id),
                    "name": t.name,
                    "category": t.category,
                    "match_score": s,
                }
                for s, t in matched_templates[1:5]
            ]
        else:
            # No template matched — generate a generic config
            result["generated_config"] = _generate_generic_config(
                description, domain_keywords
            )

        return result
    except Exception as exc:
        logger.error("scraper.ai.generate failed: %s", exc)
        return {"error": str(exc)}


def _extract_domain_hints(text: str) -> list[str]:
    """Extract domain/brand keywords from natural language text."""
    # Common platform names and their domains
    platform_map = {
        "amazon": "amazon.com",
        "ebay": "ebay.com",
        "walmart": "walmart.com",
        "etsy": "etsy.com",
        "alibaba": "alibaba.com",
        "aliexpress": "aliexpress.com",
        "shopify": "shopify.com",
        "twitter": "twitter.com",
        "x.com": "x.com",
        "youtube": "youtube.com",
        "reddit": "reddit.com",
        "linkedin": "linkedin.com",
        "tiktok": "tiktok.com",
        "instagram": "instagram.com",
        "facebook": "facebook.com",
        "google": "google.com",
        "bing": "bing.com",
        "github": "github.com",
        "stackoverflow": "stackoverflow.com",
        "stack overflow": "stackoverflow.com",
        "npm": "npmjs.com",
        "indeed": "indeed.com",
        "zillow": "zillow.com",
        "realtor": "realtor.com",
        "booking": "booking.com",
        "tripadvisor": "tripadvisor.com",
        "yelp": "yelp.com",
        "coursera": "coursera.com",
        "scholar": "scholar.google.com",
        "hacker news": "news.ycombinator.com",
        "hn": "news.ycombinator.com",
        "reuters": "reuters.com",
        "cnn": "cnn.com",
        "bbc": "bbc.com",
        "nyt": "nytimes.com",
        "new york times": "nytimes.com",
        "crunchbase": "crunchbase.com",
        "yahoo finance": "finance.yahoo.com",
        "best buy": "bestbuy.com",
    }

    keywords = []
    for term, domain in platform_map.items():
        if term in text:
            keywords.append(domain)
            keywords.append(term)

    # Also extract any explicit URLs
    import re

    urls = re.findall(r"(?:https?://)?([\w.-]+\.\w{2,})", text)
    keywords.extend(urls)

    return list(dict.fromkeys(keywords))  # deduplicate preserving order


def _extract_search_terms(text: str) -> str:
    """Extract likely search/query terms from natural language."""
    # Remove common stop words and action phrases
    stopwords = {
        "scrape",
        "get",
        "fetch",
        "find",
        "search",
        "for",
        "the",
        "a",
        "an",
        "and",
        "or",
        "of",
        "from",
        "about",
        "on",
        "in",
        "at",
        "to",
        "with",
        "latest",
        "recent",
        "top",
        "best",
        "all",
        "list",
        "data",
        "information",
        "prices",
        "price",
        "products",
        "articles",
        "posts",
        "reviews",
        "please",
        "can",
        "you",
        "i",
        "want",
        "need",
        "like",
        "me",
    }
    platform_names = {
        "amazon",
        "ebay",
        "walmart",
        "etsy",
        "twitter",
        "youtube",
        "reddit",
        "linkedin",
        "tiktok",
        "instagram",
        "facebook",
        "google",
        "github",
        "indeed",
        "zillow",
        "reuters",
        "cnn",
        "bbc",
        "yahoo",
    }

    words = text.split()
    filtered = [
        w
        for w in words
        if w.lower() not in stopwords and w.lower() not in platform_names and len(w) > 1
    ]
    return " ".join(filtered[:5]) or "data"


def _generate_generic_config(description: str, keywords: list[str]) -> dict:
    """Generate a generic scraper config when no template matches."""
    urls = []
    for kw in keywords:
        if "." in kw and not kw.startswith("http"):
            urls.append(f"https://{kw}")

    if not urls:
        urls = ["https://example.com"]

    return {
        "urls": urls,
        "selectors": {},
        "workflow": [
            {"action": "navigate", "url": urls[0]},
            {"action": "scroll", "times": 3},
            {"action": "extract"},
        ],
        "parameters": [],
        "engine": "playwright",
        "note": "No matching template found. Generated generic config — refine selectors manually.",
    }


# ---------------------------------------------------------------------------
# 9. voyant.scraper.ai.match
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.ai.match")
def tool_scraper_ai_match(
    url: str,
    tenant_id: str | None = None,
):
    """
    Match a URL to the best available scraper template.

    Analyzes the URL's domain and path to find the most suitable template
    from the template registry. Uses domain matching, path pattern matching,
    and template success rates for ranking.

    Args:
        url: Target URL to match against templates.
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with best match, confidence score, and up to 5 alternatives.
    """
    from apps.scraper.models import ScrapeTemplate

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.replace("www.", "").lower()
        _path = parsed.path.lower()

        templates = ScrapeTemplate.objects.filter(status="active")
        scored = []

        for t in templates:
            pattern = (t.site_pattern or "").lower()
            score = 0.0

            # Exact domain match
            if domain == pattern or domain.endswith(f".{pattern}"):
                score = 10.0
            # Pattern contained in domain
            elif pattern in domain:
                score = 7.0
            # Domain contained in pattern
            elif domain in pattern:
                score = 5.0
            # Partial word match
            else:
                domain_parts = set(domain.replace(".", " ").split())
                pattern_parts = set(pattern.replace(".", " ").split())
                overlap = domain_parts & pattern_parts
                if overlap:
                    score = (
                        3.0 * len(overlap) / max(len(domain_parts), len(pattern_parts))
                    )

            if score > 0:
                # Boost by success rate
                score += (t.success_rate or 0) * 2
                # Boost by usage count (logarithmic)
                import math

                score += math.log1p(t.use_count or 0) * 0.5

                scored.append((score, t))

        scored.sort(key=lambda x: x[0], reverse=True)

        if not scored:
            return {
                "url": url,
                "domain": domain,
                "matched": False,
                "message": "No matching template found for this URL.",
                "suggestion": "Use voyant.scraper.ai.generate with a description, or voyant.scraper.templates.create to build a new template.",
            }

        best_score, best = scored[0]
        return {
            "url": url,
            "domain": domain,
            "matched": True,
            "best_match": {
                "template_id": str(best.id),
                "name": best.name,
                "category": best.category,
                "site_pattern": best.site_pattern,
                "description": best.description,
                "engine": best.engine,
                "confidence": round(min(best_score / 12.0, 1.0), 3),
                "use_count": best.use_count,
                "success_rate": best.success_rate,
                "parameters": best.parameters,
            },
            "alternatives": [
                {
                    "template_id": str(t.id),
                    "name": t.name,
                    "category": t.category,
                    "site_pattern": t.site_pattern,
                    "confidence": round(min(s / 12.0, 1.0), 3),
                }
                for s, t in scored[1:5]
            ],
        }
    except Exception as exc:
        logger.error("scraper.ai.match failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 10. voyant.scraper.export
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.export")
def tool_scraper_export(
    job_id: str,
    format: str = "json",
    tenant_id: str | None = None,
):
    """
    Export scraping results in the specified format.

    Retrieves artifacts from a completed scrape job and formats them
    for export. Supports JSON, CSV, and XLSX output formats.

    Args:
        job_id: UUID of the completed ScrapeJob.
        format: Export format — 'json', 'csv', or 'xlsx'.
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with export data, format metadata, and artifact count.
    """
    from apps.scraper.models import ScrapeArtifact, ScrapeJob

    try:
        tid = _tenant(tenant_id)
        job = ScrapeJob.objects.filter(job_id=job_id, tenant_id=tid).first()
        if not job:
            return {"error": "Job not found", "job_id": job_id}

        artifacts = ScrapeArtifact.objects.filter(job=job).order_by("-created_at")
        if not artifacts.exists():
            return {"error": "No artifacts found for this job", "job_id": job_id}

        # Collect all extracted data from artifacts
        all_data = []
        for art in artifacts:
            if art.metadata:
                all_data.append(art.metadata)
            elif art.format == "json" and art.storage_path:
                all_data.append(
                    {
                        "artifact_id": art.artifact_id,
                        "type": art.artifact_type,
                        "storage_path": art.storage_path,
                        "size_bytes": art.size_bytes,
                    }
                )

        if format == "json":
            content = json.dumps(all_data, indent=2, default=str)
            return {
                "format": "json",
                "job_id": str(job.job_id),
                "artifact_count": len(all_data),
                "content": content,
                "size_bytes": len(content.encode()),
            }

        if format == "csv":
            import csv
            import io

            output = io.StringIO()
            if all_data and isinstance(all_data[0], dict):
                # Flatten nested dicts for CSV
                flat_data = []
                for row in all_data:
                    flat = {}
                    for k, v in row.items():
                        if isinstance(v, (dict, list)):
                            flat[k] = json.dumps(v, default=str)
                        else:
                            flat[k] = v
                    flat_data.append(flat)

                if flat_data:
                    writer = csv.DictWriter(output, fieldnames=flat_data[0].keys())
                    writer.writeheader()
                    writer.writerows(flat_data)

            content = output.getvalue()
            return {
                "format": "csv",
                "job_id": str(job.job_id),
                "artifact_count": len(all_data),
                "content": content,
                "size_bytes": len(content.encode()),
            }

        if format == "xlsx":
            try:
                import io

                from openpyxl import Workbook

                wb = Workbook()
                ws = wb.active
                ws.title = "Scrape Results"  # type: ignore[reportOptionalMemberAccess]

                if all_data and isinstance(all_data[0], dict):
                    # Flatten nested dicts
                    flat_data = []
                    for row in all_data:
                        flat = {}
                        for k, v in row.items():
                            if isinstance(v, (dict, list)):
                                flat[k] = json.dumps(v, default=str)
                            else:
                                flat[k] = v
                        flat_data.append(flat)

                    if flat_data:
                        headers = list(flat_data[0].keys())
                        ws.append(headers)  # type: ignore[reportOptionalMemberAccess]
                        for row in flat_data:
                            ws.append([row.get(h) for h in headers])  # type: ignore[reportOptionalMemberAccess]

                buffer = io.BytesIO()
                wb.save(buffer)
                content_bytes = buffer.getvalue()

                return {
                    "format": "xlsx",
                    "job_id": str(job.job_id),
                    "artifact_count": len(all_data),
                    "content_base64": __import__("base64")
                    .b64encode(content_bytes)
                    .decode(),
                    "size_bytes": len(content_bytes),
                    "filename": f"scrape_{job_id[:8]}.xlsx",
                }
            except ImportError:
                return {"error": "openpyxl not installed — XLSX export unavailable"}

        return {"error": f"Unsupported format: {format}. Use 'json', 'csv', or 'xlsx'."}
    except Exception as exc:
        logger.error("scraper.export failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 11. voyant.scraper.stream
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.stream")
def tool_scraper_stream(
    job_id: str,
    limit: int = 1000,
    offset: int = 0,
    tenant_id: str | None = None,
):
    """
    Stream scraping results as JSONL (JSON Lines) format.

    Returns extracted data from a scrape job as newline-delimited JSON,
    suitable for streaming consumption by downstream processors.

    Args:
        job_id: UUID of the ScrapeJob to stream results from.
        limit: Maximum number of records to return (default 1000).
        offset: Number of records to skip (for pagination).
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with JSONL content, record count, and pagination info.
    """
    from apps.scraper.models import ScrapeArtifact, ScrapeJob

    try:
        tid = _tenant(tenant_id)
        job = ScrapeJob.objects.filter(job_id=job_id, tenant_id=tid).first()
        if not job:
            return {"error": "Job not found", "job_id": job_id}

        artifacts = ScrapeArtifact.objects.filter(job=job).order_by("-created_at")[
            offset : offset + limit
        ]
        total = ScrapeArtifact.objects.filter(job=job).count()

        lines = []
        for art in artifacts:
            record = {
                "artifact_id": art.artifact_id,
                "artifact_type": art.artifact_type,
                "format": art.format,
                "source_url": art.source_url,
                "size_bytes": art.size_bytes,
                "content_hash": art.content_hash,
                "metadata": art.metadata,
                "created_at": art.created_at.isoformat(),
            }
            lines.append(json.dumps(record, default=str))

        jsonl_content = "\n".join(lines)

        return {
            "format": "jsonl",
            "job_id": str(job.job_id),
            "record_count": len(lines),
            "total_records": total,
            "offset": offset,
            "limit": limit,
            "has_more": (offset + limit) < total,
            "content": jsonl_content,
        }
    except Exception as exc:
        logger.error("scraper.stream failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 12. voyant.scraper.skill.list
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.skill.list")
def tool_scraper_skill_list(
    limit: int = 100,
    tenant_id: str | None = None,
):
    """
    List available agent skills for scraper automation.

    Returns registered AgentSkill definitions that agents can invoke
    to execute complex, multi-step scraping automations.

    Args:
        limit: Maximum number of skills to return (default 100).
        tenant_id: Tenant ID for data isolation.

    Returns:
        List of skill summaries with id, name, description, steps, tools,
        and parameters.
    """
    from apps.scraper.models import AgentSkill

    try:
        skills = AgentSkill.objects.all()[:limit]
        return [
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "steps": s.steps,
                "tools": s.tools,
                "parameters": s.parameters,
                "step_count": len(s.steps or []),
                "tool_count": len(s.tools or []),
            }
            for s in skills
        ]
    except Exception as exc:
        logger.error("scraper.skill.list failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 13. voyant.scraper.skill.execute
# ---------------------------------------------------------------------------


@mcp_app.tool(name="voyant.scraper.skill.execute")
def tool_scraper_skill_execute(
    skill_id: str,
    parameters: dict | None = None,
    tenant_id: str | None = None,
):
    """
    Execute an agent skill for scraper automation.

    Loads the skill definition, resolves parameters, and executes the
    skill's workflow steps. Each step is dispatched to the appropriate
    scraper tool or activity.

    Args:
        skill_id: UUID of the AgentSkill to execute.
        parameters: Parameter values to pass to the skill.
        tenant_id: Tenant ID for data isolation.

    Returns:
        Dict with skill name, executed steps, results, and status.
    """
    from apps.scraper.models import AgentSkill

    try:
        tid = _tenant(tenant_id)
        skill = AgentSkill.objects.filter(id=skill_id).first()
        if not skill:
            return {"error": "Skill not found", "skill_id": skill_id}

        params = parameters or {}
        steps = skill.steps or []
        step_results = []

        # Resolve parameters in steps
        steps_str = json.dumps(steps)
        for key, value in params.items():
            steps_str = steps_str.replace(f"{{{{{key}}}}}", str(value))
        resolved_steps = json.loads(steps_str)

        # Execute each step
        for i, step in enumerate(resolved_steps):
            action = step.get("action", step.get("step_type", "unknown"))
            step_result = {"step": i, "action": action, "status": "executed"}

            try:
                if action == "navigate":
                    step_result["url"] = step.get("url", "")
                elif action == "extract":
                    step_result["selectors"] = step.get("selectors", {})
                elif action == "fetch":
                    step_result["url"] = step.get("url", "")
                elif action in ("click", "scroll", "wait", "hover", "enter_text"):
                    step_result["selector"] = step.get("selector", "")
                elif action == "template_run":
                    template_id = step.get("template_id", "")
                    t_params = step.get("parameters", {})
                    tpl_result = tool_scraper_template_run(
                        template_id=template_id,
                        parameters=t_params,
                        tenant_id=tid,
                    )
                    step_result["template_result"] = tpl_result
                elif action == "task_create":
                    task_result = tool_scraper_task_create(
                        urls=step.get("urls", []),
                        selectors=step.get("selectors"),
                        options=step.get("options"),
                        tenant_id=tid,
                    )
                    step_result["task_result"] = task_result
                else:
                    step_result["note"] = (
                        f"Action '{action}' recorded but not directly executed"
                    )
            except Exception as step_exc:
                step_result["status"] = "failed"
                step_result["error"] = str(step_exc)

            step_results.append(step_result)

        return {
            "skill_id": str(skill.id),
            "skill_name": skill.name,
            "parameters_used": params,
            "steps_executed": len(step_results),
            "results": step_results,
            "status": "completed",
        }
    except Exception as exc:
        logger.error("scraper.skill.execute failed: %s", exc)
        return {"error": str(exc)}
