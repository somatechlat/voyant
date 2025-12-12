"""
Voyant MCP Server - Model Context Protocol Implementation

This module implements the MCP server that exposes Voyant's data capabilities
to AI agents via the Model Context Protocol (JSON-RPC 2.0 over stdio/WebSocket).

Tools exposed:
- voyant.discover: Auto-detect data source type
- voyant.connect: Establish persistent connection
- voyant.ingest: Trigger data ingestion
- voyant.profile: Generate EDA report
- voyant.quality: Run quality checks
- voyant.kpi: Execute KPI SQL
- voyant.status: Get job status
- voyant.artifact: Retrieve artifacts
- voyant.sql: Execute ad-hoc SQL (guarded)
- voyant.search: Search metadata (DataHub)
- voyant.lineage: Get data lineage (DataHub)

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
    jsonrpc: str
    method: str
    params: Dict[str, Any]
    id: str | int


@dataclass
class MCPResponse:
    """MCP JSON-RPC 2.0 response."""
    jsonrpc: str = "2.0"
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str | int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        response = {"jsonrpc": self.jsonrpc, "id": self.id}
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
    Communicates with Voyant API for actual execution.
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
    ):
        self.api_url = api_url or os.environ.get("VOYANT_API_URL", "http://localhost:8000")
        self.api_token = api_token or os.environ.get("VOYANT_API_TOKEN")
        self.tools: Dict[str, MCPTool] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._register_tools()
        
        logger.info(f"VoyantMCPServer initialized with API: {self.api_url}")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for API calls."""
        if self._http_client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_token:
                headers["Authorization"] = f"Bearer {self.api_token}"
            self._http_client = httpx.AsyncClient(
                base_url=self.api_url,
                headers=headers,
                timeout=60.0,
            )
        return self._http_client
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    def _register_tools(self):
        """Register all MCP tools."""
        
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
            handler=self._handle_discover,
        )
        
        # voyant.connect
        self.tools["voyant.connect"] = MCPTool(
            name="voyant.connect",
            description="Establish a connection to a data source",
            input_schema={
                "type": "object",
                "properties": {
                    "hint": {"type": "string", "description": "Data source hint"},
                    "credentials": {"type": "object", "description": "Connection credentials"},
                    "destination": {
                        "type": "string",
                        "enum": ["iceberg", "postgres"],
                        "default": "iceberg",
                        "description": "Target storage destination"
                    },
                    "options": {"type": "object", "description": "Additional options"}
                },
                "required": ["hint"]
            },
            handler=self._handle_connect,
        )
        
        # voyant.ingest
        self.tools["voyant.ingest"] = MCPTool(
            name="voyant.ingest",
            description="Trigger data ingestion from a connected source",
            input_schema={
                "type": "object",
                "properties": {
                    "source_id": {"type": "string", "description": "Source ID to ingest from"},
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
            handler=self._handle_ingest,
        )
        
        # voyant.profile
        self.tools["voyant.profile"] = MCPTool(
            name="voyant.profile",
            description="Generate exploratory data analysis (EDA) profile for a dataset",
            input_schema={
                "type": "object",
                "properties": {
                    "source_id": {"type": "string", "description": "Source ID to profile"},
                    "table": {"type": "string", "description": "Table name to profile"},
                    "sample_size": {
                        "type": "integer",
                        "default": 10000,
                        "description": "Sample size for profiling"
                    }
                },
                "required": ["source_id"]
            },
            handler=self._handle_profile,
        )
        
        # voyant.quality
        self.tools["voyant.quality"] = MCPTool(
            name="voyant.quality",
            description="Run data quality checks on a dataset",
            input_schema={
                "type": "object",
                "properties": {
                    "source_id": {"type": "string", "description": "Source ID to check"},
                    "table": {"type": "string", "description": "Table name"},
                    "checks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Quality checks to run (completeness, uniqueness, validity, etc.)"
                    }
                },
                "required": ["source_id"]
            },
            handler=self._handle_quality,
        )
        
        # voyant.kpi
        self.tools["voyant.kpi"] = MCPTool(
            name="voyant.kpi",
            description="Execute KPI SQL query and return computed metrics",
            input_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "KPI SQL query"},
                    "source_id": {"type": "string", "description": "Source context for the query"},
                    "parameters": {"type": "object", "description": "Query parameters"}
                },
                "required": ["sql"]
            },
            handler=self._handle_kpi,
        )
        
        # voyant.status
        self.tools["voyant.status"] = MCPTool(
            name="voyant.status",
            description="Get the status of a job (ingest, profile, quality, etc.)",
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID to check"}
                },
                "required": ["job_id"]
            },
            handler=self._handle_status,
        )
        
        # voyant.artifact
        self.tools["voyant.artifact"] = MCPTool(
            name="voyant.artifact",
            description="Retrieve an artifact from a completed job",
            input_schema={
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "Job ID"},
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
            handler=self._handle_artifact,
        )
        
        # voyant.sql
        self.tools["voyant.sql"] = MCPTool(
            name="voyant.sql",
            description="Execute guarded ad-hoc SQL query (SELECT only, with limits)",
            input_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query (SELECT only)"},
                    "limit": {
                        "type": "integer",
                        "default": 1000,
                        "maximum": 10000,
                        "description": "Maximum rows to return"
                    }
                },
                "required": ["sql"]
            },
            handler=self._handle_sql,
        )
        
        # voyant.search
        self.tools["voyant.search"] = MCPTool(
            name="voyant.search",
            description="Search for datasets, tables, or columns in the data catalog (DataHub)",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Entity types to search (dataset, table, column)"
                    },
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["query"]
            },
            handler=self._handle_search,
        )
        
        # voyant.lineage
        self.tools["voyant.lineage"] = MCPTool(
            name="voyant.lineage",
            description="Get data lineage graph for a dataset",
            input_schema={
                "type": "object",
                "properties": {
                    "urn": {"type": "string", "description": "DataHub URN of the entity"},
                    "direction": {
                        "type": "string",
                        "enum": ["upstream", "downstream", "both"],
                        "default": "both"
                    },
                    "depth": {"type": "integer", "default": 3, "maximum": 10}
                },
                "required": ["urn"]
            },
            handler=self._handle_lineage,
        )
        
        # voyant.preset
        self.tools["voyant.preset"] = MCPTool(
            name="voyant.preset",
            description="Execute a preset analytical workflow",
            input_schema={
                "type": "object",
                "properties": {
                    "preset_name": {"type": "string", "description": "Name of the preset workflow"},
                    "source_id": {"type": "string", "description": "Source to run preset on"},
                    "parameters": {"type": "object", "description": "Preset parameters"}
                },
                "required": ["preset_name", "source_id"]
            },
            handler=self._handle_preset,
        )
    
    # =========================================================================
    # Tool Handlers
    # =========================================================================
    
    async def _handle_discover(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.discover tool."""
        client = await self._get_client()
        response = await client.post("/v1/sources/discover", json={"hint": params["hint"]})
        response.raise_for_status()
        return response.json()
    
    async def _handle_connect(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.connect tool."""
        client = await self._get_client()
        response = await client.post("/v1/sources", json={
            "hint": params["hint"],
            "credentials": params.get("credentials"),
            "destination": params.get("destination", "iceberg"),
            "options": params.get("options"),
        })
        response.raise_for_status()
        return response.json()
    
    async def _handle_ingest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.ingest tool."""
        client = await self._get_client()
        response = await client.post("/v1/jobs/ingest", json={
            "source_id": params["source_id"],
            "mode": params.get("mode", "full"),
            "tables": params.get("tables"),
        })
        response.raise_for_status()
        return response.json()
    
    async def _handle_profile(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.profile tool."""
        client = await self._get_client()
        response = await client.post("/v1/jobs/profile", json={
            "source_id": params["source_id"],
            "table": params.get("table"),
            "sample_size": params.get("sample_size", 10000),
        })
        response.raise_for_status()
        return response.json()
    
    async def _handle_quality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.quality tool."""
        client = await self._get_client()
        response = await client.post("/v1/jobs/quality", json={
            "source_id": params["source_id"],
            "table": params.get("table"),
            "checks": params.get("checks"),
        })
        response.raise_for_status()
        return response.json()
    
    async def _handle_kpi(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.kpi tool."""
        client = await self._get_client()
        response = await client.post("/v1/sql/query", json={
            "sql": params["sql"],
            "source_id": params.get("source_id"),
            "parameters": params.get("parameters"),
            "query_type": "kpi",
        })
        response.raise_for_status()
        return response.json()
    
    async def _handle_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.status tool."""
        client = await self._get_client()
        job_id = params["job_id"]
        response = await client.get(f"/v1/jobs/{job_id}")
        response.raise_for_status()
        return response.json()
    
    async def _handle_artifact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.artifact tool."""
        client = await self._get_client()
        job_id = params["job_id"]
        artifact_type = params.get("artifact_type", "profile")
        format = params.get("format", "json")
        response = await client.get(
            f"/v1/artifacts/{job_id}",
            params={"type": artifact_type, "format": format}
        )
        response.raise_for_status()
        return response.json()
    
    async def _handle_sql(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.sql tool."""
        client = await self._get_client()
        response = await client.post("/v1/sql/query", json={
            "sql": params["sql"],
            "limit": min(params.get("limit", 1000), 10000),
        })
        response.raise_for_status()
        return response.json()
    
    async def _handle_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.search tool."""
        client = await self._get_client()
        response = await client.get("/v1/governance/search", params={
            "query": params["query"],
            "types": ",".join(params.get("types", [])),
            "limit": params.get("limit", 10),
        })
        response.raise_for_status()
        return response.json()
    
    async def _handle_lineage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.lineage tool."""
        client = await self._get_client()
        urn = params["urn"]
        response = await client.get(f"/v1/governance/lineage/{urn}", params={
            "direction": params.get("direction", "both"),
            "depth": params.get("depth", 3),
        })
        response.raise_for_status()
        return response.json()
    
    async def _handle_preset(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle voyant.preset tool."""
        client = await self._get_client()
        preset_name = params["preset_name"]
        response = await client.post(f"/v1/presets/{preset_name}/execute", json={
            "source_id": params["source_id"],
            "parameters": params.get("parameters", {}),
        })
        response.raise_for_status()
        return response.json()
    
    # =========================================================================
    # MCP Protocol Methods
    # =========================================================================
    
    async def handle_request(self, request_data: Dict[str, Any]) -> MCPResponse:
        """Handle an incoming MCP request."""
        try:
            request = MCPRequest(
                jsonrpc=request_data.get("jsonrpc", "2.0"),
                method=request_data.get("method", ""),
                params=request_data.get("params", {}),
                id=request_data.get("id"),
            )
            
            # Handle MCP standard methods
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
            logger.exception("Error handling MCP request")
            return MCPResponse(
                error={"code": -32603, "message": str(e)},
                id=request_data.get("id"),
            )
    
    async def _handle_initialize(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP initialize request."""
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
        """Handle MCP tools/list request."""
        tools_list = []
        for tool in self.tools.values():
            tools_list.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema,
            })
        return MCPResponse(result={"tools": tools_list}, id=request.id)
    
    async def _handle_tools_call(self, request: MCPRequest) -> MCPResponse:
        """Handle MCP tools/call request."""
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
    
    async def run_stdio(self):
        """Run MCP server over stdio transport."""
        logger.info("Starting Voyant MCP Server (stdio transport)")
        
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
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
                    )
                    writer.write((json.dumps(error_response.to_dict()) + "\n").encode())
                    await writer.drain()
                    
        finally:
            await self.close()
            logger.info("Voyant MCP Server stopped")


async def main():
    """Main entry point for MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,  # Log to stderr to keep stdout for MCP
    )
    
    server = VoyantMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
