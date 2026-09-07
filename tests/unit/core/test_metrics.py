"""
Unit tests for apps.core.lib.metrics — Prometheus metrics with mode gating.

Real Prometheus registry. No mocks.
"""

import pytest

from apps.core.lib.metrics import (
    BASIC_METRICS,
    FULL_METRICS,
    init_metrics,
    record_airbyte_retry,
    record_artifacts_pruned,
    record_dependency,
    record_dependency_check_failure,
    record_drift_run,
    record_duration,
    record_ingest_fragments,
    record_job,
    record_kestra_retry,
    record_kpi_latency,
    record_kpi_rowsets,
    record_oauth_initiation,
    record_quality_run,
    record_sufficiency,
    reset_metrics,
    set_artifact_size,
    set_duckdb_queue_length,
)


@pytest.fixture(autouse=True)
def clean_metrics():
    reset_metrics()
    yield
    reset_metrics()


# =============================================================================
# Initialization Tests
# =============================================================================


class TestMetricsInit:
    def test_off_mode(self):
        init_metrics("off")
        assert len(BASIC_METRICS) == 0
        assert len(FULL_METRICS) == 0

    def test_basic_mode(self):
        init_metrics("basic")
        assert "jobs_total" in BASIC_METRICS
        assert "job_duration_seconds" in BASIC_METRICS
        assert "dependency_up" in BASIC_METRICS
        assert len(FULL_METRICS) == 0

    def test_full_mode(self):
        init_metrics("full")
        assert len(BASIC_METRICS) > 0
        assert len(FULL_METRICS) > 0
        assert "sufficiency_score" in FULL_METRICS
        assert "quality_runs_total" in FULL_METRICS
        assert "drift_runs_total" in FULL_METRICS

    def test_idempotent(self):
        init_metrics("basic")
        count1 = len(BASIC_METRICS)
        init_metrics("basic")
        count2 = len(BASIC_METRICS)
        assert count1 == count2

    def test_mode_case_insensitive(self):
        init_metrics("BASIC")
        assert "jobs_total" in BASIC_METRICS


# =============================================================================
# Reset Tests
# =============================================================================


class TestMetricsReset:
    def test_reset_clears_state(self):
        init_metrics("full")
        assert len(BASIC_METRICS) > 0
        reset_metrics()
        assert len(BASIC_METRICS) == 0
        assert len(FULL_METRICS) == 0

    def test_reset_allows_reinit(self):
        init_metrics("full")
        reset_metrics()
        init_metrics("basic")
        assert "jobs_total" in BASIC_METRICS
        assert len(FULL_METRICS) == 0


# =============================================================================
# Basic Metric Recording Tests
# =============================================================================


class TestBasicMetricRecording:
    def test_record_job(self):
        init_metrics("basic")
        record_job("analyze", "started")
        record_job("analyze", "completed")
        # Should not raise; metric should be incremented
        metric = BASIC_METRICS["jobs_total"]
        assert metric.labels(type="analyze", state="started")._value.get() == 1
        assert metric.labels(type="analyze", state="completed")._value.get() == 1

    def test_record_duration(self):
        init_metrics("basic")
        record_duration("analyze", 12.5)
        # Should not raise; metric was observed
        metric = BASIC_METRICS["job_duration_seconds"]
        samples = list(metric.collect())
        assert len(samples) > 0

    def test_record_dependency_up(self):
        init_metrics("basic")
        record_dependency("postgres", True)
        metric = BASIC_METRICS["dependency_up"]
        assert metric.labels(component="postgres")._value.get() == 1

    def test_record_dependency_down(self):
        init_metrics("basic")
        record_dependency("kafka", False)
        metric = BASIC_METRICS["dependency_up"]
        assert metric.labels(component="kafka")._value.get() == 0

    def test_record_job_noop_when_off(self):
        init_metrics("off")
        # Should not raise
        record_job("analyze", "started")

    def test_record_duration_noop_when_off(self):
        init_metrics("off")
        record_duration("analyze", 5.0)

    def test_record_dependency_noop_when_off(self):
        init_metrics("off")
        record_dependency("pg", True)


# =============================================================================
# Full Metric Recording Tests
# =============================================================================


class TestFullMetricRecording:
    def test_record_sufficiency(self):
        init_metrics("full")
        record_sufficiency(0.85)
        metric = FULL_METRICS["sufficiency_score"]
        samples = list(metric.collect())
        assert len(samples) > 0

    def test_record_quality_run(self):
        init_metrics("full")
        record_quality_run("success")
        metric = FULL_METRICS["quality_runs_total"]
        assert metric.labels(status="success")._value.get() == 1

    def test_record_drift_run(self):
        init_metrics("full")
        record_drift_run("detected")
        metric = FULL_METRICS["drift_runs_total"]
        assert metric.labels(status="detected")._value.get() == 1

    def test_record_kpi_latency(self):
        init_metrics("full")
        record_kpi_latency(2.5)
        metric = FULL_METRICS["kpi_exec_latency_seconds"]
        samples = list(metric.collect())
        assert len(samples) > 0

    def test_record_kpi_rowsets(self):
        init_metrics("full")
        record_kpi_rowsets(10)
        metric = FULL_METRICS["analyze_kpi_rowsets"]
        samples = list(metric.collect())
        assert len(samples) > 0

    def test_record_ingest_fragments(self):
        init_metrics("full")
        record_ingest_fragments(100)
        metric = FULL_METRICS["ingest_fragments"]
        samples = list(metric.collect())
        assert len(samples) > 0

    def test_record_artifacts_pruned(self):
        init_metrics("full")
        record_artifacts_pruned(3)
        metric = FULL_METRICS["artifacts_pruned_total"]
        assert metric._value.get() == 3

    def test_record_oauth_initiation(self):
        init_metrics("full")
        record_oauth_initiation("google")
        metric = FULL_METRICS["oauth_initiations_total"]
        assert metric.labels(provider="google")._value.get() == 1

    def test_set_artifact_size(self):
        init_metrics("full")
        set_artifact_size("job-1", 1024)
        metric = FULL_METRICS["artifact_size_bytes"]
        assert metric.labels(job_id="job-1")._value.get() == 1024

    def test_set_duckdb_queue_length(self):
        init_metrics("full")
        set_duckdb_queue_length(5)
        metric = FULL_METRICS["duckdb_queue_length"]
        assert metric._value.get() == 5

    def test_record_airbyte_retry(self):
        init_metrics("full")
        record_airbyte_retry()
        metric = FULL_METRICS["airbyte_retries_total"]
        assert metric._value.get() == 1

    def test_record_kestra_retry(self):
        init_metrics("full")
        record_kestra_retry()
        metric = FULL_METRICS["kestra_retries_total"]
        assert metric._value.get() == 1

    def test_record_dependency_check_failure(self):
        init_metrics("full")
        record_dependency_check_failure()
        metric = FULL_METRICS["dependency_check_failures_total"]
        assert metric._value.get() == 1

    def test_full_metrics_noop_in_basic_mode(self):
        init_metrics("basic")
        # Should not raise
        record_sufficiency(0.5)
        record_quality_run("success")
        record_drift_run("detected")
        record_kpi_latency(1.0)
        record_kpi_rowsets(5)
        record_ingest_fragments(10)
        record_artifacts_pruned()
        record_oauth_initiation("google")
        set_artifact_size("j1", 100)
        set_duckdb_queue_length(3)
        record_airbyte_retry()
        record_kestra_retry()
        record_dependency_check_failure()
