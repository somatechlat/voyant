"""
Unit tests for apps.core.lib.tenant_quotas — Quota enforcement and usage tracking.

Real in-memory QuotaManager. No mocks, no external services.
"""

import time

import pytest

from apps.core.lib.tenant_quotas import (
    CostMetrics,
    DEFAULT_POLICIES,
    QuotaCheckResult,
    QuotaExceededException,
    QuotaLimit,
    QuotaManager,
    QuotaPolicy,
    QuotaTier,
    ResourceType,
    UsageRecord,
    UsageSummary,
    check_quota,
    get_quota_manager,
    get_usage_stats,
    record_usage,
    require_quota,
    set_tenant_tier,
)


@pytest.fixture
def manager():
    return QuotaManager()


# =============================================================================
# Enum Tests
# =============================================================================


class TestResourceType:
    def test_all_values(self):
        assert ResourceType.JOBS_PER_DAY == "jobs_per_day"
        assert ResourceType.JOBS_CONCURRENT == "jobs_concurrent"
        assert ResourceType.ARTIFACT_SIZE_MB == "artifact_size_mb"
        assert ResourceType.TOTAL_STORAGE_MB == "total_storage_mb"
        assert ResourceType.API_CALLS_PER_MINUTE == "api_calls_per_minute"
        assert ResourceType.CPU_SECONDS_PER_DAY == "cpu_seconds_per_day"
        assert ResourceType.MEMORY_MB == "memory_mb"
        assert ResourceType.WORKFLOWS_PER_DAY == "workflows_per_day"


class TestQuotaTier:
    def test_all_values(self):
        assert QuotaTier.FREE == "free"
        assert QuotaTier.STARTER == "starter"
        assert QuotaTier.PROFESSIONAL == "professional"
        assert QuotaTier.ENTERPRISE == "enterprise"
        assert QuotaTier.UNLIMITED == "unlimited"


# =============================================================================
# QuotaLimit & QuotaPolicy Tests
# =============================================================================


class TestQuotaLimitAndPolicy:
    def test_quota_limit_defaults(self):
        limit = QuotaLimit(resource=ResourceType.JOBS_PER_DAY, limit=100)
        assert limit.period_seconds == 86400
        assert limit.burst_limit is None

    def test_quota_policy_get_limit(self):
        policy = QuotaPolicy(
            tier=QuotaTier.FREE,
            limits={
                ResourceType.JOBS_PER_DAY: QuotaLimit(
                    ResourceType.JOBS_PER_DAY, 10
                ),
            },
        )
        limit = policy.get_limit(ResourceType.JOBS_PER_DAY)
        assert limit is not None
        assert limit.limit == 10

    def test_quota_policy_get_limit_missing(self):
        policy = QuotaPolicy(tier=QuotaTier.FREE)
        assert policy.get_limit(ResourceType.JOBS_PER_DAY) is None


# =============================================================================
# Default Policies Tests
# =============================================================================


class TestDefaultPolicies:
    def test_all_tiers_have_policies(self):
        assert QuotaTier.FREE in DEFAULT_POLICIES
        assert QuotaTier.STARTER in DEFAULT_POLICIES
        assert QuotaTier.PROFESSIONAL in DEFAULT_POLICIES
        assert QuotaTier.ENTERPRISE in DEFAULT_POLICIES
        assert QuotaTier.UNLIMITED in DEFAULT_POLICIES

    def test_unlimited_has_no_limits(self):
        policy = DEFAULT_POLICIES[QuotaTier.UNLIMITED]
        assert policy.limits == {}

    def test_free_tier_limits(self):
        policy = DEFAULT_POLICIES[QuotaTier.FREE]
        assert policy.get_limit(ResourceType.JOBS_PER_DAY).limit == 10
        assert policy.get_limit(ResourceType.JOBS_CONCURRENT).limit == 2
        assert policy.get_limit(ResourceType.ARTIFACT_SIZE_MB).limit == 50


# =============================================================================
# QuotaManager — Tenant Tier
# =============================================================================


