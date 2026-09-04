# MCP Bridge Module

> **Source date**: 2026-09-04
> **Files examined**: `apps/mcp/server.py`, `apps/mcp/tools_core.py`, `apps/mcp/tools_catalog.py`, `apps/mcp/tools_scrape.py`

## Overview

The MCP (Model Context Protocol) bridge exposes Voyant's capabilities as MCP tools that AI agents can invoke over HTTP/SSE. The tools are organized into three files split from an original monolithic `tools.py` (Rule 245 compliance):

- **`tools_core.py`** — Core operational tools (discover, connect, ingest, profile, quality, analyze, SQL, search, status)
- **`tools_catalog.py`** — Catalog and management tools (lineage, presets, sources, jobs, tables, governance, quotas, vector operations, discovery services, KPI templates)
- **`tools_scrape.py`** — Scraping and UPTP template execution tools

Transport is provided by `django-mcp` (0.3.1), mounted at `/mcp` via the ASGI application.

---

## `apps/mcp/server.py`

**Path**: `apps/mcp/server.py` (25 lines)

Standalone launcher that runs the Django ASGI application with MCP via Daphne.

**`main()`**: Reads `mcp_host` (default `0.0.0.0`) and `mcp_port` (default `8001`) from settings, then starts a Daphne server with the ASGI application (which has MCP mounted at `/mcp`).

---

## `apps/mcp/tools_core.py`

**Path**: `apps/mcp/tools_core.py` (200 lines)

### Helper Functions

- `_tenant(tenant_id)` — Returns provided tenant_id or falls back to `settings.default_tenant_id`
- `_start_workflow(workflow_cls, workflow_id, payload)` — Fire-and-forget Temporal workflow launch

### Registered MCP Tools

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.discover` | `hint: str` | Auto-detect source type from URL/DSN/path |
| `voyant.connect` | `name, source_type, connection_config, credentials?, sync_schedule?, tenant_id?` | Create a new `Source` record |
| `voyant.ingest` | `source_id, mode="full", tables?, tenant_id?` | Dispatch `IngestDataWorkflow` via Temporal |
| `voyant.profile` | `source_id, table?, sample_size=10000, tenant_id?` | Dispatch `ProfileWorkflow` |
| `voyant.quality` | `source_id, table?, checks?, tenant_id?` | Dispatch `QualityWorkflow` |
| `voyant.analyze` | `source_id, table?, analyzers?, sample_size=10000, tenant_id?` | Dispatch `AnalyzeWorkflow` |
| `voyant.kpi` | `kpis, limit=1000` | Execute multiple KPI SQL queries via Trino |
| `voyant.status` | `job_id, tenant_id?` | Get job status, progress, result summary |
| `voyant.artifact` | `artifact_id, tenant_id?` | Get artifact metadata |
| `voyant.sql` | `sql, limit=1000` | Execute read-only SQL via Trino client |
| `voyant.search` | `query, limit=5, tenant_id?` | TF-IDF-based vector search (128 dims) |

### Error Handling

- Jobs/artifacts not found raise `ValueError`
- SQL queries validated by `TrinoClient` (read-only enforcement)

---

## `apps/mcp/tools_catalog.py`

**Path**: `apps/mcp/tools_catalog.py` (408 lines)

### Registered MCP Tools

#### Lineage & Governance

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.lineage` | `urn, direction="both", depth=3` | Fetch upstream/downstream lineage from DataHub GraphQL API (depth capped at 10) |
| `voyant.governance.schema` | `urn` | Fetch schema metadata from DataHub REST API |

#### Presets

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.preset` | `preset_name, payload, tenant_id?` | Create a `PresetJob` record |

#### Source Management

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.sources.list` | `tenant_id?` | List all sources for tenant |
| `voyant.sources.get` | `source_id, tenant_id?` | Get source details (includes credentials) |
| `voyant.sources.delete` | `source_id, tenant_id?` | Delete a source |

#### Job Management

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.jobs.list` | `tenant_id?, status?, job_type?, limit=50` | List jobs with optional filters |
| `voyant.jobs.cancel` | `job_id, tenant_id?` | Cancel a job (tries multiple workflow prefixes) |
| `voyant.artifacts.list` | `job_id, tenant_id?` | List artifacts for a job |

#### Table Metadata

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.tables.list` | `schema?` | List tables via Trino |
| `voyant.tables.columns` | `table, schema?` | Get column details via Trino |

