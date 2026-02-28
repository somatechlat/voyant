# Voyant v3 Production Readiness Task Plan

Document ID: VOYANT-TASKS-3.0.0
Status: In Progress (45% Complete)
Date: 2026-01-12 (Updated)
Includes: DataScraper Module (Section 19)

## 0. Tracking Conventions
- [ ] Not started
- [~] In progress
- [x] Complete

## 1. Core Agent Flow (Analyze One-Call)
- [x] Add REST endpoint `/v1/analyze` to execute full pipeline and return summary + artifact manifest.  
  Files: `apps/core/api.py`, `voyant_project/urls.py`
- [x] Add MCP tool `voyant.analyze` and map to REST endpoint.  
  Files: `apps/mcp/tools.py`
- [x] Implement Analyze Workflow (Temporal) with steps: normalize → profile → quality → KPI → charts → narrative.  
  Files: `apps/worker/workflows/analyze_workflow.py` (new), `apps/worker/activities/analysis_activities.py`, `apps/worker/activities/generation_activities.py`
- [x] Create artifact manifest structure and return with job summary.  
  Files: `apps/core/lib/artifact_store.py`, `apps/core/api.py`

Definition of Done: Agent can call `voyant.analyze` and get artifacts + summary in one call.

## 2. Persistence (Jobs, Sources, Presets, Artifacts)
- [x] Add Django ORM models for Source, Job, Preset, Artifact.  
  Files: `apps/workflows/models.py` (new)
- [x] Add migrations (Django) and bootstrapping.  
  Files: `apps/migrations/`
- [x] Replace in-memory stores with DB-backed CRUD.  
  Files: `apps/core/api.py`

Definition of Done: Jobs and sources persist across restarts.

## 3. Connector Provisioning (Airbyte)
- [ ] Implement connect/provision flow: create source, destination, connection, trigger sync.  
  Files: `apps/ingestion/lib/airbyte_client.py`, `apps/core/api.py`
- [ ] Store Airbyte IDs and sync state in DB.  
  Files: `apps/workflows/models.py`, `apps/core/api.py`

Definition of Done: `voyant.connect` provisions real Airbyte connections.

## 4. Ingestion Workflow Completion
- [ ] Update ingestion workflow to use Airbyte sync when source type is connector-based.  
  Files: `apps/worker/workflows/ingest_workflow.py`, `apps/worker/activities/ingest_activities.py`
- [ ] Add ingestion metadata persistence (row counts, tables).  
  Files: `apps/workflows/models.py`, `apps/worker/activities/ingest_activities.py`

Definition of Done: Ingest is real and tracked with job state + events.

## 5. Quality & Drift Pipeline
- [ ] Implement quality workflow execution for `/v1/jobs/quality`.  
  Files: `apps/worker/workflows/quality_workflow.py` (new), `apps/worker/activities/quality_activities.py` (new)
- [ ] Add Evidently integration or rule-based checks for quality and drift.  
  Files: `apps/core/lib/quality_rules.py`, `apps/core/lib/baseline_store.py`
- [ ] Persist quality artifacts and update manifest.  
  Files: `apps/core/lib/artifact_store.py`, `apps/core/api.py`

Definition of Done: Quality jobs generate artifacts and status updates.

## 6. Predictive Analytics (Regression, Forecasting, Anomaly)
- [ ] Expose regression and forecasting workflows via REST + MCP.  
  Files: `apps/core/api.py`, `apps/mcp/tools.py`, `apps/worker/workflows/operational_workflows.py`
- [ ] Add preset: `benchmark.brand` with KPI + comparison logic.  
  Files: `apps/core/api.py`, `apps/worker/workflows/benchmark_workflow.py`

Definition of Done: Agent can trigger regression/forecast/anomaly from MCP.

## 7. Artifacts & Manifest Standardization
- [ ] Standardize artifact types and names (profile, quality, drift, charts, narrative, kpi).  
  Files: `apps/core/lib/artifact_store.py`, `apps/core/lib/plugin_registry.py`
- [ ] Add manifest endpoint `/v1/artifacts/{job_id}/manifest`.  
  Files: `apps/core/api.py`

Definition of Done: All analysis outputs traceable in manifest.

## 8. Governance, Contracts, Lineage
- [ ] Enforce contract validation pre-ingest and pre-analyze.  
  Files: `apps/core/lib/contracts.py`, `apps/worker/activities/ingest_activities.py`
- [ ] Persist lineage graph to storage or emit to DataHub.  
  Files: `apps/core/lib/lineage.py`, `apps/core/api.py`

