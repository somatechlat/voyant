# Voyant Apps Codebase Inventory

**Generated:** 2026-08-31  
**Scope:** All 232 Python files across 16 app directories in `apps/`  
**Platform:** Django 5.0.6 + Django Ninja + Temporal + DuckDB + Milvus + Playwright + Scrapy  
**API Version:** v3.0.0

---

## Table of Contents

1. [analysis/](#analysis) — 20 files
2. [capsules/](#capsules) — 20 files
3. [core/](#core) — 25+ files (models, lib, security)
4. [discovery/](#discovery) — 8 files
5. [governance/](#governance) — 8 files
6. [ingestion/](#ingestion) — 8 files
7. [mcp/](#mcp) — 5 files
8. [ontology/](#ontology) — 6 files
9. [scraper/](#scraper) — 50+ files (incl. octopus/, deep_research/)
10. [search/](#search) — 6 files
11. [sql/](#sql) — 1 file
12. [streaming/](#streaming) — 6 files
13. [uptp_core/](#uptp_core) — 10+ files
14. [worker/](#worker) — 25 files (activities + workflows)
15. [workflows/](#workflows) — 5 files

---

## analysis/

### models.py
- **Purpose:** Django model for analysis jobs with status tracking, progress percentage, tenant isolation, and JSON result storage.
- **Key Classes:** `AnalysisJob` (extends `TenantModel`), status choices (PENDING/RUNNING/COMPLETED/FAILED/CANCELLED)
- **Dependencies:** `apps.core.models` (TenantModel, TimeStampedModel)
- **TODOs/FIXMEs:** None
- **Test Coverage:** Unknown
- **Issues:** None

### api.py
- **Purpose:** Django Ninja router for analysis endpoints — create job, list jobs, get status, cancel, get results.
- **Key Functions:** `create_analysis_job`, `list_analysis_jobs`, `get_analysis_status`, `cancel_analysis_job`, `get_analysis_results`
- **Dependencies:** `apps.core.lib.temporal_client`, `apps.analysis.models`
- **TODOs/FIXMEs:** None
- **Test Coverage:** Unknown
- **Issues:** None

### lib/ (12 modules)
- **adaptive_sampling.py** — Adaptive data sampling strategies (Bernoulli, Stratified, Adaptive). Key: `sample_table()`, `SamplingStrategy` enum, `SampleResult` dataclass.
- **anomaly.py** — Anomaly detection using Isolation Forest. Key: `detect_anomalies()`.
- **anomaly_detection.py** — Additional anomaly detection utilities.
- **cleaning_primitives.py** — Data cleaning with missing value imputation, outlier detection/treatment. Key: `DataCleaningPrimitives.clean_dataset()`.
- **forecast_primitives.py** — Prophet-based forecasting. Key: `ForecastPrimitives.forecast_prophet()`, `PROPHET_AVAILABLE` flag.
- **forecasting.py** — Native forecasting methods (EMA, Linear). Key: `forecast()`.
- **kpi_templates.py** — Pre-defined KPI SQL templates.
- **ml_primitives.py** — ML operations: K-Means clustering, classifier training, regression. Key: `MLPrimitives` class.
- **nlp_primitives.py** — NLP operations: sentiment analysis, text processing. Key: `NLPPrimitives` class.
- **segmentation.py** — Customer/data segmentation logic.
- **services_forecasting.py** — Service-level forecasting utilities.
- **stats_primitives.py** — R-backed statistical operations. Key: `RStatsPrimitives` class.
- **stats.py** — Statistical helper functions.

### migrations/
- Django migration for AnalysisJob model.

---

## capsules/

### models.py
- **Purpose:** Core capsule data models — installable intelligence recipes for AI agents.
- **Key Classes:** `Capsule` (execution_graph, parameters_schema, capabilities_whitelist, body, soul), `CapsuleInstallation`, `CapsuleInstance` (state, artifacts), `Capability`, `Constitution`
- **Dependencies:** `apps.core.models` (TenantModel, UUIDModel)
- **TODOs/FIXMEs:** None
- **Issues:** Capsule format v1.0.0 cross-compatible with somaAgent01

### schemas.py
- **Purpose:** Pydantic v2 schemas for capsule API request/response validation.
- **Key Classes:** CapsuleCreate, CapsuleUpdate, CapsuleResponse, etc.

### api.py
- **Purpose:** Django Ninja router for capsule CRUD, execution, installation endpoints.

### services/capsule_registry.py
- **Purpose:** Capsule loading and registration service. Key: `load_capsule_by_id()`

### services/ (additional)
- Additional capsule service modules.

### tests/ (5 files)
- `test_capsule_models.py` — Model unit tests
- `test_capsule_api.py` — API endpoint tests
- `test_capsule_services.py` — Service logic tests
- `test_capsule_integration.py` — Integration tests
- `test_capsule_workflows.py` — Workflow tests

---

## core/

### models.py
- **Purpose:** Base models inherited by all apps.
- **Key Classes:** `CoreConfig`, `TimeStampedModel` (created_at, updated_at), `RBACManager` (SpiceDB-backed permission checks), `TenantModel` (multi-tenant with realm_id), `UUIDModel`, `SoftDeleteModel`
- **Dependencies:** Django ORM, `apps.core.security.policy`
- **Issues:** None

### api.py
- **Purpose:** NinjaAPI registration hub — all routers registered here.
- **Key:** `NinjaAPI` instance, URL router configuration, v3.0.0

### config.py
- **Purpose:** Pydantic-settings configuration with Docker secrets support.
- **Key:** `get_settings()` singleton, environment variable mapping, Docker secret file paths

### middleware.py
- **Purpose:** Django middleware for request processing.

### views.py
- **Purpose:** Health/readiness endpoints.

### lib/errors.py
- **Purpose:** Canonical error catalog with `VYNT-XXXX` codes.
- **Key Classes:** `VoyantError` base, `AnalysisError`, `ExternalServiceError`, `IngestionError`, etc.

### lib/plugin_registry.py
- **Purpose:** Extensible plugin system for analyzers and generators.
- **Key Functions:** `get_analyzers()`, `get_generators()`, `get_plugin()`

### lib/temporal_client.py
- **Purpose:** Singleton Temporal client connection manager.
- **Key:** `get_temporal_client()` async function

### lib/artifact_store.py
- **Purpose:** Content-addressable artifact store with SHA256/SHA512/BLAKE2B hashing and gzip compression.
- **Key:** SHA256/SHA512/BLAKE2B content hashing, MinIO backend

### lib/circuit_breaker.py
- **Purpose:** Thread-safe circuit breaker pattern — CLOSED/OPEN/HALF_OPEN states.
- **Key:** `CircuitBreakerOpenError`

### lib/contracts.py
- **Purpose:** Schema validation and sensitivity classification for data contracts.
- **Key:** `get_contract()`, `validate_schema()`

### lib/event_schema.py
- **Purpose:** In-memory event schema registry with semver support.

### lib/events.py
- **Purpose:** Kafka producer for `VoyantEvent` publication.

### lib/interceptors.py
- **Purpose:** Temporal activity/workflow interceptors for metrics collection.
- **Key:** `MetricsInterceptor`

### lib/job_queue.py
- **Purpose:** Redis-backed per-tenant concurrency queue with lease-based ownership.

### lib/metrics.py
- **Purpose:** Mode-gated Prometheus metrics (off/basic/full) based on `UDB_METRICS_MODE`.

### lib/monitoring.py
- **Purpose:** `MetricsRegistry` singleton for Prometheus exposition.

### lib/namespace_analyzer.py
- **Purpose:** Tenant table isolation namespace analyzer (PREFIX/SCHEMA/METADATA modes).

### lib/pdf_engine.py
- **Purpose:** WeasyPrint + Jinja2 sandbox PDF rendering.
- **Key:** `PDFAssembler.compile_pdf()`

### lib/plotly_engine.py
- **Purpose:** Plotly/Kaleido chart rendering to artifact URIs.
- **Key:** `PlotlyRenderer.render_bar_comparison()`, `render_time_series()`

### lib/policy.py
- **Purpose:** Soma policy engine integration (OPA-based external policy).

### lib/python_sandbox.py
- **Purpose:** Docker-isolated Python script execution.
- **Key:** `PythonSandboxNode.execute_script()`

### lib/quotas.py
- **Purpose:** Tiered tenant resource quotas.

### lib/r_bridge.py
- **Purpose:** Rserve statistical engine bridge (R language integration).
- **Key:** `REngine` class

### lib/retry_config.py
- **Purpose:** Temporal retry policies with named constants (e.g., `EXTERNAL_SERVICE_RETRY`, `TIMEOUTS` dict).

### lib/secrets.py
- **Purpose:** Multi-backend secret management (in-memory, file, Vault, AWS KMS) with Fernet encryption and rotation.

### lib/spicedb_rbac.py
- **Purpose:** Realm-aware RBAC checks via Authzed gRPC.

### lib/tenant_quotas.py
- **Purpose:** Resource limits + usage tracking per tenant.

### lib/trino.py
- **Purpose:** Read-only Trino SQL client for query execution.
- **Key:** `get_trino_client()`

### lib/workflow_utils.py
- **Purpose:** Job dispatch boilerplate utilities.

### security/auth.py
- **Purpose:** Keycloak JWT authentication middleware.
- **Key:** Token validation, user extraction

### security/policy.py
- **Purpose:** SpiceDBClient for authorization policy enforcement.

---

## discovery/

### models.py
- **Purpose:** `ServiceDefinition` model for discovered external APIs.
- **Key Classes:** `ServiceDefinition`

### api.py
- **Purpose:** API endpoints for service discovery management.

### lib/catalog.py
- **Purpose:** Service catalog management.

### lib/spec_parser.py
- **Purpose:** OpenAPI/Swagger specification parser.
- **Key:** `SpecParser.parse_from_url()`

### lib/search_utils.py
- **Purpose:** External API documentation search client.
- **Key:** `SearchClient.search_apis()`

---

## governance/

### models.py
- **Purpose:** Governance data models — contracts, lineage, policies.
- **Key Classes:** `DataContract`, `DataLineage`, `GovernancePolicy`

### api.py
- **Purpose:** Governance API endpoints.

### lib/datahub_client.py
- **Purpose:** DataHub integration client for metadata management.

### lib/lineage.py
- **Purpose:** Data lineage graph recording and querying.
- **Key:** `get_lineage_graph()`, `record_job_lineage()`

### lib/policy_engine.py
- **Purpose:** Governance policy engine for compliance checks.

### lib/schema_evolution.py
- **Purpose:** Schema versioning and evolution tracking.
- **Key:** `ColumnSchema`, `TableSchema`, `track_schema()`

---

## ingestion/

### models.py
- **Purpose:** `IngestionJob` model with source tracking and status management.

### lib/duckdb_loader.py
- **Purpose:** DuckDB data loading operations.

### lib/transform.py
- **Purpose:** Data transformation pipeline.

### lib/quality_rules.py
- **Purpose:** Quality rule definitions — `NullCheck`, `RangeCheck`, `UniqueCheck`, `QualityEngine`.
- **Key:** `QualityEngine.validate()`

### lib/airbyte_client.py
- **Purpose:** Airbyte integration client for ELT sync operations.
- **Key:** `get_airbyte_client()`, `trigger_sync()`, `wait_for_completion()`

---

## mcp/

### server.py
- **Purpose:** MCP (Model Context Protocol) tool server entry point.

### tools_core.py
- **Purpose:** Core MCP tools for data operations.

### tools_catalog.py
- **Purpose:** MCP tools for catalog management.

### tools_scrape.py
- **Purpose:** MCP tools for web scraping operations.

---

## ontology/

### models.py
- **Purpose:** Ontology data models for entity/relationship management.

### api.py
- **Purpose:** Ontology API endpoints.

### services/ontology_service.py
- **Purpose:** Ontology CRUD and query operations.

### validators.py
- **Purpose:** Ontology schema validation.

---

## scraper/ (Largest App)

### models.py
- **Purpose:** Scraper data models — `ScrapeJob` (UUID pk, status, progress), `ScrapeArtifact` (content hash idempotent).
- **Key Classes:** `ScrapeJob`, `ScrapeArtifact`

### api.py
- **Purpose:** Scraper API endpoints — `start_scrape`, `extract`, `ocr`, `parse_pdf`, `status`, `cancel`.
- **Key:** `scrape_router`

### security.py
- **Purpose:** SSRF protection — `BLOCKED_HOSTS`, `BLOCKED_NETWORKS`, URL validation, DNS resolution, selector sanitization, rate limiting.
- **Key Functions:** `validate_url()`, `validate_url_ssrf()`, `resolve_hostname()`, `is_ip_blocked()`

### workflow.py
- **Purpose:** `ScrapeWorkflow` — Temporal orchestration for fetch→extract→store pipeline.
- **Key:** `ScrapeWorkflow` (Temporal workflow)

### search_activities.py
- **Purpose:** `SearchActivities` — SearXNG sovereign search node integration.
- **Key:** `execute_searxng_query()` activity

### activities/ (Rule 245 split)
- **fetch_activities.py** — `FetchActivities`: Playwright/httpx/Scrapy page fetching
- **parse_activities.py** — `ParseActivities`: HTML/OCR/Whisper/PDF content extraction
- **storage_activities.py** — `StorageActivities`: MinIO artifact storage + ORM persistence
- **Backward compat:** `ScrapeActivities` aggregate class

### browser/scrapy_client.py
- **Purpose:** Scrapy client wrapper for crawling operations.
- **Key:** `ScrapyClient`

### parsing/html_parser.py
- **Purpose:** lxml-based HTML parser with CSS/XPath extraction.
- **Key:** `HTMLParser.extract()`, `get_all_links()`, `get_all_images()`

### parsing/ocr_processor.py
- **Purpose:** Tesseract OCR processor for image text extraction.
- **Key:** `OCRProcessor.extract_structured()`

### parsing/pdf_parser.py
- **Purpose:** PDF parsing with pdfplumber + Tika.
- **Key:** `PDFParser.parse()`

### deep_research_workflow.py
- **Purpose:** Deep Research v1 — search→scrape→extract pipeline.
- **Key:** `DeepResearchWorkflow`

### deep_research/ (v2)
- **workflow.py** — `DeepResearchWorkflowV2`: 10-step deterministic pipeline (query expansion → multi-engine search → parallel fetch → content extraction → source scoring → MinHash dedup → synthesis → recursive follow-up → cross-validation → report generation)
- **activities.py** — All zero-LLM activities for the v2 workflow
- **agents/**:
  - `query_generator.py` — `QueryGenerator`: Deterministic query expansion
  - `content_extractor.py` — `ContentExtractor`: trafilatura/readability/newspaper/crawl4ai fallback chain
  - `source_scorer.py` — `SourceScorer`: credibility×freshness scoring
  - `synthesizer.py` — `Synthesizer`: TF-IDF sentence clustering
  - `cross_validator.py` — `CrossValidator`: n-gram overlap validation
  - `report_generator.py` — `ReportGenerator`: Markdown templating
- **sources/**:
  - `searxng_client.py` — SearXNG search engine client
  - `brave_client.py` — Brave Search API client
  - `google_cse_client.py` — Google Custom Search client
- **credibility/domain_db.py** — Static tier-based domain scoring (academic→low-quality)
- **schemas.py** — Pydantic v2 schemas: `ResearchConfig`, `Citation`, `Finding`, `EvidenceChunk`, `ResearchReport`, etc.

### octopus/ (Multi-Arm Web Intelligence Engine)
- **dispatcher.py** — `OctopusDispatcher`: Routes requests to ARM executors, enforces SSRF/quotas/circuit breakers
- **schemas.py** — `OctopusRequest`, `OctopusResult`, `OctopusARM` enum (STATIC/DYNAMIC/EVASION/CRAWL/API_INTERCEPT/DOCUMENT/OCR/TRANSCRIBE/ARCHIVE)
- **arms/** (9 ARM executors):
  - **arm_static.py** — ARM-1: Static scraping with httpx + parsel (CSS/XPath extraction, OpenGraph/Schema.org metadata)
  - **arm_dynamic.py** — ARM-2: Dynamic scraping with Playwright + playwright-stealth (JS rendering, browser actions)
  - **arm_evasion.py** — ARM-3: Evasion scraping with curl-cffi (TLS fingerprint impersonation) or camoufox (stealth browser)
  - **arm_crawl.py** — ARM-4: Large-scale site crawling with Scrapy (depth control, robots.txt, sitemap)
  - **arm_api_intercept.py** — ARM-5: API interception via Playwright network monitoring (XHR/Fetch JSON capture)
  - **arm_document.py** — ARM-6: Document parsing with pdfplumber + unstructured (PDF/Office extraction)
  - **arm_ocr.py** — ARM-7a: OCR extraction with Tesseract (image text + bounding boxes)
  - **arm_transcribe.py** — ARM-7b: Audio/video transcription with OpenAI Whisper (text/JSON/SRT output)
  - **arm_archive.py** — ARM-8: Interactive deep archive with Playwright (UI clicking + file downloading)

### tests/ (4 files)
- **test_html_parser.py** — CSS/XPath extraction tests, edge cases (empty HTML, invalid selectors, Spanish content), Ecuador-specific data
- **test_security.py** — SSRF protection tests (localhost, private IPs, metadata endpoints, DNS resolution)
- **test_workflow.py** — ScrapeWorkflow import/structure test
- **test_e2e_network_infra.py** — Real infrastructure E2E tests (httpbin.org, Ecuador gov sites, DNS resolution)

---

## search/

### api.py
- **Purpose:** Semantic search + indexing API endpoints.
- **Key:** `search_router`, `index_router`

### lib/embeddings.py
- **Purpose:** Embedding models — TF-IDF, char-based, dense, sparse.
- **Key:** Multiple embedding strategy implementations

### lib/milvus_store.py
- **Purpose:** Milvus vector store with hybrid dense+sparse search and tenant partition keys.
- **Key:** `get_vector_store()`, `search()`, `index()`

### tests/
- Search module tests.

---

## sql/

### api.py
- **Purpose:** SQL execution API via Trino (read-only queries).
- **Key:** `sql_router`

---

## streaming/

### activities.py
- **Purpose:** `StreamingActivities` — Apache Flink REST API bridge.
- **Key:** `get_cluster_overview()`, `list_running_jobs()`, `submit_streaming_job()`

### workflow.py
- **Purpose:** `StreamingJobWorkflow` — validate→submit→monitor pipeline for Flink jobs.

### flink_client.py
- **Purpose:** Flink REST API client wrapper.
- **Key:** `FlinkClient`

### jobs/
- Additional streaming job management files.

---

## uptp_core/

### engine.py
- **Purpose:** UPTP (Universal Parametric Template Pattern) dispatch engine — central execution routing.
- **Key:** `UPTPEngine` class

### parser.py
- **Purpose:** Generic URI parser for UPTP resource addressing.
- **Key:** `URIParser.parse_uri()`

### models/
- UPTP-specific data models.

### tests/
- UPTP engine tests.

---

## worker/

### worker_main.py
- **Purpose:** Temporal worker entrypoint — initializes Django, connects to Temporal, registers all workflows and activities, handles graceful shutdown.
- **Key:** `run_worker()`, `_setup_django()`, worker mode selection (scraper vs full)
- **Registered Activities (full mode):** 30+ activities across all domains
- **Registered Workflows:** IngestDataWorkflow, ProfileWorkflow, AnalyzeWorkflow, QualityWorkflow, BenchmarkBrandWorkflow, DetectAnomaliesWorkflow, AnalyzeSentimentWorkflow, FixDataQualityWorkflow, ForecastWorkflow, SegmentCustomersWorkflow, LinearRegressionWorkflow, ScrapeWorkflow, DeepResearchWorkflow, StreamingJobWorkflow, SandboxWorkflow, CapsuleWorkflow, DeepResearchWorkflowV2
- **Activity Executor:** ThreadPoolExecutor sized from config or `min(32, cpu_count * 5)`

### activities/ (13 files)
- **analysis_activities.py** — `AnalysisActivities`: `fetch_sample` (DuckDB read-only), `run_analyzers` (plugin registry execution with feature flags)
- **capsule_activities.py** — `CapsuleActivities`: `load_capsule`, `eval_condition`, `substitute_params` (Jinja2 sandbox), `execute_step` (routes to 10 action handlers: deep_research, scrape, ingest, analyze, search, sql_query, render_plotly, render_pdf, notify, audit_log), `cross_validate`, `generate_artifacts`, `store_report`. Persists results to DB to avoid Temporal event history bloat.
- **discovery_activities.py** — `DiscoveryActivities`: `search_for_apis`, `scan_spec_url` (OpenAPI spec parsing)
- **generation_activities.py** — `GenerationActivities`: `run_generators` (plugin registry execution with feature flags)
- **ingest_activities.py** — `IngestActivities`: `run_ingestion` (DuckDB connectivity + row counting), `sync_airbyte` (Airbyte sync with UPTP URI resolution), `validate_contract_activity`, `record_lineage_activity`
- **kpi_activities.py** — `KPIActivities`: `run_kpis` (Trino SQL execution for KPI definitions)
- **ml_activities.py** — `MLActivities`: `cluster_data` (K-Means), `train_classifier_model` (RandomForest), `forecast_time_series` (Prophet), `train_regression_model` (Linear)
- **operational_activities.py** — `OperationalActivities`: `clean_data`, `detect_anomalies`, `analyze_sentiment_batch`, `fix_data_quality` (with quality score calculation), `forecast_time_series`
- **profile_activities.py** — `ProfileActivities`: `profile_data` (adaptive sampling with SQL Bernoulli + Python-side refinement, per-column statistics)
- **quality_activities.py** — `QualityActivities`: `fetch_sample` (DuckDB), `run_quality_checks` (NullCheck/RangeCheck/UniqueCheck rules via QualityEngine)
- **sandbox_activities.py** — `SandboxActivities`: `run_python_sandbox` (Docker-isolated execution via PythonSandboxNode)
- **stats_activities.py** — `StatsActivities`: `describe_distribution` (with schema tracking), `calculate_correlation`, `fit_distribution`, `calculate_market_share` (R script execution), `perform_hypothesis_test` (t-test)

### workflows/ (12 files)
- **analyze_workflow.py** — `AnalyzeWorkflow`: Orchestrates profile→analyze→KPI→generate pipeline
- **benchmark_workflow.py** — `BenchmarkBrandWorkflow`: Full Tier-4 competitive brand analysis — parallel ingestion → data sampling → market share + hypothesis test → bar chart generation → PDF report. All data is real, no hardcoded values.
- **capsule_workflow.py** — `CapsuleWorkflow`: Multi-step capsule execution with conditions, retries, artifact generation. State carried in workflow; results persisted to CapsuleInstance DB.
- **ingest_workflow.py** — `IngestDataWorkflow`: Contract validation → data ingestion → lineage recording. Retry policy with non-retryable error types.
- **operational_workflows.py** — Four workflows: `DetectAnomaliesWorkflow`, `AnalyzeSentimentWorkflow`, `FixDataQualityWorkflow`, `ForecastWorkflow`
- **profile_workflow.py** — `ProfileWorkflow`: Data profiling orchestration (15 min timeout)
- **quality_workflow.py** — `QualityWorkflow`: Sample fetch → quality validation pipeline
- **regression_workflow.py** — `LinearRegressionWorkflow`: Model training → equation formatting → R² interpretation
- **sandbox_workflow.py** — `SandboxWorkflow`: Script execution in Docker sandbox (1 hour timeout, no retry for security)
- **segmentation_workflow.py** — `SegmentCustomersWorkflow`: K-Means clustering → segment profile enrichment
- **types.py** — Dataclasses: `IngestParams`, `IngestResult`
- **__init__.py** — Empty

---

## workflows/

### models.py
- **Purpose:** Workflow-related data models — `Job`, `Artifact`, `PresetJob`.
- **Key Classes:** `Job` (Temporal dispatch), `Artifact` (download tracking), `PresetJob` (template presets)

### api.py
- **Purpose:** API routers for jobs, presets, artifacts.
- **Key:** `jobs_router` (CRUD + KPI templates + Temporal dispatch), `presets_router` (template management), `artifacts_router` (download + artifact management)

---

## Cross-Cutting Concerns

### Architecture Patterns
- **Multi-tenancy:** `TenantModel` with `realm_id`, all queries filtered by tenant
- **RBAC:** SpiceDB (Authzed gRPC) via `RBACManager` and `SpiceDBClient`
- **Async Jobs:** Temporal workflows for all long-running operations
- **Plugin System:** `plugin_registry.py` for extensible analyzers/generators
- **Content-Addressable Storage:** SHA256/SHA512/BLAKE2B artifact dedup
- **Circuit Breaker:** Thread-safe CLOSED/OPEN/HALF_OPEN for external services
- **Circuit Breaker Pattern:** `CircuitBreakerOpenError` used across ingestion, stats, Airbyte
- **SSRF Protection:** Comprehensive URL/DNS/IP blocking in scraper
- **Metrics:** Prometheus mode-gated (off/basic/full), MetricsInterceptor for Temporal
- **Secrets:** Multi-backend (in-memory, file, Vault, AWS KMS) with Fernet encryption and rotation
- **Namespace Isolation:** PREFIX/SCHEMA/METADATA modes for tenant table isolation
- **Concurrency Queue:** Redis-backed per-tenant job queue with lease-based ownership

### Key Dependencies
- Django 5.0.6, Django Ninja, Temporal, pydantic-settings, scikit-learn, Prophet, NLTK, Playwright, httpx, jinja2 sandbox, Apache Flink, Plotly/Kaleido, WeasyPrint, Prometheus, Milvus (pymilvus), Docker, Scrapy, Tesseract OCR, Whisper, pdfplumber, trafilatura, readability-lxml, newspaper3k, crawl4ai, curl-cffi, camoufox, parsel, unstructured, SpiceDB (Authzed gRPC), Kafka, Rserve, Airbyte, MinIO

### Error Code Format
- Canonical `VYNT-XXXX` codes in `apps/core/lib/errors.py`

### Capsule System
- Capsules = "installable intelligence recipes for AI agents"
- Cross-compatible with somaAgent01 format v1.0.0
- Execution graph with conditions, retries, capability whitelisting
- Jinja2 sandbox parameter substitution
- Results persisted to DB to avoid Temporal 2MB event history limit
- Cross-validation across steps

### Deep Research v2
- Deterministic multi-source research pipeline (zero LLM dependency)
- MinHash/LSH deduplication, TF-IDF synthesis
- Cross-validation via n-gram overlap
- Multiple search engine backends (SearXNG, Brave, Google CSE)
- Domain credibility scoring (static tier database)

### OCTOPUS
- "Multi-Arm Autonomous Web Intelligence Engine"
- 9 ARM executors covering static, dynamic, evasion, crawl, API intercept, document, OCR, transcription, and archive strategies
- Unified `OctopusRequest`/`OctopusResult` schemas
- SSRF protection, rate limiting, circuit breaker enforcement
