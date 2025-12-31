"""
Tests for Metrics Mode Gating

Verifies that VOYANT_METRICS_MODE controls which metrics are registered.
Reference: docs/CANONICAL_ARCHITECTURE.md Section 8
"""
import os
import pytest

# Set metrics mode before importing metrics module
os.environ["VOYANT_METRICS_MODE"] = "off"

# Clear any cached settings
import importlib
import voyant.core.config as config_module
import voyant.core.metrics as metrics_module


class TestMetricsModeOff:
    """Test metrics are not registered when mode is 'off'."""

    def setup_method(self):
        """Reset metrics module state."""
        os.environ["VOYANT_METRICS_MODE"] = "off"
        # Reset cached settings
        config_module.get_settings.cache_clear()
        # Reset metrics module
        metrics_module._initialized = False
        metrics_module.BASIC_METRICS.clear()
        metrics_module.FULL_METRICS.clear()

    def test_metrics_mode_off_no_basic_metrics(self):
        """When mode is 'off', no basic metrics should be registered."""
        metrics_module.init_metrics("off")
        assert len(metrics_module.BASIC_METRICS) == 0

    def test_metrics_mode_off_no_full_metrics(self):
        """When mode is 'off', no full metrics should be registered."""
        metrics_module.init_metrics("off")
        assert len(metrics_module.FULL_METRICS) == 0

    def test_record_job_safe_when_off(self):
        """Recording should not raise errors when metrics are off."""
        metrics_module.init_metrics("off")
        # Should not raise
        metrics_module.record_job("analyze", "completed")
        metrics_module.record_duration("analyze", 5.0)
        metrics_module.record_sufficiency(0.85)


class TestMetricsModeBasic:
    """Test only basic metrics are registered when mode is 'basic'."""

    def setup_method(self):
        """Reset metrics module state."""
        os.environ["VOYANT_METRICS_MODE"] = "basic"
        config_module.get_settings.cache_clear()
        metrics_module._initialized = False
        metrics_module.BASIC_METRICS.clear()
        metrics_module.FULL_METRICS.clear()

    def test_metrics_mode_basic_has_core_metrics(self):
        """When mode is 'basic', core metrics should be registered."""
        metrics_module.init_metrics("basic")
        assert "jobs_total" in metrics_module.BASIC_METRICS
        assert "job_duration_seconds" in metrics_module.BASIC_METRICS
        assert "dependency_up" in metrics_module.BASIC_METRICS

    def test_metrics_mode_basic_no_extended_metrics(self):
        """When mode is 'basic', extended metrics should NOT be registered."""
        metrics_module.init_metrics("basic")
        assert len(metrics_module.FULL_METRICS) == 0

    def test_record_basic_metrics_works(self):
        """Recording basic metrics should work in basic mode."""
        metrics_module.init_metrics("basic")
        metrics_module.record_job("sync", "completed")
        # Verify counter was incremented (prometheus_client internal)
        counter = metrics_module.BASIC_METRICS["jobs_total"]
        assert counter._metrics  # Has recorded values


class TestMetricsModeFull:
    """Test all metrics are registered when mode is 'full'."""

    def setup_method(self):
        """Reset metrics module state."""
        os.environ["VOYANT_METRICS_MODE"] = "full"
        config_module.get_settings.cache_clear()
        metrics_module._initialized = False
        metrics_module.BASIC_METRICS.clear()
        metrics_module.FULL_METRICS.clear()

    def test_metrics_mode_full_has_basic_metrics(self):
        """When mode is 'full', basic metrics should be registered."""
        metrics_module.init_metrics("full")
        assert "jobs_total" in metrics_module.BASIC_METRICS
        assert "job_duration_seconds" in metrics_module.BASIC_METRICS

    def test_metrics_mode_full_has_extended_metrics(self):
        """When mode is 'full', extended metrics should be registered."""
        metrics_module.init_metrics("full")
        assert "sufficiency_score" in metrics_module.FULL_METRICS
        assert "quality_runs_total" in metrics_module.FULL_METRICS
        assert "drift_runs_total" in metrics_module.FULL_METRICS
        assert "kpi_exec_latency_seconds" in metrics_module.FULL_METRICS

    def test_record_all_metrics_works(self):
        """Recording all metrics should work in full mode."""
        metrics_module.init_metrics("full")
        metrics_module.record_job("analyze", "completed")
        metrics_module.record_duration("analyze", 10.5)
        metrics_module.record_sufficiency(0.75)
        metrics_module.record_quality_run("success")
        metrics_module.record_kpi_latency(2.5)
        # All should have recorded without error


class TestMetricsModeFromSettings:
    """Test that metrics mode is read from settings when not passed."""

    def setup_method(self):
        """Reset state."""
        config_module.get_settings.cache_clear()
        metrics_module._initialized = False
        metrics_module.BASIC_METRICS.clear()
        metrics_module.FULL_METRICS.clear()

    def test_mode_reads_from_env(self):
        """init_metrics() without args should read from VOYANT_METRICS_MODE."""
        os.environ["VOYANT_METRICS_MODE"] = "basic"
        config_module.get_settings.cache_clear()
        
        mode = metrics_module.get_mode()
        assert mode == "basic"

    def test_is_enabled_true_for_basic(self):
        """is_enabled() should return True for 'basic' mode."""
        os.environ["VOYANT_METRICS_MODE"] = "basic"
        config_module.get_settings.cache_clear()
        assert metrics_module.is_enabled() is True

    def test_is_enabled_false_for_off(self):
        """is_enabled() should return False for 'off' mode."""
        os.environ["VOYANT_METRICS_MODE"] = "off"
        config_module.get_settings.cache_clear()
        assert metrics_module.is_enabled() is False