#### Quotas

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.quotas.tiers` | — | List all quota tiers |
| `voyant.quotas.usage` | `tenant_id?` | Get current quota usage |
| `voyant.quotas.limits` | `tenant_id?` | Get quota limits |
| `voyant.quotas.set_tier` | `tier, tenant_id?` | Update tenant's quota tier |

#### Presets & KPI Templates

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.presets.list` | — | List preset jobs (up to 200) |
| `voyant.presets.get` | `job_id` | Get preset job details |
| `voyant.kpi_templates.list` | `category?` | List KPI templates |
| `voyant.kpi_templates.categories` | — | List KPI template categories |
| `voyant.kpi_templates.get` | `name` | Get KPI template details |
| `voyant.kpi_templates.render` | `name, params` | Render a KPI template with params |

#### Discovery Services

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.discovery.services.list` | `tag?` | List registered services (in-memory repo) |
| `voyant.discovery.services.get` | `name` | Get service definition |
| `voyant.discovery.services.register` | `name, base_url, spec_url?, version?, owner?, tags?` | Register a service (optionally parse OpenAPI spec) |
| `voyant.discovery.scan` | `url` | Scan an OpenAPI spec URL |

#### Vector Operations

| Tool Name | Parameters | Description |
|---|---|---|
| `voyant.vector.search` | `query, limit=5, tenant_id?` | Full hybrid search (dense 1536d + sparse) via Milvus |
| `voyant.vector.index` | `text, metadata?, item_id?, tenant_id?` | Index text with dense + sparse embeddings |

---

## `apps/mcp/tools_scrape.py`

**Path**: `apps/mcp/tools_scrape.py` (192 lines)

All scrape tools are pure mechanical bridges to `FetchActivities` and `ParseActivities`. No LLM or intelligence logic runs in the MCP layer.

### Registered MCP Tools

| Tool Name | Parameters | Description |
|---|---|---|
| `scrape.fetch` | `url, engine="playwright", wait_for?, scroll?, timeout=30, wait_until?, settle_ms?, block_resources?, capture_json?, capture_url_contains?, capture_max_bytes?, capture_max_items?` | Fetch a web page; SSRF-protected |
| `scrape.deep_archive` | `url, interaction_selectors?, download_patterns?, target_dir?, wait_settle_ms=2000, timeout_ms=60000` | Generic deep archival scrape for SPAs; async |
| `scrape.extract` | `html, selectors, url?` | Extract structured data from HTML using CSS/XPath selectors |
| `scrape.ocr` | `images, language="spa+eng"` | Run Tesseract OCR on image URLs/paths |
| `scrape.parse_pdf` | `pdf_url, extract_tables=False` | Parse PDF for text, metadata, and optionally tables |
| `scrape.transcribe` | `media_urls, language="es"` | Transcribe audio/video via OpenAI Whisper |
| `voyant.templates.execute` | `template_id, category, tenant_id, params, job_name?` | UPTP engine dispatch for template execution |

### Activity Instances

Singleton instances reused across tool calls:
- `_fetch_activities = FetchActivities()`
- `_parse_activities = ParseActivities()`

---

## Dependencies and Integration Points

- **django-mcp** — MCP transport layer (HTTP/SSE at `/mcp`)
- **Temporal** — Workflow dispatch for ingest, profile, quality, analyze
- **Trino** — SQL execution for KPI and ad-hoc queries
- **Milvus** — Vector search and indexing
- **DataHub** — GraphQL and REST for lineage and schema governance
- **Daphne** — ASGI server for MCP transport
- **httpx** — HTTP client for DataHub and discovery service calls

## Security Measures

- All workflow tools use `_tenant()` for tenant isolation
- Source creation/deletion goes through ORM with tenant filtering
- SQL tools delegate to `TrinoClient` with full read-only validation
- SSRF protection on scrape tools (via `apps/scraper/security.py`)
- MCP API token configured via `mcp_api_token` setting for upstream calls
