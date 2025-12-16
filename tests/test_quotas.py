"""
Tests for Tenant Quotas

Verifies quota tiers, usage tracking, and limit enforcement.
Reference: docs/CANONICAL_ROADMAP.md - P4 Scale & Multi-Tenant
"""
import pytest

from voyant.core.quotas import (
    QUOTA_TIERS,
    DEFAULT_TIER,
    set_tenant_tier,
    get_tenant_tier,
    get_quota_limits,
    get_usage_status,
    check_quota,
    record_job_start,
    record_job_end,
    record_artifact_size,
    record_source_added,
    record_source_removed,
    reset_tenant_usage,
    list_tiers,
)


class TestQuotaTiers:
    """Test quota tier definitions."""

    def test_four_tiers_exist(self):
        """Should have 4 default tiers."""
        assert len(QUOTA_TIERS) == 4
        assert "free" in QUOTA_TIERS
        assert "starter" in QUOTA_TIERS
        assert "professional" in QUOTA_TIERS
        assert "enterprise" in QUOTA_TIERS

    def test_default_tier_is_free(self):
        """Default tier should be free."""
        assert DEFAULT_TIER == "free"

    def test_tier_limits_increase(self):
        """Higher tiers should have higher limits."""
        free = QUOTA_TIERS["free"]
        starter = QUOTA_TIERS["starter"]
        professional = QUOTA_TIERS["professional"]
        enterprise = QUOTA_TIERS["enterprise"]
        
        assert free.max_jobs_per_day < starter.max_jobs_per_day
        assert starter.max_jobs_per_day < professional.max_jobs_per_day
        assert professional.max_jobs_per_day < enterprise.max_jobs_per_day

    def test_list_tiers(self):
        """Should list all tiers with limits."""
        tiers = list_tiers()
        assert len(tiers) == 4
        for tier_data in tiers.values():
            assert "max_jobs_per_day" in tier_data
            assert "max_artifacts_gb" in tier_data


class TestTenantTierAssignment:
    """Test tenant tier assignment."""

    def setup_method(self):
        """Reset state before each test."""
        reset_tenant_usage("test_tenant")

    def test_new_tenant_gets_default_tier(self):
        """New tenants should get free tier."""
        tier = get_tenant_tier("new_tenant_xyz")
        assert tier == "free"

    def test_set_tenant_tier(self):
        """Should be able to set tenant tier."""
        set_tenant_tier("test_tenant", "professional")
        assert get_tenant_tier("test_tenant") == "professional"

    def test_invalid_tier_raises_error(self):
        """Setting invalid tier should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            set_tenant_tier("test_tenant", "invalid_tier")
        assert "Unknown tier" in str(exc_info.value)

    def test_get_quota_limits(self):
        """Should return limits for tenant's tier."""
        set_tenant_tier("test_tenant", "starter")
        limits = get_quota_limits("test_tenant")
        
        assert limits["tier"] == "starter"
        assert limits["max_jobs_per_day"] == 100
        assert limits["max_sources"] == 10


class TestUsageTracking:
    """Test usage tracking."""

    def setup_method(self):
        """Reset state before each test."""
        reset_tenant_usage("test_tenant")
        set_tenant_tier("test_tenant", "free")

    def test_initial_usage_is_zero(self):
        """New tenant should have zero usage."""
        reset_tenant_usage("test_tenant")
        status = get_usage_status("test_tenant")
        
        assert status["jobs_today"] == 0
        assert status["artifacts_gb"] == 0
        assert status["sources_count"] == 0
        assert status["concurrent_jobs"] == 0

    def test_record_job_start_increments_counters(self):
        """Starting a job should increment counters."""
        reset_tenant_usage("test_tenant")
        result = record_job_start("test_tenant")
        
        assert result is True
        status = get_usage_status("test_tenant")
        assert status["jobs_today"] == 1
        assert status["concurrent_jobs"] == 1

    def test_record_job_end_decrements_concurrent(self):
        """Ending a job should decrement concurrent counter."""
        reset_tenant_usage("test_tenant")
        record_job_start("test_tenant")
        record_job_end("test_tenant")
        
        status = get_usage_status("test_tenant")
        assert status["jobs_today"] == 1  # Still counted
        assert status["concurrent_jobs"] == 0  # Decremented

    def test_record_artifact_size(self):
        """Should track artifact storage."""
        reset_tenant_usage("test_tenant")
        record_artifact_size("test_tenant", 1024 * 1024 * 100)  # 100 MB
        
        status = get_usage_status("test_tenant")
        assert status["artifacts_gb"] > 0


class TestQuotaEnforcement:
    """Test quota limit enforcement."""

    def setup_method(self):
        """Reset state before each test."""
        reset_tenant_usage("test_tenant")
        set_tenant_tier("test_tenant", "free")  # Low limits for testing

    def test_jobs_quota_allows_under_limit(self):
        """Should allow jobs under limit."""
        reset_tenant_usage("test_tenant")
        allowed, msg = check_quota("test_tenant", "jobs_per_day")
        assert allowed is True
        assert msg is None

    def test_jobs_quota_blocks_over_limit(self):
        """Should block jobs over limit."""
        reset_tenant_usage("test_tenant")
        # Exhaust quota (free tier = 10 jobs)
        for _ in range(10):
            record_job_start("test_tenant")
            record_job_end("test_tenant")
        
        allowed, msg = check_quota("test_tenant", "jobs_per_day")
        assert allowed is False
        assert "exceeded" in msg.lower()

    def test_concurrent_jobs_limit(self):
        """Should enforce concurrent job limit."""
        reset_tenant_usage("test_tenant")
        # Start max concurrent (free tier = 1)
        result = record_job_start("test_tenant")
        assert result is True
        
        # Try to start another - should fail
        result = record_job_start("test_tenant")
        assert result is False

    def test_source_limit_enforcement(self):
        """Should enforce source limit."""
        reset_tenant_usage("test_tenant")
        # Free tier = 3 sources
        for i in range(3):
            result = record_source_added("test_tenant")
            assert result is True
        
        # 4th source should fail
        result = record_source_added("test_tenant")
        assert result is False

    def test_source_removal_frees_quota(self):
        """Removing source should free quota."""
        reset_tenant_usage("test_tenant")
        for i in range(3):
            record_source_added("test_tenant")
        
        record_source_removed("test_tenant")
        
        # Should now be able to add another
        result = record_source_added("test_tenant")
        assert result is True


class TestUpgradePath:
    """Test tier upgrades."""

    def setup_method(self):
        """Reset state before each test."""
        reset_tenant_usage("test_tenant")

    def test_upgrade_increases_limits(self):
        """Upgrading tier should increase limits."""
        set_tenant_tier("test_tenant", "free")
        free_limits = get_quota_limits("test_tenant")
        
        set_tenant_tier("test_tenant", "professional")
        pro_limits = get_quota_limits("test_tenant")
        
        assert pro_limits["max_jobs_per_day"] > free_limits["max_jobs_per_day"]

    def test_upgrade_releases_blocked_operations(self):
        """Upgrading should allow previously blocked operations."""
        reset_tenant_usage("test_tenant")
        set_tenant_tier("test_tenant", "free")
        
        # Exhaust free tier concurrent limit (1)
        record_job_start("test_tenant")
        result = record_job_start("test_tenant")
        assert result is False
        
        record_job_end("test_tenant")
        
        # Upgrade to starter (3 concurrent)
        set_tenant_tier("test_tenant", "starter")
        
        # Should now be able to start more jobs
        result = record_job_start("test_tenant")
        assert result is True
