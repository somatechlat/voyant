# Streaming and Workers Module

> **Source date**: 2026-09-04
> **Files examined**: `apps/streaming/`, `apps/worker/worker_main.py`, `apps/worker/workflows/`, `apps/worker/activities/`

## Overview

The streaming and workers module has two major components:

1. **Streaming** (`apps/streaming/`) — Apache Flink integration for real-time stream processing (FR-21)
2. **Worker** (`apps/worker/`) — The Temporal worker process that executes all workflows and activities

---

## Streaming (`apps/streaming/`)

### Directory Structure

```
apps/streaming/
├── activities.py      # Temporal activities for Flink operations
├── flink_client.py    # Apache Flink REST API client
├── workflow.py         # Temporal workflow for streaming jobs
└── jobs/               # (directory, not examined in detail)
```

### `flink_client.py` (95 lines)

#### `FlinkClient`

HTTP client for the Apache Flink JobManager REST API. Built on `httpx`.

**Constructor**: `FlinkClient(jobmanager_url=None)` — resolves URL from parameter or `Settings.flink_jobmanager_url`. Raises `ValueError` if URL not configured.

| Method | Signature | Endpoint | Timeout | Description |
|---|---|---|---|---|
| `get_overview` | `() -> dict` | `GET /overview` | 5s | Cluster stats (slots, task managers) |
| `list_jobs` | `() -> dict` | `GET /jobs/overview` | 5s | List all Flink jobs |
| `submit_jar` | `(jar_id, entry_class?, program_args?, parallelism?) -> str` | `POST /jars/{jar_id}/run` | 30s | Submit a JAR for execution; returns job ID |
| `upload_jar` | `(jar_path: str) -> str` | `POST /jars/upload` | 60s | Upload a JAR file; returns JAR ID |

**Error handling**: `FlinkClientError` for connection failures, API errors, missing job IDs, and file not found.

### `activities.py` (157 lines)

#### `FlinkJobResult` (dataclass)

| Field | Type | Description |
|---|---|---|
| `success` | `bool` | Whether operation succeeded |
| `job_id` | `str \| None` | Flink job ID |
| `message` | `str` | Human-readable status |
| `details` | `dict \| None` | Additional metadata |

#### `StreamingActivities`

Temporal activities for Flink operations.

| Activity | Parameters | Description |
|---|---|---|
| `get_cluster_overview` | — | Health check — fetches cluster stats |
| `list_running_jobs` | — | Lists all running Flink jobs |
| `submit_streaming_job` | `(job_name, job_config)` | Submits a streaming job: checks available slots, uploads JAR if needed, submits |

**`submit_streaming_job` flow**:
1. Checks cluster slot availability
2. Uploads JAR from `jar_path` if `jar_id` not provided
3. Submits via `FlinkClient.submit_jar()`
4. Returns `FlinkJobResult` with success/failure status

### `workflow.py` (103 lines)

#### `StreamingJobInput` (dataclass)

| Field | Type | Description |
|---|---|---|
| `job_name` | `str` | Human-readable name |
| `job_type` | `str` | Type (e.g. `"kpi_aggregation"`, `"anomaly_detection"`) |
| `source_topic` | `str` | Kafka source topic |
| `sink_topic` | `str \| None` | Kafka sink topic |
| `config` | `dict \| None` | Additional config |

#### `StreamingJobWorkflow`

Temporal workflow that:
1. Validates Flink cluster health via `get_cluster_overview` activity (30s timeout)
2. Submits streaming job via `submit_streaming_job` activity (5min timeout)
3. Returns `FlinkJobResult`

---

## Worker (`apps/worker/`)

### `worker_main.py` (291 lines)

The primary entry point for the Temporal worker process.

#### Initialization Sequence

1. **`_setup_django()`** — Configures Django ORM for activities that use it. Sets `DJANGO_SETTINGS_MODULE` and calls `django.setup()`.
2. **Metrics server** — Starts Prometheus exposition server on `worker_metrics_port` (default 9090).
3. **Temporal connection** — Connects via `get_temporal_client()`.
4. **Register workflows and activities** (see below).
5. **Signal handlers** — `SIGINT` and `SIGTERM` for graceful shutdown.
6. **Worker creation** — `Worker(client, task_queue, workflows, activities, activity_executor, interceptors)`.
7. **Run** — `await worker.run()`.

#### Worker Modes

**`settings.worker_mode`** controls which workflows/activities are registered:

##### `"scraper"` Mode (dedicated scraping worker)

| Workflows | Activities |
|---|---|
| `ScrapeWorkflow` | `FetchActivities.fetch_page`, `FetchActivities.deep_archive`, `ParseActivities.extract_data`, `ParseActivities.process_ocr`, `ParseActivities.transcribe_media`, `ParseActivities.parse_pdf`, `StorageActivities.store_artifact`, `StorageActivities.finalize_job` |

##### `"full"` Mode (default — all workflows and activities)

**Workflows** (17 total):

