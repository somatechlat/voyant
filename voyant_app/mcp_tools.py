"""django-mcp tool registry for Voyant production MCP endpoints."""

import hashlib
import logging
from typing import Any, Dict, List, Optional

import httpx
from django_mcp import mcp_app

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)


class VoyantTools:
    """HTTP client wrapper for calling Voyant API endpoints from MCP tools."""

    def __init__(self) -> None:
        settings = get_settings()
        self.api_url = settings.mcp_api_url
        self.api_token = settings.mcp_api_token or None

    def _call_api(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not self.api_url:
            raise RuntimeError("VOYANT_MCP_API_URL must be configured for MCP API calls")
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        with httpx.Client(base_url=self.api_url, headers=headers, timeout=60.0) as client:
            if method == "GET":
                response = client.get(endpoint, params=json_data)
            elif method == "DELETE":
                response = client.delete(endpoint, params=json_data)
            elif method == "PUT":
                response = client.put(endpoint, json=json_data)
            elif method == "PATCH":
                response = client.patch(endpoint, json=json_data)
            else:
                response = client.post(endpoint, json=json_data)
            response.raise_for_status()
            return response.json()


voyant_tools = VoyantTools()


def _stable_source_name(source_type: str, hint: str) -> str:
    digest = hashlib.sha1(hint.encode("utf-8")).hexdigest()[:10]
    return f"{source_type}-{digest}"


@mcp_app.tool(name="voyant.discover")
def tool_voyant_discover(hint: str) -> Dict[str, Any]:
    logger.info("voyant.discover called")
    return voyant_tools._call_api("POST", "/v1/sources/discover", {"hint": hint})


@mcp_app.tool(name="voyant.connect")
def tool_voyant_connect(
    hint: str,
    credentials: Optional[Dict[str, Any]] = None,
    destination: str = "iceberg",
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    logger.info("voyant.connect called")
    discovered = voyant_tools._call_api("POST", "/v1/sources/discover", {"hint": hint})
    source_type = discovered.get("source_type", "unknown")
    detected_properties = discovered.get("detected_properties", {})
    source_name = (options or {}).get("name") or _stable_source_name(source_type, hint)
    payload = {
        "name": source_name,
        "source_type": source_type,
        "connection_config": {
            "hint": hint,
            "destination": destination,
            "detected_properties": detected_properties,
            "options": options or {},
        },
        "credentials": credentials,
    }
    return voyant_tools._call_api("POST", "/v1/sources", payload)


@mcp_app.tool(name="voyant.ingest")
def tool_voyant_ingest(
    source_id: str,
    mode: str = "full",
    tables: Optional[List[str]] = None,
) -> Dict[str, Any]:
    logger.info("voyant.ingest called")
    return voyant_tools._call_api(
        "POST",
        "/v1/jobs/ingest",
        {"source_id": source_id, "mode": mode, "tables": tables},
    )


@mcp_app.tool(name="voyant.profile")
def tool_voyant_profile(
    source_id: str,
    table: Optional[str] = None,
    sample_size: int = 10000,
) -> Dict[str, Any]:
    logger.info("voyant.profile called")
    return voyant_tools._call_api(
        "POST",
        "/v1/jobs/profile",
        {"source_id": source_id, "table": table, "sample_size": sample_size},
    )


@mcp_app.tool(name="voyant.quality")
def tool_voyant_quality(
    source_id: str,
    table: Optional[str] = None,
    checks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    logger.info("voyant.quality called")
    return voyant_tools._call_api(
        "POST",
        "/v1/jobs/quality",
        {"source_id": source_id, "table": table, "checks": checks},
    )


@mcp_app.tool(name="voyant.analyze")
def tool_voyant_analyze(
    source_id: Optional[str] = None,
    table: Optional[str] = None,
    tables: Optional[List[str]] = None,
    sample_size: int = 10000,
    kpis: Optional[List[Dict[str, Any]]] = None,
    analyzers: Optional[List[str]] = None,
    profile: bool = True,
    run_analyzers: bool = True,
    generate_artifacts: bool = True,
) -> Dict[str, Any]:
    logger.info("voyant.analyze called")
    return voyant_tools._call_api(
        "POST",
        "/v1/analyze",
        {
            "source_id": source_id,
            "table": table,
            "tables": tables,
            "sample_size": sample_size,
            "kpis": kpis,
            "analyzers": analyzers,
            "profile": profile,
            "run_analyzers": run_analyzers,
            "generate_artifacts": generate_artifacts,
        },
    )


@mcp_app.tool(name="voyant.kpi")
def tool_voyant_kpi(
    sql: str,
    source_id: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    logger.info("voyant.kpi called")
    return voyant_tools._call_api(
        "POST",
        "/v1/sql/query",
        {
            "sql": sql,
            "source_id": source_id,
            "parameters": parameters,
            "query_type": "kpi",
        },
    )


@mcp_app.tool(name="voyant.status")
def tool_voyant_status(job_id: str) -> Dict[str, Any]:
    logger.info("voyant.status called")
    return voyant_tools._call_api("GET", f"/v1/jobs/{job_id}")


@mcp_app.tool(name="voyant.artifact")
def tool_voyant_artifact(
    job_id: str,
    artifact_type: str,
    format: str = "json",
) -> Dict[str, Any]:
    logger.info("voyant.artifact called")
    return voyant_tools._call_api(
        "GET",
        f"/v1/artifacts/{job_id}/{artifact_type}",
        {"format": format},
    )


@mcp_app.tool(name="voyant.sql")
def tool_voyant_sql(sql: str, limit: int = 1000) -> Dict[str, Any]:
    logger.info("voyant.sql called")
    return voyant_tools._call_api("POST", "/v1/sql/query", {"sql": sql, "limit": limit})


@mcp_app.tool(name="voyant.search")
def tool_voyant_search(
    query: str,
    types: Optional[List[str]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    logger.info("voyant.search called")
    return voyant_tools._call_api(
        "GET",
        "/v1/governance/search",
        {"query": query, "types": ",".join(types or []), "limit": limit},
    )


@mcp_app.tool(name="voyant.lineage")
def tool_voyant_lineage(
    urn: str,
    direction: str = "both",
    depth: int = 3,
) -> Dict[str, Any]:
    logger.info("voyant.lineage called")
    return voyant_tools._call_api(
        "GET",
        f"/v1/governance/lineage/{urn}",
        {"direction": direction, "depth": depth},
    )


@mcp_app.tool(name="voyant.preset")
def tool_voyant_preset(
    preset_name: str,
    source_id: str,
    parameters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    logger.info("voyant.preset called")
    return voyant_tools._call_api(
        "POST",
        f"/v1/presets/{preset_name}/execute",
        {"source_id": source_id, "parameters": parameters},
    )


@mcp_app.tool(name="voyant.sources.list")
def tool_voyant_sources_list() -> List[Dict[str, Any]]:
    logger.info("voyant.sources.list called")
    return voyant_tools._call_api("GET", "/v1/sources")


@mcp_app.tool(name="voyant.sources.get")
def tool_voyant_sources_get(source_id: str) -> Dict[str, Any]:
    logger.info("voyant.sources.get called")
    return voyant_tools._call_api("GET", f"/v1/sources/{source_id}")


@mcp_app.tool(name="voyant.sources.delete")
def tool_voyant_sources_delete(source_id: str) -> Dict[str, Any]:
    logger.info("voyant.sources.delete called")
    return voyant_tools._call_api("DELETE", f"/v1/sources/{source_id}")


@mcp_app.tool(name="voyant.jobs.list")
def tool_voyant_jobs_list(
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    logger.info("voyant.jobs.list called")
    return voyant_tools._call_api(
        "GET",
        "/v1/jobs",
        {"status": status, "job_type": job_type, "limit": limit},
    )


@mcp_app.tool(name="voyant.jobs.cancel")
def tool_voyant_jobs_cancel(job_id: str) -> Dict[str, Any]:
    logger.info("voyant.jobs.cancel called")
    return voyant_tools._call_api("POST", f"/v1/jobs/{job_id}/cancel")


@mcp_app.tool(name="voyant.artifacts.list")
def tool_voyant_artifacts_list(job_id: str) -> Dict[str, Any]:
    logger.info("voyant.artifacts.list called")
    return voyant_tools._call_api("GET", f"/v1/artifacts/{job_id}")


@mcp_app.tool(name="voyant.tables.list")
def tool_voyant_tables_list(schema_name: Optional[str] = None) -> Dict[str, Any]:
    logger.info("voyant.tables.list called")
    return voyant_tools._call_api("GET", "/v1/sql/tables", {"schema": schema_name})


@mcp_app.tool(name="voyant.tables.columns")
def tool_voyant_tables_columns(
    table: str,
    schema_name: Optional[str] = None,
) -> Dict[str, Any]:
    logger.info("voyant.tables.columns called")
    return voyant_tools._call_api(
        "GET",
        f"/v1/sql/tables/{table}/columns",
        {"schema": schema_name},
    )


@mcp_app.tool(name="voyant.governance.schema")
def tool_voyant_governance_schema(urn: str) -> Dict[str, Any]:
    logger.info("voyant.governance.schema called")
    return voyant_tools._call_api("GET", f"/v1/governance/schema/{urn}")


@mcp_app.tool(name="voyant.quotas.tiers")
def tool_voyant_quotas_tiers() -> List[Dict[str, Any]]:
    logger.info("voyant.quotas.tiers called")
    return voyant_tools._call_api("GET", "/v1/governance/quotas/tiers")


@mcp_app.tool(name="voyant.quotas.usage")
def tool_voyant_quotas_usage() -> Dict[str, Any]:
    logger.info("voyant.quotas.usage called")
    return voyant_tools._call_api("GET", "/v1/governance/quotas/usage")


@mcp_app.tool(name="voyant.quotas.limits")
def tool_voyant_quotas_limits() -> Dict[str, Any]:
    logger.info("voyant.quotas.limits called")
    return voyant_tools._call_api("GET", "/v1/governance/quotas/limits")


@mcp_app.tool(name="voyant.quotas.set_tier")
def tool_voyant_quotas_set_tier(tier: str) -> Dict[str, Any]:
    logger.info("voyant.quotas.set_tier called")
    return voyant_tools._call_api("POST", "/v1/governance/quotas/tier", {"tier": tier})


@mcp_app.tool(name="voyant.presets.list")
def tool_voyant_presets_list(category: Optional[str] = None) -> Dict[str, Any]:
    logger.info("voyant.presets.list called")
    return voyant_tools._call_api("GET", "/v1/presets", {"category": category})


@mcp_app.tool(name="voyant.presets.get")
def tool_voyant_presets_get(preset_name: str) -> Dict[str, Any]:
    logger.info("voyant.presets.get called")
    return voyant_tools._call_api("GET", f"/v1/presets/{preset_name}")


@mcp_app.tool(name="voyant.kpi_templates.list")
def tool_voyant_kpi_templates_list(category: Optional[str] = None) -> List[Dict[str, Any]]:
    logger.info("voyant.kpi_templates.list called")
    return voyant_tools._call_api("GET", "/v1/presets/kpi-templates", {"category": category})


@mcp_app.tool(name="voyant.kpi_templates.categories")
def tool_voyant_kpi_templates_categories() -> List[str]:
    logger.info("voyant.kpi_templates.categories called")
    return voyant_tools._call_api("GET", "/v1/presets/kpi-templates/categories")


@mcp_app.tool(name="voyant.kpi_templates.get")
def tool_voyant_kpi_templates_get(template_name: str) -> Dict[str, Any]:
    logger.info("voyant.kpi_templates.get called")
    return voyant_tools._call_api("GET", f"/v1/presets/kpi-templates/{template_name}")


@mcp_app.tool(name="voyant.kpi_templates.render")
def tool_voyant_kpi_templates_render(
    template_name: str,
    parameters: Dict[str, str],
) -> Dict[str, Any]:
    logger.info("voyant.kpi_templates.render called")
    return voyant_tools._call_api(
        "POST",
        f"/v1/presets/kpi-templates/{template_name}/render",
        {"parameters": parameters},
    )


@mcp_app.tool(name="voyant.discovery.services.list")
def tool_voyant_discovery_services_list(tag: Optional[str] = None) -> List[Dict[str, Any]]:
    logger.info("voyant.discovery.services.list called")
    return voyant_tools._call_api("GET", "/v1/discovery/services", {"tag": tag})


@mcp_app.tool(name="voyant.discovery.services.get")
def tool_voyant_discovery_services_get(name: str) -> Dict[str, Any]:
    logger.info("voyant.discovery.services.get called")
    return voyant_tools._call_api("GET", f"/v1/discovery/services/{name}")


@mcp_app.tool(name="voyant.discovery.services.register")
def tool_voyant_discovery_services_register(
    name: str,
    base_url: str,
    spec_url: Optional[str] = None,
    version: str = "1.0.0",
    owner: str = "unknown",
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    logger.info("voyant.discovery.services.register called")
    return voyant_tools._call_api(
        "POST",
        "/v1/discovery/services",
        {
            "name": name,
            "base_url": base_url,
            "spec_url": spec_url,
            "version": version,
            "owner": owner,
            "tags": tags or [],
        },
    )


@mcp_app.tool(name="voyant.discovery.scan")
def tool_voyant_discovery_scan(url: str) -> Dict[str, Any]:
    logger.info("voyant.discovery.scan called")
    return voyant_tools._call_api("POST", "/v1/discovery/scan", {"url": url})


@mcp_app.tool(name="voyant.vector.search")
def tool_voyant_vector_search(
    query: str,
    limit: int = 5,
    filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    logger.info("voyant.vector.search called")
    return voyant_tools._call_api(
        "POST",
        "/v1/search/query",
        {"query": query, "limit": limit, "filters": filters},
    )


@mcp_app.tool(name="voyant.vector.index")
def tool_voyant_vector_index(
    text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    logger.info("voyant.vector.index called")
    return voyant_tools._call_api(
        "POST",
        "/v1/search/index",
        {"text": text, "metadata": metadata},
    )


@mcp_app.tool(name="scrape.fetch")
def tool_scrape_fetch(
    url: str,
    engine: str = "playwright",
    wait_for: Optional[str] = None,
    scroll: bool = False,
    timeout: int = 30,
) -> Dict[str, Any]:
    logger.info("scrape.fetch called")
    return voyant_tools._call_api(
        "POST",
        "/v1/scrape/fetch",
        {
            "url": url,
            "engine": engine,
            "wait_for": wait_for,
            "scroll": scroll,
            "timeout": timeout,
        },
    )


@mcp_app.tool(name="scrape.extract")
def tool_scrape_extract(html: str, selectors: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("scrape.extract called")
    return voyant_tools._call_api(
        "POST",
        "/v1/scrape/extract",
        {"html": html, "selectors": selectors},
    )


@mcp_app.tool(name="scrape.ocr")
def tool_scrape_ocr(image_url: str, language: str = "spa+eng") -> Dict[str, Any]:
    logger.info("scrape.ocr called")
    return voyant_tools._call_api(
        "POST",
        "/v1/scrape/ocr",
        {"image_url": image_url, "language": language},
    )


@mcp_app.tool(name="scrape.parse_pdf")
def tool_scrape_parse_pdf(pdf_url: str, extract_tables: bool = False) -> Dict[str, Any]:
    logger.info("scrape.parse_pdf called")
    return voyant_tools._call_api(
        "POST",
        "/v1/scrape/parse_pdf",
        {"pdf_url": pdf_url, "extract_tables": extract_tables},
    )


@mcp_app.tool(name="scrape.transcribe")
def tool_scrape_transcribe(media_url: str, language: str = "es") -> Dict[str, Any]:
    logger.info("scrape.transcribe called")
    return voyant_tools._call_api(
        "POST",
        "/v1/scrape/transcribe",
        {"media_url": media_url, "language": language},
    )
