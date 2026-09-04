# Workflows and Execution Module

> **Source date**: 2026-09-04
> **Files examined**: `apps/workflows/`, `apps/analysis/`, `apps/scraper/`

## Overview

The workflows and execution module covers three areas:

1. **Workflows** (`apps/workflows/`) — Job orchestration, artifact management, presets, and KPI template endpoints
2. **Analysis** (`apps/analysis/`) — Statistical analysis API that dispatches to Temporal workflows
3. **Scraper** (`apps/scraper/`) — Web scraping execution engine with SSRF protection, multiple fetch engines, and artifact storage

---

## Workflows (`apps/workflows/`)

### Models (`models.py`, 70 lines)

#### `Job(TenantModel, UUIDModel)`

**Table**: `voyant_job`

| Field | Type | Notes |
|---|---|---|
| `job_type` | `CharField(64)` | Indexed (e.g. `"ingest"`, `"profile"`, `"quality"`) |
| `source_id` | `CharField(36)` | Nullable |
| `soma_session_id` | `CharField(128)` | Nullable, agent session tracking |
| `status` | `CharField(64)` | Default `"queued"` |
| `progress` | `IntegerField` | Default 0 |
| `parameters` | `JSONField` | Job parameters |
| `started_at` | `DateTimeField` | Nullable |
| `completed_at` | `DateTimeField` | Nullable |
| `result_summary` | `JSONField` | Nullable |
| `error_message` | `TextField` | Nullable |

Property `job_id` returns `str(self.id)` (compatibility alias).

#### `Artifact(TenantModel)`

**Table**: `voyant_artifact`

| Field | Type | Notes |
|---|---|---|
| `artifact_id` | `CharField(512)` | Primary key |
| `job_id` | `CharField(36)` | Indexed |
| `artifact_type` | `CharField(128)` | |
| `format` | `CharField(32)` | |
| `storage_path` | `CharField(512)` | MinIO object path |
| `size_bytes` | `IntegerField` | Nullable |

#### `PresetJob(TenantModel, UUIDModel)`

**Table**: `voyant_preset_job`

| Field | Type |
|---|---|
| `preset_name` | `CharField(255)` — indexed |
| `source_id` | `CharField(36)` |
| `parameters` | `JSONField` |
| `status` | `CharField(64)` — default `"queued"` |

### API (`api.py`, 572 lines)

#### Jobs Router (`/v1/jobs`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `POST` | `/ingest` | `write:jobs` | `JobResponse` | Start ingestion; launches `IngestDataWorkflow` via Temporal |
| `POST` | `/profile` | `write:jobs` | `JobResponse` | Start profiling; launches `ProfileWorkflow` |
| `POST` | `/quality` | `write:jobs` | `JobResponse` | Start quality checks; launches `QualityWorkflow` |
| `GET` | `/` | `read:*` | `list[JobResponse]` | List jobs (filterable by `status`, `job_type`, `limit`) |
| `GET` | `/{job_id}` | `read:*` | `JobResponse` | Get job details |
| `POST` | `/{job_id}/cancel` | `write:jobs` | `{"status", "job_id"}` | Cancel job (tries 16 workflow prefixes) |

**Workflow launch pattern**:
1. Validate table scope via `namespace_analyzer.validate_table_access()`
2. Call `apply_policy()` for governance check
3. Create `Job` record
4. Start Temporal workflow via `get_temporal_client()`
5. On failure, set job status to `"failed"`

**Cancel**: Tries prefixes: `ingest`, `profile`, `quality`, `analyze`, `capsule`, `sandbox`, `streaming`, `scrape`, `research`, `benchmark`, `anomaly`, `sentiment`, `forecast`, `segment`, `regression`.

#### Artifacts Router (`/v1/artifacts`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `GET` | `/{job_id}` | `read:*` | `{"artifacts": list[ArtifactInfo]}` | List artifacts for a job |
| `GET` | `/{job_id}/{artifact_type}/download` | `read:*` | `StreamingHttpResponse` | Download artifact from MinIO |

**Download**: Streams artifact content from MinIO as `application/octet-stream`.

#### Presets Router (`/v1/presets`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `GET` | `/` | `read:*` | `dict[str, list[PresetInfo]]` | List presets (grouped by category, optional `category` filter) |
| `GET` | `/{preset_name}` | `read:*` | `PresetInfo` | Get preset details |
| `POST` | `/{preset_name}/execute` | `execute:presets` | `{"job_id", "status"}` | Execute a preset (creates `PresetJob`, launches workflow) |
| `GET` | `/kpi-templates` | `read:*` | `list[KPITemplateInfo]` | List KPI templates |
| `GET` | `/kpi-templates/categories` | `read:*` | `list[str]` | List KPI template categories |
| `GET` | `/kpi-templates/{name}` | `read:*` | `dict` | Get KPI template with SQL |
| `POST` | `/kpi-templates/{name}/render` | `execute:presets` | `{"sql": str}` | Render KPI template with params |

