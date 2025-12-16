"""
Tenant Quotas Module

Implements per-tenant resource limits and usage tracking.
Reference: docs/CANONICAL_ROADMAP.md - P4 Scale & Multi-Tenant

Quota Types:
- max_jobs_per_day: Maximum analyze jobs per tenant per day
- max_artifacts_gb: Maximum total artifact storage per tenant
- max_sources: Maximum data sources per tenant
- max_concurrent_jobs: Maximum concurrent jobs per tenant

Usage:
    from voyant.core.quotas import check_quota, record_usage, get_quota_status
    
    # Check before starting a job
    allowed, msg = await check_quota("tenant_123", "jobs_per_day")
    if not allowed:
        raise QuotaExceededException(msg)
    
    # Record usage after job completes
    await record_usage("tenant_123", "jobs_per_day")
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


# =============================================================================
# Quota Definitions
# =============================================================================

@dataclass
class QuotaTier:
    """Quota limits for a pricing tier."""
    name: str
    max_jobs_per_day: int
    max_artifacts_gb: float
    max_sources: int
    max_concurrent_jobs: int
    max_kpi_latency_seconds: int = 300  # Max execution time per KPI


# Default quota tiers
QUOTA_TIERS: Dict[str, QuotaTier] = {
    "free": QuotaTier(
        name="Free",
        max_jobs_per_day=10,
        max_artifacts_gb=1.0,
        max_sources=3,
        max_concurrent_jobs=1,
        max_kpi_latency_seconds=60,
    ),
    "starter": QuotaTier(
        name="Starter",
        max_jobs_per_day=100,
        max_artifacts_gb=10.0,
        max_sources=10,
        max_concurrent_jobs=3,
        max_kpi_latency_seconds=120,
    ),
    "professional": QuotaTier(
        name="Professional",
        max_jobs_per_day=1000,
        max_artifacts_gb=100.0,
        max_sources=50,
        max_concurrent_jobs=10,
        max_kpi_latency_seconds=300,
    ),
    "enterprise": QuotaTier(
        name="Enterprise",
        max_jobs_per_day=10000,
        max_artifacts_gb=1000.0,
        max_sources=500,
        max_concurrent_jobs=50,
        max_kpi_latency_seconds=600,
    ),
}

# Default tier for tenants without explicit assignment
DEFAULT_TIER = "free"


# =============================================================================
# Usage Tracking (In-Memory - Replace with Redis in production)
# =============================================================================

@dataclass
class TenantUsage:
    """Current usage for a tenant."""
    tenant_id: str
    tier: str = DEFAULT_TIER
    jobs_today: int = 0
    jobs_today_reset: datetime = field(default_factory=datetime.utcnow)
    artifacts_bytes: int = 0
    current_sources: int = 0
    concurrent_jobs: int = 0


# In-memory usage store (replace with Redis in production)
_usage_store: Dict[str, TenantUsage] = {}
# Tenant tier assignments (replace with database lookup)
_tenant_tiers: Dict[str, str] = {}


def _get_usage(tenant_id: str) -> TenantUsage:
    """Get or create usage record for tenant."""
    if tenant_id not in _usage_store:
        tier = _tenant_tiers.get(tenant_id, DEFAULT_TIER)
        _usage_store[tenant_id] = TenantUsage(tenant_id=tenant_id, tier=tier)
    return _usage_store[tenant_id]


def _reset_daily_if_needed(usage: TenantUsage) -> None:
    """Reset daily counters if day has changed."""
    now = datetime.utcnow()
    if now.date() > usage.jobs_today_reset.date():
        usage.jobs_today = 0
        usage.jobs_today_reset = now


# =============================================================================
# Public API
# =============================================================================

def set_tenant_tier(tenant_id: str, tier: str) -> None:
    """Set the quota tier for a tenant."""
    if tier not in QUOTA_TIERS:
        raise ValueError(f"Unknown tier: {tier}. Valid tiers: {list(QUOTA_TIERS.keys())}")
    
    _tenant_tiers[tenant_id] = tier
    if tenant_id in _usage_store:
        _usage_store[tenant_id].tier = tier
    
    logger.info(f"Set tenant {tenant_id} to tier {tier}")


def get_tenant_tier(tenant_id: str) -> str:
    """Get the quota tier for a tenant."""
    return _tenant_tiers.get(tenant_id, DEFAULT_TIER)


def get_quota_limits(tenant_id: str) -> Dict[str, Any]:
    """Get quota limits for a tenant."""
    tier = get_tenant_tier(tenant_id)
    quota = QUOTA_TIERS[tier]
    return {
        "tier": tier,
        "tier_name": quota.name,
        "max_jobs_per_day": quota.max_jobs_per_day,
        "max_artifacts_gb": quota.max_artifacts_gb,
        "max_sources": quota.max_sources,
        "max_concurrent_jobs": quota.max_concurrent_jobs,
        "max_kpi_latency_seconds": quota.max_kpi_latency_seconds,
    }


def get_usage_status(tenant_id: str) -> Dict[str, Any]:
    """Get current usage status for a tenant."""
    usage = _get_usage(tenant_id)
    _reset_daily_if_needed(usage)
    quota = QUOTA_TIERS[usage.tier]
    
    return {
        "tenant_id": tenant_id,
        "tier": usage.tier,
        "jobs_today": usage.jobs_today,
        "jobs_limit": quota.max_jobs_per_day,
        "jobs_remaining": max(0, quota.max_jobs_per_day - usage.jobs_today),
        "artifacts_gb": round(usage.artifacts_bytes / (1024 ** 3), 3),
        "artifacts_limit_gb": quota.max_artifacts_gb,
        "sources_count": usage.current_sources,
        "sources_limit": quota.max_sources,
        "concurrent_jobs": usage.concurrent_jobs,
        "concurrent_limit": quota.max_concurrent_jobs,
    }


def check_quota(tenant_id: str, quota_type: str) -> Tuple[bool, Optional[str]]:
    """
    Check if tenant can use a quota resource.
    
    Args:
        tenant_id: Tenant identifier
        quota_type: One of 'jobs_per_day', 'artifacts', 'sources', 'concurrent_jobs'
    
    Returns:
        Tuple of (allowed: bool, error_message: Optional[str])
    """
    usage = _get_usage(tenant_id)
    _reset_daily_if_needed(usage)
    quota = QUOTA_TIERS[usage.tier]
    
    if quota_type == "jobs_per_day":
        if usage.jobs_today >= quota.max_jobs_per_day:
            return False, f"Daily job quota exceeded ({usage.jobs_today}/{quota.max_jobs_per_day})"
    
    elif quota_type == "concurrent_jobs":
        if usage.concurrent_jobs >= quota.max_concurrent_jobs:
            return False, f"Concurrent job limit reached ({usage.concurrent_jobs}/{quota.max_concurrent_jobs})"
    
    elif quota_type == "sources":
        if usage.current_sources >= quota.max_sources:
            return False, f"Source limit reached ({usage.current_sources}/{quota.max_sources})"
    
    elif quota_type == "artifacts":
        max_bytes = int(quota.max_artifacts_gb * (1024 ** 3))
        if usage.artifacts_bytes >= max_bytes:
            return False, f"Artifact storage limit reached ({usage.artifacts_bytes / (1024**3):.2f}GB/{quota.max_artifacts_gb}GB)"
    
    else:
        logger.warning(f"Unknown quota type: {quota_type}")
    
    return True, None


def record_job_start(tenant_id: str) -> bool:
    """
    Record a job start. Returns True if allowed.
    """
    allowed, msg = check_quota(tenant_id, "jobs_per_day")
    if not allowed:
        return False
    
    allowed, msg = check_quota(tenant_id, "concurrent_jobs")
    if not allowed:
        return False
    
    usage = _get_usage(tenant_id)
    usage.jobs_today += 1
    usage.concurrent_jobs += 1
    
    logger.debug(f"Tenant {tenant_id}: job started (today: {usage.jobs_today}, concurrent: {usage.concurrent_jobs})")
    return True


def record_job_end(tenant_id: str) -> None:
    """Record a job completion."""
    usage = _get_usage(tenant_id)
    usage.concurrent_jobs = max(0, usage.concurrent_jobs - 1)
    logger.debug(f"Tenant {tenant_id}: job ended (concurrent: {usage.concurrent_jobs})")


def record_artifact_size(tenant_id: str, size_bytes: int) -> None:
    """Record artifact storage usage."""
    usage = _get_usage(tenant_id)
    usage.artifacts_bytes += size_bytes
    logger.debug(f"Tenant {tenant_id}: artifact size updated ({usage.artifacts_bytes} bytes)")


def record_source_added(tenant_id: str) -> bool:
    """Record a source being added. Returns True if allowed."""
    allowed, msg = check_quota(tenant_id, "sources")
    if not allowed:
        return False
    
    usage = _get_usage(tenant_id)
    usage.current_sources += 1
    return True


def record_source_removed(tenant_id: str) -> None:
    """Record a source being removed."""
    usage = _get_usage(tenant_id)
    usage.current_sources = max(0, usage.current_sources - 1)


def reset_tenant_usage(tenant_id: str) -> None:
    """Reset all usage for a tenant (for testing)."""
    if tenant_id in _usage_store:
        tier = _usage_store[tenant_id].tier
        _usage_store[tenant_id] = TenantUsage(tenant_id=tenant_id, tier=tier)


def list_tiers() -> Dict[str, Dict[str, Any]]:
    """List all available quota tiers."""
    return {
        name: {
            "name": tier.name,
            "max_jobs_per_day": tier.max_jobs_per_day,
            "max_artifacts_gb": tier.max_artifacts_gb,
            "max_sources": tier.max_sources,
            "max_concurrent_jobs": tier.max_concurrent_jobs,
        }
        for name, tier in QUOTA_TIERS.items()
    }
