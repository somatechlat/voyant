# Voyant Workflow & Activity Documentation

This document provides a comprehensive reference for all Temporal workflows and activities in the Voyant platform.

---

## Table of Contents

1. [Workflows](#workflows)
2. [Activities](#activities)
3. [Retry & Timeout Configuration](#retry--timeout-configuration)

---

## Workflows

### Worker Workflows (`apps/worker/workflows/`)

| Workflow Class | File | Description | Activities Used |
|---|---|---|---|
| `ProfileWorkflow` | `profile_workflow.py` | Orchestrates data profiling jobs — generates statistical summaries of datasets. | `profile_data` |
| `IngestDataWorkflow` | `ingest_workflow.py` | End-to-end data ingestion: contract validation → data ingestion → lineage recording. | `validate_contract_activity`, `run_ingestion`, `record_lineage_activity` |
| `AnalyzeWorkflow` | `analyze_workflow.py` | Full data analysis pipeline: profiling → analyzer plugins → KPI calculation → artifact generation. | `profile_data`, `fetch_sample`, `run_analyzers`, `run_kpis`, `run_generators` |
| `CapsuleWorkflow` | `capsule_workflow.py` | Multi-step capsule execution with conditions, retries, and artifact generation. Persists step results to DB. | `capsule.load_capsule`, `capsule.eval_condition`, `capsule.substitute_params`, `capsule.execute_step`, `capsule.cross_validate`, `capsule.generate_artifacts`, `capsule.store_report` |
| `BenchmarkBrandWorkflow` | `benchmark_workflow.py` | Tier-4 competitive brand analysis: parallel ingestion → sampling → statistical analysis → chart → PDF report. | `run_ingestion`, `fetch_sample`, `calculate_market_share`, `perform_hypothesis_test`, `run_generators` |
| `SegmentCustomersWorkflow` | `segmentation_workflow.py` | Customer/data segmentation via clustering (K-Means), with post-processing segment profiles. | `cluster_data` |
| `LinearRegressionWorkflow` | `regression_workflow.py` | Linear regression analysis: trains model, formats equation, interprets R². | `train_regression_model` |
| `SandboxWorkflow` | `sandbox_workflow.py` | Executes raw Python scripts in an isolated Docker sandbox with no network access. | `run_python_sandbox` |
| `QualityWorkflow` | `quality_workflow.py` | Data quality validation: samples data then runs quality checks. | `quality_fetch_sample`, `run_quality_checks` |
| `DetectAnomaliesWorkflow` | `operational_workflows.py` | Detects anomalies/outliers in a dataset (e.g., Isolation Forest). | `detect_anomalies` |
| `AnalyzeSentimentWorkflow` | `operational_workflows.py` | Batch sentiment analysis on text inputs with aggregate breakdown. | `analyze_sentiment_batch` |
| `FixDataQualityWorkflow` | `operational_workflows.py` | Automatic remediation of data quality issues (missing values, outliers). | `fix_data_quality` |
| `ForecastWorkflow` | `operational_workflows.py` | Time series forecasting using EMA, Prophet, or linear methods. | `forecast_time_series` |

### Scraper Workflows (`apps/scraper/`)

| Workflow Class | File | Description | Activities Used |
|---|---|---|---|
| `ScrapeWorkflow` | `workflow.py` | Agent-Tool web scraping: fetch → extract → OCR (optional) → transcribe (optional) → store → finalize. | `fetch_page`, `extract_data`, `process_ocr`, `transcribe_media`, `store_artifact`, `finalize_job` |
| `DeepResearchWorkflow` | `deep_research_workflow.py` | Google AI-style deep research: SearXNG search → parallel Playwright scrape → content extraction. | `execute_searxng_query`, `fetch_page` |
| `DeepResearchWorkflowV2` | `deep_research/workflow.py` | Autonomous multi-source research pipeline: query expansion → multi-engine search → fetch → extract → score → dedup → synthesize → cross-validate → report → store. | `dr_generate_queries`, `dr_search_all_engines`, `dr_fetch_octopus`, `dr_extract_content`, `dr_score_sources`, `dr_deduplicate`, `dr_synthesize`, `dr_cross_validate`, `dr_generate_report`, `dr_store_artifact` |

### Streaming Workflows (`apps/streaming/`)

| Workflow Class | File | Description | Activities Used |
|---|---|---|---|
| `StreamingJobWorkflow` | `workflow.py` | Manages Apache Flink streaming jobs: cluster health check → job submission. | `get_cluster_overview`, `submit_streaming_job` |

---

## Activities

### Worker Activities (`apps/worker/activities/`)

#### `profile_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `profile_data` | `ProfileActivities.profile_data` | Profiles a dataset using adaptive sampling via DuckDB. Computes per-column statistics (type, nulls, uniques, descriptive stats). |

#### `ingest_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `run_ingestion` | `IngestActivities.run_ingestion` | Executes data ingestion pipeline: fetches source config, validates mode, connects to DuckDB, counts rows. |
| `sync_airbyte` | `IngestActivities.sync_airbyte` | Triggers Airbyte sync with circuit breaker protection. Supports UPTP generic URI resolution for dynamic connection creation. |
| `validate_contract_activity` | `IngestActivities.validate_contract_activity` | Validates data contracts for a source before ingestion. Returns `skipped=True` if no contract exists. |
| `record_lineage_activity` | `IngestActivities.record_lineage_activity` | Records data lineage edges linking source → job → output table in the lineage graph. |

#### `analysis_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `fetch_sample` | `AnalysisActivities.fetch_sample` | Fetches a data sample from DuckDB for in-memory analysis. Configurable table and sample size. |
| `run_analyzers` | `AnalysisActivities.run_analyzers` | Dynamically loads and executes registered analyzer plugins against provided data. Respects feature flags. |

#### `generation_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `run_generators` | `GenerationActivities.run_generators` | Dynamically runs all active artifact generator plugins (charts, reports, narratives). Respects feature flags. |

#### `ml_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `cluster_data` | `MLActivities.cluster_data` | Performs K-Means clustering on input data. Returns cluster assignments and quality metrics. |
| `train_classifier_model` | `MLActivities.train_classifier_model` | Trains a classification model (e.g., RandomForest). Returns performance metrics. |
| `forecast_time_series` | `MLActivities.forecast_time_series` | Generates time series forecast using Prophet. Returns predicted values and confidence intervals. |
| `train_regression_model` | `MLActivities.train_regression_model` | Trains a linear regression model. Returns coefficients, intercept, and R² score. |

#### `kpi_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `run_kpis` | `KPIActivities.run_kpis` | Executes a list of KPI SQL queries via Trino. Returns columns, rows, and query IDs. |

#### `sandbox_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `run_python_sandbox` | `SandboxActivities.run_python_sandbox` | Executes Python scripts in an isolated Docker sandbox via `PythonSandboxNode`. |

#### `discovery_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `search_for_apis` | `DiscoveryActivities.search_for_apis` | Searches for external API documentation based on a query string. |
| `scan_spec_url` | `DiscoveryActivities.scan_spec_url` | Downloads and parses an OpenAPI/Swagger specification from a URL. Returns title, version, base URL, endpoints. |

#### `quality_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `quality_fetch_sample` | `QualityActivities.fetch_sample` | Fetches a sample from DuckDB specifically for quality checks. |
| `run_quality_checks` | `QualityActivities.run_quality_checks` | Executes quality rules (NullCheck, RangeCheck, UniqueCheck) against sampled data. Builds rules from specs or defaults. |

#### `stats_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `describe_distribution` | `StatsActivities.describe_distribution` | Calculates descriptive statistics via R-Engine. Optionally infers and tracks schema changes. |
| `calculate_correlation` | `StatsActivities.calculate_correlation` | Calculates correlation matrix (Pearson, Spearman) via R-Engine. |
| `fit_distribution` | `StatsActivities.fit_distribution` | Fits a statistical distribution (normal, lognormal) to data via R-Engine. |
| `calculate_market_share` | `StatsActivities.calculate_market_share` | Calculates market share metrics from brand/competitor data via R-Engine. |
| `perform_hypothesis_test` | `StatsActivities.perform_hypothesis_test` | Performs t-test via R-Engine. Returns p-value, statistic, and method. |

#### `operational_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `clean_data` | `OperationalActivities.clean_data` | Performs data cleaning with configurable strategies for missing values and outliers. |
| `detect_anomalies` | `OperationalActivities.detect_anomalies` | Detects anomalies using MLPrimitives (Isolation Forest). Returns anomaly scores and labels. |
| `analyze_sentiment_batch` | `OperationalActivities.analyze_sentiment_batch` | Batch sentiment analysis via NLPPrimitives. Returns per-text sentiment results. |
| `fix_data_quality` | `OperationalActivities.fix_data_quality` | Automatic data quality remediation: imputation, outlier treatment, quality score calculation. |
| `forecast_time_series` | `OperationalActivities.forecast_time_series` | Time series forecasting using EMA, linear, or Prophet methods. |

#### `capsule_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `capsule.load_capsule` | `CapsuleActivities.load_capsule` | Loads capsule definition from DB including execution graph and parameters schema. |
| `capsule.eval_condition` | `CapsuleActivities.eval_condition` | Evaluates a step condition against previous step results. Returns boolean. |
| `capsule.substitute_params` | `CapsuleActivities.substitute_params` | Substitutes Jinja2 templates in params dict using parameter values and step results. |
| `capsule.execute_step` | `CapsuleActivities.execute_step` | Routes step action to Voyant services (deep_research, scrape, ingest, analyze, search, sql_query, render_plotly, render_pdf, notify, audit_log). Enforces capability whitelist. |
| `capsule.cross_validate` | `CapsuleActivities.cross_validate` | Cross-validates findings across multiple steps by loading state from DB. Returns consistency score. |
| `capsule.generate_artifacts` | `CapsuleActivities.generate_artifacts` | Generates output artifacts (summary, checksum) from completed capsule steps. |
| `capsule.store_report` | `CapsuleActivities.store_report` | Persists final report to CapsuleInstance DB record with status "completed". |

### Scraper Activities (`apps/scraper/activities/`)

#### `fetch_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `fetch_page` | `FetchActivities.fetch_page` | Fetches a web page using Playwright, httpx, or Scrapy. Includes SSRF protection. Supports JS rendering, scrolling, JSON capture. |
| `deep_archive` | `FetchActivities.deep_archive` | Deep archival scrape: connects to obfuscated SPAs, clicks UI elements, downloads matching files. |

#### `parse_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `extract_data` | `ParseActivities.extract_data` | Extracts structured data from HTML using CSS selectors or XPath. Returns fields, images, and media URLs. |
| `process_ocr` | `ParseActivities.process_ocr` | Processes images with Tesseract OCR. Supports configurable language packs. |
| `transcribe_media` | `ParseActivities.transcribe_media` | Transcribes audio/video files using Whisper. |
| `parse_pdf` | `ParseActivities.parse_pdf` | Parses PDF documents via Apache Tika for text/metadata and pdfplumber for tables. |

#### `storage_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `store_artifact` | `StorageActivities.store_artifact` | Stores extracted data as JSON artifact in MinIO. Creates/updates ScrapeArtifact ORM record (idempotent). |
| `finalize_job` | `StorageActivities.finalize_job` | Finalizes a scrape job by updating ORM status ("succeeded" or "partial") and recording metrics. |

#### `search_activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `execute_searxng_query` | `SearchActivities.execute_searxng_query` | Queries the sovereign internal SearXNG instance. Returns list of {url, title, snippet} dicts. |

#### `deep_research/activities.py`

| Activity Name | Function | Description |
|---|---|---|
| `dr_generate_queries` | `DeepResearchActivities.generate_queries` | Generates search-optimized sub-queries from a primary query using QueryGenerator agent. |
| `dr_search_all_engines` | `DeepResearchActivities.search_all_engines` | Searches across SearXNG, Brave, and Google CSE in parallel. Deduplicates by URL. |
| `dr_fetch_octopus` | `DeepResearchActivities.fetch_octopus` | Fetches a URL via Octopus ARM (dynamic/evasion) with fallback to legacy fetch_page. |
| `dr_extract_content` | `DeepResearchActivities.extract_content` | Extracts text from HTML using ContentExtractor agent (trafilatura/readability/newspaper/crawl4ai). |
| `dr_score_sources` | `DeepResearchActivities.score_sources` | Scores sources by credibility and freshness using domain credibility DB. Filters below min_score. |
| `dr_deduplicate` | `DeepResearchActivities.deduplicate` | Removes near-duplicate sources using MinHash/LSH with configurable Jaccard threshold. |
| `dr_synthesize` | `DeepResearchActivities.synthesize` | Synthesizes extracted text into findings, citations, and follow-up queries via Synthesizer agent. |
| `dr_cross_validate` | `DeepResearchActivities.cross_validate` | Cross-validates findings against the full source corpus (≥2 independent sources required). |
| `dr_generate_report` | `DeepResearchActivities.generate_report` | Generates final Markdown research report with confidence score via ReportGenerator agent. |
| `dr_store_artifact` | `DeepResearchActivities.store_artifact` | Stores research report artifact in MinIO via ArtifactStore. Returns artifact_hash. |

### Streaming Activities (`apps/streaming/activities.py`)

| Activity Name | Function | Description |
|---|---|---|
| `get_cluster_overview` | `StreamingActivities.get_cluster_overview` | Gets Flink cluster overview (slots, jobs, task managers). Used for health checks. |
| `list_running_jobs` | `StreamingActivities.list_running_jobs` | Lists all running Flink jobs. |
| `submit_streaming_job` | `StreamingActivities.submit_streaming_job` | Submits a new streaming job to Flink. Uploads JAR if needed, checks for available slots. |

---

## Retry & Timeout Configuration

### Retry Policies (`apps/core/lib/retry_config.py`)

| Policy Name | Initial Interval | Backoff | Max Interval | Max Attempts | Non-Retryable Errors |
|---|---|---|---|---|---|
| `EXTERNAL_SERVICE_RETRY` | 1s | 2.0 | 60s | 3 | ValidationError, AuthenticationError, AuthorizationError, ApplicationError |
| `DATA_PROCESSING_RETRY` | 2s | 2.0 | 120s | 2 | ValidationError, DataQualityError, AnalysisError, ApplicationError |
| `NO_RETRY` | — | — | — | 1 | — |

### Timeout Defaults (`TIMEOUTS` dict)

| Key | Duration | Use Case |
|---|---|---|
| `stats_short` | 5 min | Simple stats: mean, median, correlation |
| `stats_long` | 10 min | Complex stats: market share, hypothesis tests |
| `ml_clustering` | 10 min | K-means clustering |
| `ml_training` | 15 min | Model training (regression, classification) |
| `ml_forecasting` | 15 min | Time series forecasting (Prophet) |
| `ingestion_short` | 15 min | Small datasets (<10K rows) |
| `ingestion_long` | 30 min | Large datasets (>10K rows) |
| `ingestion_airbyte` | 45 min | Airbyte syncs (network bound) |
| `operational_short` | 5 min | Anomaly detection |
| `operational_medium` | 10 min | Sentiment analysis |
| `operational_long` | 15 min | Data quality fixing (large datasets) |
| `processing_short` | 5 min | Generic short processing |
| `processing_long` | 20 min | Generic long processing |
| `discovery` | 5 min | API search, spec parsing |

### Heartbeat Intervals

| Key | Interval | Use Case |
|---|---|---|
| `default` | 30s | General activities |
| `long_running` | 1 min | Long-running activities |
| `data_transfer` | 2 min | Data transfer activities |

### Workflow-Specific Config

| Workflow | Timeout | Retry Policy | Notes |
|---|---|---|---|
| `ProfileWorkflow` | 15 min | `EXTERNAL_SERVICE_RETRY` | — |
| `IngestDataWorkflow` | 1–10 min (per activity) | Custom: 3 attempts, non-retryable on validation/auth errors | Raises `ApplicationError` on contract failure |
| `AnalyzeWorkflow` | 5–15 min (per stage) | Default | Stages can be toggled via params |
| `CapsuleWorkflow` | Dynamic per step | Per-step retry from capsule definition | Persists results to DB to avoid 2MB event history limit |
| `BenchmarkBrandWorkflow` | 2–10 min (per phase) | Default | Parallel ingestion, parallel sampling |
| `SandboxWorkflow` | 1 hour | `None` (no retry) | Security: no silent retry of malicious code |
| `QualityWorkflow` | 5–10 min | Custom: 3 attempts, backoff 2.0 | — |
| `DetectAnomaliesWorkflow` | 5 min | Default | — |
| `AnalyzeSentimentWorkflow` | 10 min | Default | — |
| `FixDataQualityWorkflow` | 15 min | Default | — |
| `ForecastWorkflow` | 5 min | Default | — |
| `ScrapeWorkflow` | 1–10 min (per URL) | Default | Sequential URL processing, per-URL error collection |
| `DeepResearchWorkflow` | 2–10 min | `None` for scrape phase | Parallel scrape of all URLs |
| `DeepResearchWorkflowV2` | 1–3 min (per activity) | Custom: 3 attempts, non-retryable on validation/auth errors | Multi-layer depth recursion, all parallel within layer |
| `StreamingJobWorkflow` | 30s–5 min | Default | Health check → submit |

---

## Workflow Type Definitions (`apps/worker/workflows/types.py`)

| Dataclass | Fields | Purpose |
|---|---|---|
| `IngestParams` | `job_id`, `source_id`, `mode="full"`, `tables=None` | Input parameters for `IngestDataWorkflow` |
| `IngestResult` | `job_id`, `source_id`, `status`, `rows_ingested`, `tables_synced`, `completed_at` | Output of `IngestDataWorkflow` |
| `StreamingJobInput` | `job_name`, `job_type`, `source_topic`, `sink_topic=None`, `config=None` | Input parameters for `StreamingJobWorkflow` |
| `FlinkJobResult` | `success`, `job_id=None`, `message=""`, `details=None` | Output of streaming activities |
