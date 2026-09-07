"""
Unit tests for apps.core.lib.retry_config — Retry policies and timeout configuration.

Real Temporal RetryPolicy objects. No mocks.
"""

from datetime import timedelta

import pytest

from apps.core.lib.retry_config import (
    DATA_PROCESSING_RETRY,
    EXTERNAL_SERVICE_RETRY,
    HEARTBEAT_INTERVALS,
    NO_RETRY,
    TIMEOUTS,
    get_retry_policy,
    get_timeout,
)

# =============================================================================
# Retry Policy Tests
# =============================================================================


class TestRetryPolicies:
    def test_external_service_retry_config(self):
        assert EXTERNAL_SERVICE_RETRY.maximum_attempts == 3
        assert EXTERNAL_SERVICE_RETRY.initial_interval == timedelta(seconds=1)
        assert EXTERNAL_SERVICE_RETRY.backoff_coefficient == 2.0
        assert EXTERNAL_SERVICE_RETRY.maximum_interval == timedelta(seconds=60)

    def test_external_service_non_retryable_errors(self):
        non_retryable = EXTERNAL_SERVICE_RETRY.non_retryable_error_types
        assert "ValidationError" in non_retryable
        assert "AuthenticationError" in non_retryable
        assert "AuthorizationError" in non_retryable
        assert "ApplicationError" in non_retryable

    def test_data_processing_retry_config(self):
        assert DATA_PROCESSING_RETRY.maximum_attempts == 2
        assert DATA_PROCESSING_RETRY.initial_interval == timedelta(seconds=2)
        assert DATA_PROCESSING_RETRY.backoff_coefficient == 2.0
        assert DATA_PROCESSING_RETRY.maximum_interval == timedelta(seconds=120)

    def test_data_processing_non_retryable_errors(self):
        non_retryable = DATA_PROCESSING_RETRY.non_retryable_error_types
        assert "ValidationError" in non_retryable
        assert "DataQualityError" in non_retryable
        assert "AnalysisError" in non_retryable
        assert "ApplicationError" in non_retryable

    def test_no_retry_config(self):
        assert NO_RETRY.maximum_attempts == 1


# =============================================================================
# Timeout Tests
# =============================================================================


class TestTimeouts:
    def test_all_timeout_keys_exist(self):
        expected_keys = [
            "stats_short", "stats_long",
            "ml_clustering", "ml_training", "ml_forecasting",
            "ingestion_short", "ingestion_long", "ingestion_airbyte",
            "operational_short", "operational_medium", "operational_long",
            "processing_short", "processing_long",
            "discovery",
        ]
        for key in expected_keys:
            assert key in TIMEOUTS, f"Missing timeout key: {key}"

    def test_timeout_values_are_timedelta(self):
        for key, value in TIMEOUTS.items():
            assert isinstance(value, timedelta), f"TIMEOUTS['{key}'] is not timedelta"

    def test_stats_short_timeout(self):
        assert TIMEOUTS["stats_short"] == timedelta(minutes=5)

    def test_stats_long_timeout(self):
        assert TIMEOUTS["stats_long"] == timedelta(minutes=10)

    def test_ml_clustering_timeout(self):
        assert TIMEOUTS["ml_clustering"] == timedelta(minutes=10)

    def test_ingestion_airbyte_timeout(self):
        assert TIMEOUTS["ingestion_airbyte"] == timedelta(minutes=45)

    def test_discovery_timeout(self):
        assert TIMEOUTS["discovery"] == timedelta(minutes=5)


# =============================================================================
# Heartbeat Interval Tests
# =============================================================================


class TestHeartbeatIntervals:
    def test_default_heartbeat(self):
        assert HEARTBEAT_INTERVALS["default"] == timedelta(seconds=30)

    def test_long_running_heartbeat(self):
        assert HEARTBEAT_INTERVALS["long_running"] == timedelta(minutes=1)

    def test_data_transfer_heartbeat(self):
        assert HEARTBEAT_INTERVALS["data_transfer"] == timedelta(minutes=2)


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestGetRetryPolicy:
    def test_external_service(self):
        policy = get_retry_policy("external_service")
        assert policy is EXTERNAL_SERVICE_RETRY

    def test_data_processing(self):
        policy = get_retry_policy("data_processing")
        assert policy is DATA_PROCESSING_RETRY

    def test_no_retry(self):
        policy = get_retry_policy("no_retry")
        assert policy is NO_RETRY

    def test_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown activity_type"):
            get_retry_policy("unknown_type")

    def test_error_message_includes_valid_types(self):
        with pytest.raises(ValueError, match="external_service"):
            get_retry_policy("bad")


class TestGetTimeout:
    def test_valid_key(self):
        timeout = get_timeout("stats_short")
        assert timeout == timedelta(minutes=5)

    def test_unknown_key_raises(self):
        with pytest.raises(ValueError, match="Unknown timeout_key"):
            get_timeout("nonexistent_key")

    def test_error_message_includes_valid_keys(self):
        with pytest.raises(ValueError, match="stats_short"):
            get_timeout("bad_key")