Definition of Done: Contracts enforced and lineage queryable.

## 9. Security & Auth Enforcement
- [ ] Add Keycloak auth dependency to protected routes.  
  Files: `apps/core/security/auth.py`, `apps/core/api.py`
- [ ] Add tenant enforcement to SQL and artifact access.  
  Files: `apps/core/api.py`

Definition of Done: All sensitive routes require JWT and tenant scoping.

## 10. Observability
- [ ] Expose `/metrics` in API and unify metric names.  
  Files: `apps/core/api.py`, `apps/core/lib/metrics.py`, `apps/core/lib/monitoring.py`
- [ ] Add tracing spans across API → workflow → activity.  
  Files: `apps/core/lib/structured_logging.py`, workflow/activity modules

Definition of Done: Metrics and traces available in production stack.

## 11. Reliability & Resilience
- [ ] Add circuit breakers around DataHub, MinIO, Trino.  
  Files: `apps/core/lib/circuit_breaker.py`, respective clients
- [ ] Add retry and timeout policies for all external calls.  
  Files: `apps/core/lib/retry_config.py`

Definition of Done: External failures are isolated and observable.

## 12. Rate Limiting and Quotas
- [ ] Implement rate limiting middleware on high-cost endpoints.  
  Files: `apps/core/middleware.py`, `apps/core/lib/tenant_quotas.py`

Definition of Done: Excessive requests receive 429 with error codes.

## 13. Error Contract Adoption
- [ ] Make API responses return structured error codes (`VYNT-XXXX`).  
  Files: `apps/core/lib/errors.py`, `apps/core/api.py`

Definition of Done: All error responses contain error code and message.

## 14. Test Coverage (Production Grade)
- [ ] Add end-to-end tests for analyze pipeline and artifacts.  
  Files: `tests/test_analyze_failure.py`, `tests/test_e2e_smoke.py`
- [ ] Add integration tests for Airbyte, DataHub, MinIO flows.  
  Files: `tests/integration/*`

Definition of Done: CI validates core agent journey.

## 15. Deployment Hardening
- [ ] Validate docker-compose healthchecks and dependency order.  
  Files: `docker-compose.yml`
- [ ] Helm chart values updated for new endpoints and services.  
  Files: `helm/*`

Definition of Done: Stack starts cleanly and supports production defaults.

## 16. Milestones
- M1: One-call analyze with artifacts + manifest
- M2: Persistence + real connectors
- M3: Quality + predictive workflows
- M4: Security + observability + reliability
- M5: Production hardening + tests
- M6: Apache platform integration (Iceberg, Ranger, Atlas, SkyWalking, NiFi, Superset, Druid/Pinot, Tika, Flink)

## 17. Apache Platform Integration
- [ ] Integrate Apache Iceberg as the lakehouse storage layer.  
  Files: `apps/core/lib/iceberg.py` (new), `config/iceberg/*` (new)
- [~] Add Apache Flink streaming pipelines for continuous KPIs and anomalies.
  Files: `apps/streaming/*` (new), `config/flink/*` (new)
  - [x] Add Flink JobManager/TaskManager to `docker-compose.yml`.
  - [x] Implement `voyant_flink_worker` or client keys.
  - [ ] Deploy `StreamingJob` via Temporal.
- [ ] Enforce Apache Ranger policies at query and artifact access.  
  Files: `apps/core/security/policy.py` (new), `apps/core/api.py`
- [ ] Publish metadata and lineage to Apache Atlas.  
  Files: `apps/governance/lib/atlas.py` (new), `apps/core/lib/lineage.py`
- [ ] Add Apache SkyWalking tracing export for API and workflows.  
  Files: `apps/observability/skywalking.py` (new), `voyant_project/urls.py`, workflow/activity modules
- [ ] Add Apache NiFi ingestion adapters and flow registration.  
  Files: `apps/ingestion/lib/nifi.py` (new), `apps/core/api.py`
- [ ] Add Apache Superset integration for curated datasets and artifacts.  
  Files: `apps/bi/superset.py` (new)
- [ ] Add Apache Druid and Pinot export pipelines for OLAP workloads.  
  Files: `apps/olap/druid.py` (new), `apps/olap/pinot.py` (new)
- [ ] Add Apache Tika document extraction path for unstructured ingestion.  
  Files: `apps/ingestion/lib/tika.py` (new), `apps/ingestion/lib/unstructured_utils.py`

Definition of Done: All Apache integrations are configured, testable, and wired into core agent workflows.

