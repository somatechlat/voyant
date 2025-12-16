"""
Cost Metrics Module

Tracks resource consumption for billing and capacity planning.
Reference: docs/CANONICAL_ROADMAP.md - P4 Scale & Multi-Tenant

Metrics Tracked:
- CPU time per job
- Memory usage per job
- Artifact storage size
- Query execution time
- API request counts

Usage:
    from voyant.core.cost_metrics import (
        start_job_tracking, stop_job_tracking,
        get_job_costs, get_tenant_costs_summary
    )
    
    # Start tracking
    tracking = start_job_tracking(job_id, tenant_id)
    
    # ... do work ...
    
    # Stop and get costs
    costs = stop_job_tracking(job_id)
"""
from __future__ import annotations

import logging
import os
import time
import psutil
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class JobCostRecord:
    """Cost record for a single job."""
    job_id: str
    tenant_id: str
    job_type: str
    
    # Timing
    started_at: float = 0
    completed_at: float = 0
    duration_seconds: float = 0
    
    # Resources
    cpu_time_seconds: float = 0
    memory_peak_mb: float = 0
    artifact_size_bytes: int = 0
    
    # Operations
    query_count: int = 0
    query_time_seconds: float = 0
    api_requests: int = 0
    
    # Billing units (can be customized per tier)
    compute_units: float = 0
    storage_units: float = 0
    
    def __post_init__(self):
        if self.started_at == 0:
            self.started_at = time.time()
    
    def finalize(self):
        """Calculate derived metrics after job completion."""
        self.completed_at = time.time()
        self.duration_seconds = self.completed_at - self.started_at
        
        # Compute units: 1 unit = 1 second of CPU time
        self.compute_units = self.cpu_time_seconds
        
        # Storage units: 1 unit = 1 MB
        self.storage_units = self.artifact_size_bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "job_type": self.job_type,
            "started_at": datetime.fromtimestamp(self.started_at).isoformat() if self.started_at else None,
            "completed_at": datetime.fromtimestamp(self.completed_at).isoformat() if self.completed_at else None,
            "duration_seconds": round(self.duration_seconds, 3),
            "cpu_time_seconds": round(self.cpu_time_seconds, 3),
            "memory_peak_mb": round(self.memory_peak_mb, 2),
            "artifact_size_bytes": self.artifact_size_bytes,
            "query_count": self.query_count,
            "query_time_seconds": round(self.query_time_seconds, 3),
            "api_requests": self.api_requests,
            "compute_units": round(self.compute_units, 3),
            "storage_units": round(self.storage_units, 3),
        }


# =============================================================================
# In-Memory Storage (Replace with TimescaleDB in production)
# =============================================================================

_active_tracking: Dict[str, JobCostRecord] = {}
_completed_costs: Dict[str, JobCostRecord] = {}
_tenant_aggregates: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))


def start_job_tracking(
    job_id: str,
    tenant_id: str,
    job_type: str = "analyze",
) -> JobCostRecord:
    """
    Start tracking costs for a job.
    
    Returns:
        JobCostRecord for the job
    """
    record = JobCostRecord(
        job_id=job_id,
        tenant_id=tenant_id,
        job_type=job_type,
    )
    
    _active_tracking[job_id] = record
    logger.debug(f"Started cost tracking for job {job_id}")
    
    return record


def stop_job_tracking(job_id: str) -> Optional[JobCostRecord]:
    """
    Stop tracking and finalize costs for a job.
    
    Returns:
        Finalized JobCostRecord or None if not found
    """
    if job_id not in _active_tracking:
        logger.warning(f"Job {job_id} not found in active tracking")
        return None
    
    record = _active_tracking.pop(job_id)
    record.finalize()
    
    # Store completed record
    _completed_costs[job_id] = record
    
    # Aggregate for tenant
    tenant_id = record.tenant_id
    _tenant_aggregates[tenant_id]["total_compute_units"] += record.compute_units
    _tenant_aggregates[tenant_id]["total_storage_units"] += record.storage_units
    _tenant_aggregates[tenant_id]["total_jobs"] += 1
    _tenant_aggregates[tenant_id]["total_duration_seconds"] += record.duration_seconds
    
    logger.debug(f"Stopped cost tracking for job {job_id}: {record.compute_units:.2f} compute units")
    
    return record


def record_cpu_time(job_id: str, seconds: float):
    """Record CPU time for a job."""
    if job_id in _active_tracking:
        _active_tracking[job_id].cpu_time_seconds += seconds


