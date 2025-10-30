# Operations Guide

## Environments
Recommended staged environments:
- `dev`: Rapid iteration, permissive logging.
- `staging`: Pre-release validation, realistic data volume (sanitized).
- `prod`: Hardened config, restricted access.

## Services & Responsibilities
| Service | Responsibility | Scaling Guidance |
|---------|----------------|------------------|
| udb-api | Orchestration, APIs, artifact serving | CPU-bound (analysis), start 2 replicas, HPA on CPU & latency |
| Airbyte server/worker | Connector metadata & execution | Scale workers by concurrent sync jobs |
| Postgres (Airbyte) | Metadata store | Managed or HA pair; monitor IOPS |
| DuckDB (file) | Analytical store | Single-writer pattern; serialize writes |
| Redis | Cache, status, transient coordination | 1 small instance; enable persistence optional |
| Kafka | Event streaming | 1-3 brokers dev; prod min 3 |
| Dagster (optional) | Orchestration pipelines | Scale webserver separately from daemon |

## Scaling & Concurrency
- DuckDB: Limit simultaneous write operations (mutex or queue) while allowing concurrent reads via new connections.
- Analysis jobs: CPU intensive; configure max parallel analyses via env (e.g., `UDB_MAX_ANALYSIS_JOBS`).
- Airbyte Syncs: Constrain with worker replica count + job queue depth.

## Health & Readiness
- `/healthz`: Basic liveness.
- `/readyz`: Valid dependency checks (Airbyte reachable, DuckDB file accessible).

## Metrics (Prometheus)
| Metric | Type | Description |
|--------|------|-------------|
| `udb_jobs_total{state}` | Counter | Count of jobs by terminal state |
| `udb_job_duration_seconds` | Histogram | End-to-end job durations |
| `udb_artifact_bytes_total` | Counter | Total artifact bytes generated |
| `udb_detect_latency_seconds` | Histogram | Auto-detection time |
| `udb_sql_queries_total` | Counter | Ad-hoc SQL queries executed |

## Logging
- JSON structured logs: `timestamp`, `level`, `job_id`, `event`, `message`.
- Sensitive field scrubbing middleware.

## Tracing
- OpenTelemetry exporter (OTLP); spans for `detect`, `provision`, `sync`, `analyze`, `publish`.
- Job ID injected as trace attribute.

## Backups & Retention
- DuckDB snapshots: Daily PV snapshot (K8s CSI) or object storage copy.
- Artifacts: TTL policy (e.g., cleanup after 30 days, configurable).
- Redis: Optional persistence if job recovery required.

## Disaster Recovery
- Recreate Airbyte + Postgres from backup; re-run critical syncs.
- DuckDB restore from latest snapshot; re-materialize derived views.
- Artifacts can be regenerated (idempotent) if raw data intact.

## Alerting (Examples)
- High job failure rate (>20% over 15m).
- Sync duration P95 > threshold.
- API latency P95 > 2s.
- Artifact disk usage > 80% capacity.

## Runbooks (Summaries)
1. Job Failures Spiking:
   - Inspect Kafka `udb.failed` events.
   - Check Airbyte job logs.
   - Retry with backoff; escalate if connector regression.
2. DuckDB Lock Contention:
   - Review concurrent writes; serialize heavy operations.
   - Temporarily scale down analysis concurrency.
3. OAuth Callback Errors:
   - Validate redirect URIs & client secret rotation.
   - Re-initiate device code flow fallback.

## Configuration Management
- Central `config.py` loads env vars & defaults.
- Kubernetes ConfigMaps for non-secret config; Secrets for credentials.

## Maintenance Tasks
- Rotate OAuth client secrets quarterly.
- Run dependency vulnerability scan weekly.
- Rebuild base images monthly.
- Clean artifacts older than retention window nightly (cronjob).

---
Evolve operations guide as metrics and incident history accumulate.