## 18. Soma Stack Integration (SomaAgentHub + SomaAgent01)
- [ ] Add Soma context middleware to accept `X-Soma-Session-ID`, `X-User-ID`, and `traceparent`.  
  Files: `apps/core/middleware.py`
- [ ] Persist `soma_session_id` on Job records and include in status callbacks.  
  Files: `apps/workflows/models.py`, `apps/core/api.py`
- [ ] Add Soma policy client to call Policy Engine `/v1/evaluate` for sensitive actions (ingest, analyze, artifact download).  
  Files: `apps/integrations/soma.py` (new), `apps/core/api.py`
- [ ] Add Memory Gateway client to persist analysis summaries via `/v1/remember` and optional `/v1/rag/retrieve`.  
  Files: `apps/integrations/soma.py` (new), `apps/worker/workflows/analyze_workflow.py`
- [ ] Add Orchestrator callback publishing job status updates to `/v1/sessions/*` when `X-Soma-Session-ID` is present.  
  Files: `apps/integrations/soma.py` (new), `apps/core/api.py`
- [ ] Add tool metadata export for SomaAgent01 tool registry (MCP schema and health).  
  Files: `apps/mcp/tools.py`, `voyant_project/asgi.py`
- [ ] Add integration tests against SomaAgentHub local stack (gateway, policy, memory).  
  Files: `tests/integration/*`

Definition of Done: SomaAgentHub can orchestrate Voyant workflows with policy and memory integration, and SomaAgent01 can register Voyant tools.

## 19. DataScraper Module (Pure Execution Tools)

### 19.1 Core Infrastructure (COMPLETED)
- [x] Create `apps/scraper/` module structure  
  Files: `apps/scraper/__init__.py`, `apps/scraper/apps.py`
- [x] Implement SSRF protection and URL validation  
  Files: `apps/scraper/security.py`
- [x] Create Django ORM models (ScrapeJob, ScrapeArtifact)  
  Files: `apps/scraper/models.py`
- [x] Implement Django Ninja API router  
  Files: `apps/scraper/api.py`
- [x] Create Temporal workflow (ScrapeWorkflow)  
  Files: `apps/scraper/workflow.py`
- [x] Implement 7 pure execution activities  
  Files: `apps/scraper/activities.py`

### 19.2 Parsing Stack (COMPLETED)
- [x] Create HTML parser with CSS/XPath extraction  
  Files: `apps/scraper/parsing/html_parser.py`
- [x] Create PDF parser with Apache Tika integration  
  Files: `apps/scraper/parsing/pdf_parser.py`
- [x] Create OCR processor with Tesseract  
  Files: `apps/scraper/parsing/ocr_processor.py`
- [x] Create Whisper transcription processor  
  Files: `apps/scraper/media/transcription.py`

### 19.3 Browser Clients (COMPLETED)
- [x] Implement Playwright client for JS rendering  
  Files: `apps/scraper/browser/playwright_client.py`
- [x] Implement BeautifulSoup client for static pages  
  Files: `apps/scraper/browser/beautifulsoup_client.py`
- [x] Implement Scrapy client for high volume  
  Files: `apps/scraper/browser/scrapy_client.py`
- [x] Implement Selenium client for legacy browser automation  
  Files: `apps/scraper/browser/selenium_client.py`

### 19.4 MCP Tool Registration (COMPLETED)
- [x] Register `scrape.fetch` tool  
  Files: `apps/mcp/tools.py`
- [x] Register `scrape.extract` tool  
  Files: `apps/mcp/tools.py`
- [x] Register `scrape.ocr` tool  
  Files: `apps/mcp/tools.py`
- [x] Register `scrape.parse_pdf` tool  
  Files: `apps/mcp/tools.py`
- [x] Register `scrape.transcribe` tool  
  Files: `apps/mcp/tools.py`

### 19.5 Integration & Testing (Planned)
- [ ] Add `voyant.scraper` to INSTALLED_APPS  
  Files: `voyant_project/settings.py`
- [ ] Run migrations for scraper models  
  Files: `apps/scraper/migrations/`
- [ ] Register workflow in worker_main.py  
  Files: `apps/worker/worker_main.py`
- [ ] Create unit tests for security module  
  Files: `tests/scraper/test_security.py`
- [ ] Create integration tests for workflow  
  Files: `tests/scraper/test_workflow.py`

Definition of Done: Agent Zero can use `scrape.*` MCP tools for pure execution web scraping.

**Architecture Reminder**: DataScraper is a PURE EXECUTION toolbox. NO LLM integration. Agent Zero handles all intelligence and provides selectors.
