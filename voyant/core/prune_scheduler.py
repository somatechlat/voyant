"""
Prune Scheduler Module

Scheduled background pruning of old jobs and artifacts.
Reference: docs/CANONICAL_ROADMAP.md - P2 Operability

Features:
- Configurable prune interval (env-gated)
- Age-based artifact cleanup
- Quota-based artifact cleanup
- Async background task
- Graceful shutdown

Personas Applied:
- PhD Developer: Correct async patterns
- Analyst: Retention policy enforcement
- QA: Edge case handling
- ISO Documenter: Clear configuration
- Security: Safe deletion, audit logging
- Performance: Efficient batch operations
- UX: Clear logging

Usage:
    from voyant.core.prune_scheduler import (
        PruneScheduler, start_scheduler, stop_scheduler,
        prune_old_jobs, get_prune_stats
    )
    
    # Start the scheduler
    scheduler = start_scheduler()
    
    # Manual prune
    stats = await prune_old_jobs(max_age_days=7)
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PruneConfig:
    """Configuration for pruning."""
    enabled: bool = True
    interval_seconds: int = 3600           # 1 hour default
    max_job_age_days: int = 30             # Delete jobs older than this
    max_artifact_age_days: int = 30        # Delete artifacts older than this
    max_artifacts_per_tenant: int = 1000   # Per-tenant limit
    batch_size: int = 100                  # Delete in batches
    dry_run: bool = False                  # Log but don't delete


@dataclass
class PruneStats:
    """Statistics from a prune operation."""
    jobs_deleted: int = 0
    artifacts_deleted: int = 0
    bytes_freed: int = 0
    duration_seconds: float = 0
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "jobs_deleted": self.jobs_deleted,
            "artifacts_deleted": self.artifacts_deleted,
            "bytes_freed": self.bytes_freed,
            "bytes_freed_mb": round(self.bytes_freed / (1024 * 1024), 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "errors": self.errors,
            "timestamp": self.timestamp,
        }


# =============================================================================
# In-Memory Job/Artifact Store (Replace with real DB in production)
# =============================================================================

@dataclass
class JobRecord:
    """In-memory job record for pruning."""
    job_id: str
    tenant_id: str
    created_at: float  # Unix timestamp
    status: str
    artifact_paths: List[str] = field(default_factory=list)


# In-memory stores for development/testing (integrate with DuckDB in production)
_jobs: Dict[str, JobRecord] = {}
_artifacts: Dict[str, Dict[str, Any]] = {}  # artifact_key -> metadata


def _add_job(job: JobRecord):
    """Add job to store (for testing)."""
    _jobs[job.job_id] = job


def _add_artifact(key: str, metadata: Dict[str, Any]):
    """Add artifact to store (for testing)."""
    _artifacts[key] = metadata


def _clear_stores():
    """Clear stores (for testing)."""
    _jobs.clear()
    _artifacts.clear()


# =============================================================================
# Prune Operations
# =============================================================================

async def prune_old_jobs(
    max_age_days: int = 30,
    batch_size: int = 100,
    dry_run: bool = False,
) -> PruneStats:
    """
    Prune jobs older than max_age_days.
    
    Args:
        max_age_days: Maximum age in days
        batch_size: Delete in batches of this size
        dry_run: If True, log but don't delete
    
    Returns:
        PruneStats with deletion counts
    """
    start_time = time.time()
    stats = PruneStats()
    cutoff = time.time() - (max_age_days * 24 * 60 * 60)
    
    # Find old jobs
    old_job_ids = [
        job_id for job_id, job in _jobs.items()
        if job.created_at < cutoff
    ]
    
    if dry_run:
        logger.info(f"DRY RUN: Would delete {len(old_job_ids)} old jobs")
        stats.jobs_deleted = len(old_job_ids)
    else:
        # Delete in batches
        for i in range(0, len(old_job_ids), batch_size):
            batch = old_job_ids[i:i + batch_size]
            for job_id in batch:
                try:
                    job = _jobs.pop(job_id, None)
                    if job:
                        # Delete associated artifacts
                        for artifact_path in job.artifact_paths:
                            artifact_meta = _artifacts.pop(artifact_path, None)
                            if artifact_meta:
                                stats.artifacts_deleted += 1
                                stats.bytes_freed += artifact_meta.get("size_bytes", 0)
                        stats.jobs_deleted += 1
                except Exception as e:
                    stats.errors.append(f"Failed to delete job {job_id}: {str(e)}")
            
            # Yield to event loop between batches
            await asyncio.sleep(0)
    
    stats.duration_seconds = time.time() - start_time
    logger.info(f"Pruned {stats.jobs_deleted} jobs, freed {stats.bytes_freed} bytes")
    
    return stats


async def prune_by_quota(
    tenant_id: str,
    max_artifacts: int = 1000,
    dry_run: bool = False,
) -> PruneStats:
    """
    Prune old artifacts when tenant exceeds quota.
    
    Deletes oldest artifacts first until under quota.
    """
    start_time = time.time()
    stats = PruneStats()
    
    # Find tenant's artifacts
    tenant_artifacts = [
        (key, meta) for key, meta in _artifacts.items()
        if meta.get("tenant_id") == tenant_id
    ]
    
    if len(tenant_artifacts) <= max_artifacts:
        return stats
    
    # Sort by creation time (oldest first)
    tenant_artifacts.sort(key=lambda x: x[1].get("created_at", 0))
    
    # Delete oldest until under quota
    to_delete = len(tenant_artifacts) - max_artifacts
    
    if dry_run:
        logger.info(f"DRY RUN: Would delete {to_delete} artifacts for tenant {tenant_id}")
        stats.artifacts_deleted = to_delete
    else:
        for key, meta in tenant_artifacts[:to_delete]:
            try:
                del _artifacts[key]
                stats.artifacts_deleted += 1
                stats.bytes_freed += meta.get("size_bytes", 0)
            except Exception as e:
                stats.errors.append(f"Failed to delete artifact {key}: {str(e)}")
    
    stats.duration_seconds = time.time() - start_time
    return stats


# =============================================================================
# Scheduler
# =============================================================================

class PruneScheduler:
    """
    Background scheduler for periodic pruning.
    
    Runs as an async task and can be started/stopped gracefully.
    """
    
    def __init__(self, config: Optional[PruneConfig] = None):
        self.config = config or PruneConfig()
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_run: Optional[datetime] = None
        self._last_stats: Optional[PruneStats] = None
    
    async def start(self):
        """Start the scheduler."""
        if not self.config.enabled:
            logger.info("Prune scheduler disabled")
            return
        
        if self._running:
            logger.warning("Prune scheduler already running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(f"Prune scheduler started (interval: {self.config.interval_seconds}s)")
    
    async def stop(self):
        """Stop the scheduler gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Prune scheduler stopped")
    
    async def _run_loop(self):
        """Main scheduler loop."""
        while self._running:
            try:
                # Wait for interval
                await asyncio.sleep(self.config.interval_seconds)
                
                if not self._running:
                    break
                
                # Run prune
                await self._run_prune()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Prune scheduler error: {e}")
                # Continue running despite errors
    
    async def _run_prune(self):
        """Execute a prune cycle."""
        logger.info("Starting scheduled prune cycle")
        self._last_run = datetime.utcnow()
        
        try:
            stats = await prune_old_jobs(
                max_age_days=self.config.max_job_age_days,
                batch_size=self.config.batch_size,
                dry_run=self.config.dry_run,
            )
            self._last_stats = stats
            
            if stats.errors:
                logger.warning(f"Prune completed with {len(stats.errors)} errors")
            else:
                logger.info(f"Prune completed: {stats.jobs_deleted} jobs, {stats.artifacts_deleted} artifacts")
                
        except Exception as e:
            logger.exception(f"Prune cycle failed: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "enabled": self.config.enabled,
            "running": self._running,
            "interval_seconds": self.config.interval_seconds,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "last_stats": self._last_stats.to_dict() if self._last_stats else None,
        }