class TestQuotaManagerTier:
    def test_default_tier_is_free(self, manager):
        assert manager.get_tenant_tier("t1") == QuotaTier.FREE

    def test_set_tenant_tier(self, manager):
        manager.set_tenant_tier("t1", QuotaTier.PROFESSIONAL)
        assert manager.get_tenant_tier("t1") == QuotaTier.PROFESSIONAL

    def test_get_policy(self, manager):
        manager.set_tenant_tier("t1", QuotaTier.ENTERPRISE)
        policy = manager.get_policy("t1")
        assert policy.tier == QuotaTier.ENTERPRISE

    def test_get_policy_unknown_tier_falls_back(self, manager):
        # Manually set an unknown tier
        manager._tenant_tiers["t1"] = "nonexistent"
        policy = manager.get_policy("t1")
        assert policy.tier == QuotaTier.FREE


# =============================================================================
# QuotaManager — Check Quota
# =============================================================================


class TestQuotaManagerCheckQuota:
    def test_within_quota(self, manager):
        result = manager.check_quota("t1", ResourceType.JOBS_PER_DAY)
        assert result.allowed is True
        assert result.message == "Within quota"

    def test_exceeds_quota(self, manager):
        # Fill up the quota
        for _ in range(10):
            manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 1)

        result = manager.check_quota("t1", ResourceType.JOBS_PER_DAY)
        assert result.allowed is False
        assert "Quota exceeded" in result.message

    def test_unlimited_tier(self, manager):
        manager.set_tenant_tier("t1", QuotaTier.UNLIMITED)
        result = manager.check_quota("t1", ResourceType.JOBS_PER_DAY)
        assert result.allowed is True
        assert result.limit == float("inf")

    def test_no_limit_configured(self, manager):
        # UNLIMITED has no limits
        manager.set_tenant_tier("t1", QuotaTier.UNLIMITED)
        result = manager.check_quota("t1", ResourceType.MEMORY_MB)
        assert result.allowed is True

    def test_requested_amount_exceeds(self, manager):
        result = manager.check_quota("t1", ResourceType.JOBS_PER_DAY, requested_amount=11)
        assert result.allowed is False

    def test_concurrent_quota_uses_recent_window(self, manager):
        # Record concurrent usage
        manager.record_usage("t1", ResourceType.JOBS_CONCURRENT, 2)
        result = manager.check_quota("t1", ResourceType.JOBS_CONCURRENT)
        assert result.allowed is False  # Free tier limit is 2

    def test_quota_check_result_to_dict(self, manager):
        result = manager.check_quota("t1", ResourceType.JOBS_PER_DAY)
        d = result.to_dict()
        assert "allowed" in d
        assert "resource" in d
        assert "current_usage" in d
        assert "limit" in d
        assert "message" in d


# =============================================================================
# QuotaManager — Record Usage
# =============================================================================


class TestQuotaManagerRecordUsage:
    def test_record_usage(self, manager):
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 1)
        summaries = manager.get_usage_summary("t1", ResourceType.JOBS_PER_DAY)
        assert len(summaries) == 1
        assert summaries[0].current_usage == 1

    def test_record_usage_accumulates(self, manager):
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 1)
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 1)
        summaries = manager.get_usage_summary("t1", ResourceType.JOBS_PER_DAY)
        assert summaries[0].current_usage == 2

    def test_record_usage_with_job_id(self, manager):
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 1, job_id="j1")
        # Should not raise
        summaries = manager.get_usage_summary("t1", ResourceType.JOBS_PER_DAY)
        assert summaries[0].current_usage == 1

    def test_tenant_isolation(self, manager):
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 5)
        manager.record_usage("t2", ResourceType.JOBS_PER_DAY, 3)
        s1 = manager.get_usage_summary("t1", ResourceType.JOBS_PER_DAY)
        s2 = manager.get_usage_summary("t2", ResourceType.JOBS_PER_DAY)
        assert s1[0].current_usage == 5
        assert s2[0].current_usage == 3


# =============================================================================
# QuotaManager — Usage Summary
# =============================================================================


