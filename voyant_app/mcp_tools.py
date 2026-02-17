"""django-mcp tool registry for Voyant production MCP endpoints."""

import hashlib
import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from django_mcp import mcp_app

logger = logging.getLogger(__name__)


class VoyantTools:
    """HTTP client wrapper for calling Voyant API endpoints from MCP tools."""

    def __init__(self) -> None:
        self.api_url = os.environ.get("VOYANT_API_URL", "http://localhost:8000")
        self.api_token = os.environ.get("VOYANT_API_TOKEN")

    def _call_api(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        with httpx.Client(base_url=self.api_url, headers=headers, timeout=60.0) as client:
            if method == "GET":
                response = client.get(endpoint, params=json_data)
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
