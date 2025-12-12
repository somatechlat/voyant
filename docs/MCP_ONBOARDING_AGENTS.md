# Voyant MCP - Agent Onboarding Guide

> **Version:** 3.0.0  
> **Protocol:** Model Context Protocol (MCP) - JSON-RPC 2.0  
> **Last Updated:** December 2024

---

## Quick Start

### 1. Prerequisites

Ensure the Voyant Docker stack is running:

```bash
cd /path/to/voyant
docker compose up -d
```

Verify services are healthy:
```bash
docker compose ps
# voyant-api should show "healthy"
```

### 2. Connection Details

| Endpoint | URL |
|----------|-----|
| **MCP Server (HTTP)** | `http://localhost:45001` |
| **REST API** | `http://localhost:45000` |

---

## MCP Protocol Overview

Voyant uses **JSON-RPC 2.0** over HTTP for MCP communication.

### Request Format
```json
{
  "jsonrpc": "2.0",
  "method": "<method_name>",
  "params": { ... },
  "id": <unique_request_id>
}
```

### Response Format
```json
{
  "jsonrpc": "2.0",
  "result": { ... },
  "id": <same_request_id>
}
```

---

## Step-by-Step Connection

### Step 1: Initialize Connection

```json
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {},
  "id": 1
}
```

**Expected Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "tools": {}
    },
    "serverInfo": {
      "name": "voyant-mcp",
      "version": "3.0.0"
    }
  },
  "id": 1
}
```

### Step 2: List Available Tools

```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": 2
}
```

### Step 3: Call a Tool

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "<tool_name>",
    "arguments": { ... }
  },
  "id": 3
}
```

---

## Available Tools

### Data Discovery & Connection

| Tool | Description | Required Args |
|------|-------------|---------------|
| `voyant.discover` | Auto-detect data source type | `hint` |
| `voyant.connect` | Create data source connection | `hint` |

### Data Operations

| Tool | Description | Required Args |
|------|-------------|---------------|
| `voyant.ingest` | Trigger data ingestion | `source_id` |
| `voyant.profile` | Generate EDA profile | `source_id` |
| `voyant.quality` | Run quality checks | `source_id` |

### Analytics

| Tool | Description | Required Args |
|------|-------------|---------------|
| `voyant.kpi` | Execute KPI SQL | `sql` |
| `voyant.sql` | Run guarded SELECT queries | `sql` |
| `voyant.preset` | Execute preset workflow | `preset_name`, `source_id` |

### Job & Artifact Management

| Tool | Description | Required Args |
|------|-------------|---------------|
| `voyant.status` | Get job status | `job_id` |
| `voyant.artifact` | Retrieve job artifacts | `job_id` |

### Data Governance

| Tool | Description | Required Args |
|------|-------------|---------------|
| `voyant.search` | Search DataHub catalog | `query` |
| `voyant.lineage` | Get data lineage graph | `urn` |

---

## Tool Examples

### Discover a Data Source

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "voyant.discover",
    "arguments": {
      "hint": "postgresql://user:pass@host:5432/mydb"
    }
  },
  "id": 10
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"source_type\": \"postgresql\", \"connector\": \"airbyte/source-postgres\", \"confidence\": 0.95}"
    }]
  },
  "id": 10
}
```

### Connect and Ingest

```json
// Step 1: Connect
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "voyant.connect",
    "arguments": {
      "hint": "postgresql://user:pass@host:5432/mydb",
      "destination": "iceberg"
    }
  },
  "id": 11
}

// Step 2: Ingest (use source_id from connect response)
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "voyant.ingest",
    "arguments": {
      "source_id": "<source_id_from_connect>",
      "mode": "full"
    }
  },
  "id": 12
}
```

### Run SQL Query

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "voyant.sql",
    "arguments": {
      "sql": "SELECT * FROM customers LIMIT 10",
      "limit": 100
    }
  },
  "id": 20
}
```

### Execute Preset Workflow

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "voyant.preset",
    "arguments": {
      "preset_name": "financial.revenue_analysis",
      "source_id": "<source_id>",
      "parameters": {
        "date_column": "created_at",
        "amount_column": "revenue"
      }
    }
  },
  "id": 30
}
```

---

## Supported Source Types

Voyant auto-detects these source types from hints:

| Type | Hint Pattern | Connector |
|------|--------------|-----------|
| PostgreSQL | `postgresql://...` | airbyte/source-postgres |
| MySQL | `mysql://...` | airbyte/source-mysql |
| MongoDB | `mongodb://...` | airbyte/source-mongodb-v2 |
| Snowflake | `snowflake://...` | airbyte/source-snowflake |
| S3 | `s3://bucket/path` | airbyte/source-s3 |
| Google Sheets | `sheets.google.com/...` | airbyte/source-google-sheets |
| CSV File | `*.csv` | file |
| Parquet File | `*.parquet` | file |
| JSON File | `*.json` | file |
| HTTP API | `https://api.example.com` | airbyte/source-http |

---

## Available Presets

| Preset Name | Category | Description |
|-------------|----------|-------------|
| `financial.revenue_analysis` | Financial | Revenue trends & growth |
| `financial.expense_tracking` | Financial | Expense categorization |
| `financial.margin_analysis` | Financial | Profit margin analysis |
| `customer.churn_analysis` | Customer | Churn pattern detection |
| `customer.segmentation` | Customer | RFM & clustering |
| `customer.ltv_prediction` | Customer | Lifetime value prediction |
| `quality.data_profiling` | Quality | Comprehensive EDA |
| `quality.anomaly_detection` | Quality | Outlier detection |
| `ops.inventory_analysis` | Operations | Inventory turnover |

---

## Error Handling

Errors follow JSON-RPC spec:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params: source_id is required"
  },
  "id": 1
}
```

### Error Codes

| Code | Meaning |
|------|---------|
| -32700 | Parse error |
| -32600 | Invalid request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |
| 400-599 | HTTP status codes from API |

---

## Testing with curl

```bash
# Initialize
curl -X POST http://localhost:45001 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}'

# List tools
curl -X POST http://localhost:45001 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":2}'

# Discover source
curl -X POST http://localhost:45001 \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"voyant.discover","arguments":{"hint":"postgresql://localhost/test"}},"id":3}'
```

---

## Multi-Tenancy

Include tenant ID in request headers:

```bash
curl -X POST http://localhost:45001 \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: my-tenant-id" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}'
```

---

## Authentication (Production)

In production, include Keycloak JWT token:

```bash
curl -X POST http://localhost:45001 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <jwt_token>" \
  -d '...'
```

---

## Support

- **GitHub:** https://github.com/somatechlat/voyant
- **Docs:** `/docs/MCP_INTERFACE.md`
- **API Spec:** `http://localhost:45000/docs` (OpenAPI)
