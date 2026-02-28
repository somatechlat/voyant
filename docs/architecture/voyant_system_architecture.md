# Voyant v3.0.0 System Architecture & Tool Registry

Targeting the **Autonomous Data Intelligence for AI Agents** initiative, Voyant operates as a sprawling infrastructure to provide agents (like SomaAgent Hub) with data workflows, governance, ingestion, and querying tools.

A central design pillar of the Voyant project is that it serves as a **Tool Provider** utilizing **Model Context Protocol (MCP)** via Django (`django-mcp` version 0.3.1).

---

## 1. The 10 Core Modules (Django Apps)
Based on `voyant_project/settings.py` and `apps/core/api.py`, Voyant contains **10 top-level modules**, each loaded with a specialized capability:

1. **`apps.discovery`**:
   - **Purpose**: Semantic cataloging, crawling target schemas, detecting file types (e.g., inferring a source type based on an OpenAPI spec or database URL), and generating source connectors.
2. **`apps.ingestion`**:
   - **Purpose**: The physical data movement layer. Binds to Airbyte/NiFi connectors to ingest external files and streams into local environments like DuckDB, Trino, and Iceberg.
3. **`apps.scraper`**:
   - **Purpose**: Pure mechanical execution for pulling web pages using Playwright, httpx, Tesseract (OCR), and Whisper (Transcription).
4. **`apps.analysis`**:
   - **Purpose**: Statistical profiling, data quality evaluation (Evidently), drift measurement, and executing predictive machine learning.
5. **`apps.sql`**:
   - **Purpose**: Direct SQL querying and semantic query generation running on top of **Trino** and **Iceberg Lakehouse**.
6. **`apps.search`**:
   - **Purpose**: Vector Database interfacing (using Milvus) to provide Semantic Similarity search against embedded artifacts and documents.
7. **`apps.governance`**:
   - **Purpose**: Lineage graphing, Data contracts (Atlas/DataHub backend support), handling tenant quotas, tiers, and data masking/policies via Apache Ranger.
8. **`apps.workflows`**:
   - **Purpose**: Wraps around **Temporal** to chain different tasks together into multi-step async sequences (Jobs, Artifact state, Presets).
9. **`apps.core`**:
   - **Purpose**: Handles Base Django Models (Tenant Isolation logic), Audit logs, Soma Context injection (`X-Soma-Session-ID`), and universal Middlewares.
10. **`apps.streaming` / `apps.worker`**:
    - **Purpose**: Runs Kafka topics, Flink aggregators, and Python celery-style runners for handling stream data anomaly tracking.

---

## 2. Infrastructure Technologies (The Underbelly)

According to the official `docs/architecture/DESIGN.md`, the platform rests on heavy infrastructure components:
- **API & RPC:** Django Ninja + django-mcp
- **Orchestration:** Temporal (for long-running jobs)
- **Data Lakehouse:** Apache Iceberg + Trino (distributed SQL) + MinIO (S3 Artifacts)
- **Streaming & Event Bus:** Apache Kafka + Flink
- **Observability:** SkyWalking (Trace IDs)

---

## 3. Tool Manifest: All Available Capabilities

An external Agent interfacing with Voyant via MCP currently has access to the following top-level API routes (as exposed by `apps/core/api.py`):

*   `/sources` (Discovery & Ingestion bindings)
*   `/jobs` (Temporal execution tracking)
*   `/sql` (Run distributed data queries)
*   `/governance` (Search metadata, lineage paths, check usage limits)
*   `/presets` (Pre-defined Temporal job routines)
*   `/artifacts` (Retrieve stored results, PDFs, CSVS in MinIO)
*   `/analyze` (Execute ML/Stats profiling arrays)
*   `/discovery` (Register new external schema definitions)
*   `/search` (Query Milvus vector database)
*   `/scrape` (Fetch URL -> Execute Script -> Read Text -> OCR Images)

---

## 4. Architectural Rules in Effect
Based on the provided codebase review:
*   **Django/Ninja Only**: Full compliance. No FastAPI. No SQLAlchemy used for new definitions (only Django ORM).
*   **Centralized Messages**: `apps.core.middleware` binds the SOMASession context.
*   **Agent-First**: Agent passes inputs; Voyant handles all intelligence mechanization. None of these apps contain internal "LLM brains;" they are *tools* for the SomaAgent to trigger.
