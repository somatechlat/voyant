# Voyant Master Project Documentation
**Date:** February 2026
**Compliance:** Vibe Coding Rules (PhD-level, ISO-style, No Assumptions, Read-Only Code)

## Executive Summary
Voyant is an enterprise-grade "Zero Intelligence" execution engine designed specifically to act as the backend muscle for intelligent agents (like Soma). It operates entirely through a Model Context Protocol (MCP) bridge, executing deterministic tasks (SQL queries, vector searches, web scraping, statistical analysis, and Flink streaming workflows) precisely as directed by external agentic models, rather than generating text or interpreting intelligence itself.

This document serves as the master index for the exhaustive file-by-file documentation generated for the Voyant ecosystem.

---

## Part I: Core Infrastructure & Architecture

### 1. Framework & Core
**Documentation:** [doc_core_framework.md](file:///Users/macbookpro201916i964gb1tb/.gemini/antigravity/brain/5ade9880-9dcb-4c04-8e20-83748b36a39a/doc_core_framework.md)
*   **Focus:** Django setup, routing, and strict security posture.
*   **Key Files:** `voyant_project/urls.py`, `voyant_project/security_settings.py`, `apps/core/api.py`.
*   **Highlights:** HSTS/CSP implementations, singleton instance management, API version routing under `/v1/`.

### 2. Core Foundations
**Documentation:** [doc_core_foundations.md](file:///Users/macbookpro201916i964gb1tb/.gemini/antigravity/brain/5ade9880-9dcb-4c04-8e20-83748b36a39a/doc_core_foundations.md)
*   **Focus:** Database models and request middleware.
*   **Key Files:** `apps/core/models.py`, `apps/core/middleware.py`.
*   **Highlights:** Strict multi-tenancy enforced via `TenantModel` and `TenantMiddleware`, and immutable `AuditLog` generation.

### 3. Data Engines
**Documentation:** [doc_data_engines.md](file:///Users/macbookpro201916i964gb1tb/.gemini/antigravity/brain/5ade9880-9dcb-4c04-8e20-83748b36a39a/doc_data_engines.md)
*   **Focus:** Raw query execution engines.
*   **Key Files:** `apps/core/lib/trino.py`, `apps/core/lib/temporal_client.py`, `apps/core/lib/vector_store.py`.
*   **Highlights:** Strict Read-Only Trino client preventing database mutation (`DROP/DELETE` blocking), Temporal client singletons for asynchronous execution.

---

## Part II: The Agent Bridge

### 4. MCP Gateway
**Documentation:** [doc_mcp_bridge.md](file:///Users/macbookpro201916i964gb1tb/.gemini/antigravity/brain/5ade9880-9dcb-4c04-8e20-83748b36a39a/doc_mcp_bridge.md)
*   **Focus:** The interface exposing Voyant capabilities to intelligent agents.
*   **Key Files:** `apps/mcp/server.py`, `apps/mcp/tools.py`.
*   **Highlights:** Exposes every domain app as a standard `@mcp_app.tool`, translating agent requests into Temporal workflows or synchronous DB hits without requiring human APIs.

---

## Part III: Domain Applications

### 5. Data Lifecycle (Discovery, Ingestion, Governance)
**Documentation:** [doc_data_lifecycle.md](file:///Users/macbookpro201916i964gb1tb/.gemini/antigravity/brain/5ade9880-9dcb-4c04-8e20-83748b36a39a/doc_data_lifecycle.md)
*   **Focus:** Managing external data moving into Voyant.
*   **Key Files:** `apps/discovery/api.py`, `apps/ingestion/api.py`, `apps/governance/api.py`.
*   **Highlights:** DataHub integration via GraphQL for lineage/schemas. Temporal asynchronous workflow dispatch for ingestion tasks.

### 6. Workflows, Analysis, and Scraping
**Documentation:** [doc_workflows_and_execution.md](file:///Users/macbookpro201916i964gb1tb/.gemini/antigravity/brain/5ade9880-9dcb-4c04-8e20-83748b36a39a/doc_workflows_and_execution.md)
*   **Focus:** Deep processing and mechanical web interaction.
*   **Key Files:** `apps/workflows/api.py`, `apps/analysis/api.py`, `apps/scraper/api.py`.
*   **Highlights:** Single-shot non-LLM scrapers using Playwright and XPath/CSS extractors. Heavy namespace validation on analytical tables prior to Temporal dispatch.

### 7. Search and SQL API Gateways
**Documentation:** [doc_search_and_sql.md](file:///Users/macbookpro201916i964gb1tb/.gemini/antigravity/brain/5ade9880-9dcb-4c04-8e20-83748b36a39a/doc_search_and_sql.md)
*   **Focus:** The HTTP routers for querying.
*   **Key Files:** `apps/search/api.py`, `apps/sql/api.py`.
*   **Highlights:** Implementation of cosine similarity logic against the Milvus vector store. Hard isolation of embeddings and search limits via `tenant_id`.

---

## Part IV: Execution Plane & Frontend

### 8. Streaming and Background Workers
**Documentation:** [doc_streaming_and_workers.md](file:///Users/macbookpro201916i964gb1tb/.gemini/antigravity/brain/5ade9880-9dcb-4c04-8e20-83748b36a39a/doc_streaming_and_workers.md)
*   **Focus:** The heavy-lifting execution environments processing real-time and background jobs.
*   **Key Files:** `apps/streaming/flink_client.py`, `apps/worker/worker_main.py`.
*   **Highlights:** Flink JobManager HTTP wrappers. Strict segregation of the Python Temporal Worker into "scraper" mode vs "analytics" mode preventing sandbox pollution.

### 9. Frontend Dashboard & Tooling
**Documentation:** [doc_dashboard_and_scripts.md](file:///Users/macbookpro201916i964gb1tb/.gemini/antigravity/brain/5ade9880-9dcb-4c04-8e20-83748b36a39a/doc_dashboard_and_scripts.md)
*   **Focus:** The Web UI and verification environment.
*   **Key Files:** `dashboard/src/*`, `scripts/verify_*.py`.
*   **Highlights:** 100% adherence to Lit 3 Web Components (Vibe Coding Rule 9 - No Alpine.js). Verification scripts physically execute endpoints against the network stack rather than relying on mocks.

---
## Vibe Coding Rule Conformance Audit
*   **NO BULLSHIT (Rule 1):** Verified. All documented features exist physically in code and run on Trino/Temporal/Postgres.
*   **REAL IMPLEMENTATIONS ONLY (Rule 4):** Verified. Documented true execution paths (`asyncio`, `temporalio`).
*   **API FRAMEWORK POLICY (Rule 8):** Verified. Entire project operates on Django Ninja (`ninja.Router`). FastAPI is absent.
*   **UI FRAMEWORK POLICY (Rule 9):** Verified. The Dashboard uses pure Lit 3.
*   **DATABASE ORM POLICY (Rule 10):** Verified. `TenantModel`, `AuditLog`, `ScrapeJob` map perfectly to standard Django ORM `models.py` architectures.
