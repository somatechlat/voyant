# Voyant Documentation: Model Context Protocol (MCP) Bridge (`apps/mcp`)

## 1. Overview
The MCP module serves as the primary integration artery between external Intelligent Agents (like Soma) and Voyant's internal execution engines. By leveraging `django-mcp`, it exposes all business logic blocks as standardized, discoverable "Tools".

## 2. File-by-File Breakdown

### `apps/mcp/server.py`
The launcher module for the MCP transport layer.
*   **ASGI Mounting:** Instead of running through standard WSGI/Gunicorn, the MCP bridge uses `uvicorn` to mount the Django application via ASGI (`voyant_project.asgi:application`).
*   **Network Binding:** Binds to `settings.mcp_host` and `settings.mcp_port` (typically `0.0.0.0:8000` inside the container), exposing the `/mcp` server sent events (SSE) endpoint endpoint designed specifically for `django-mcp`.

### `apps/mcp/tools.py`
The central registry defining every tool available to connected agents. It maps directly to the Domain Apps defined in previous phases.
*   **Workflow Triggers (`voyant.ingest`, `voyant.profile`, `voyant.analyze`, `voyant.quality`):**
    *   Creates a tracking `Job` in the database.
    *   Fires off the corresponding Temporal workflow using `_start_workflow` (e.g., `IngestDataWorkflow`, `AnalyzeWorkflow`).
    *   Returns the `job_id` so the agent can poll for status.
*   **Job & Artifact Polling (`voyant.status`, `voyant.jobs.*`, `voyant.artifacts.list`):**
    *   Allows the agent to synchronously fetch the execution status of long-running workflows.
    *   Enforces `_tenant(tenant_id)` scoping to ensure an agent cannot see jobs from another tenant space.
*   **Data Engines (`voyant.sql`, `voyant.search`):**
    *   `voyant.sql`: Directly wraps `get_trino_client().execute()`.
    *   `voyant.search`: Directly wraps the TF-IDF embedding extraction and Milvus vector store `search()` function.
*   **Governance & Discovery (`voyant.governance.schema`, `voyant.lineage`, `voyant.discovery.*`):**
    *   Pulls DataHub GraphQL information and internal source records to give the agent context on the data landscape.
*   **Scraper Capabilities (`scrape.fetch`, `scrape.extract`, `scrape.ocr`):**
    *   Exposes pure, single-shot mechanical tools via `ScrapeActivities`.
    *   Agents inject their own `extract` configurations (XPath/CSS) and target URLs, preventing the scraper from needing any built-in LLM capabilities.

## 3. Core Principles Reflected
*   **Zero Intelligence within Voyant:** None of the MCP tools attempt to interpret results. They execute exactly what parameters are passed to them (e.g., specific SQL queries, XPath selectors, specific Sample Sizes) and return raw structured data or job IDs.
*   **Complete Parity:** Every major capability documented across the `apps/` directory is mapped 1:1 to an exposed `@mcp_app.tool`.
*   **Consistent Security Layer:** Every tool explicitly or implicitly evaluates against the `_tenant()` function, reinforcing the multi-tenant SaaS architecture.
