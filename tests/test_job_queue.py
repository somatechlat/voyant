"""
Tests for Job Queue

Verifies job queue functionality including concurrency control and leases.
Reference: docs/CANONICAL_ROADMAP.md - P4 Scale & Multi-Tenant
"""
import pytest
import asyncio
import time

from voyant.core.job_queue import (
    InMemoryJobQueue,
    QueuedJob,
    JobStatus,
    get_job_queue,
    reset_job_queue,
)


@pytest.fixture
def queue():
    """Create a fresh queue for each test."""
    return InMemoryJobQueue(default_lease_seconds=10)


class TestEnqueue:
    """Test job enqueueing."""

    @pytest.mark.asyncio
    async def test_enqueue_returns_position(self, queue):
        """Should return position in queue."""
        pos = await queue.enqueue("tenant1", "job1")
        assert pos == 0
        
        pos = await queue.enqueue("tenant1", "job2")
        assert pos == 1

    @pytest.mark.asyncio
    async def test_enqueue_priority_ordering(self, queue):
        """Higher priority (lower number) should be placed earlier."""
        await queue.enqueue("tenant1", "job1", priority=10)
        await queue.enqueue("tenant1", "job2", priority=5)
        await queue.enqueue("tenant1", "job3", priority=1)
        
        # Acquire should return highest priority first
        job = await queue.acquire_next("tenant1", max_concurrent=10)
        assert job.job_id == "job3"  # Priority 1
        
        job = await queue.acquire_next("tenant1", max_concurrent=10)
        assert job.job_id == "job2"  # Priority 5

    @pytest.mark.asyncio
    async def test_enqueue_with_metadata(self, queue):
        """Should store metadata."""
        await queue.enqueue("tenant1", "job1", metadata={"key": "value"})
        
        job = await queue.get_job("job1")
        assert job.metadata["key"] == "value"


class TestAcquire:
    """Test job acquisition."""

    @pytest.mark.asyncio
    async def test_acquire_returns_job(self, queue):
        """Should return queued job."""
        await queue.enqueue("tenant1", "job1")
        
        job = await queue.acquire_next("tenant1")
        assert job is not None
        assert job.job_id == "job1"
        assert job.status == JobStatus.RUNNING

    @pytest.mark.asyncio
    async def test_acquire_empty_queue_returns_none(self, queue):
        """Should return None if queue is empty."""
        job = await queue.acquire_next("tenant1")
        assert job is None

    @pytest.mark.asyncio
    async def test_acquire_respects_concurrency_limit(self, queue):
        """Should return None if at concurrency limit."""
        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")
        
        # Acquire first job
        job1 = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job1 is not None
        
        # Try to acquire second - should fail due to limit
        job2 = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job2 is None

    @pytest.mark.asyncio
    async def test_acquire_sets_lease(self, queue):
        """Should set lease expiration time."""
        await queue.enqueue("tenant1", "job1")
        
        job = await queue.acquire_next("tenant1")
        assert job.lease_expires_at is not None
        assert job.lease_expires_at > time.time()


class TestRelease:
    """Test job release."""

    @pytest.mark.asyncio
    async def test_release_marks_completed(self, queue):
        """Should mark job as completed."""
        await queue.enqueue("tenant1", "job1")
        await queue.acquire_next("tenant1")
        
        result = await queue.release("job1", status=JobStatus.COMPLETED)
        assert result is True

    @pytest.mark.asyncio
    async def test_release_allows_next_acquisition(self, queue):
        """Releasing should allow next job to be acquired."""
        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")
        
        job1 = await queue.acquire_next("tenant1", max_concurrent=1)
        
        # Can't acquire second yet
        job2 = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job2 is None
        
        # Release first
        await queue.release("job1")
        
        # Now can acquire second
        job2 = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job2 is not None
        assert job2.job_id == "job2"

    @pytest.mark.asyncio
    async def test_release_nonexistent_returns_false(self, queue):
        """Should return False for unknown job."""
        result = await queue.release("nonexistent")
        assert result is False


class TestLeaseManagement:
    """Test lease renewal and expiration."""

    @pytest.mark.asyncio
    async def test_renew_lease_extends_time(self, queue):
        """Should extend lease expiration."""
        await queue.enqueue("tenant1", "job1")
        job = await queue.acquire_next("tenant1")
        original_expiry = job.lease_expires_at
        
        await asyncio.sleep(0.1)  # Small delay
        
        result = await queue.renew_lease("job1")
        assert result is True
        
        updated_job = await queue.get_job("job1")
        assert updated_job.lease_expires_at > original_expiry

    @pytest.mark.asyncio
    async def test_requeue_expired_leases(self, queue):
        """Should requeue jobs with expired leases."""
        # Create queue with very short lease
        short_queue = InMemoryJobQueue(default_lease_seconds=0)
        
        await short_queue.enqueue("tenant1", "job1")
        job = await short_queue.acquire_next("tenant1")
        
        # Wait for lease to expire
        await asyncio.sleep(0.1)
        
        # Requeue expired
        count = await short_queue.requeue_expired_leases()
        assert count == 1
        
        # Job should be back in queue
        assert await short_queue.get_queue_length("tenant1") == 1


class TestConcurrencyControl:
    """Test concurrency limits."""

    @pytest.mark.asyncio
    async def test_concurrent_limit_per_tenant(self, queue):
        """Each tenant has independent concurrency limits."""
        # Enqueue for both tenants
        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")
        await queue.enqueue("tenant2", "job3")
        await queue.enqueue("tenant2", "job4")
        
        # Acquire max for tenant1
        await queue.acquire_next("tenant1", max_concurrent=1)
        
        # Tenant2 should still work
        job = await queue.acquire_next("tenant2", max_concurrent=1)
        assert job is not None
        assert job.job_id == "job3"


class TestQueueStats:
    """Test queue statistics."""

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, queue):
        """Should return accurate stats."""
        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")
        await queue.acquire_next("tenant1", max_concurrent=5)
        
        stats = await queue.get_queue_stats("tenant1")
        assert stats["queued_count"] == 1
        assert stats["running_count"] == 1
        assert "job1" in stats["running_job_ids"]

    @pytest.mark.asyncio
    async def test_get_queue_length(self, queue):
        """Should return correct queue length."""
        assert await queue.get_queue_length("tenant1") == 0
        
        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")
        
        assert await queue.get_queue_length("tenant1") == 2


class TestCancel:
    """Test job cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, queue):
        """Should cancel queued job."""
        await queue.enqueue("tenant1", "job1")
        
        result = await queue.cancel("job1")
        assert result is True
        assert await queue.get_queue_length("tenant1") == 0

    @pytest.mark.asyncio
    async def test_cancel_running_job(self, queue):
        """Should cancel running job."""
        await queue.enqueue("tenant1", "job1")
        await queue.acquire_next("tenant1")
        
        result = await queue.cancel("job1")
        assert result is True
        assert await queue.get_running_count("tenant1") == 0


class TestSingleton:
    """Test global singleton."""

    def test_get_job_queue_returns_instance(self):
        """Should return queue instance."""
        reset_job_queue()
        queue = get_job_queue()
        assert queue is not None

    def test_get_job_queue_returns_same_instance(self):
        """Should return same instance on repeated calls."""
        reset_job_queue()
        queue1 = get_job_queue()
        queue2 = get_job_queue()
        assert queue1 is queue2
