"""
Voyant Metrics with Mode Gating

Implements UDB_METRICS_MODE environment variable functionality.
Reference: docs/CANONICAL_ARCHITECTURE.md Section 8

Modes:
- off: No metrics registered (minimal footprint)
- basic: Core job metrics only (job_total, job_duration)
- full: All metrics including quality, drift, KPI latency, sufficiency, etc.

Usage:
    from voyant.core.metrics import get_metric, record_job, record_duration

    # Record a job
    record_job("analyze", "completed")

    # Record duration (histogram)
    record_duration("analyze", 12.5)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from prometheus_client import REGISTRY, Counter, Gauge, Histogram

logger = logging.getLogger(__name__)

# =============================================================================
# Metric Definitions
# =============================================================================

# Basic metrics (registered in basic and full modes)
BASIC_METRICS: Dict[str, Any] = {}

# Full metrics (registered only in full mode)
FULL_METRICS: Dict[str, Any] = {}

# Initialization flag
_initialized = False


def reset_metrics():
    """
    Reset metrics state for testing.
    Unregisters all metrics from the Prometheus registry and clears the metric dictionaries.
    This should ONLY be used in tests.
    """
    global _initialized, BASIC_METRICS, FULL_METRICS
    
    # Unregister all basic metrics
    for metric_name, metric in list(BASIC_METRICS.items()):
        try:
            REGISTRY.unregister(metric)
        except Exception:
            pass  # Metric might not be registered
    
    # Unregister all full metrics
    for metric_name, metric in list(FULL_METRICS.items()):
        try:
            REGISTRY.unregister(metric)
        except Exception:
            pass  # Metric might not be registered
    
    # Clear the dictionaries
    BASIC_METRICS.clear()
    FULL_METRICS.clear()
    
    # Reset initialization flag
    _initialized = False
    
    logger.debug("Metrics reset complete")


def _create_basic_metrics():
    """
    Create and register the set of basic metrics.
    These metrics are registered when the mode is 'basic' or 'full'.
    """
    global BASIC_METRICS

    BASIC_METRICS["jobs_total"] = Counter(
        "udb_jobs_total", "Job lifecycle counts", ["type", "state"]
    )

    BASIC_METRICS["job_duration_seconds"] = Histogram(
        "udb_job_duration_seconds",
        "Job duration in seconds",
        ["type"],
        buckets=[1, 5, 10, 30, 60, 120, 300, 600],
    )

    BASIC_METRICS["dependency_up"] = Gauge(
        "udb_dependency_up", "Dependency health status (1=up, 0=down)", ["component"]
    )


def _create_full_metrics():
    """
    Create and register the set of extended metrics.
    These metrics are only registered when the mode is 'full'.
    """
    global FULL_METRICS

    FULL_METRICS["sufficiency_score"] = Histogram(
        "udb_sufficiency_score",
        "Sufficiency readiness score distribution",
        buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    )

    FULL_METRICS["quality_runs_total"] = Counter(
        "udb_quality_runs_total", "Quality artifact generation runs", ["status"]
    )

    FULL_METRICS["drift_runs_total"] = Counter(
        "udb_drift_runs_total", "Drift detection runs", ["status"]
    )

    FULL_METRICS["kpi_exec_latency_seconds"] = Histogram(
        "udb_kpi_exec_latency_seconds",
        "KPI execution latency",
        buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
    )

    FULL_METRICS["analyze_kpi_rowsets"] = Histogram(
        "udb_analyze_kpi_rowsets",
        "Number of KPI rowsets per analyze job",
        buckets=[1, 5, 10, 25, 50, 100],
    )

    FULL_METRICS["ingest_fragments"] = Histogram(
        "udb_ingest_fragments",
        "Fragments produced per ingest job",
        buckets=[1, 10, 50, 100, 500, 1000],
    )

    FULL_METRICS["artifacts_pruned_total"] = Counter(
        "udb_artifacts_pruned_total", "Number of artifact directories pruned"
    )

    FULL_METRICS["oauth_initiations_total"] = Counter(
        "udb_oauth_initiations_total", "OAuth initiation attempts", ["provider"]
    )

    FULL_METRICS["artifact_size_bytes"] = Gauge(
        "udb_artifact_size_bytes", "Total size of job artifact directory", ["job_id"]
    )

    FULL_METRICS["duckdb_queue_length"] = Gauge(
        "udb_duckdb_queue_length", "Current DuckDB write queue length"
    )

    FULL_METRICS["airbyte_retries_total"] = Counter(
        "udb_airbyte_retries_total", "Airbyte client retry attempts"
    )

    FULL_METRICS["kestra_retries_total"] = Counter(
        "udb_kestra_retries_total", "Kestra client retry attempts"
    )

    FULL_METRICS["dependency_check_failures_total"] = Counter(
        "udb_dependency_check_failures_total", "Failed dependency health probes"
    )


def init_metrics(mode: Optional[str] = None):
    """
    Initialize and register metrics based on the specified mode.
    This function is idempotent and will only initialize the metrics once.
    Args:
        mode: The metrics mode ('off', 'basic', or 'full'). If None, it is
              loaded from the application settings.
    """
    global _initialized

    if _initialized:
        logger.debug("Metrics already initialized, skipping")
        return

    if mode is None:
        # Avoid circular import - import here
        from voyant.core.config import get_settings

        mode = get_settings().metrics_mode

    mode = mode.lower()

    if mode == "off":
        logger.info("Metrics mode: OFF - no metrics registered")
        _initialized = True
        return

    if mode in ("basic", "full"):
        _create_basic_metrics()
        logger.info(f"Metrics mode: {mode.upper()} - basic metrics registered")

    if mode == "full":
        _create_full_metrics()
        logger.info("Metrics mode: FULL - extended metrics registered")

    _initialized = True


def get_mode() -> str:
    """
    Get the current metrics mode from the application settings.
    Returns:
        The current metrics mode as a string.
    """
    from voyant.core.config import get_settings

    return get_settings().metrics_mode


def is_enabled() -> bool:
    """
    Check if metrics are currently enabled (i.e., not in 'off' mode).
    Returns:
        True if metrics are enabled, False otherwise.
    """
    return get_mode().lower() != "off"


# =============================================================================
# Metric Recording Helpers
# =============================================================================


def record_job(job_type: str, state: str):
    """
    Record a job lifecycle event by incrementing the 'jobs_total' counter.
    Args:
        job_type: The type of the job (e.g., 'analyze', 'ingest').
        state: The state of the job (e.g., 'started', 'completed', 'failed').
    """
    if "jobs_total" in BASIC_METRICS:
        BASIC_METRICS["jobs_total"].labels(type=job_type, state=state).inc()


def record_duration(job_type: str, duration_seconds: float):
    """
    Record the duration of a job using a histogram.
    Args:
        job_type: The type of the job.
        duration_seconds: The duration of the job in seconds.
    """
    if "job_duration_seconds" in BASIC_METRICS:
        BASIC_METRICS["job_duration_seconds"].labels(type=job_type).observe(
            duration_seconds
        )


def record_dependency(component: str, is_up: bool):
    """
    Record the health status of an external dependency.
    Args:
        component: The name of the dependency (e.g., 'postgres', 'kafka').
        is_up: True if the dependency is up, False otherwise.
    """
    if "dependency_up" in BASIC_METRICS:
        BASIC_METRICS["dependency_up"].labels(component=component).set(
            1 if is_up else 0
        )


def record_sufficiency(score: float):
    """
    Record a sufficiency score. (Full mode only)
    Args:
        score: The calculated sufficiency score.
    """
    if "sufficiency_score" in FULL_METRICS:
        FULL_METRICS["sufficiency_score"].observe(score)


def record_quality_run(status: str):
    """
    Record the status of a quality artifact generation run. (Full mode only)
    Args:
        status: The final status of the run (e.g., 'success', 'failure').
    """
    if "quality_runs_total" in FULL_METRICS:
        FULL_METRICS["quality_runs_total"].labels(status=status).inc()


def record_drift_run(status: str):
    """
    Record the status of a drift detection run. (Full mode only)
    Args:
        status: The final status of the run.
    """
    if "drift_runs_total" in FULL_METRICS:
        FULL_METRICS["drift_runs_total"].labels(status=status).inc()


def record_kpi_latency(seconds: float):
    """
    Record the execution latency of a KPI. (Full mode only)
    Args:
        seconds: The latency in seconds.
    """
    if "kpi_exec_latency_seconds" in FULL_METRICS:
        FULL_METRICS["kpi_exec_latency_seconds"].observe(seconds)


def record_kpi_rowsets(count: int):
    """
    Record the number of KPI rowsets in an analyze job. (Full mode only)
    Args:
        count: The number of rowsets.
    """
    if "analyze_kpi_rowsets" in FULL_METRICS:
        FULL_METRICS["analyze_kpi_rowsets"].observe(count)


def record_ingest_fragments(count: int):
    """
    Record the number of fragments produced by an ingest job. (Full mode only)
    Args:
        count: The number of fragments.
    """
    if "ingest_fragments" in FULL_METRICS:
        FULL_METRICS["ingest_fragments"].observe(count)


def record_artifacts_pruned(count: int = 1):
    """
    Record that artifacts have been pruned. (Full mode only)
    Args:
        count: The number of artifacts pruned.
    """
    if "artifacts_pruned_total" in FULL_METRICS:
        FULL_METRICS["artifacts_pruned_total"].inc(count)


def record_oauth_initiation(provider: str):
    """
    Record an OAuth initiation attempt. (Full mode only)
    Args:
        provider: The name of the OAuth provider.
    """
    if "oauth_initiations_total" in FULL_METRICS:
        FULL_METRICS["oauth_initiations_total"].labels(provider=provider).inc()


def set_artifact_size(job_id: str, size_bytes: int):
    """
    Set the size of a job's artifact directory. (Full mode only)
    Args:
        job_id: The ID of the job.
        size_bytes: The size of the artifact directory in bytes.
    """
    if "artifact_size_bytes" in FULL_METRICS:
        FULL_METRICS["artifact_size_bytes"].labels(job_id=job_id).set(size_bytes)


def set_duckdb_queue_length(length: int):
    """
    Set the current length of the DuckDB write queue. (Full mode only)
    Args:
        length: The current queue length.
    """
    if "duckdb_queue_length" in FULL_METRICS:
        FULL_METRICS["duckdb_queue_length"].set(length)


def record_airbyte_retry():
    """Record an Airbyte client retry attempt. (Full mode only)"""
    if "airbyte_retries_total" in FULL_METRICS:
        FULL_METRICS["airbyte_retries_total"].inc()


def record_kestra_retry():
    """Record a Kestra client retry attempt. (Full mode only)"""
    if "kestra_retries_total" in FULL_METRICS:
        FULL_METRICS["kestra_retries_total"].inc()


def record_dependency_check_failure():
    """Record a failed dependency health probe. (Full mode only)"""
    if "dependency_check_failures_total" in FULL_METRICS:
        FULL_METRICS["dependency_check_failures_total"].inc()
