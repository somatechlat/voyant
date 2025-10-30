# Universal Data Box (UDB)

Production-grade, Kubernetes-native "black box" service providing agent-accessible data source discovery, ingestion, normalization, automated exploratory & quality analysis, KPI computation, and artifact publication through both MCP tools and REST APIs.

## Key Features (v1 Scope)
- Hot-plug connectivity to new data sources at runtime via simple hints (URL, path, domain).
- Auto-detection of provider, auth type, and required Airbyte source spec.
- Unified ingestion through Airbyte into DuckDB (primary analytical store) and/or Postgres.
- Automated analysis: ydata-profiling (EDA), Evidently (quality/drift), KPI SQL & Plotly charts.
- Unstructured document parsing to tabular/text rows.
- MCP tools and REST API symmetry for agent and non-agent clients.
- Secure-by-default: scoped credentials, network policies, PII/PHI guards, audit logs.

## High-Level Architecture
Core components:
- udb-api (FastAPI + MCP server) orchestrating detection → connect → sync → analyze.
- Airbyte OSS (connectors) + Postgres metadata DB.
- DuckDB analytical store + artifacts persistent volume.
- Redis (cache/status), Kafka (event bus), optional Dagster (orchestration), optional Superset/Metabase.
- Analysis stack: ydata-profiling, Evidently, Plotly, Unstructured.

See `docs/ARCHITECTURE.md` for detailed diagrams & flows.

## Roadmap & Sprints
A rapid development roadmap is maintained in `docs/ROADMAP.md` with sprint goals (Foundations, Auto-Detection & OAuth, Analysis & Artifacts, Hardening & Observability, etc.).

## Core Principles
See `docs/PRINCIPLES.md` – Truth, No Mocking Core Paths, Elegance, Simplicity, Security, Observability, Reproducibility.

## Getting Started (Developer)
For a complete hands-on walkthrough (bring up stack, ingest sample data, run analysis, view artifacts, lineage, metrics) see `GETTING_STARTED.md`.

Quick summary:
1. Clone repository & create virtual env.
2. Install dependencies.
3. Launch real stack: `docker compose up -d --build`.
4. Run API locally (alternative): `uvicorn udb_api.app:app --reload`.
5. Use the example script: `python examples/ingest_and_analyze.py`.

Example assets live under `examples/` (including a sample CSV and Python script).

### Real-Mode Quickstart (No Mocks)
```
docker compose up -d --build
curl -s localhost:8000/readyz | jq
curl -s -X POST localhost:8000/analyze -H 'Content-Type: application/json' -d '{}'
curl -s localhost:8000/metrics | grep udb_sufficiency_score
```
Environment Flags (selected):
- UDB_ENABLE_EVENTS=1 : Enable Kafka event emission
- UDB_ENABLE_KESTRA=1 : Enable Kestra trigger endpoint
- UDB_STRICT_STARTUP=1 : Fail fast if dependencies unhealthy
- UDB_DISABLE_RATE_LIMIT=1 : Disable rate limiting for local dev

### Feature Flags Mapping
Flag -> Env Var -> Description
- quality -> UDB_ENABLE_QUALITY -> Generate profiling/quality artifacts
- charts -> UDB_ENABLE_CHARTS -> Build Plotly charts
- unstructured -> UDB_ENABLE_UNSTRUCTURED -> Enable document ingestion path
- events -> UDB_ENABLE_EVENTS -> Emit Kafka lifecycle events
- tracing -> UDB_ENABLE_TRACING -> OTEL tracing export
- rbac -> UDB_ENABLE_RBAC -> Enforce analyst/admin role checks
- narrative -> UDB_ENABLE_NARRATIVE -> Generate narrative summary
- kestra -> UDB_ENABLE_KESTRA -> Allow /kestra/trigger usage

### Observability (Metrics & ServiceMonitor)
- Core Metrics Subset:
```
curl -s localhost:8000/metrics/select?mode=core
```
Excludes high-cardinality metrics (e.g., artifact size with jobId label). Use full `/metrics` for complete set.
The API exposes Prometheus metrics at `/metrics`. To have Prometheus Operator scrape automatically, enable in Helm values:
```
metrics:
	serviceMonitor:
		enabled: true
		interval: 30s
```
This renders a `ServiceMonitor` resource targeting the API service.

Key Metrics (selected):
- `udb_jobs_total{type,state}` – job lifecycle counts
- `udb_job_duration_seconds` – analyze & sync durations
- `udb_sufficiency_score` – readiness score distribution
- `udb_dependency_up{component}` – dependency health gauges
- `udb_airbyte_retries_total` / `udb_kestra_retries_total` – client retry attempts
- `udb_dependency_check_failures_total` – failed dependency probes
- `udb_kpi_exec_latency_seconds` – KPI execution latency
- `udb_artifact_size_bytes{jobId}` – artifact size per job
- `udb_duckdb_queue_length` – queued writers for DuckDB lock

### Retry Logic
Airbyte & Kestra clients use exponential backoff (0.5s → 1s → 2s → 4s → 5s cap) up to 5 attempts, counting each retry. Surface via metrics above.

### Recent Events
Fetch most recent in-process events (ring buffer) for quick debug:
```
curl -s localhost:8000/events/recent | jq
```

Full list of metrics & guidance: see `docs/OBSERVABILITY.md`. Scaling considerations: `docs/SCALING.md`.

## MCP Tools (Preview)
- `udb.discover_connect`
- `udb.analyze`
- `udb.status`
- `udb.artifact`
- `udb.sql`

Schema contracts documented in `docs/MCP_INTERFACE.md`.

## License
Apache 2.0 (see `LICENSE`).

## Contributing
Please read `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md` (to be added).

---
Refer also to `GETTING_STARTED.md` for end-to-end usage; this repository intentionally avoids mocks for core paths—examples exercise production code paths.
