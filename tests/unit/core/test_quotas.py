"""
Unit tests for apps.core.lib.quotas — Tenant quota enforcement and usage tracking.

Real in-memory store. No mocks, no external services.
"""

import pytest

from apps.core.lib.quotas import (
    QUOTA_TIERS,
    DEFAULT_TIER,
    QuotaTier,
    TenantUsage,
    check_quota,
    get_quota_limits,
    get_tenant_tier,
    get_usage_status,
    list_tiers,
    record_artifact_size,
    record_job_end,
    record_job_start,
    record_source_added,
    record_source_removed,
    reset_tenant_usage,
    set_tenant_tier,
    _get_usage,
    _usage_store,
    _tenant_tiers,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Reset all tenant state between tests."""
    _usage_store.clear()
    _tenant_tiers.clear()
    yield
    _usage_store.clear()
    _tenant_tiers.clear()


# =============================================================================
# QuotaTier Tests
# =============================================================================


class TestQuotaTiers:
    def test_default_tiers_exist(self):
        assert "free" in QUOTA_TIERS
        assert "starter" in QUOTA_TIERS
        assert "professional" in QUOTA_TIERS
        assert "enterprise" in QUOTA_TIERS

    def test_free_tier_limits(self):
        free = QUOTA_TIERS["free"]
        assert free.max_jobs_per_day == 10
        assert free.max_artifacts_gb == 1.0
        assert free.max_sources == 3
        assert free.max_concurrent_jobs == 1

    def test_enterprise_tier_limits(self):
        ent = QUOTA_TIERS["enterprise"]
        assert ent.max_jobs_per_day == 10000
        assert ent.max_concurrent_jobs == 50

    def test_default_tier_is_free(self):
        assert DEFAULT_TIER == "free"


# =============================================================================
# Tenant Tier Tests
# =============================================================================


class TestTenantTier:
    def test_set_and_get_tier(self):
        set_tenant_tier("t1", "starter")
        assert get_tenant_tier("t1") == "starter"

    def test_default_tier(self):
        assert get_tenant_tier("unknown") == "free"

    def test_set_invalid_tier(self):
        with pytest.raises(ValueError, match="Unknown tier"):
            set_tenant_tier("t1", "nonexistent")

    def test_set_tier_updates_existing_usage(self):
        _get_usage("t1")  # Creates with default tier
        set_tenant_tier("t1", "professional")
        usage = _get_usage("t1")
        assert usage.tier == "professional"


# =============================================================================
# Quota Limits Tests
# =============================================================================


class TestQuotaLimits:
    def test_get_quota_limits(self):
        set_tenant_tier("t1", "starter")
        limits = get_quota_limits("t1")
        assert limits["tier"] == "starter"
        assert limits["max_jobs_per_day"] == 100
        assert limits["max_artifacts_gb"] == 10.0

    def test_get_quota_limits_default(self):
        limits = get_quota_limits("unknown")
        assert limits["tier"] == "free"


# =============================================================================
# Check Quota Tests
# =============================================================================


class TestCheckQuota:
    def test_jobs_per_day_within_limit(self):
        allowed, msg = check_quota("t1", "jobs_per_day")
        assert allowed is True
        assert msg is None

    def test_jobs_per_day_exceeded(self):
        tier = QUOTA_TIERS["free"]
        usage = _get_usage("t1")
        usage.jobs_today = tier.max_jobs_per_day

        allowed, msg = check_quota("t1", "jobs_per_day")
        assert allowed is False
        assert "Daily job quota exceeded" in msg

    def test_concurrent_jobs_within_limit(self):
        allowed, msg = check_quota("t1", "concurrent_jobs")
        assert allowed is True

    def test_concurrent_jobs_exceeded(self):
        tier = QUOTA_TIERS["free"]
        usage = _get_usage("t1")
        usage.concurrent_jobs = tier.max_concurrent_jobs

        allowed, msg = check_quota("t1", "concurrent_jobs")
        assert allowed is False
        assert "Concurrent job limit" in msg

    def test_sources_within_limit(self):
        allowed, msg = check_quota("t1", "sources")
        assert allowed is True

    def test_sources_exceeded(self):
        tier = QUOTA_TIERS["free"]
        usage = _get_usage("t1")
        usage.current_sources = tier.max_sources

        allowed, msg = check_quota("t1", "sources")
        assert allowed is False
        assert "Source limit" in msg

    def test_artifacts_within_limit(self):
        allowed, msg = check_quota("t1", "artifacts")
        assert allowed is True

    def test_artifacts_exceeded(self):
        tier = QUOTA_TIERS["free"]
        usage = _get_usage("t1")
        usage.artifacts_bytes = int(tier.max_artifacts_gb * (1024**3)) + 1

        allowed, msg = check_quota("t1", "artifacts")
        assert allowed is False
        assert "Artifact storage limit" in msg

    def test_unknown_quota_type(self):
        allowed, msg = check_quota("t1", "unknown_type")
        assert allowed is True
        assert msg is None


# =============================================================================
# Record Usage Tests
# =============================================================================


class TestRecordUsage:
    def test_record_job_start(self):
        result = record_job_start("t1")
        assert result is True
        usage = _get_usage("t1")
        assert usage.jobs_today == 1
        assert usage.concurrent_jobs == 1

    def test_record_job_start_exceeds_daily(self):
        tier = QUOTA_TIERS["free"]
        usage = _get_usage("t1")
        usage.jobs_today = tier.max_jobs_per_day

        result = record_job_start("t1")
        assert result is False

    def test_record_job_start_exceeds_concurrent(self):
        tier = QUOTA_TIERS["free"]
        usage = _get_usage("t1")
        usage.concurrent_jobs = tier.max_concurrent_jobs

        result = record_job_start("t1")
        assert result is False

    def test_record_job_end(self):
        usage = _get_usage("t1")
        usage.concurrent_jobs = 3
        record_job_end("t1")
        assert usage.concurrent_jobs == 2

    def test_record_job_end_no_negative(self):
        record_job_end("t1")
        usage = _get_usage("t1")
        assert usage.concurrent_jobs == 0

    def test_record_artifact_size(self):
        record_artifact_size("t1", 1024)
        usage = _get_usage("t1")
        assert usage.artifacts_bytes == 1024

    def test_record_artifact_size_accumulates(self):
        record_artifact_size("t1", 1024)
        record_artifact_size("t1", 2048)
        usage = _get_usage("t1")
        assert usage.artifacts_bytes == 3072

    def test_record_source_added(self):
        result = record_source_added("t1")
        assert result is True
        usage = _get_usage("t1")
        assert usage.current_sources == 1

    def test_record_source_added_exceeded(self):
        tier = QUOTA_TIERS["free"]
        usage = _get_usage("t1")
        usage.current_sources = tier.max_sources

        result = record_source_added("t1")
        assert result is False

    def test_record_source_removed(self):
        usage = _get_usage("t1")
        usage.current_sources = 3
        record_source_removed("t1")
        assert usage.current_sources == 2

    def test_record_source_removed_no_negative(self):
        record_source_removed("t1")
        usage = _get_usage("t1")
        assert usage.current_sources == 0


# =============================================================================
# Usage Status Tests
# =============================================================================


class TestUsageStatus:
    def test_usage_status_structure(self):
        status = get_usage_status("t1")
        assert status["tenant_id"] == "t1"
        assert status["tier"] == "free"
        assert status["jobs_today"] == 0
        assert status["jobs_limit"] == 10
        assert status["jobs_remaining"] == 10
        assert "artifacts_gb" in status
        assert "sources_count" in status
        assert "concurrent_jobs" in status

    def test_usage_status_after_jobs(self):
        record_job_start("t1")
        record_job_start("t1")
        status = get_usage_status("t1")
        assert status["jobs_today"] == 2
        assert status["jobs_remaining"] == 8


# =============================================================================
# Reset Tests
# =============================================================================


class TestReset:
    def test_reset_tenant_usage(self):
        record_job_start("t1")
        record_artifact_size("t1", 1024)
        reset_tenant_usage("t1")
        usage = _get_usage("t1")
        assert usage.jobs_today == 0
        assert usage.artifacts_bytes == 0

    def test_reset_preserves_tier(self):
        set_tenant_tier("t1", "professional")
        record_job_start("t1")
        reset_tenant_usage("t1")
        usage = _get_usage("t1")
        assert usage.tier == "professional"


# =============================================================================
# List Tiers Tests
# =============================================================================


class TestListTiers:
    def test_list_tiers(self):
        tiers = list_tiers()
        assert "free" in tiers
        assert "starter" in tiers
        assert "professional" in tiers
        assert "enterprise" in tiers
        assert tiers["free"]["name"] == "Free"