class TestQuotaManagerUsageSummary:
    def test_usage_summary_structure(self, manager):
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 3)
        summaries = manager.get_usage_summary("t1", ResourceType.JOBS_PER_DAY)
        assert len(summaries) == 1
        s = summaries[0]
        assert s.resource == ResourceType.JOBS_PER_DAY
        assert s.current_usage == 3
        assert s.limit == 10
        assert s.utilization_percent == 30.0
        assert s.remaining == 7

    def test_usage_summary_all_resources(self, manager):
        summaries = manager.get_usage_summary("t1")
        # Should have summaries for all resources configured in FREE tier
        assert len(summaries) > 0
        resource_types = [s.resource for s in summaries]
        assert ResourceType.JOBS_PER_DAY in resource_types

    def test_usage_summary_to_dict(self, manager):
        summaries = manager.get_usage_summary("t1", ResourceType.JOBS_PER_DAY)
        d = summaries[0].to_dict()
        assert "resource" in d
        assert "current_usage" in d
        assert "limit" in d
        assert "utilization_percent" in d
        assert "remaining" in d
        assert "period_start" in d
        assert "period_end" in d


# =============================================================================
# QuotaManager — Cleanup
# =============================================================================


class TestQuotaManagerCleanup:
    def test_cleanup_old_records(self, manager):
        # Add records with old timestamps
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 1)
        # Manually set timestamp to old
        manager._usage["t1"][0].timestamp = time.time() - (86400 * 8)

        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 1)  # Recent

        manager.cleanup_old_records(max_age_seconds=86400 * 7)
        assert len(manager._usage["t1"]) == 1

    def test_cleanup_preserves_recent(self, manager):
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 1)
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 1)
        manager.cleanup_old_records()
        assert len(manager._usage["t1"]) == 2


# =============================================================================
# QuotaManager — All Tenant Stats
# =============================================================================


class TestQuotaManagerAllStats:
    def test_get_all_tenant_stats(self, manager):
        manager.record_usage("t1", ResourceType.JOBS_PER_DAY, 5)
        manager.record_usage("t2", ResourceType.JOBS_PER_DAY, 3)
        stats = manager.get_all_tenant_stats()
        assert "t1" in stats
        assert "t2" in stats
        assert stats["t1"]["tier"] == "free"
        assert "resources" in stats["t1"]


# =============================================================================
# CostMetrics Tests
# =============================================================================


class TestCostMetrics:
    def test_creation(self):
        cm = CostMetrics(job_id="j1", tenant_id="t1")
        assert cm.job_id == "j1"
        assert cm.tenant_id == "t1"
        assert cm.start_time > 0

    def test_complete(self):
        cm = CostMetrics(job_id="j1", tenant_id="t1")
        time.sleep(0.01)
        cm.complete()
        assert cm.end_time > cm.start_time
        assert cm.duration_seconds > 0

    def test_to_dict(self):
        cm = CostMetrics(
            job_id="j1", tenant_id="t1",
            cpu_seconds=5.5, memory_mb_seconds=100.0,
            io_read_mb=10.0, io_write_mb=5.0,
        )
        cm.complete()
        d = cm.to_dict()
        assert d["job_id"] == "j1"
        assert d["cpu_seconds"] == 5.5
        assert d["memory_mb_seconds"] == 100.0


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    def test_set_tenant_tier_convenience(self):
        set_tenant_tier("conv_t1", QuotaTier.STARTER)
        manager = get_quota_manager()
        assert manager.get_tenant_tier("conv_t1") == QuotaTier.STARTER

    def test_check_quota_convenience(self):
        result = check_quota("conv_t2", ResourceType.JOBS_PER_DAY)
        assert result.allowed is True

    def test_record_usage_convenience(self):
        record_usage("conv_t3", ResourceType.JOBS_PER_DAY, 1)
        stats = get_usage_stats("conv_t3")
        assert len(stats) > 0

    def test_require_quota_within_limit(self):
        require_quota("conv_t4", ResourceType.JOBS_PER_DAY)

    def test_require_quota_exceeded(self):
        for _ in range(10):
            record_usage("conv_t5", ResourceType.JOBS_PER_DAY, 1)
        with pytest.raises(QuotaExceededException):
            require_quota("conv_t5", ResourceType.JOBS_PER_DAY)

    def test_quota_exceeded_exception_has_result(self):
        for _ in range(10):
            record_usage("conv_t6", ResourceType.JOBS_PER_DAY, 1)
        try:
            require_quota("conv_t6", ResourceType.JOBS_PER_DAY)
        except QuotaExceededException as e:
            assert e.result is not None
            assert e.result.allowed is False
            assert e.result.resource == ResourceType.JOBS_PER_DAY
