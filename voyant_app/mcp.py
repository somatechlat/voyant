"""
Voyant MCP Toolset Implementation.

This module defines the Model Context Protocol (MCP) tools for Voyant,
using the django-mcp-server package to expose them via Django.

NOTE: Methods must be synchronous (def, not async def) because django-mcp-server
automatically wraps them with sync_to_async. We use httpx.Client for sync calls.
"""

from typing import Any, Dict, List, Optional
import httpx
import os
import logging

try:
    from mcp_server import MCPToolset
except ImportError:
    # If django-mcp-server is not installed, create a stub
    class MCPToolset:
        """Stub for MCPToolset when mcp_server is not available."""
        def __init__(self):
            pass

logger = logging.getLogger(__name__)

class VoyantTools(MCPToolset):
    """
    Exposes Voyant's data capabilities as MCP tools.
    """

    def __init__(self):
        super().__init__()
        self.api_url = os.environ.get("VOYANT_API_URL", "http://localhost:8000")
        self.api_token = os.environ.get("VOYANT_API_TOKEN")

    def _call_api(self, method: str, endpoint: str, json_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Helper to call the internal Voyant API (Synchronous)."""
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        # Use sync Client
        with httpx.Client(base_url=self.api_url, headers=headers, timeout=60.0) as client:
            if method == "GET":
                response = client.get(endpoint, params=json_data)
            else:
                response = client.post(endpoint, json=json_data)
            
            response.raise_for_status()
            return response.json()

    # --- Core Voyant Tools ---

    def discover(self, hint: str) -> Dict[str, Any]:
        """
        Auto-detect the type of a data source from a hint (URL, path, connection string).
        """
        return self._call_api("POST", "/v1/sources/discover", {"hint": hint})

    def connect(self, hint: str, credentials: Optional[Dict] = None, destination: str = "iceberg", options: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Establish a connection to a data source.
        """
        return self._call_api("POST", "/v1/sources", {
            "hint": hint,
            "credentials": credentials,
            "destination": destination,
            "options": options
        })

    def ingest(self, source_id: str, mode: str = "full", tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Trigger data ingestion from a connected source.
        """
        return self._call_api("POST", "/v1/jobs/ingest", {
            "source_id": source_id,
            "mode": mode,
            "tables": tables
        })

    def profile(self, source_id: str, table: Optional[str] = None, sample_size: int = 10000) -> Dict[str, Any]:
        """
        Generate exploratory data analysis (EDA) profile for a dataset.
        """
        return self._call_api("POST", "/v1/jobs/profile", {
            "source_id": source_id,
            "table": table,
            "sample_size": sample_size
        })

    def quality(self, source_id: str, table: Optional[str] = None, checks: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run data quality checks on a dataset.
        """
        return self._call_api("POST", "/v1/jobs/quality", {
            "source_id": source_id,
            "table": table,
            "checks": checks
        })

    def analyze(self, source_id: Optional[str] = None, table: Optional[str] = None, tables: Optional[List[str]] = None, sample_size: int = 10000, kpis: Optional[List[Dict]] = None, analyzers: Optional[List[str]] = None, profile: bool = True, run_analyzers: bool = True, generate_artifacts: bool = True) -> Dict[str, Any]:
        """
        Run end-to-end analysis (profile, KPI, analyzers, artifacts).
        """
        return self._call_api("POST", "/v1/analyze", {
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

    def kpi(self, sql: str, source_id: Optional[str] = None, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute KPI SQL query and return computed metrics.
        """
        return self._call_api("POST", "/v1/sql/query", {
            "sql": sql,
            "source_id": source_id,
            "parameters": parameters,
            "query_type": "kpi"
        })

    def status(self, job_id: str) -> Dict[str, Any]:
        """
        Get the status of a job (ingest, profile, quality, etc.).
        """
        return self._call_api("GET", f"/v1/jobs/{job_id}")

    def artifact(self, job_id: str, artifact_type: str, format: str = "json") -> Dict[str, Any]:
        """
        Retrieve an artifact from a completed job.
        """
        return self._call_api("GET", f"/v1/jobs/{job_id}/artifacts/{artifact_type}", {"format": format})
    
    def sql_query(self, sql: str, limit: int = 1000) -> Dict[str, Any]:
        """
        Execute guarded ad-hoc SQL query (SELECT only, with limits).
        """
        return self._call_api("POST", "/v1/sql/query", {
            "sql": sql,
            "limit": limit
        })

    def search(self, query: str, types: Optional[List[str]] = None, limit: int = 10) -> Dict[str, Any]:
        """
        Search for datasets, tables, or columns in the data catalog (DataHub).
        """
        return self._call_api("GET", "/v1/catalog/search", {
            "query": query,
            "types": types,
            "limit": limit
        })

    def lineage(self, urn: str, direction: str = "both", depth: int = 3) -> Dict[str, Any]:
        """
        Get data lineage graph for a dataset.
        """
        return self._call_api("GET", "/v1/catalog/lineage", {
            "urn": urn,
            "direction": direction,
            "depth": depth
        })

    def preset(self, preset_name: str, source_id: str, parameters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a preset analytical workflow.
        """
        return self._call_api("POST", f"/v1/presets/{preset_name}/execute", {
            "source_id": source_id,
            "parameters": parameters
        })


class ScraperTools(MCPToolset):
    """
    Voyant DataScraper Tools (Pure Execution - NO LLM).
    """

    def __init__(self):
        super().__init__()
        self.api_url = os.environ.get("VOYANT_API_URL", "http://localhost:8000")
        self.api_token = os.environ.get("VOYANT_API_TOKEN")

    def _call_api(self, endpoint: str, json_data: Dict) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        
        with httpx.Client(base_url=self.api_url, headers=headers, timeout=60.0) as client:
            response = client.post(endpoint, json=json_data)
            response.raise_for_status()
            return response.json()

    def fetch(self, url: str, engine: str = "playwright", wait_for: Optional[str] = None, scroll: bool = False, timeout: int = 30) -> Dict[str, Any]:
        """
        Fetch raw HTML from a URL using browser automation.
        """
        return self._call_api("/v1/scraper/fetch", {
            "url": url,
            "engine": engine,
            "wait_for": wait_for,
            "scroll": scroll,
            "timeout": timeout
        })

    def extract(self, html: str, selectors: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract data from HTML using agent-provided CSS/XPath selectors.
        """
        return self._call_api("/v1/scraper/extract", {
            "html": html,
            "selectors": selectors
        })

    def ocr(self, image_url: str, language: str = "spa+eng") -> Dict[str, Any]:
        """
        Extract text from an image using OCR.
        """
        return self._call_api("/v1/scraper/ocr", {
            "image_url": image_url,
            "language": language
        })

    def parse_pdf(self, pdf_url: str, extract_tables: bool = False) -> Dict[str, Any]:
        """
        Extract text and tables from a PDF document.
        """
        return self._call_api("/v1/scraper/parse_pdf", {
            "pdf_url": pdf_url,
            "extract_tables": extract_tables
        })

    def transcribe(self, media_url: str, language: str = "es") -> Dict[str, Any]:
        """
        Transcribe audio/video to text.
        """
        return self._call_api("/v1/scraper/transcribe", {
            "media_url": media_url,
            "language": language
        })