# =============================================================================
# Singleton
# =============================================================================

_scheduler: Optional[PruneScheduler] = None


def get_prune_config() -> PruneConfig:
    """Get prune configuration from environment."""
    import os
    
    return PruneConfig(
        enabled=os.getenv("VOYANT_PRUNE_ENABLED", "true").lower() == "true",
        interval_seconds=int(os.getenv("VOYANT_PRUNE_INTERVAL_SECONDS", "3600")),
        max_job_age_days=int(os.getenv("VOYANT_PRUNE_MAX_JOB_AGE_DAYS", "30")),
        max_artifact_age_days=int(os.getenv("VOYANT_PRUNE_MAX_ARTIFACT_AGE_DAYS", "30")),
        max_artifacts_per_tenant=int(os.getenv("VOYANT_PRUNE_MAX_ARTIFACTS_PER_TENANT", "1000")),
        dry_run=os.getenv("VOYANT_PRUNE_DRY_RUN", "false").lower() == "true",
    )


async def start_scheduler() -> PruneScheduler:
    """Start the global prune scheduler."""
    global _scheduler
    if _scheduler is None:
        config = get_prune_config()
        _scheduler = PruneScheduler(config)
    await _scheduler.start()
    return _scheduler


async def stop_scheduler():
    """Stop the global prune scheduler."""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()


def get_scheduler_status() -> Dict[str, Any]:
    """Get status of the global scheduler."""
    if _scheduler:
        return _scheduler.get_status()
    return {"enabled": False, "running": False}


def reset_scheduler():
    """Reset the scheduler (for testing)."""
    global _scheduler
    _scheduler = None
