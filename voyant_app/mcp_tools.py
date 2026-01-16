"""
Voyant MCP Toolset Implementation using django-mcp 0.3.1.

This module defines Model Context Protocol (MCP) tools for Voyant
using the @mcp_app.tool() decorator from django-mcp.

Tools exposed:
- Voyant Tools (12 tools): discover, connect, ingest, profile, quality, analyze,
  kpi, status, artifact, sql_query, search, lineage, preset
- DataScraper Tools (5 tools): fetch, extract, ocr, parse_pdf, transcribe

Reference: https://pypi.org/project/django-mcp/
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

# Import mcp_app from django-mcp
from django_mcp import mcp_app

logger = logging.getLogger(__name__)


class VoyantTools:
    """
    Voyant data tools for AI agents.

    These tools are automatically registered with django-mcp when @mcp_app.tool()
    decorator is applied.
    """

    def __init__(self):
        self.api_url = "http://localhost:8000"
        self.api_token = None

    def _call_api(self, method: str, endpoint: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Helper to call internal Voyant API (Synchronous).

        VIBE: Real httpx.Client, no mocks.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        # Use sync Client for production reliability
        with httpx.Client(base_url=self.api_url, headers=headers, timeout=60.0) as client:
            if method == "GET":
                response = client.get(endpoint, params=json_data)
            else:
                response = client.post(endpoint, json=json_data)

            response.raise_for_status()
            return response.json()


# Initialize toolset
voyant_tools = VoyantTools()


# =============================================================================
# VOYANT TOOLS - Core Data Platform
# =============================================================================

@mcp_app.tool()
def voyant_discover(hint: str) -> Dict[str, Any]:
    """
    Auto-detect the type of a data source from a hint (URL, path, connection string).

    Args:
        hint: Data source hint (URL, file path, connection string)

    Returns:
        Dict with discovered source type and metadata

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.discover called with hint: {hint[:50]}...")
    return voyant_tools._call_api("POST", "/v1/sources/discover", {"hint": hint})


