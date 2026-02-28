"""Central MCP tool registry for Voyant."""

import httpx
from django_mcp import mcp_app

from apps.core.api_utils import run_async
from apps.core.config import get_settings
from apps.core.lib.embeddings import get_embedding_extractor
from apps.core.lib.kpi_templates import (
    get_categories as kpi_categories,
)
from apps.core.lib.kpi_templates import (
    get_template as kpi_get,
)
from apps.core.lib.kpi_templates import (
    list_templates as kpi_list,
)
from apps.core.lib.kpi_templates import (
    render_template as kpi_render,
)
from apps.core.lib.temporal_client import get_temporal_client
from apps.core.lib.tenant_quotas import QuotaTier, get_quota_manager, set_tenant_tier
from apps.core.lib.trino import get_trino_client
from apps.core.lib.vector_store import get_vector_store
from apps.discovery.lib.catalog import ServiceDef, get_discovery_repo
from apps.discovery.lib.spec_parser import SpecParser
from apps.discovery.models import Source
from apps.discovery.source_detection import detect_source_type
from apps.governance.api import _quota_usage_for_tenant
from apps.scraper.activities import ScrapeActivities
from apps.uptp_core.engine import UPTPExecutionEngine
from apps.uptp_core.schemas import TemplateExecutionRequest
from apps.worker.workflows.analyze_workflow import AnalyzeWorkflow
from apps.worker.workflows.ingest_workflow import IngestDataWorkflow
from apps.worker.workflows.profile_workflow import ProfileWorkflow
from apps.worker.workflows.quality_workflow import QualityWorkflow
from apps.worker.workflows.types import IngestParams
from apps.workflows.models import Artifact, Job, PresetJob

settings = get_settings()


def _tenant(tenant_id):
    return tenant_id or "default"


def _start_workflow(workflow_cls, workflow_id, payload):
    client = run_async(get_temporal_client)
    run_async(
        client.start_workflow,
        workflow_cls.run,
        payload,
        id=workflow_id,
        task_queue=settings.temporal_task_queue,
    )


@mcp_app.tool(name="voyant.discover")
def tool_discover(hint: str):
    return detect_source_type(hint)


@mcp_app.tool(name="voyant.connect")
def tool_connect(
    name: str,
    source_type: str,
    connection_config,
    credentials=None,
    sync_schedule=None,
    tenant_id=None,
):
    source = Source.objects.create(
        tenant_id=_tenant(tenant_id),
        name=name,
        source_type=source_type,
        status="pending",
        connection_config=connection_config,
        credentials=credentials,
        sync_schedule=sync_schedule,
    )
    return {"source_id": str(source.id), "status": source.status}


@mcp_app.tool(name="voyant.ingest")
def tool_ingest(source_id: str, mode: str = "full", tables=None, tenant_id=None):
    job = Job.objects.create(
        tenant_id=_tenant(tenant_id),
        job_type="ingest",
        source_id=source_id,
        status="queued",
        progress=0,
        parameters={"mode": mode, "tables": tables},
    )
    _start_workflow(
        IngestDataWorkflow,
        f"ingest-{job.job_id}",
        IngestParams(
            job_id=str(job.job_id), source_id=source_id, mode=mode, tables=tables
        ).__dict__,
    )
    job.status = "running"
    job.save(update_fields=["status"])
    return {"job_id": str(job.job_id), "status": job.status}


@mcp_app.tool(name="voyant.profile")
def tool_profile(source_id: str, table=None, sample_size: int = 10000, tenant_id=None):
    job = Job.objects.create(
        tenant_id=_tenant(tenant_id),
        job_type="profile",
        source_id=source_id,
        status="queued",
        progress=0,
        parameters={"table": table, "sample_size": sample_size},
    )
    _start_workflow(
        ProfileWorkflow,
        f"profile-{job.job_id}",
        {
            "source_id": source_id,
            "table": table,
            "sample_size": sample_size,
            "job_id": str(job.job_id),
            "tenant_id": job.tenant_id,
        },
    )
    job.status = "running"
    job.save(update_fields=["status"])
    return {"job_id": str(job.job_id), "status": job.status}


