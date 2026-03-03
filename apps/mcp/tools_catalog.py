"""
Voyant MCP — Catalog, Management & Discovery Tools.

Tools for data catalog operations, resource management, governance, quotas,
KPI templates, service discovery, and vector indexing.

Extracted from mcp/tools.py (Rule 245 compliance — 723-line split).
"""

import httpx
from django_mcp import mcp_app

from apps.analysis.lib.kpi_templates import (
    get_categories as kpi_categories,
)
from apps.analysis.lib.kpi_templates import (
    get_template as kpi_get,
)
from apps.analysis.lib.kpi_templates import (
    list_templates as kpi_list,
)
from apps.analysis.lib.kpi_templates import (
    render_template as kpi_render,
)
from apps.core.api_utils import run_async
from apps.core.config import get_settings
from apps.core.lib.temporal_client import get_temporal_client
from apps.core.lib.tenant_quotas import QuotaTier, get_quota_manager, set_tenant_tier
from apps.core.lib.trino import get_trino_client
from apps.discovery.lib.catalog import ServiceDef, get_discovery_repo
from apps.discovery.lib.spec_parser import SpecParser
from apps.discovery.models import Source
from apps.governance.api import _quota_usage_for_tenant
from apps.mcp.tools_core import _tenant
from apps.search.lib.embeddings import get_embedding_extractor
from apps.search.lib.vector_store import get_vector_store
from apps.workflows.models import Artifact, Job, PresetJob

settings = get_settings()


@mcp_app.tool(name="voyant.lineage")
def tool_lineage(urn: str, direction: str = "both", depth: int = 3):
    """
    Fetch upstream/downstream data lineage from DataHub for a given URN.
    Returns nodes and typed edges up to the specified depth (capped at 10).
    """
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
    """Launch a preset job (named workflow configuration). Returns job_id."""
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
    """List all registered data sources for a tenant."""
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
    """Get full details of a specific data source including connection config."""
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
    """Delete a registered data source by ID."""
    source = Source.objects.filter(id=source_id, tenant_id=_tenant(tenant_id)).first()
    if not source:
        raise ValueError("Source not found")
    source.delete()
    return {"source_id": source_id, "status": "deleted"}


@mcp_app.tool(name="voyant.jobs.list")
def tool_jobs_list(tenant_id=None, status=None, job_type=None, limit: int = 50):
    """List jobs for a tenant, optionally filtered by status and/or job_type."""
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
    """Cancel a running job and its underlying Temporal workflow."""
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
    """List all artifacts generated by a specific job."""
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
    """List all tables available in Trino for the given schema."""
    client = get_trino_client()
    tables = client.get_tables(schema)
    return {"tables": tables, "schema": schema or client.schema}


@mcp_app.tool(name="voyant.tables.columns")
def tool_tables_columns(table: str, schema=None):
    """Get column definitions for a specific Trino table."""
    columns = get_trino_client().get_columns(table, schema)
    return {"table": table, "columns": columns}


@mcp_app.tool(name="voyant.governance.schema")
def tool_governance_schema(urn: str):
    """Retrieve schema metadata from DataHub for a dataset URN."""
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
    """List all available quota tiers with their descriptions."""
    manager = get_quota_manager()
    return [
        {"tier": t.value, "description": manager.policies[t].description}
        for t in QuotaTier
        if t in manager.policies
    ]


@mcp_app.tool(name="voyant.quotas.usage")
def tool_quotas_usage(tenant_id=None):
    """Get current quota usage for a tenant."""
    return _quota_usage_for_tenant(_tenant(tenant_id)).model_dump()


@mcp_app.tool(name="voyant.quotas.limits")
def tool_quotas_limits(tenant_id=None):
    """Get quota limits for a tenant."""
    return _quota_usage_for_tenant(_tenant(tenant_id)).model_dump()


@mcp_app.tool(name="voyant.quotas.set_tier")
def tool_quotas_set_tier(tier: str, tenant_id=None):
    """Assign a quota tier to a tenant."""
    set_tenant_tier(_tenant(tenant_id), QuotaTier(tier))
    return {"tenant_id": _tenant(tenant_id), "tier": tier, "status": "updated"}


@mcp_app.tool(name="voyant.presets.list")
def tool_presets_list():
    """List the 200 most recent preset jobs across all tenants."""
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
    """Get details of a specific preset job by job_id."""
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
    """List available KPI templates, optionally filtered by category."""
    return kpi_list(category)


@mcp_app.tool(name="voyant.kpi_templates.categories")
def tool_kpi_templates_categories():
    """List all KPI template categories."""
    return kpi_categories()


@mcp_app.tool(name="voyant.kpi_templates.get")
def tool_kpi_templates_get(name: str):
    """Get a specific KPI template definition including SQL and column requirements."""
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
    """Render a KPI template with the given parameters, returning executable SQL."""
    return {"sql": kpi_render(name, params)}


@mcp_app.tool(name="voyant.discovery.services.list")
def tool_discovery_services_list(tag=None):
    """List all registered external services, optionally filtered by tag."""
    repo = get_discovery_repo()
    services = repo.search(tag) if tag else repo.list_services()
    return [s.to_dict() for s in services]


@mcp_app.tool(name="voyant.discovery.services.get")
def tool_discovery_services_get(name: str):
    """Get full details of a registered external service by name."""
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
    """Register an external API service, optionally auto-parsing its OpenAPI spec."""
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
    """Parse an OpenAPI spec URL and return endpoint metadata."""
    spec = SpecParser().parse_from_url(url)
    return {
        "title": spec.title,
        "version": spec.version,
        "endpoint_count": len(spec.endpoints),
        "endpoints": [e.path for e in spec.endpoints[:10]],
    }


@mcp_app.tool(name="voyant.vector.search")
def tool_vector_search(query: str, limit: int = 5, tenant_id=None):
    """Semantic vector search over tenant data. Alias for voyant.search."""
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


@mcp_app.tool(name="voyant.vector.index")
def tool_vector_index(text: str, metadata=None, item_id=None, tenant_id=None):
    """Index a text snippet into the vector store for later semantic retrieval."""
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