def record_memory_peak(job_id: str, mb: float):
    """Record peak memory usage for a job."""
    if job_id in _active_tracking:
        current = _active_tracking[job_id].memory_peak_mb
        _active_tracking[job_id].memory_peak_mb = max(current, mb)


def record_artifact_size(job_id: str, size_bytes: int):
    """Record artifact storage size for a job."""
    if job_id in _active_tracking:
        _active_tracking[job_id].artifact_size_bytes += size_bytes


def record_query(job_id: str, duration_seconds: float):
    """Record a query execution for a job."""
    if job_id in _active_tracking:
        _active_tracking[job_id].query_count += 1
        _active_tracking[job_id].query_time_seconds += duration_seconds


def record_api_request(job_id: str):
    """Record an API request for a job."""
    if job_id in _active_tracking:
        _active_tracking[job_id].api_requests += 1


def get_current_process_metrics() -> Dict[str, float]:
    """Get current process resource metrics."""
    try:
        process = psutil.Process(os.getpid())
        return {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": process.memory_info().rss / (1024 * 1024),
            "threads": process.num_threads(),
        }
    except Exception as e:
        logger.warning(f"Failed to get process metrics: {e}")
        return {"cpu_percent": 0, "memory_mb": 0, "threads": 0}


# =============================================================================
# Query APIs
# =============================================================================

def get_job_costs(job_id: str) -> Optional[Dict[str, Any]]:
    """Get costs for a specific job."""
    if job_id in _completed_costs:
        return _completed_costs[job_id].to_dict()
    if job_id in _active_tracking:
        return _active_tracking[job_id].to_dict()
    return None


def get_tenant_costs_summary(
    tenant_id: str,
    since: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Get cost summary for a tenant."""
    aggregates = _tenant_aggregates.get(tenant_id, {})
    
    # Get recent jobs
    recent_jobs = [
        record for record in _completed_costs.values()
        if record.tenant_id == tenant_id
        and (since is None or record.completed_at >= since.timestamp())
    ]
    
    return {
        "tenant_id": tenant_id,
        "total_compute_units": aggregates.get("total_compute_units", 0),
        "total_storage_units": aggregates.get("total_storage_units", 0),
        "total_jobs": int(aggregates.get("total_jobs", 0)),
        "total_duration_seconds": aggregates.get("total_duration_seconds", 0),
        "recent_jobs_count": len(recent_jobs),
        "avg_compute_units_per_job": (
            aggregates.get("total_compute_units", 0) / max(1, aggregates.get("total_jobs", 1))
        ),
    }


def get_all_active_jobs() -> List[Dict[str, Any]]:
    """Get all currently active/tracked jobs."""
    return [record.to_dict() for record in _active_tracking.values()]


def reset_tenant_costs(tenant_id: str):
    """Reset cost data for a tenant (for testing)."""
    # Remove completed jobs for tenant
    to_remove = [
        job_id for job_id, record in _completed_costs.items()
        if record.tenant_id == tenant_id
    ]
    for job_id in to_remove:
        del _completed_costs[job_id]
    
    # Reset aggregates
    if tenant_id in _tenant_aggregates:
        del _tenant_aggregates[tenant_id]


def reset_all_costs():
    """Reset all cost data (for testing)."""
    _active_tracking.clear()
    _completed_costs.clear()
    _tenant_aggregates.clear()


# =============================================================================
# Billing Estimation
# =============================================================================

# Default pricing (can be customized per tier)
DEFAULT_PRICING = {
    "compute_unit_price": 0.001,  # $0.001 per compute unit (1 CPU-second)
    "storage_unit_price": 0.0001,  # $0.0001 per storage unit (1 MB)
}


def estimate_job_cost(job_id: str, pricing: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    Estimate cost for a job.
    
    Returns dict with estimated cost breakdown.
    """
    costs = get_job_costs(job_id)
    if not costs:
        return {"error": "Job not found"}
    
    pricing = pricing or DEFAULT_PRICING
    
    compute_cost = costs["compute_units"] * pricing["compute_unit_price"]
    storage_cost = costs["storage_units"] * pricing["storage_unit_price"]
    total_cost = compute_cost + storage_cost
    
    return {
        "job_id": job_id,
        "compute_cost": round(compute_cost, 6),
        "storage_cost": round(storage_cost, 6),
        "total_cost": round(total_cost, 6),
        "currency": "USD",
        "compute_units": costs["compute_units"],
        "storage_units": costs["storage_units"],
    }