@mcp_app.tool(name="voyant.quality")
def tool_quality(source_id: str, table=None, checks=None, tenant_id=None):
    job = Job.objects.create(
        tenant_id=_tenant(tenant_id),
        job_type="quality",
        source_id=source_id,
        status="queued",
        progress=0,
        parameters={"table": table, "checks": checks},
    )
    _start_workflow(
        QualityWorkflow,
        f"quality-{job.job_id}",
        {
            "source_id": source_id,
            "table": table,
            "checks": checks,
            "job_id": str(job.job_id),
            "tenant_id": job.tenant_id,
        },
    )
    job.status = "running"
    job.save(update_fields=["status"])
    return {"job_id": str(job.job_id), "status": job.status}


@mcp_app.tool(name="voyant.analyze")
def tool_analyze(
    source_id=None,
    table=None,
    tables=None,
    sample_size: int = 10000,
    kpis=None,
    analyzers=None,
    tenant_id=None,
):
    table_name = table or source_id or (tables[0] if tables else None)
    if not table_name:
        raise ValueError("table or source_id is required")
    job = Job.objects.create(
        tenant_id=_tenant(tenant_id),
        job_type="analyze",
        source_id=source_id or table_name,
        status="queued",
        progress=0,
        parameters={"table": table_name, "sample_size": sample_size},
    )
    _start_workflow(
        AnalyzeWorkflow,
        f"analyze-{job.job_id}",
        {
            "source_id": source_id,
            "table": table_name,
            "tables": tables,
            "sample_size": sample_size,
            "kpis": kpis,
            "analyzers": analyzers,
            "job_id": str(job.job_id),
            "tenant_id": job.tenant_id,
        },
    )
    job.status = "running"
    job.save(update_fields=["status"])
    return {"job_id": str(job.job_id), "status": job.status}


@mcp_app.tool(name="voyant.kpi")
def tool_kpi(kpis, limit: int = 1000):
    client = get_trino_client()
    results = []
    for item in kpis:
        sql = item.get("sql") if isinstance(item, dict) else None
        if not sql:
            continue
        res = client.execute(sql, limit=limit)
        results.append(
            {
                "name": item.get("name", "kpi"),
                "columns": res.columns,
                "rows": res.rows,
                "row_count": res.row_count,
            }
        )
    return {"results": results}


@mcp_app.tool(name="voyant.status")
def tool_status(job_id: str, tenant_id=None):
    job = Job.objects.filter(id=job_id, tenant_id=_tenant(tenant_id)).first()
    if not job:
        raise ValueError("Job not found")
    return {
        "job_id": str(job.job_id),
        "status": job.status,
        "progress": job.progress,
        "result_summary": job.result_summary,
        "error_message": job.error_message,
    }


@mcp_app.tool(name="voyant.artifact")
def tool_artifact(artifact_id: str, tenant_id=None):
    artifact = Artifact.objects.filter(
        artifact_id=artifact_id, tenant_id=_tenant(tenant_id)
    ).first()
    if not artifact:
        raise ValueError("Artifact not found")
    return {
        "artifact_id": artifact.artifact_id,
        "job_id": artifact.job_id,
        "artifact_type": artifact.artifact_type,
        "format": artifact.format,
        "storage_path": artifact.storage_path,
        "size_bytes": artifact.size_bytes,
    }


@mcp_app.tool(name="voyant.sql")
def tool_sql(sql: str, limit: int = 1000):
    res = get_trino_client().execute(sql, limit=limit)
    return {
        "columns": res.columns,
        "rows": res.rows,
        "row_count": res.row_count,
        "truncated": res.truncated,
        "query_id": res.query_id,
    }


@mcp_app.tool(name="voyant.search")
def tool_search(query: str, limit: int = 5, tenant_id=None):
    store = get_vector_store()
    extractor = get_embedding_extractor(model="tfidf", dimensions=128)
    vec = extractor.embed([query]).embeddings[0]
    results = store.search(
        query_vector=vec, k=limit, filter_metadata={"tenant_id": _tenant(tenant_id)}
    )
    return [
        {"id": item.id, "score": score, "metadata": item.metadata}
        for item, score in results
    ]


