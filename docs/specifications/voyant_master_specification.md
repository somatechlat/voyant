# VOYANT: UNIVERSAL AI DATA WORKFLOW ENGINE
**Master Architectural State & MCP Tool Registry**

## 1. Core Philosophy: The Universal Toolbox
Voyant is NOT bound exclusively to `SomaAgentHub`.
Voyant is a **Universal Model Context Protocol (MCP) Server** (`django-mcp` v0.3.1) designed to provide heavy-duty data engineering, scraping, and analytical capabilities to **ANY** AI Agent capable of speaking the MCP standard.

The target architecture (`docs/architecture/DESIGN.md`) mentions Soma, but the *actual deployed code* in `apps/mcp/tools.py` proves Voyant operates as a standalone, stateless toolbox.

### The "Zero Intelligence" Rule
* **No LLMs Inside:** Voyant has absolutely no Large Language Models built into it.
* **No Autonomous Decisions:** Voyant cannot "decide" what to scrape or query.
* **Pure Execution:** The connected Agent (Claude, GPT, SomaAgent, etc.) provides the SQL, the URLs, and the CSS Selectors. Voyant provides the compute (Iceberg, Trino, Temporal, Playwright, Whisper) to execute those commands and return the raw data safely.

---

## 2. Exhaustive Registry of Exposed MCP Tools (37 Total)
Voyant exposes **37 distinct tools** to any connected agent. These tools cover the entire data lifecycle:

### A. Web Scraping & Media Extraction (`apps/scraper`)
1. `scrape.fetch`: Fetch a webpage using Playwright or HTTPX (supports JS rendering & scrolling).
2. `scrape.extract`: Parse HTML using Agent-provided CSS/XPath selectors.
3. `scrape.ocr`: Extract text from images using Tesseract OCR.
4. `scrape.parse_pdf`: Extract text and tables from PDF documents.
5. `scrape.transcribe`: Convert audio/video to text using Whisper.

### B. Discovery & Connectors (`apps/discovery`)
6. `voyant.discover`: Auto-detect source types from DB URIs or hints.
7. `voyant.connect`: Create a new connection to a data source (DB, API, S3).
8. `voyant.discovery.services.list`: List registered external API services.
9. `voyant.discovery.services.get`: Get details of a single API service.
10. `voyant.discovery.services.register`: Register a new OpenAPI spec or API endpoint.
11. `voyant.discovery.scan`: Scan an OpenAPI URL to preview its available endpoints.

### C. Data Ingestion & Sync (`apps/ingestion`)
12. `voyant.ingest`: Trigger a Temporal workflow to pull data from a source into the Data Lakehouse (Iceberg).
13. `voyant.sources.list`: List all configured data sources.
14. `voyant.sources.get`: Retrieve credentials/configuration for a source.
15. `voyant.sources.delete`: Remove a data source.

### D. Data Quality & Profiling (`apps/analysis`)
16. `voyant.profile`: Run deep statistical profiling on a table.
17. `voyant.quality`: Run Data Quality checks (e.g., Evidently) against a table.
18. `voyant.analyze`: Execute ML predictors, KPI metrics, and advanced analyzers.

### E. Semantic Search (Vector DB) (`apps/search`)
19. `voyant.vector.search`: Query Milvus for semantically similar text embeddings.
20. `voyant.vector.index`: Generate an embedding for text (TF-IDF) and store it in Milvus.
21. `voyant.search`: Legacy alias for vector search.

### F. SQL Query Engine (`apps/sql` & `apps/analysis`)
22. `voyant.sql`: Execute ad-hoc, read-only SQL queries via Trino against the data lake.
23. `voyant.kpi`: Run multiple predefined SQL KPI queries simultaneously.
24. `voyant.tables.list`: List all available tables in the Trino schema.
25. `voyant.tables.columns`: Inspect columns and data types for a specific table.

### G. Governance, Lineage, & Quotas (`apps/governance`)
26. `voyant.lineage`: Query DataHub for upstream/downstream data dependencies.
27. `voyant.governance.schema`: Pull schema metadata directly from DataHub.
28. `voyant.quotas.tiers`: List available quota tiers.
29. `voyant.quotas.usage`: Check current API/Job usage for the connected tenant.
30. `voyant.quotas.limits`: See the exact limits (storage, jobs) allowed for the tenant.
31. `voyant.quotas.set_tier`: Upgrade or downgrade a tenant's tier.

### H. Workflow & Artifact Management (`apps/workflows`)
32. `voyant.status`: Check the status/progress of a long-running Temporal Job (e.g., `ingest`, `profile`).
33. `voyant.jobs.list`: List all historical and active jobs.
34. `voyant.jobs.cancel`: Abort a running Temporal workflow.
35. `voyant.artifact`: Fetch metadata and storage path for a completed artifact.
36. `voyant.artifacts.list`: List all artifacts (CSVs, JSONs, PDFs) produced by a specific job.

### I. Templated Presets (`apps/workflows`)
37. `voyant.preset`: Execute a pre-configured job pipeline.
38. `voyant.presets.list`: List all executed preset jobs.
39. `voyant.presets.get`: Get details of a specific preset job.
40. `voyant.kpi_templates.list`: List available SQL templates for Business KPIs.
41. `voyant.kpi_templates.categories`: Filter templates by category (e.g., Sales, HR).
42. `voyant.kpi_templates.get`: Retrieve the SQL string for a template.
43. `voyant.kpi_templates.render`: Safely inject parameters into a KPI SQL template.

---

## 3. Infrastructure & Frameworks
Voyant relies heavily on the following robust, scalable backend:
* **API Layer**: Django 5 + Django Ninja (REST) + `django-mcp` (Tool Provider)
* **Metadata/Governance**: DataHub (GraphQL API)
* **Vector Store**: Milvus (for search embeddings)
* **Async Orchestration**: Temporal (managing long-running python activities)
* **Analytic Engine**: Trino + Apache Iceberg (SQL layer)
* **Scraping Runtime**: Playwright + httpx + Tesseract + Whisper