| Workflow | Source |
|---|---|
| `IngestDataWorkflow` | `apps.worker.workflows.ingest_workflow` |
| `ProfileWorkflow` | `apps.worker.workflows.profile_workflow` |
| `AnalyzeWorkflow` | `apps.worker.workflows.analyze_workflow` |
| `QualityWorkflow` | `apps.worker.workflows.quality_workflow` |
| `BenchmarkBrandWorkflow` | `apps.worker.workflows.benchmark_workflow` |
| `DetectAnomaliesWorkflow` | `apps.worker.workflows.operational_workflows` |
| `AnalyzeSentimentWorkflow` | `apps.worker.workflows.operational_workflows` |
| `FixDataQualityWorkflow` | `apps.worker.workflows.operational_workflows` |
| `ForecastWorkflow` | `apps.worker.workflows.operational_workflows` |
| `SegmentCustomersWorkflow` | `apps.worker.workflows.segmentation_workflow` |
| `LinearRegressionWorkflow` | `apps.worker.workflows.regression_workflow` |
| `ScrapeWorkflow` | `apps.scraper.workflow` |
| `DeepResearchWorkflow` | `apps.scraper.deep_research_workflow` |
| `StreamingJobWorkflow` | `apps.streaming.workflow` |
| `SandboxWorkflow` | `apps.worker.workflows.sandbox_workflow` |
| `CapsuleWorkflow` | `apps.worker.workflows.capsule_workflow` |
| `DeepResearchWorkflowV2` | `apps.scraper.deep_research.workflow` |

**Activities** (40+ total), grouped by domain:

| Domain | Activities | Source |
|---|---|---|
| **Ingestion** | `run_ingestion`, `sync_airbyte`, `validate_contract_activity`, `record_lineage_activity` | `IngestActivities` |
| **Profiling** | `profile_data` | `ProfileActivities` |
| **Analysis** | `fetch_sample`, `run_analyzers` | `AnalysisActivities` |
| **Generation** | `run_generators` | `GenerationActivities` |
| **KPI** | `run_kpis` | `KPIActivities` |
| **Quality** | `fetch_sample`, `run_quality_checks` | `QualityActivities` |
| **Statistics** | `calculate_market_share`, `perform_hypothesis_test`, `describe_distribution`, `calculate_correlation`, `fit_distribution` | `StatsActivities` |
| **ML** | `cluster_data`, `train_classifier_model`, `forecast_time_series`, `train_regression_model` | `MLActivities` |
| **Discovery** | `search_for_apis`, `scan_spec_url` | `DiscoveryActivities` |
| **Operational** | `detect_anomalies`, `analyze_sentiment_batch`, `fix_data_quality`, `clean_data` | `OperationalActivities` |
| **Scraper** | `fetch_page`, `deep_archive`, `extract_data`, `process_ocr`, `transcribe_media`, `parse_pdf`, `store_artifact`, `finalize_job` | `FetchActivities`, `ParseActivities`, `StorageActivities` |
| **Search** | `execute_searxng_query` | `SearchActivities` |
| **Streaming** | `get_cluster_overview`, `list_running_jobs`, `submit_streaming_job` | `StreamingActivities` |
| **Sandbox** | `run_python_sandbox` | `SandboxActivities` |
| **Capsule** | `load_capsule`, `eval_condition`, `substitute_params`, `execute_step`, `cross_validate`, `generate_artifacts`, `store_report` | `CapsuleActivities` |
| **Deep Research V2** | `generate_queries`, `search_all_engines`, `fetch_octopus`, `extract_content`, `score_sources`, `deduplicate`, `synthesize`, `cross_validate`, `generate_report`, `store_artifact` | `DeepResearchActivities` |

### Activity Executor

- `ThreadPoolExecutor` with configurable `max_workers`
- Default: `min(32, cpu_count * 5)`
- Override via `TEMPORAL_ACTIVITY_MAX_WORKERS` env var

### Interceptors

- **`MetricsInterceptor`** — Cross-cutting concern for Prometheus metrics on all activity/workflow executions

---

## Workflow Files Reference

| File | Workflows |
|---|---|
| `ingest_workflow.py` | `IngestDataWorkflow` |
| `profile_workflow.py` | `ProfileWorkflow` |
| `analyze_workflow.py` | `AnalyzeWorkflow` |
| `quality_workflow.py` | `QualityWorkflow` |
| `benchmark_workflow.py` | `BenchmarkBrandWorkflow` |
| `operational_workflows.py` | `DetectAnomaliesWorkflow`, `AnalyzeSentimentWorkflow`, `FixDataQualityWorkflow`, `ForecastWorkflow` |
| `segmentation_workflow.py` | `SegmentCustomersWorkflow` |
| `regression_workflow.py` | `LinearRegressionWorkflow` |
| `sandbox_workflow.py` | `SandboxWorkflow` |
| `capsule_workflow.py` | `CapsuleWorkflow` |

---

## Dependencies and Integration Points

- **Temporal** — Workflow orchestration (client from `apps.core.lib.temporal_client`)
- **Apache Flink** — Stream processing (REST API via `FlinkClient`)
- **Kafka** — Source/sink topics for streaming jobs
- **Django ORM** — Required for activity persistence (initialized via `_setup_django()`)
- **Prometheus** — Metrics exposition on `worker_metrics_port`
- **SearXNG** — Sovereign search engine for deep research

## Security Measures

- Graceful shutdown on `SIGINT`/`SIGTERM`
- Activity executor bounded by `max_workers` config
- Scraper mode isolates scraping activities from other workflows
- `MetricsInterceptor` for observability
