# UDB Architecture

## Overview
Universal Data Box (UDB) provides automated discovery → ingestion → normalization → analysis for heterogeneous data sources, exposed via MCP tools and REST APIs.

## Component Summary
- **udb-api**: FastAPI service + MCP server. Orchestrates lifecycle, manages jobs, publishes artifacts.
- **Airbyte OSS**: Connector runtime for sources/destinations; metadata in Postgres.
- **DuckDB**: Primary analytical store for synchronized & normalized tables.
- **Postgres**: Airbyte metadata + optional serving schema + audit logs.
- **Redis**: Caching (job status, small dimension tables) & transient coordination.
- **Kafka**: Event bus for job lifecycle events (`udb.requested`, `udb.started`, `udb.completed`, `udb.failed`).
- **Analysis Stack**: ydata-profiling (EDA), Evidently (quality/drift), Plotly (charts), Unstructured (document parsing).
- **Orchestrator (Optional)**: Dagster for multi-stage pipeline graphs (discover → connect → sync → analyze → publish). Airflow alternative.
- **Artifact Storage**: Persistent volume mounted at `/artifacts/<jobId>` served via udb-api.

## Data Flow (Happy Path)
1. Agent calls `udb.discover_connect` with a hint.
2. AutoDetect module parses hint, resolves provider, returns mapping to Airbyte source definition & config template.
3. Airbyte source + destination (DuckDB) + connection are provisioned.
4. Sync job launched; ingestion monitor polls status.
5. On success, Normalizer (optional transforms) prepares tables.
6. Analysis Runner executes profiling, quality, KPI SQL, chart rendering.
7. Artifacts generated & stored; summary returned to agent.

## Auto Detection Heuristics
Ordered logic:
1. URI scheme / host pattern / path signature.
2. OpenID configuration discovery.
3. Protocol probing (conditional & gated).
4. DNS / HTTP header fingerprints.
5. Minimal interactive disambiguation.

Outputs: `{ provider, authType, airbyteSourceDefinitionId, configTemplate, oauthUrl? }`.

## Security & Isolation
- Tenant-scoped namespaces (future multi-tenancy).
- K8s NetworkPolicies (deny-all baseline + explicit egress for allowed domains).
- Secrets via Kubernetes Secrets or external vault (never stored in plain configmaps/logs).
- PII detection & masking at view generation layer; artifact redaction.

## Observability
- Structured JSON logs with correlation/job IDs.
- Prometheus metrics: job durations, counts, errors, artifact sizes.
- OpenTelemetry tracing spans across stages.
- Kafka events for asynchronous subscribers (alerts, downstream automation).

## Storage Layout
- DuckDB file: `/data/warehouse.duckdb`
- Schema naming: `src_<shortname>__table` for raw/landing; views in `public`.
- Artifacts: `/artifacts/<jobId>/<type>` (profile.html/json, quality.html/json, charts/...).
- Redis keys: `job:<jobId>`, `artifact_index:<jobId>`.

## Module Responsibilities (udb-api)
- `autodetect.py` – heuristics engine.
- `airbyte_client.py` – REST wrapper for Airbyte (sources, destinations, connections, jobs).
- `ingest.py` – utilities for uploads & document parsing (Unstructured) → DuckDB.
- `analyze.py` – orchestration of profiling, quality, KPI computation, chart generation.
- `charts.py` – Plotly wrappers & spec interpreter.
- `security.py` – authZ logic, PII masking hooks, rate limiting stubs.
- `app.py` – FastAPI router + dependency injection & MCP integration (future `mcp_server.py`).

## Extensibility
- Additional connectors: extend mapping dict in `autodetect.py`.
- New analysis modules: plugin registry pattern in `analyze.py`.
- Policy enforcement: middleware injecting guards before dangerous operations (e.g., `/sql`).

## Future Enhancements
- Data contracts (Great Expectations) pre-analysis.
- RAG/Q&A indexing of unstructured corpora.
- Iceberg/Parquet lake & multi-engine federation.
- Row-level & column-level security policies.

---
See `ROADMAP.md` for phased delivery details and `PRINCIPLES.md` for governing values (Truth, No Mocking, Elegance, Simplicity).