**Built-in presets**: `quality.data_profiling` and `quality.data_checks`.

---

## Analysis (`apps/analysis/`)

### Models (`models.py`, 61 lines)

#### `AnalysisJob(TenantModel, UUIDModel)`

**Table**: `voyant_analysis_job`

**Deprecated** (not used by current API — uses `Job` from `apps.workflows.models` instead; scheduled for removal v4.0.0).

### API (`api.py`, 137 lines)

#### Analyze Router (`/v1/analyze`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `POST` | `/` | `write:*` | `AnalyzeResponse` | Execute analysis workflow (synchronous — waits for result) |

**`analyze` endpoint flow**:
1. Resolves table from `table`, `source_id`, or `tables[0]`
2. Validates table access via `namespace_analyzer`
3. Calls `apply_policy()` for governance
4. Creates `Job` record
5. Executes `AnalyzeWorkflow` **synchronously** via `client.execute_workflow()` (unlike other workflows which use fire-and-forget `start_workflow`)
6. Returns summary, artifacts, and manifest

**Key difference**: This is a **synchronous** endpoint — it blocks until the Temporal workflow completes and returns the result directly.

---

## Scraper (`apps/scraper/`)

### API (`api.py`, 432 lines)

#### Scraper Router (`/v1/scrape`)

| Method | Path | Auth | Response | Description |
|---|---|---|---|---|
| `POST` | `/start` | `write:jobs` | 202 `ScrapeJobSchema` | Start scraping job (Temporal workflow) |
| `POST` | `/extract` | `write:jobs` | `dict` | Extract data from HTML using CSS/XPath selectors |
| `POST` | `/fetch` | `write:jobs` | `dict` | Fetch a web page (direct activity call) |
| `POST` | `/deep_archive` | `write:jobs` | `dict` | Deep archival scrape for SPAs |
| `POST` | `/ocr` | `write:jobs` | `dict` | OCR processing on images |
| `POST` | `/parse_pdf` | `write:jobs` | `dict` | Parse PDF for text/tables |
| `POST` | `/transcribe` | `write:jobs` | `dict` | Transcribe media (503 if disabled) |
| `GET` | `/status/{job_id}` | `read:*` | `ScrapeJobSchema` | Get scrape job status |
| `POST` | `/cancel` | `write:jobs` | `{"status", "job_id"}` | Cancel scrape job |
| `GET` | `/result/{job_id}` | `read:*` | `ScrapeResultSchema` | Get scrape results with artifacts |
| `GET` | `/metrics/{job_id}` | `read:*` | `dict` | Get scrape job metrics |

### Key Classes

- **`ScrapeStartSchema`**: `urls`, `selectors` (agent-provided), `options`
- **`ScrapeFetchSchema`**: `url`, `engine` (default from settings), `wait_for`, `scroll`, `timeout`, `wait_until`, `settle_ms`, `block_resources`, `capture_json`, `capture_url_contains`, `capture_max_bytes`, `capture_max_items`
- **`ScrapeDeepArchiveSchema`**: `url`, `interaction_selectors`, `download_patterns`, `target_dir`, `wait_settle_ms`, `timeout_ms`

### SSRF Protection

All URLs validated via `apps/scraper/security.py`:
- `validate_urls(payload.urls)` in `start_scrape`
- Returns 400 on `SSRFError`

### Workflow Integration

`_start_scrape_workflow()` launches `ScrapeWorkflow` via Temporal with id `"scrape-{job_id}"`.

### Transcription Guard

`/transcribe` returns `503` with `{"error_code": "TRANSCRIPTION_DISABLED"}` when `settings.scraper_enable_transcribe` is `False`.

---

## Dependencies and Integration Points

- **Temporal** — All workflows (ingest, profile, quality, analyze, scrape)
- **MinIO** — Artifact storage and download
- **namespace_analyzer** — Table access validation
- **Governance** — `apply_policy()` checks before workflow dispatch
- **Scraper security** — SSRF protection on all URLs
- **lxml** — HTML/CSS/XPath extraction in `/extract`

## Error Handling

- 404 for missing jobs, artifacts, presets, and KPI templates
- 403 for namespace violations and tenant mismatches
- 400 for validation errors
- 500 for workflow failures and system errors
- 503 for storage unavailable and transcription disabled
