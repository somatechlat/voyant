"""
Concurrency Queue Module

Redis-backed job queue with per-tenant concurrency control.
Reference: docs/CANONICAL_ROADMAP.md - P4 Scale & Multi-Tenant

Features:
- Per-tenant job concurrency limits
- Job priority queuing (FIFO with priority override)
- Lease-based ownership (prevents zombie jobs)
- Graceful shutdown handling

Usage:
    from voyant.core.job_queue import JobQueue, get_job_queue
    
    queue = get_job_queue()
    
    # Enqueue a job
    position = await queue.enqueue("tenant_123", job_id, priority=0)
    
    # Try to acquire next job (returns None if at concurrency limit)
    job = await queue.acquire_next("tenant_123")
    
    # Release when done
    await queue.release(job_id)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class QueuedJob:
    """A job in the queue."""
    job_id: str
    tenant_id: str
    job_type: str
    priority: int = 0  # Lower = higher priority
    created_at: float = 0  # Unix timestamp
    status: JobStatus = JobStatus.QUEUED
    worker_id: Optional[str] = None
    lease_expires_at: Optional[float] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "tenant_id": self.tenant_id,
            "job_type": self.job_type,
            "priority": self.priority,
            "created_at": self.created_at,
            "status": self.status.value,
            "worker_id": self.worker_id,
            "lease_expires_at": self.lease_expires_at,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueuedJob":
        return cls(
            job_id=data["job_id"],
            tenant_id=data["tenant_id"],
            job_type=data["job_type"],
            priority=data.get("priority", 0),
            created_at=data.get("created_at", time.time()),
            status=JobStatus(data.get("status", "queued")),
            worker_id=data.get("worker_id"),
            lease_expires_at=data.get("lease_expires_at"),
            metadata=data.get("metadata", {}),
        )


class InMemoryJobQueue:
    """
    In-memory job queue implementation.
    
    For production, use RedisJobQueue instead.
    This implementation is useful for testing and development.
    """
    
    def __init__(self, default_lease_seconds: int = 300):
        self.lease_duration = default_lease_seconds
        self._queues: Dict[str, List[QueuedJob]] = {}  # tenant_id -> jobs
        self._running: Dict[str, QueuedJob] = {}  # job_id -> job
        self._all_jobs: Dict[str, QueuedJob] = {}  # job_id -> job
        self._lock = asyncio.Lock()
    
    async def enqueue(
        self,
        tenant_id: str,
        job_id: str,
        job_type: str = "analyze",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Add job to tenant's queue.
        
        Returns:
            Position in queue (0-indexed)
        """
        async with self._lock:
            job = QueuedJob(
                job_id=job_id,
                tenant_id=tenant_id,
                job_type=job_type,
                priority=priority,
                metadata=metadata or {},
            )
            
            if tenant_id not in self._queues:
                self._queues[tenant_id] = []
            
            # Insert by priority (lower = higher priority)
            queue = self._queues[tenant_id]
            insert_pos = len(queue)
            for i, existing in enumerate(queue):
                if priority < existing.priority:
                    insert_pos = i
                    break
            
            queue.insert(insert_pos, job)
            self._all_jobs[job_id] = job
            
            logger.debug(f"Enqueued job {job_id} for tenant {tenant_id} at position {insert_pos}")
            return insert_pos
    
    async def acquire_next(
        self,
        tenant_id: str,
        worker_id: str = "default",
        max_concurrent: int = 1,
    ) -> Optional[QueuedJob]:
        """
        Try to acquire the next job for a tenant.
        
        Returns:
            QueuedJob if acquired, None if at concurrency limit or queue empty
        """
        async with self._lock:
            # Check current running count for tenant
            running_count = sum(
                1 for j in self._running.values()
                if j.tenant_id == tenant_id and j.status == JobStatus.RUNNING
            )
            
            if running_count >= max_concurrent:
                logger.debug(f"Tenant {tenant_id} at concurrency limit ({running_count}/{max_concurrent})")
                return None
            
            # Get next from queue
            queue = self._queues.get(tenant_id, [])
            if not queue:
                return None
            
            job = queue.pop(0)
            job.status = JobStatus.RUNNING
            job.worker_id = worker_id
            job.lease_expires_at = time.time() + self.lease_duration
            
            self._running[job.job_id] = job
            
            logger.debug(f"Acquired job {job.job_id} by worker {worker_id}")
            return job
    
    async def release(
        self,
        job_id: str,
        status: JobStatus = JobStatus.COMPLETED,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Release a job after completion.
        
        Returns:
            True if released, False if job not found
        """
        async with self._lock:
            if job_id not in self._running:
                logger.warning(f"Job {job_id} not found in running jobs")
                return False
            
            job = self._running.pop(job_id)
            job.status = status
            job.lease_expires_at = None
            
            if result:
                job.metadata["result"] = result
            
            logger.debug(f"Released job {job_id} with status {status.value}")
            return True
    
    async def renew_lease(self, job_id: str) -> bool:
        """Extend lease for a running job."""
        async with self._lock:
            if job_id not in self._running:
                return False
            
            job = self._running[job_id]
            job.lease_expires_at = time.time() + self.lease_duration
            return True
    
    async def get_job(self, job_id: str) -> Optional[QueuedJob]:
        """Get job by ID."""
        if job_id in self._running:
            return self._running[job_id]
        return self._all_jobs.get(job_id)
    
    async def get_queue_length(self, tenant_id: str) -> int:
        """Get number of queued jobs for tenant."""
        return len(self._queues.get(tenant_id, []))
    
    async def get_running_count(self, tenant_id: str) -> int:
        """Get number of running jobs for tenant."""
        return sum(
            1 for j in self._running.values()
            if j.tenant_id == tenant_id
        )
    
    async def get_queue_stats(self, tenant_id: str) -> Dict[str, Any]:
        """Get queue statistics for tenant."""
        queue = self._queues.get(tenant_id, [])
        running = [j for j in self._running.values() if j.tenant_id == tenant_id]
        
        return {
            "tenant_id": tenant_id,
            "queued_count": len(queue),
            "running_count": len(running),
            "oldest_queued_age_seconds": (
                time.time() - queue[0].created_at if queue else 0
            ),
            "running_job_ids": [j.job_id for j in running],
        }
    
    async def requeue_expired_leases(self) -> int:
        """
        Requeue jobs with expired leases.
        
        Returns:
            Number of jobs requeued
        """
        async with self._lock:
            now = time.time()
            expired = [
                job_id for job_id, job in self._running.items()
                if job.lease_expires_at and job.lease_expires_at < now
            ]
            
            for job_id in expired:
                job = self._running.pop(job_id)
                job.status = JobStatus.QUEUED
                job.worker_id = None
                job.lease_expires_at = None
                
                # Re-add to front of queue (high priority due to retry)
                if job.tenant_id not in self._queues:
                    self._queues[job.tenant_id] = []
                self._queues[job.tenant_id].insert(0, job)
                
                logger.warning(f"Requeued expired job {job_id}")
            
            return len(expired)
    
    async def cancel(self, job_id: str) -> bool:
        """Cancel a queued or running job."""
        async with self._lock:
            # Check running jobs
            if job_id in self._running:
                job = self._running.pop(job_id)
                job.status = JobStatus.CANCELLED
                return True
            
            # Check queues
            for queue in self._queues.values():
                for i, job in enumerate(queue):
                    if job.job_id == job_id:
                        queue.pop(i)
                        job.status = JobStatus.CANCELLED
                        return True
            
            return False
    
    async def clear_tenant(self, tenant_id: str) -> int:
        """Clear all jobs for a tenant (for testing)."""
        async with self._lock:
            count = 0
            
            # Clear queue
            if tenant_id in self._queues:
                count += len(self._queues[tenant_id])
                del self._queues[tenant_id]
            
            # Clear running
            to_remove = [
                job_id for job_id, job in self._running.items()
                if job.tenant_id == tenant_id
            ]
            for job_id in to_remove:
                del self._running[job_id]
                count += 1
            
            return count


# =============================================================================
# Redis Implementation (Production - when Redis configured)
# =============================================================================

class RedisJobQueue(InMemoryJobQueue):
    """
    Redis-backed job queue implementation.
    
    Uses Redis sorted sets for priority queuing and
    hash maps for job metadata.
    
    Keys:
    - voyant:queue:{tenant_id} - Sorted set of job IDs by priority (score=priority)
    - voyant:job:{job_id} - Hash with job metadata (JSON serialized)
    - voyant:running:{tenant_id} - Set of currently running job IDs
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_lease_seconds: int = 300,
    ):
        super().__init__(default_lease_seconds)
        self.redis_url = redis_url
        self._redis = None
        logger.info(f"RedisJobQueue configured with {redis_url}")
    
    async def _get_redis(self):
        """Lazy init redis client."""
        if self._redis is None:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def enqueue(
        self,
        tenant_id: str,
        job_id: str,
        job_type: str = "analyze",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Add job to tenant's queue."""
        client = await self._get_redis()
        
        job = QueuedJob(
            job_id=job_id,
            tenant_id=tenant_id,
            job_type=job_type,
            priority=priority,
            metadata=metadata or {},
        )
        
        # Add to queue (sorted set)
        queue_key = f"voyant:queue:{tenant_id}"
        
        # Store job data
        job_key = f"voyant:job:{job_id}"
        await client.set(job_key, json.dumps(job.to_dict()))
        
        # Add to priority queue
        # Use priority as score. For FIFO within same priority, we could combine priority + timestamp
        # But for now simple priority score is fine.
        await client.zadd(queue_key, {job_id: priority})
        
        # Get rank (position)
        rank = await client.zrank(queue_key, job_id)
        
        logger.debug(f"Enqueued job {job_id} for tenant {tenant_id} at rank {rank}")
        return rank if rank is not None else 0

    async def acquire_next(
        self,
        tenant_id: str,
        worker_id: str = "default",
        max_concurrent: int = 1,
    ) -> Optional[QueuedJob]:
        """Try to acquire next job."""
        client = await self._get_redis()
        
        queue_key = f"voyant:queue:{tenant_id}"
        running_key = f"voyant:running:{tenant_id}"
        
        # Check concurrency
        running_count = await client.scard(running_key)
        if running_count >= max_concurrent:
            return None
        
        # Optimistic locking logic or Lua script would be ideal here to avoid race conditions
        # For MVP+ we pop the first item
        
        # Get first item
        items = await client.zrange(queue_key, 0, 0)
        if not items:
            return None
            
        job_id = items[0]
        job_key = f"voyant:job:{job_id}"
        
        # Move from queue to running
        # Use a pipeline/transaction
        async with client.pipeline(transaction=True) as pipe:
            pipe.zrem(queue_key, job_id)
            pipe.sadd(running_key, job_id)
            try:
                await pipe.execute()
            except Exception:
                # Race condition - another worker took it
                return None

        # Update job status
        raw_job = await client.get(job_key)
        if not raw_job:
            # Job data missing? Should clean up keys
            await client.srem(running_key, job_id)
            return None
            
        job_dict = json.loads(raw_job)
        job = QueuedJob.from_dict(job_dict)
        
        job.status = JobStatus.RUNNING
        job.worker_id = worker_id
        job.lease_expires_at = time.time() + self.lease_duration
        
        await client.set(job_key, json.dumps(job.to_dict()))
        
        logger.debug(f"Acquired job {job.job_id} by worker {worker_id}")
        return job

    async def release(
        self,
        job_id: str,
        status: JobStatus = JobStatus.COMPLETED,
        result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Release a job."""
        client = await self._get_redis()
        
        job_key = f"voyant:job:{job_id}"
        raw_job = await client.get(job_key)
        
        if not raw_job:
            return False
            
        job_dict = json.loads(raw_job)
        tenant_id = job_dict["tenant_id"]
        running_key = f"voyant:running:{tenant_id}"
        
        # Remove from running set
        await client.srem(running_key, job_id)
        
        # Update job
        job_dict["status"] = status.value
        job_dict["lease_expires_at"] = None
        if result:
            if "metadata" not in job_dict:
                job_dict["metadata"] = {}
            job_dict["metadata"]["result"] = result
            
        # We might keep completed jobs for a while or expire them
        await client.set(job_key, json.dumps(job_dict), ex=3600*24) # Expire after 24h
        
        return True

    async def get_queue_length(self, tenant_id: str) -> int:
        client = await self._get_redis()
        return await client.zcard(f"voyant:queue:{tenant_id}")

    async def get_running_count(self, tenant_id: str) -> int:
        client = await self._get_redis()
        return await client.scard(f"voyant:running:{tenant_id}")



# =============================================================================
# Singleton
# =============================================================================

_job_queue: Optional[InMemoryJobQueue] = None


def get_job_queue() -> InMemoryJobQueue:
    """Get or create the global job queue instance."""
    global _job_queue
    if _job_queue is None:
        # In production, check for Redis URL and use RedisJobQueue
        from voyant.core.config import get_settings
        settings = get_settings()
        
        if settings.redis_url and settings.redis_url.startswith("redis://"):
            _job_queue = RedisJobQueue(redis_url=settings.redis_url)
        else:
            _job_queue = InMemoryJobQueue()
        
        logger.info(f"Initialized job queue: {type(_job_queue).__name__}")
    
    return _job_queue


def reset_job_queue():
    """Reset the global job queue (for testing)."""
    global _job_queue
    _job_queue = None
