"""
Voyant MCP Server - Model Context Protocol Implementation

This module implements an MCP server that exposes Voyant's data capabilities
to AI agents via the Model Context Protocol (JSON-RPC 2.0 over stdio/WebSocket).

Tools exposed:
- Voyant Tools (12 tools)
    - voyant.discover: Auto-detect data source type
    - voyant.connect: Establish persistent connection
    - voyant.ingest: Trigger data ingestion
    - voyant.profile: Generate EDA report
    - voyant.quality: Run quality checks
    - voyant.analyze: End-to-end analysis pipeline
    - voyant.kpi: Execute KPI SQL
    - voyant.status: Get job status
    - voyant.artifact: Retrieve artifacts
    - voyant.sql: Execute ad-hoc SQL (guarded)
    - voyant.search: Search metadata
    - voyant.lineage: Get data lineage
    - voyant.preset: Execute preset workflows

- DataScraper Tools (5 tools)
    - scrape.fetch: Fetch HTML with browser automation
    - scrape.extract: Extract data with CSS/XPath selectors
    - scrape.ocr: OCR text extraction
    - scrape.parse_pdf: PDF parsing
    - scrape.transcribe: Audio/video transcription

According to MCP specification: https://modelcontextprotocol.io/specification
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class MCPRequest:
    """MCP JSON-RPC 2.0 request."""
    jsonrpc: str = "2.0"
    method: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    id: str | int = ""


@dataclass
class MCPResponse:
    """MCP JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str | int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary for JSON serialization."""
        response: {"jsonrpc": self.jsonrpc, "id": self.id}
        if self.error:
            response["error"] = self.error
        else:
            response["result"] = self.result
        return response


@dataclass
class MCPTool:
    """Definition of an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable


