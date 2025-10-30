"""Prometheus metrics instrumentation."""
from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

job_counter = Counter("udb_jobs_total", "Total jobs by type/state", ["type", "state"])
job_duration = Histogram(
    "udb_job_duration_seconds",
    "Job durations",
    ["type"],
    buckets=(1, 5, 15, 30, 60, 120, 300, 600),
)
analyze_kpi_count = Histogram(
    "udb_analyze_kpi_rowsets",
    "Number of KPI rowsets returned per analyze",
    buckets=(0, 1, 2, 5, 10, 20, 50),
)
quality_runs = Counter("udb_quality_runs_total", "Quality report runs", ["status"]) # status=success|error|skipped
drift_runs = Counter("udb_drift_runs_total", "Drift report runs", ["status"]) # status=success|error|skipped
oauth_initiations = Counter("udb_oauth_initiations_total", "OAuth initiation requests", ["provider"]) 
ingest_fragments = Histogram(
    "udb_ingest_fragments",
    "Number of fragments per ingest",
    buckets=(0, 1, 5, 10, 25, 50, 100, 250, 500, 1000),
)
artifacts_pruned = Counter("udb_artifacts_pruned_total", "Number of artifact job directories pruned")
sufficiency_scores = Histogram(
    "udb_sufficiency_score",
    "Distribution of sufficiency readiness scores",
    buckets=(0, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)

dependency_up = Gauge(
    "udb_dependency_up",
    "Dependency health status (1=up,0=down)",
    ["component"],
)

dependency_check_failures = Counter(
    "udb_dependency_check_failures_total",
    "Count of dependency check failures",
)

airbyte_retries = Counter(
    "udb_airbyte_retries_total",
    "Total Airbyte client retry attempts",
)

kestra_retries = Counter(
    "udb_kestra_retries_total",
    "Total Kestra client retry attempts",
)

artifact_size_bytes = Gauge(
    "udb_artifact_size_bytes",
    "Total size of artifacts directory for a job (bytes)",
    ["jobId"],
)

kpi_exec_latency = Histogram(
    "udb_kpi_exec_latency_seconds",
    "Latency of KPI execution block",
    buckets=(0.1, 0.25, 0.5, 1, 2, 5, 10),
)

duckdb_queue_length = Gauge(
    "udb_duckdb_queue_length",
    "Current length of queued DuckDB operations",
)

router = APIRouter()

@router.get("/metrics")
async def metrics():  # pragma: no cover (exposed endpoint)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

@router.get("/metrics/select")
async def metrics_select(mode: str = "core"):
    """Return a reduced metrics set when mode=core to lower cardinality footprint.

    Excludes high-cardinality metrics (artifact size with jobId labels) and any line containing jobId=.
    Additional modes can be added later (e.g., 'perf', 'all'). Currently any non-'core' returns full set.
    """
    if mode != "core":  # full passthrough
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    raw = generate_latest().decode()
    filtered_lines: list[str] = []
    for line in raw.splitlines():
        if line.startswith('#'):
            filtered_lines.append(line)
            continue
        if not line.strip():
            continue
        if line.startswith('udb_artifact_size_bytes'):
            continue
        if 'jobId="' in line:
            continue
        filtered_lines.append(line)
    body = '\n'.join(filtered_lines) + '\n'
    return Response(body, media_type=CONTENT_TYPE_LATEST)
