# Observability

This service is designed with metrics-first, log-structured, and trace-optional philosophy.

## Metrics Inventory
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| udb_jobs_total | counter | type, state | Job lifecycle counts (sync, analyze, ingest) |
| udb_job_duration_seconds | histogram | type | Duration of jobs |
| udb_analyze_kpi_rowsets | histogram |  | Number of KPI rowsets per analyze |
| udb_quality_runs_total | counter | status | Quality artifact status (success/error/skipped) |
| udb_drift_runs_total | counter | status | Drift artifact status |
| udb_oauth_initiations_total | counter | provider | OAuth initiation calls |
| udb_ingest_fragments | histogram |  | Fragments produced by ingest |
| udb_artifacts_pruned_total | counter |  | Pruned job directories |
| udb_sufficiency_score | histogram |  | Sufficiency readiness score distribution |
| udb_dependency_up | gauge | component | Dependency health (duckdb, kafka, redis, airbyte, kestra) |
| udb_dependency_check_failures_total | counter |  | Count of failed dependency probes |
| udb_airbyte_retries_total | counter |  | Airbyte client retry attempts |
| udb_kestra_retries_total | counter |  | Kestra client retry attempts |
| udb_kpi_exec_latency_seconds | histogram |  | Duration of KPI execution block |
| udb_artifact_size_bytes | gauge | jobId | Total size of a job's artifact directory |
| udb_duckdb_queue_length | gauge |  | Current length of waiters for DuckDB lock |

## Logs
All logs are structured JSON via standard logger `udb`. Recommended to centralize with fluentbit or vector.

Key fields: `correlation_id`, `tenant`, `event`, `error`.

## Traces
OpenTelemetry tracing enabled when `UDB_ENABLE_TRACING=1` and OTLP endpoint provided (`OTEL_EXPORTER_OTLP_ENDPOINT`). Spans:
* analyze.request
* kpi.execute
* kpi.mask
* artifacts.generate
* sufficiency.compute
* charts.build

## Startup Health
`/startupz` returns dependency probe results. `/readyz` summarizes status (ready/degraded). Metrics for each dependency are updated whenever checks run.

## Events
Kafka topic (default `udb.job.events`) receives lifecycle events. `/events/recent` offers in-process ring buffer for quick inspection.

## Suggested Dashboards
1. Job Throughput: jobs_total (rate) by type/state.
2. Analyze Duration: job_duration_seconds histogram over time.
3. Sufficiency Distribution & Quantiles.
4. Dependency Health: dependency_up stacked panel.
5. KPI Performance: kpi_exec_latency_seconds p50/p95.
6. DuckDB Concurrency: queue length gauge over time.
7. Artifact Size: artifact_size_bytes per job (top N recent).

## Alerting Examples
| Condition | Rationale |
|-----------|-----------|
| dependency_up{component!="duckdb"} == 0 for 5m | External dependency outage |
| increase(udb_dependency_check_failures_total[10m]) > 5 | Flapping or degraded service |
| histogram_quantile(0.95, rate(udb_kpi_exec_latency_seconds_bucket[5m])) > 5 | KPI performance regression |
| rate(udb_job_duration_seconds_sum[5m]) / rate(udb_job_duration_seconds_count[5m]) > 120 | Extended average job time |

## Sampling & Cardinality Notes
- `jobId` label only on artifact size gauge—avoid high cardinality elsewhere.
- Retry counters have no labels to prevent cardinality explosion.

## Future Enhancements
- Trace linkage to emitted events (inject span_id).
- OpenLineage emission (pending design).
- Artifact compression ratio metric for large datasets.

## Retry Jitter Details
Backoff base sequence: 0.5s, 1s, 2s, 4s, 5s (cap). Actual sleep per attempt:

```
effective_sleep = base_backoff + uniform(0, base_backoff) / 2
```

This spreads retries (0–50% additional delay) mitigating thundering herd. Expected average factor ≈1.25× base. Metrics `udb_airbyte_retries_total` and `udb_kestra_retries_total` count attempts beyond the first.