@mcp_app.tool(name="voyant.lineage")
def tool_lineage(urn: str, direction: str = "both", depth: int = 3):
    query = """
    query lineage($urn: String!, $direction: LineageDirection!, $depth: Int!) {
      lineage(input: { urn: $urn, direction: $direction, depth: $depth }) {
        relationships { entity { urn type } type }
      }
    }
    """
    directions = (
        ["UPSTREAM", "DOWNSTREAM"] if direction == "both" else [direction.upper()]
    )
    edges = []
    nodes = set([urn])
    for d in directions:
        resp = httpx.post(
            f"{settings.datahub_gms_url}/api/graphql",
            json={
                "query": query,
                "variables": {"urn": urn, "direction": d, "depth": min(depth, 10)},
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json().get("data", {}).get("lineage", {}).get("relationships", [])
        for rel in data:
            eurn = rel.get("entity", {}).get("urn", "")
            nodes.add(eurn)
            edges.append(
                {
                    "source": eurn if d == "UPSTREAM" else urn,
                    "target": urn if d == "UPSTREAM" else eurn,
                    "type": rel.get("type", "PRODUCES"),
                }
            )
    return {"nodes": [{"urn": n} for n in nodes], "edges": edges}


@mcp_app.tool(name="voyant.preset")
def tool_preset(preset_name: str, payload, tenant_id=None):
    job = PresetJob.objects.create(
        tenant_id=_tenant(tenant_id),
        preset_name=preset_name,
        source_id=payload.get("source_id", ""),
        parameters=payload,
        status="queued",
    )
    return {"job_id": str(job.job_id), "status": job.status}


@mcp_app.tool(name="voyant.sources.list")
def tool_sources_list(tenant_id=None):
    sources = Source.objects.filter(tenant_id=_tenant(tenant_id)).order_by(
        "-created_at"
    )
    return [
        {
            "source_id": str(s.id),
            "name": s.name,
            "source_type": s.source_type,
            "status": s.status,
        }
        for s in sources
    ]


@mcp_app.tool(name="voyant.sources.get")
def tool_sources_get(source_id: str, tenant_id=None):
    source = Source.objects.filter(id=source_id, tenant_id=_tenant(tenant_id)).first()
    if not source:
        raise ValueError("Source not found")
    return {
        "source_id": str(source.id),
        "name": source.name,
        "source_type": source.source_type,
        "status": source.status,
        "connection_config": source.connection_config,
        "credentials": source.credentials,
    }


@mcp_app.tool(name="voyant.sources.delete")
def tool_sources_delete(source_id: str, tenant_id=None):
    source = Source.objects.filter(id=source_id, tenant_id=_tenant(tenant_id)).first()
    if not source:
        raise ValueError("Source not found")
    source.delete()
    return {"source_id": source_id, "status": "deleted"}


@mcp_app.tool(name="voyant.jobs.list")
def tool_jobs_list(tenant_id=None, status=None, job_type=None, limit: int = 50):
    q = Job.objects.filter(tenant_id=_tenant(tenant_id))
    if status:
        q = q.filter(status=status)
    if job_type:
        q = q.filter(job_type=job_type)
    q = q.order_by("-created_at")[:limit]
    return [
        {
            "job_id": str(j.job_id),
            "job_type": j.job_type,
            "status": j.status,
            "progress": j.progress,
        }
        for j in q
    ]


@mcp_app.tool(name="voyant.jobs.cancel")
def tool_jobs_cancel(job_id: str, tenant_id=None):
    job = Job.objects.filter(id=job_id, tenant_id=_tenant(tenant_id)).first()
    if not job:
        raise ValueError("Job not found")
    try:
        client = run_async(get_temporal_client)
        for prefix in ("ingest", "profile", "quality", "analyze"):
            try:
                handle = client.get_workflow_handle(f"{prefix}-{job_id}")
                run_async(handle.cancel)
                break
            except Exception:
                continue
    except Exception:
        pass
    job.status = "cancelled"
    job.save(update_fields=["status"])
    return {"job_id": str(job.job_id), "status": "cancelled"}


@mcp_app.tool(name="voyant.artifacts.list")
def tool_artifacts_list(job_id: str, tenant_id=None):
    rows = Artifact.objects.filter(
        job_id=job_id, tenant_id=_tenant(tenant_id)
    ).order_by("-created_at")
    return [
        {
            "artifact_id": r.artifact_id,
            "artifact_type": r.artifact_type,
            "format": r.format,
            "storage_path": r.storage_path,
            "size_bytes": r.size_bytes,
        }
        for r in rows
    ]


@mcp_app.tool(name="voyant.tables.list")
def tool_tables_list(schema=None):
    client = get_trino_client()
    tables = client.get_tables(schema)
    return {"tables": tables, "schema": schema or client.schema}


@mcp_app.tool(name="voyant.tables.columns")
def tool_tables_columns(table: str, schema=None):
    columns = get_trino_client().get_columns(table, schema)
    return {"table": table, "columns": columns}


@mcp_app.tool(name="voyant.governance.schema")
def tool_governance_schema(urn: str):
    response = httpx.get(
        f"{settings.datahub_gms_url}/aspects/{urn}?aspect=schemaMetadata", timeout=30.0
    )
    if response.status_code == 404:
        raise ValueError("Schema not found")
    response.raise_for_status()
    schema_data = response.json().get("value", {}).get("schemaMetadata", {})
    fields = [
        {
            "name": f.get("fieldPath", ""),
            "type": f.get("nativeDataType", "unknown"),
            "nullable": f.get("nullable", True),
            "description": f.get("description"),
        }
        for f in schema_data.get("fields", [])
    ]
    return {"urn": urn, "fields": fields}


@mcp_app.tool(name="voyant.quotas.tiers")
def tool_quotas_tiers():
    manager = get_quota_manager()
    return [
        {"tier": t.value, "description": manager.policies[t].description}
        for t in QuotaTier
        if t in manager.policies
    ]


@mcp_app.tool(name="voyant.quotas.usage")
def tool_quotas_usage(tenant_id=None):
    return _quota_usage_for_tenant(_tenant(tenant_id)).model_dump()


@mcp_app.tool(name="voyant.quotas.limits")
def tool_quotas_limits(tenant_id=None):
    return _quota_usage_for_tenant(_tenant(tenant_id)).model_dump()


@mcp_app.tool(name="voyant.quotas.set_tier")
def tool_quotas_set_tier(tier: str, tenant_id=None):
    set_tenant_tier(_tenant(tenant_id), QuotaTier(tier))
    return {"tenant_id": _tenant(tenant_id), "tier": tier, "status": "updated"}


@mcp_app.tool(name="voyant.presets.list")
def tool_presets_list():
    return [
        {
            "preset_name": p.preset_name,
            "status": p.status,
            "source_id": p.source_id,
            "job_id": str(p.job_id),
        }
        for p in PresetJob.objects.order_by("-created_at")[:200]
    ]


@mcp_app.tool(name="voyant.presets.get")
def tool_presets_get(job_id: str):
    p = PresetJob.objects.filter(id=job_id).first()
    if not p:
        raise ValueError("Preset job not found")
    return {
        "job_id": str(p.job_id),
        "preset_name": p.preset_name,
        "status": p.status,
        "parameters": p.parameters,
    }


@mcp_app.tool(name="voyant.kpi_templates.list")
def tool_kpi_templates_list(category=None):
    return kpi_list(category)


@mcp_app.tool(name="voyant.kpi_templates.categories")
def tool_kpi_templates_categories():
    return kpi_categories()


@mcp_app.tool(name="voyant.kpi_templates.get")
def tool_kpi_templates_get(name: str):
    t = kpi_get(name)
    if not t:
        raise ValueError("Template not found")
    return {
        "name": t.name,
        "category": t.category,
        "description": t.description,
        "required_columns": t.required_columns,
        "optional_columns": t.optional_columns,
        "output_columns": t.output_columns,
        "sql": t.sql,
    }


@mcp_app.tool(name="voyant.kpi_templates.render")
def tool_kpi_templates_render(name: str, params):
    return {"sql": kpi_render(name, params)}


@mcp_app.tool(name="voyant.discovery.services.list")
def tool_discovery_services_list(tag=None):
    repo = get_discovery_repo()
    services = repo.search(tag) if tag else repo.list_services()
    return [s.to_dict() for s in services]


@mcp_app.tool(name="voyant.discovery.services.get")
def tool_discovery_services_get(name: str):
    service = get_discovery_repo().get(name)
    if not service:
        raise ValueError("Service not found")
    return service.to_dict()


@mcp_app.tool(name="voyant.discovery.services.register")
def tool_discovery_services_register(
    name: str,
    base_url: str,
    spec_url=None,
    version: str = "1.0.0",
    owner: str = "unknown",
    tags=None,
):
    parser = SpecParser()
    service = ServiceDef(
        name=name,
        base_url=base_url,
        version=version,
        metadata={"owner": owner, "tags": ",".join(tags or [])},
    )
    if spec_url:
        spec = parser.parse_from_url(spec_url)
        service.endpoints = spec.endpoints
        service.version = spec.version or service.version
    reg = get_discovery_repo().register(service)
    return reg.to_dict()


@mcp_app.tool(name="voyant.discovery.scan")
def tool_discovery_scan(url: str):
    spec = SpecParser().parse_from_url(url)
    return {
        "title": spec.title,
        "version": spec.version,
        "endpoint_count": len(spec.endpoints),
        "endpoints": [e.path for e in spec.endpoints[:10]],
    }


@mcp_app.tool(name="voyant.vector.search")
def tool_vector_search(query: str, limit: int = 5, tenant_id=None):
    return tool_search(query=query, limit=limit, tenant_id=tenant_id)


@mcp_app.tool(name="voyant.vector.index")
def tool_vector_index(text: str, metadata=None, item_id=None, tenant_id=None):
    store = get_vector_store()
    extractor = get_embedding_extractor(model="tfidf", dimensions=128)
    embedding_result = extractor.embed([text])
    vector = embedding_result.embeddings[0]
    final_id = item_id or f"vec-{abs(hash((text, _tenant(tenant_id))))}"
    m = metadata or {}
    m["tenant_id"] = _tenant(tenant_id)
    m["text_preview"] = text[:200]
    store.add(id=final_id, vector=vector, metadata=m)
    store.save()
    return {
        "id": final_id,
        "status": "indexed",
        "dimensions": embedding_result.dimensions,
    }


@mcp_app.tool(name="scrape.fetch")
def tool_scrape_fetch(
    url: str,
    engine: str = "playwright",
    wait_for=None,
    scroll: bool = False,
    timeout: int = 30,
    wait_until=None,
    settle_ms=None,
    block_resources=None,
    capture_json: bool = False,
    capture_url_contains=None,
    capture_max_bytes=None,
    capture_max_items=None,
):
    return run_async(
        ScrapeActivities().fetch_page,
        {
            "url": url,
            "engine": engine,
            "wait_for": wait_for,
            "scroll": scroll,
            "timeout": timeout,
            "wait_until": wait_until,
            "settle_ms": settle_ms,
            "block_resources": block_resources,
            "capture_json": capture_json,
            "capture_url_contains": capture_url_contains,
            "capture_max_bytes": capture_max_bytes,
            "capture_max_items": capture_max_items,
        },
    )


@mcp_app.tool(name="scrape.deep_archive")
async def tool_scrape_deep_archive(
    url: str,
    interaction_selectors: list[str] = None,
    download_patterns: list[str] = None,
    target_dir: str = "scrapes/unknown",
    wait_settle_ms: int = 2000,
    timeout_ms: int = 60000,
):
    """
    Generic deep archival web scrape. Connects to the URL and programmatically clicks
    the `interaction_selectors` waiting for the DOM to settle, then matches and downloads
    all files matching the `download_patterns` to the `target_dir`.
    """
    params = {
        "url": url,
        "interaction_selectors": interaction_selectors or [],
        "download_patterns": download_patterns or [],
        "target_dir": target_dir,
        "wait_settle_ms": wait_settle_ms,
        "timeout_ms": timeout_ms,
    }
    return await ScrapeActivities().deep_archive(params)


@mcp_app.tool(name="scrape.extract")
def tool_scrape_extract(html: str, selectors, url: str = ""):
    return run_async(
        ScrapeActivities().extract_data,
        {"html": html, "selectors": selectors, "url": url},
    )


@mcp_app.tool(name="scrape.ocr")
def tool_scrape_ocr(images, language: str = "spa+eng"):
    return run_async(
        ScrapeActivities().process_ocr, {"images": images, "language": language}
    )


@mcp_app.tool(name="scrape.parse_pdf")
def tool_scrape_parse_pdf(pdf_url: str, extract_tables: bool = False):
    return run_async(
        ScrapeActivities().parse_pdf,
        {"pdf_url": pdf_url, "extract_tables": extract_tables},
    )


@mcp_app.tool(name="scrape.transcribe")
def tool_scrape_transcribe(media_urls, language: str = "es"):
    return run_async(
        ScrapeActivities().transcribe_media,
        {"media_urls": media_urls, "language": language},
    )


# --- UPTP Integration ---


@mcp_app.tool(name="voyant.templates.execute")
def tool_execute_template(
    template_id: str, category: str, tenant_id: str, params: dict, job_name: str = None
):
    """
    [UPTP Core Router]
    Universal endpoint for all Data Box operations.
    Passes generic parameters to predefined mathematical/structural templates.
    """
    request_payload = TemplateExecutionRequest(
        template_id=template_id,
        category=category,
        tenant_id=tenant_id,
        params=params,
        job_name=job_name,
    )
    return UPTPExecutionEngine.dispatch_execution(request_payload)