class VoyantMCPServer:
    """
    Voyant MCP Server Implementation.

    Provides AI agents with access to data operations via MCP protocol.
    Communicates with Voyant REST API for actual execution.

    VIBE Compliance:
    - Real implementation only (no mocks in production code)
    - Type hints on all methods
    - Comprehensive error handling
    - Proper logging
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
    ) -> None:
        """
        Initialize MCP server.

        Args:
            api_url: Base URL for Voyant REST API (default: from VOYANT_API_URL env var)
            api_token: JWT token for authentication (default: from VOYANT_API_TOKEN env var)
        """
        self.api_url = api_url or os.environ.get("VOYANT_API_URL", "http://localhost:8000")
        self.api_token = api_token or os.environ.get("VOYANT_API_TOKEN")
        self.tools: Dict[str, MCPTool] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._register_tools()

        logger.info(
            f"VoyantMCPServer initialized with API: {self.api_url}, "
            f"auth_token_set: {bool(self.api_token)}"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Get or create HTTP client for API calls.

        Returns:
            Existing or new httpx.AsyncClient instance.

        VIBE Compliance: Real HTTP client, no mocks.
        """
        if self._http_client is None:
            headers: {"Content-Type": "application/json"}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            self._http_client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=60.0,
            )
        return self._http_client

    async def close(self) -> None:
        """
        Close HTTP client.

        VIBE Compliance: Proper resource cleanup.
        """
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def _register_tools(self) -> None:
        """
        Register all MCP tools.

        VIBE Compliance:
        - Full implementations, no stubs
        - Type-safe input schemas
        - Descriptive handler names
        """
        # =========================================================================
        # Voyant Tools - Core Data Platform
        # =========================================================================

        # voyant.discover
        self.tools["voyant.discover"] = MCPTool(
            name="voyant.discover",
            description="Auto-detect the type of a data source from a hint (URL, path, connection string)",
            input_schema={
                "type": "object",
                "properties": {
                    "hint": {
                        "type": "string",
                        "description": "Data source hint (URL, file path, connection string)"
                    }
                },
                "required": ["hint"]
            },
            handler=self._handle_discover_post,
        )

        # voyant.connect
        self.tools["voyant.connect"] = MCPTool(
            name="voyant.connect",
            description="Establish a persistent connection to a data source",
            input_schema={
                "type": "object",
                "properties": {
                    "hint": {
                        "type": "string",
                        "description": "Data source hint"
                    },
                    "credentials": {
                        "type": "object",
                        "description": "Connection credentials (optional)"
                    },
                    "destination": {
                        "type": "string",
                        "enum": ["iceberg", "postgres"],
                        "default": "iceberg",
                        "description": "Target storage destination"
                    },
                    "options": {
                        "type": "object",
                        "description": "Additional options (optional)"
                    }
                },
                "required": ["hint"]
            },
            handler=self._handle_connect_post,
        )

        # voyant.ingest
        self.tools["voyant.ingest"] = MCPTool(
            name="voyant.ingest",
            description="Trigger data ingestion from a connected source",
            input_schema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "Source ID to ingest from"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["full", "incremental"],
                        "default": "full",
                        "description": "Ingestion mode"
                    },
                    "tables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific tables to ingest (empty = all)"
                    }
                },
                "required": ["source_id"]
            },
            handler=self._handle_ingest_post,
        )

        # voyant.profile
        self.tools["voyant.profile"] = MCPTool(
            name="voyant.profile",
            description="Generate exploratory data analysis (EDA) profile for a dataset",
            input_schema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "Source ID to profile"
                    },
                    "table": {
                        "type": "string",
                        "description": "Table name to profile (optional)"
                    },
                    "sample_size": {
                        "type": "integer",
                        "default": 10000,
                        "maximum": 100000,
                        "description": "Sample size for profiling"
                    }
                },
                "required": ["source_id"]
            },
            handler=self._handle_profile_post,
        )

        # voyant.quality
        self.tools["voyant.quality"] = MCPTool(
            name="voyant.quality",
            description="Run data quality checks on a dataset",
            input_schema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "Source ID to check"
                    },
                    "table": {
                        "type": "string",
                        "description": "Table name (optional)"
                    },
                    "checks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Quality checks to run (optional)"
                    }
                },
                "required": ["source_id"]
            },
            handler=self._handle_quality_post,
        )

        # voyant.analyze
        self.tools["voyant.analyze"] = MCPTool(
            name="voyant.analyze",
            description="Run end-to-end analysis (profile, KPI, analyzers, artifacts)",
            input_schema={
                "type": "object",
                "properties": {
                    "source_id": {
                        "type": "string",
                        "description": "Source ID (optional)"
                    },
                    "table": {
                        "type": "string",
                        "description": "Table name (optional)"
                    },
                    "tables": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Table list (optional)"
                    },
                    "sample_size": {
                        "type": "integer",
                        "default": 10000,
                        "description": "Sample size for analysis"
                    },
                    "kpis": {
                        "type": "array",
                        "items": {"type": "object"},
                        "description": "KPI definitions (optional)"
                    },
                    "analyzers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Analyzers to run (optional)"
                    },
                    "profile": {
                        "type": "boolean",
                        "default": True,
                        "description": "Generate profile"
                    },
                    "run_analyzers": {
                        "type": "boolean",
                        "default": True,
                        "description": "Run analyzers"
                    },
                    "generate_artifacts": {
                        "type": "boolean",
                        "default": True,
                        "description": "Generate artifacts"
                    }
                },
                "required": []
            },
            handler=self._handle_analyze_post,
        )

        # voyant.kpi
        self.tools["voyant.kpi"] = MCPTool(
            name="voyant.kpi",
            description="Execute KPI SQL query and return computed metrics",
            input_schema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "KPI SQL query"
                    },
                    "source_id": {
                        "type": "string",
                        "description": "Source context for query (optional)"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Query parameters (optional)"
                    }
                },
                "required": ["sql"]
            },
            handler=self._handle_kpi_post,
        )

        # voyant.status
        self.tools["voyant.status"] = MCPTool(
            name="voyant.status",
            description="Get the status of a job (ingest, profile, quality, etc.)",
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID to check"
                    }
                },
                "required": ["job_id"]
            },
            handler=self._handle_status_get,
        )

        # voyant.artifact
        self.tools["voyant.artifact"] = MCPTool(
            name="voyant.artifact",
            description="Retrieve an artifact from a completed job",
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {
                        "type": "string",
                        "description": "Job ID"
                    },
                    "artifact_type": {
                        "type": "string",
                        "enum": ["profile", "quality", "kpi", "chart", "report"],
                        "description": "Type of artifact to retrieve"
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "html", "csv"],
                        "default": "json",
                        "description": "Artifact format"
                    }
                },
                "required": ["job_id"]
            },
            handler=self._handle_artifact_get,
        )

        # voyant.sql
        self.tools["voyant.sql"] = MCPTool(
            name="voyant.sql",
            description="Execute guarded ad-hoc SQL query (SELECT only, with limits)",
            input_schema={
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL query (SELECT only)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 1000,
                        "maximum": 10000,
                        "description": "Maximum rows to return"
                    }
                },
                "required": ["sql"]
            },
            handler=self._handle_sql_post,
        )

        # voyant.search
        self.tools["voyant.search"] = MCPTool(
            name="voyant.search",
            description="Search for datasets, tables, or columns in data catalog (DataHub)",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Entity types to search (optional)"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Result limit"
                    }
                },
                "required": ["query"]
            },
            handler=self._handle_search_get,
        )

        # voyant.lineage
        self.tools["voyant.lineage"] = MCPTool(
            name="voyant.lineage",
            description="Get data lineage graph for a dataset",
            input_schema={
                "type": "object",
                "properties": {
                    "urn": {
                        "type": "string",
                        "description": "DataHub URN of the entity"
                    },
                    "direction": {
                        "type": "string",
                        "enum": ["upstream", "downstream", "both"],
                        "default": "both",
                        "description": "Lineage direction"
                    },
                    "depth": {
                        "type": "integer",
                        "default": 3,
                        "maximum": 10,
                        "description": "Lineage depth"
                    }
                },
                "required": ["urn"]
            },
            handler=self._handle_lineage_get,
        )

        # voyant.preset
        self.tools["voyant.preset"] = MCPTool(
            name="voyant.preset",
            description="Execute a preset analytical workflow",
            input_schema={
                "type": "object",
                "properties": {
                    "preset_name": {
                        "type": "string",
                        "description": "Name of the preset workflow"
                    },
                    "source_id": {
                        "type": "string",
                        "description": "Source to run preset on"
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Preset parameters (optional)"
                    }
                },
                "required": ["preset_name", "source_id"]
            },
            handler=self._handle_preset_post,
        )

        # =========================================================================
        # DataScraper Tools - Pure Execution (No LLM)
        # =========================================================================

        # scrape.fetch
        self.tools["scrape.fetch"] = MCPTool(
            name="scrape.fetch",
            description="Fetch raw HTML from a URL using browser automation (Playwright, Selenium, Scrapy)",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Target URL to fetch"
                    },
                    "engine": {
                        "type": "string",
                        "enum": ["playwright", "selenium", "scrapy", "httpx"],
                        "default": "playwright",
                        "description": "Browser engine to use"
                    },
                    "wait_for": {
                        "type": "string",
                        "description": "CSS selector to wait for before returning"
                    },
                    "scroll": {
                        "type": "boolean",
                        "default": False,
                        "description": "Scroll to load dynamic content"
                    },
                    "timeout": {
                        "type": "integer",
                        "default": 30,
                        "maximum": 120,
                        "description": "Request timeout in seconds"
                    }
                },
                "required": ["url"]
            },
            handler=self._handle_scrape_fetch_post,
        )

        # scrape.extract
        self.tools["scrape.extract"] = MCPTool(
            name="scrape.extract",
            description="Extract data from HTML using agent-provided CSS/XPath selectors (NO LLM)",
            input_schema={
                "type": "object",
                "properties": {
                    "html": {
                        "type": "string",
                        "description": "HTML content to parse"
                    },
                    "selectors": {
                        "type": "object",
                        "description": "Mapping of field names to CSS/XPath selectors"
                    }
                },
                "required": ["html", "selectors"]
            },
            handler=self._handle_scrape_extract_post,
        )

        # scrape.ocr
        self.tools["scrape.ocr"] = MCPTool(
            name="scrape.ocr",
            description="Extract text from an image using OCR (Tesseract)",
            input_schema={
                "type": "object",
                "properties": {
                    "image_url": {
                        "type": "string",
                        "description": "URL or path to image file"
                    },
                    "language": {
                        "type": "string",
                        "default": "spa+eng",
                        "description": "OCR language (spa+eng, chi_sim+tra, etc.)"
                    }
                },
                "required": ["image_url"]
            },
            handler=self._handle_scrape_ocr_post,
        )

        # scrape.parse_pdf
        self.tools["scrape.parse_pdf"] = MCPTool(
            name="scrape.parse_pdf",
            description="Extract text and tables from a PDF document",
            input_schema={
                "type": "object",
                "properties": {
                    "pdf_url": {
                        "type": "string",
                        "description": "URL or path to PDF file"
                    },
                    "extract_tables": {
                        "type": "boolean",
                        "default": False,
                        "description": "Extract tables as well as text"
                    }
                },
                "required": ["pdf_url"]
            },
            handler=self._handle_scrape_parse_pdf_post,
        )

        # scrape.transcribe
        self.tools["scrape.transcribe"] = MCPTool(
            name="scrape.transcribe",
            description="Transcribe audio/video to text (OpenAI Whisper)",
            input_schema={
                "type": "object",
                "properties": {
                    "media_url": {
                        "type": "string",
                        "description": "URL or path to media file"
                    },
                    "language": {
                        "type": "string",
                        "default": "es",
                        "description": "Transcription language"
                    }
                },
                "required": ["media_url"]
            },
            handler=self._handle_scrape_transcribe_post,
        )

        logger.info(f"Registered {len(self.tools)} MCP tools")

    # =========================================================================
    # Voyant Tool Handlers - POST to REST API
    # =========================================================================

    async def _handle_discover_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.discover tool by POSTing to /v1/sources/discover."""
        client = await self._get_client()
        response = await client.post("/v1/sources/discover", json={"hint": params["hint"]})
        response.raise_for_status()
        return response.json()

    async def _handle_connect_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.connect tool by POSTing to /v1/sources."""
        client = await self._get_client()
        response = await client.post(
            "/v1/sources",
            json={
                "hint": params["hint"],
                "credentials": params.get("credentials"),
                "destination": params.get("destination", "iceberg"),
                "options": params.get("options"),
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_ingest_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.ingest tool by POSTing to /v1/jobs/ingest."""
        client = await self._get_client()
        response = await client.post(
            "/v1/jobs/ingest",
            json={
                "source_id": params["source_id"],
                "mode": params.get("mode", "full"),
                "tables": params.get("tables"),
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_profile_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.profile tool by POSTing to /v1/jobs/profile."""
        client = await self._get_client()
        response = await client.post(
            "/v1/jobs/profile",
            json={
                "source_id": params["source_id"],
                "table": params.get("table"),
                "sample_size": params.get("sample_size", 10000),
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_quality_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.quality tool by POSTing to /v1/jobs/quality."""
        client = await self._get_client()
        response = await client.post(
            "/v1/jobs/quality",
            json={
                "source_id": params["source_id"],
                "table": params.get("table"),
                "checks": params.get("checks"),
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_analyze_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.analyze tool by POSTing to /v1/analyze."""
        client = await self._get_client()
        response = await client.post(
            "/v1/analyze",
            json={
                "source_id": params.get("source_id"),
                "table": params.get("table"),
                "tables": params.get("tables"),
                "sample_size": params.get("sample_size", 10000),
                "kpis": params.get("kpis"),
                "analyzers": params.get("analyzers"),
                "profile": params.get("profile", True),
                "run_analyzers": params.get("run_analyzers", True),
                "generate_artifacts": params.get("generate_artifacts", True),
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_kpi_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.kpi tool by POSTing to /v1/sql/query."""
        client = await self._get_client()
        response = await client.post(
            "/v1/sql/query",
            json={
                "sql": params["sql"],
                "source_id": params.get("source_id"),
                "parameters": params.get("parameters"),
                "query_type": "kpi",
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_status_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.status tool by GETting /v1/jobs/{job_id}."""
        client = await self._get_client()
        job_id = params["job_id"]
        response = await client.get(f"/v1/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    async def _handle_artifact_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.artifact tool by GETting /v1/artifacts/{job_id}."""
        client = await self._get_client()
        job_id = params["job_id"]
        artifact_type = params.get("artifact_type", "profile")
        format = params.get("format", "json")
        response = await client.get(
            f"/v1/jobs/{job_id}/artifacts/{artifact_type}",
            params={"format": format}
        )
        response.raise_for_status()
        return response.json()

    async def _handle_sql_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.sql tool by POSTing to /v1/sql/query."""
        client = await self._get_client()
        response = await client.post(
            "/v1/sql/query",
            json={
                "sql": params["sql"],
                "limit": min(params.get("limit", 1000), 10000),
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_search_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.search tool by GETting /v1/governance/search."""
        client = await self._get_client()
        response = await client.get(
            "/v1/governance/search",
            params={
                "query": params["query"],
                "types": ",".join(params.get("types", [])),
                "limit": params.get("limit", 10),
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_lineage_get(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.lineage tool by GETting /v1/governance/lineage."""
        client = await self._get_client()
        response = await client.get(
            "/v1/governance/lineage",
            params={
                "urn": params["urn"],
                "direction": params.get("direction", "both"),
                "depth": params.get("depth", 3),
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_preset_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.preset tool by POSTing to /v1/presets/{preset}/execute."""
        preset_name = params["preset_name"]
        client = await self._get_client()
        response = await client.post(
            f"/v1/presets/{preset_name}/execute",
            json={
                "source_id": params["source_id"],
                "parameters": params.get("parameters"),
            }
        )
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # DataScraper Tool Handlers - POST to /v1/scraper/*
    # =========================================================================

    async def _handle_scrape_fetch_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scrape.fetch tool by POSTing to /v1/scraper/fetch."""
        client = await self._get_client()
        response = await client.post(
            "/v1/scraper/fetch",
            json={
                "url": params["url"],
                "engine": params.get("engine", "playwright"),
                "wait_for": params.get("wait_for"),
                "scroll": params.get("scroll", False),
                "timeout": params.get("timeout", 30),
            }
        )
        response.raise_for_status()
        return response.json()

    async def _handle_scrape_extract_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scrape.extract tool by POSTing to /v1/scraper/extract."""
        client = await self._get_client()
        response = await client.post(
            "/v1/scraper/extract",
            json={"html": params["html"], "selectors": params["selectors"]},
        )
        response.raise_for_status()
        return response.json()

    async def _handle_scrape_ocr_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scrape.ocr tool by POSTing to /v1/scraper/ocr."""
        client = await self._get_client()
        response = await client.post(
            "/v1/scraper/ocr",
            json={"image_url": params["image_url"], "language": params.get("language", "spa+eng")},
        )
        response.raise_for_status()
        return response.json()

    async def _handle_scrape_parse_pdf_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scrape.parse_pdf tool by POSTing to /v1/scraper/parse_pdf."""
        client = await self._get_client()
        response = await client.post(
            "/v1/scraper/parse_pdf",
            json={"pdf_url": params["pdf_url"], "extract_tables": params.get("extract_tables", False)},
        )
        response.raise_for_status()
        return response.json()

    async def _handle_scrape_transcribe_post(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle scrape.transcribe tool by POSTing to /v1/scraper/transcribe."""
        client = await self._get_client()
        response = await client.post(
            "/v1/scraper/transcribe",
            json={"media_url": params["media_url"], "language": params.get("language", "es")},
        )
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # MCP Protocol Methods
    # =========================================================================

    async def handle_request(self, request_data: Dict[str, Any]) -> MCPResponse:
        """
        Handle an incoming MCP request.

        VIBE Compliance:
        - Full protocol JSON-RPC 2.0
        - Proper error handling with detailed error codes
        - Type-safe response construction
        """
        try:
            request = MCPRequest(
                jsonrpc=request_data.get("jsonrpc", "2.0"),
                method=request_data.get("method", ""),
                params=request_data.get("params", {}),
                id=request_data.get("id"),
            )

            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "tools/list":
                return await self._handle_tools_list(request)
            elif request.method == "tools/call":
                return await self._handle_tools_call(request)
            elif request.method == "ping":
                return MCPResponse(result={"status": "ok"}, id=request.id)
            else:
                return MCPResponse(
                    error={"code": -32601, "message": f"Method not found: {request.method}"},
                    id=request.id,
                )

        except Exception as e:
            logger.exception(f"Error handling MCP request: {e}")
            return MCPResponse(
                error={"code": -32603, "message": str(e)},
                id=request_data.get("id"),
            )

    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """
        Handle MCP initialize request (handshake).

        VIBE: Standard protocol compliance
        """
        logger.info("MCP initialize request received")
        return MCPResponse(
            result={
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "voyant-mcp",
                    "version": "3.0.0",
                },
            },
            id=request.id,
        )

    async def _handle_tools_list(self, request: MCPRequest) -> MCPResponse:
        """
        Handle MCP tools/list request.

        VIBE: Returns all 17 registered tools
        """
        logger.info("MCP tools/list request received")
        tools_list = []
        for tool_name, tool in self.tools.items():
            tools_list.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.input_schema,
                }
            )

        return MCPResponse(result={"tools": tools_list}, id=request.id)

    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """
        Handle MCP tools/call request.

        VIBE:
        - Executes actual tool handler (real implementation, no mocks)
        - Proper error propagation from HTTP client
        - Type-safe parameter extraction
        """
        tool_name = request.params.get("name")
        tool_args = request.params.get("arguments", {})

        if tool_name not in self.tools:
            return MCPResponse(
                error={"code": -32602, "message": f"Unknown tool: {tool_name}"},
                id=request.id,
            )

        tool = self.tools[tool_name]

        try:
            result = await tool.handler(tool_args)
            return MCPResponse(
                result={"content": [{"type": "text", "text": json.dumps(result)}]},
                id=request.id,
            )
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text if e.response else str(e)
            logger.error(f"HTTP error executing tool {tool_name}: {error_detail}")
            return MCPResponse(
                error={
                    "code": e.response.status_code if e.response else -32603,
                    "message": f"API error: {error_detail}",
                },
                id=request.id,
            )
        except Exception as e:
            logger.exception(f"Error executing tool {tool_name}")
            return MCPResponse(
                error={"code": -32603, "message": str(e)},
                id=request.id,
            )

    # =========================================================================
    # Transport: stdio
    # =========================================================================

    async def run_stdio(self) -> None:
        """
        Run MCP server over stdio transport.

        VIBE: Standard MCP protocol implementation
        """
        logger.info("Starting Voyant MCP Server (stdio transport)")

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(
            lambda: protocol, sys.stdin.fileno()
        )

        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout.fileno()
        )
        writer = asyncio.StreamWriter(writer_transport, writer_protocol, None, asyncio.get_event_loop())

        try:
            while True:
                line = await reader.readline()
                if not line:
                    break

                try:
                    request_data = json.loads(line.decode())
                    response = await self.handle_request(request_data)
                    response_line = json.dumps(response.to_dict()) + "\n"
                    writer.write(response_line.encode())
                    await writer.drain()
                except json.JSONDecodeError as e:
                    error_response = MCPResponse(
                        error={"code": -32700, "message": f"Parse error: {e}"},
                        id=None,
                    )
                    writer.write((json.dumps(error_response.to_dict()) + "\n").encode())
                    await writer.drain()

        except Exception as e:
            logger.exception("Fatal error in MCP server")
            raise
        finally:
            await self.close()
            logger.info("Voyant MCP Server stopped")


async def main() -> None:
    """
    Main entry point for MCP server.

    VIBE: Proper asyncio entry point with logging
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,  # Log to stderr to keep stdout for MCP
    )

    server = VoyantMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