@mcp_app.tool()
def voyant_connect(
    hint: str,
    credentials: Optional[Dict] = None,
    destination: str = "iceberg",
    options: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Establish a persistent connection to a data source.

    Args:
        hint: Data source hint
        credentials: Connection credentials (optional)
        destination: Target storage destination (iceberg, postgres)
        options: Additional options (optional)

    Returns:
        Dict with source_id and connection details

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.connect called for destination: {destination}")
    return voyant_tools._call_api("POST", "/v1/sources", {
        "hint": hint,
        "credentials": credentials,
        "destination": destination,
        "options": options
    })


@mcp_app.tool()
def voyant_ingest(
    source_id: str,
    mode: str = "full",
    tables: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Trigger data ingestion from a connected source.

    Args:
        source_id: Source ID to ingest from
        mode: Ingestion mode (full, incremental)
        tables: Specific tables to ingest (empty = all)

    Returns:
        Dict with job_id and status

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.ingest called for source_id: {source_id}")
    return voyant_tools._call_api("POST", "/v1/jobs/ingest", {
        "source_id": source_id,
        "mode": mode,
        "tables": tables
    })


@mcp_app.tool()
def voyant_profile(
    source_id: str,
    table: Optional[str] = None,
    sample_size: int = 10000,
) -> Dict[str, Any]:
    """
    Generate exploratory data analysis (EDA) profile for a dataset.

    Args:
        source_id: Source ID to profile
        table: Table name to profile (optional)
        sample_size: Sample size for profiling

    Returns:
        Dict with profile report

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.profile called for source_id: {source_id}")
    return voyant_tools._call_api("POST", "/v1/jobs/profile", {
        "source_id": source_id,
        "table": table,
        "sample_size": sample_size
    })


@mcp_app.tool()
def voyant_quality(
    source_id: str,
    table: Optional[str] = None,
    checks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Run data quality checks on a dataset.

    Args:
        source_id: Source ID to check
        table: Table name (optional)
        checks: Quality checks to run (optional)

    Returns:
        Dict with quality check results

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.quality called for source_id: {source_id}")
    return voyant_tools._call_api("POST", "/v1/jobs/quality", {
        "source_id": source_id,
        "table": table,
        "checks": checks
    })


@mcp_app.tool()
def voyant_analyze(
    source_id: Optional[str] = None,
    table: Optional[str] = None,
    tables: Optional[List[str]] = None,
    sample_size: int = 10000,
    kpis: Optional[List[Dict]] = None,
    analyzers: Optional[List[str]] = None,
    profile: bool = True,
    run_analyzers: bool = True,
    generate_artifacts: bool = True,
) -> Dict[str, Any]:
    """
    Run end-to-end analysis (profile, KPI, analyzers, artifacts).

    Args:
        source_id: Source ID (optional)
        table: Table name (optional)
        tables: Table list (optional)
        sample_size: Sample size for analysis
        kpis: KPI definitions (optional)
        analyzers: Analyzers to run (optional)
        profile: Generate profile
        run_analyzers: Run analyzers
        generate_artifacts: Generate artifacts

    Returns:
        Dict with analysis results

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.analyze called with sample_size: {sample_size}")
    return voyant_tools._call_api("POST", "/v1/analyze", {
        "source_id": source_id,
        "table": table,
        "tables": tables,
        "sample_size": sample_size,
        "kpis": kpis,
        "analyzers": analyzers,
        "profile": profile,
        "run_analyzers": run_analyzers,
        "generate_artifacts": generate_artifacts
    })


@mcp_app.tool()
def voyant_kpi(
    sql: str,
    source_id: Optional[str] = None,
    parameters: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Execute KPI SQL query and return computed metrics.

    Args:
        sql: KPI SQL query
        source_id: Source context for query (optional)
        parameters: Query parameters (optional)

    Returns:
        Dict with KPI results

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.kpi called")
    return voyant_tools._call_api("POST", "/v1/sql/query", {
        "sql": sql,
        "source_id": source_id,
        "parameters": parameters,
        "query_type": "kpi"
    })


@mcp_app.tool()
def voyant_status(job_id: str) -> Dict[str, Any]:
    """
    Get the status of a job (ingest, profile, quality, etc.).

    Args:
        job_id: Job ID to check

    Returns:
        Dict with job status and details

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.status called for job_id: {job_id}")
    return voyant_tools._call_api("GET", f"/v1/jobs/{job_id}")


@mcp_app.tool()
def voyant_artifact(
    job_id: str,
    artifact_type: str,
    format: str = "json",
) -> Dict[str, Any]:
    """
    Retrieve an artifact from a completed job.

    Args:
        job_id: Job ID
        artifact_type: Type of artifact (profile, quality, kpi, chart, report)
        format: Artifact format (json, html, csv)

    Returns:
        Dict with artifact content

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.artifact called for job_id: {job_id}")
    return voyant_tools._call_api("GET", f"/v1/jobs/{job_id}/artifacts/{artifact_type}", {"format": format})


@mcp_app.tool()
def voyant_sql_query(sql: str, limit: int = 1000) -> Dict[str, Any]:
    """
    Execute guarded ad-hoc SQL query (SELECT only, with limits).

    Args:
        sql: SQL query (SELECT only)
        limit: Maximum rows to return

    Returns:
        Dict with query results

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.sql_query called with limit: {limit}")
    return voyant_tools._call_api("POST", "/v1/sql/query", {
        "sql": sql,
        "limit": limit
    })


@mcp_app.tool()
def voyant_search(
    query: str,
    types: Optional[List[str]] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Search for datasets, tables, or columns in data catalog.

    Args:
        query: Search query
        types: Entity types to search (optional)
        limit: Result limit

    Returns:
        Dict with search results

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.search called for query: {query}")
    return voyant_tools._call_api("GET", "/v1/catalog/search", {
        "query": query,
        "types": types,
        "limit": limit
    })


@mcp_app.tool()
def voyant_lineage(
    urn: str,
    direction: str = "both",
    depth: int = 3,
) -> Dict[str, Any]:
    """
    Get data lineage graph for a dataset.

    Args:
        urn: DataHub URN of the entity
        direction: Lineage direction (upstream, downstream, both)
        depth: Lineage depth

    Returns:
        Dict with lineage graph

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.lineage called for urn: {urn}")
    return voyant_tools._call_api("GET", "/v1/catalog/lineage", {
        "urn": urn,
        "direction": direction,
        "depth": depth
    })


@mcp_app.tool()
def voyant_preset(
    preset_name: str,
    source_id: str,
    parameters: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Execute a preset analytical workflow.

    Args:
        preset_name: Name of the preset workflow
        source_id: Source to run preset on
        parameters: Preset parameters (optional)

    Returns:
        Dict with execution results

    VIBE: Real API call, no mock.
    """
    logger.info(f"voyant.preset called for preset: {preset_name}")
    return voyant_tools._call_api("POST", f"/v1/presets/{preset_name}/execute", {
        "source_id": source_id,
        "parameters": parameters
    })


# =============================================================================
# DATASCRAPER TOOLS - Pure Execution (No LLM)
# =============================================================================


class ScraperTools:
    """
    DataScraper tools for AI agents.

    These tools perform web scraping and data extraction without using LLMs
    (browser automation, OCR, PDF parsing, etc.).
    """

    def __init__(self):
        self.api_url = "http://localhost:8000"
        self.api_token = None

    def _call_api(self, endpoint: str, json_data: Dict) -> Dict[str, Any]:
        """
        Helper to call scraper API.

        VIBE: Real httpx.Client, no mocks.
        """
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        with httpx.Client(base_url=self.api_url, headers=headers, timeout=60.0) as client:
            response = client.post(endpoint, json=json_data)
            response.raise_for_status()
            return response.json()


# Initialize scraper tools
scraper_tools = ScraperTools()


@mcp_app.tool()
def scrape_fetch(
    url: str,
    engine: str = "playwright",
    wait_for: Optional[str] = None,
    scroll: bool = False,
    timeout: int = 30,
) -> Dict[str, Any]:
    """
    Fetch raw HTML from a URL using browser automation.

    Args:
        url: Target URL to fetch
        engine: Browser engine (playwright, selenium, scrapy, httpx)
        wait_for: CSS selector to wait for before returning
        scroll: Scroll to load dynamic content
        timeout: Request timeout in seconds

    Returns:
        Dict with HTML content and metadata

    VIBE: Real scraper execution, no mock.
    """
    logger.info(f"scrape.fetch called for URL: {url}")
    return scraper_tools._call_api("/v1/scraper/fetch", {
        "url": url,
        "engine": engine,
        "wait_for": wait_for,
        "scroll": scroll,
        "timeout": timeout
    })


@mcp_app.tool()
def scrape_extract(html: str, selectors: Dict[str, str]) -> Dict[str, Any]:
    """
    Extract data from HTML using agent-provided CSS/XPath selectors.

    Note: NO LLM is used for extraction - relies on explicit selectors.

    Args:
        html: HTML content to parse
        selectors: Mapping of field names to CSS/XPath selectors

    Returns:
        Dict with extracted data

    VIBE: Real parsing, no mock or LLM.
    """
    logger.info(f"scrape.extract called with {len(selectors)} selectors")
    return scraper_tools._call_api("/v1/scraper/extract", {
        "html": html,
        "selectors": selectors
    })


@mcp_app.tool()
def scrape_ocr(image_url: str, language: str = "spa+eng") -> Dict[str, Any]:
    """
    Extract text from an image using OCR (Tesseract).

    Args:
        image_url: URL or path to image file
        language: OCR language (spa+eng, chi_sim+tra, etc.)

    Returns:
        Dict with extracted text

    VIBE: Real OCR execution, no mock.
    """
    logger.info(f"scrape.ocr called for image: {image_url}")
    return scraper_tools._call_api("/v1/scraper/ocr", {
        "image_url": image_url,
        "language": language
    })


@mcp_app.tool()
def scrape_parse_pdf(pdf_url: str, extract_tables: bool = False) -> Dict[str, Any]:
    """
    Extract text and tables from a PDF document.

    Args:
        pdf_url: URL or path to PDF file
        extract_tables: Extract tables as well as text

    Returns:
        Dict with extracted content

    VIBE: Real PDF parsing, no mock.
    """
    logger.info(f"scrape.parse_pdf called for PDF: {pdf_url}")
    return scraper_tools._call_api("/v1/scraper/parse_pdf", {
        "pdf_url": pdf_url,
        "extract_tables": extract_tables
    })


@mcp_app.tool()
def scrape_transcribe(media_url: str, language: str = "es") -> Dict[str, Any]:
    """
    Transcribe audio/video to text (OpenAI Whisper).

    Args:
        media_url: URL or path to media file
        language: Transcription language

    Returns:
        Dict with transcribed text

    VIBE: Real transcription execution, no mock.
    """
    logger.info(f"scrape.transcribe called for media: {media_url}")
    return scraper_tools._call_api("/v1/scraper/transcribe", {
        "media_url": media_url,
        "language": language
    })
