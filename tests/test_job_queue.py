"""
Tests for Job Queue Functionality.

This module contains comprehensive tests for the `InMemoryJobQueue`
implementation, which manages asynchronous job processing within the Voyant
platform. It verifies core functionalities such as:
- Enqueueing jobs with priority.
- Acquiring jobs with concurrency limits and lease management.
- Releasing jobs upon completion or failure.
- Renewing and managing job leases.
- Cancelling jobs.
- Providing queue statistics.

These tests ensure the reliability and scalability of the background job
processing system.

Reference: docs/CANONICAL_ROADMAP.md - P4 Scale & Multi-Tenant
"""

import asyncio
import time
from typing import Any, Dict, List

import pytest

from voyant.core.job_queue import (
    InMemoryJobQueue,
    JobStatus,
    QueuedJob,
    get_job_queue,
    reset_job_queue,
)


@pytest.fixture
def queue() -> InMemoryJobQueue:
    """
    Pytest fixture that provides a fresh `InMemoryJobQueue` instance for each test.

    This ensures test isolation and a consistent state for job queue operations.
    """
    reset_job_queue()  # Clear any global instance for clean slate.
    return InMemoryJobQueue(default_lease_seconds=0.1) # Use short lease for lease management tests.


class TestEnqueue:
    """
    Tests for the job enqueueing mechanism of the `InMemoryJobQueue`.

    Verifies correct job placement, priority handling, and metadata storage.
    """

    @pytest.mark.asyncio
    async def test_enqueue_returns_position(self, queue: InMemoryJobQueue):
        """
        Verifies that `enqueue` correctly returns the job's position in the queue.
        """
        pos = await queue.enqueue("tenant1", "job1")
        assert pos == 0

        pos = await queue.enqueue("tenant1", "job2")
        assert pos == 1

    @pytest.mark.asyncio
    async def test_enqueue_priority_ordering(self, queue: InMemoryJobQueue):
        """
        Ensures that jobs with higher priority (lower priority number) are
        placed and acquired earlier than lower priority jobs.
        """
        await queue.enqueue("tenant1", "job1", priority=10)
        await queue.enqueue("tenant1", "job2", priority=5)
        await queue.enqueue("tenant1", "job3", priority=1)

        # Acquire should return the highest priority job first.
        job = await queue.acquire_next("tenant1", max_concurrent=10)
        assert job is not None
        assert job.job_id == "job3"  # Priority 1.

        job = await queue.acquire_next("tenant1", max_concurrent=10)
        assert job is not None
        assert job.job_id == "job2"  # Priority 5.

    @pytest.mark.asyncio
    async def test_enqueue_with_metadata(self, queue: InMemoryJobQueue):
        """
        Verifies that `enqueue` correctly stores and retrieves associated job metadata.
        """
        await queue.enqueue("tenant1", "job1", metadata={"key": "value", "user": "test_user"})

        job = await queue.get_job("job1")
        assert job is not None
        assert job.metadata["key"] == "value"
        assert job.metadata["user"] == "test_user"


class TestAcquire:
    """
    Tests for the job acquisition mechanism of the `InMemoryJobQueue`.

    Verifies correct job retrieval, status changes, and adherence to concurrency limits.
    """

    @pytest.mark.asyncio
    async def test_acquire_returns_job(self, queue: InMemoryJobQueue):
        """
        Ensures that `acquire_next` successfully retrieves a queued job
        and updates its status to `RUNNING`.
        """
        await queue.enqueue("tenant1", "job1")

        job = await queue.acquire_next("tenant1")
        assert job is not None
        assert job.job_id == "job1"
        assert job.status == JobStatus.RUNNING

    @pytest.mark.asyncio
    async def test_acquire_empty_queue_returns_none(self, queue: InMemoryJobQueue):
        """
        Verifies that `acquire_next` returns None when the queue is empty.
        """
        job = await queue.acquire_next("tenant1")
        assert job is None

    @pytest.mark.asyncio
    async def test_acquire_respects_concurrency_limit(self, queue: InMemoryJobQueue):
        """
        Tests that `acquire_next` respects the maximum concurrency limit
        for a given tenant, preventing more jobs from being acquired than allowed.
        """
        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")

        # Acquire the first job, reaching the concurrency limit of 1.
        job1 = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job1 is not None
        assert job1.job_id == "job1"

        # Attempt to acquire the second job; it should fail due to the limit.
        job2 = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job2 is None

    @pytest.mark.asyncio
    async def test_acquire_sets_lease(self, queue: InMemoryJobQueue):
        """
        Verifies that `acquire_next` correctly sets a lease expiration time for the acquired job.
        """
        await queue.enqueue("tenant1", "job1")

        job = await queue.acquire_next("tenant1")
        assert job is not None
        assert job.lease_expires_at is not None
        # Ensure the lease expiration is in the future.
        assert job.lease_expires_at > time.time()


class TestRelease:
    """
    Tests for the job release mechanism of the `InMemoryJobQueue`.

    Verifies that jobs can be marked as completed/failed and that releasing
    a job frees up concurrency slots.
    """

    @pytest.mark.asyncio
    async def test_release_marks_completed(self, queue: InMemoryJobQueue):
        """
        Ensures that `release` correctly updates a job's status to `COMPLETED`.
        """
        await queue.enqueue("tenant1", "job1")
        await queue.acquire_next("tenant1")

        result = await queue.release("job1", status=JobStatus.COMPLETED)
        assert result is True

        job = await queue.get_job("job1")
        assert job is not None
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_release_allows_next_acquisition(self, queue: InMemoryJobQueue):
        """
        Verifies that releasing a running job allows another job for the same
        tenant to be acquired, respecting concurrency limits.
        """
        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")

        job1 = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job1 is not None

        # Cannot acquire the second job yet due to concurrency limit.
        job2_attempt = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job2_attempt is None

        # Release the first job.
        await queue.release("job1", status=JobStatus.COMPLETED)

        # Now, the second job should be acquirable.
        job2 = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job2 is not None
        assert job2.job_id == "job2"

    @pytest.mark.asyncio
    async def test_release_nonexistent_returns_false(self, queue: InMemoryJobQueue):
        """
        Ensures that `release` returns False when attempting to release an unknown job.
        """
        result = await queue.release("nonexistent_job_id")
        assert result is False


class TestLeaseManagement:
    """
    Tests for lease renewal and expiration functionalities within the `InMemoryJobQueue`.
    """

    @pytest.mark.asyncio
    async def test_renew_lease_extends_time(self, queue: InMemoryJobQueue):
        """
        Verifies that `renew_lease` successfully extends a job's lease expiration time.
        """
        await queue.enqueue("tenant1", "job1")
        job = await queue.acquire_next("tenant1")
        assert job is not None
        original_expiry = job.lease_expires_at

        await asyncio.sleep(0.05)  # Simulate some work time within the lease.

        result = await queue.renew_lease("job1")
        assert result is True

        updated_job = await queue.get_job("job1")
        assert updated_job is not None
        assert updated_job.lease_expires_at > original_expiry

    @pytest.mark.asyncio
    async def test_requeue_expired_leases(self):
        """
        Ensures that `requeue_expired_leases` correctly identifies and requeues
        jobs whose leases have expired.
        """
        # Use a queue with a very short lease duration for testing expiration.
        short_queue = InMemoryJobQueue(default_lease_seconds=0.001)

        await short_queue.enqueue("tenant1", "job1")
        job = await short_queue.acquire_next("tenant1", max_concurrent=1)
        assert job is not None
        assert job.job_id == "job1"
        assert job.status == JobStatus.RUNNING

        # Wait for the lease to expire.
        await asyncio.sleep(0.002)

        # Requeue expired jobs.
        count = await short_queue.requeue_expired_leases()
        assert count == 1

        # The job should now be back in the queue and running count should be 0.
        assert await short_queue.get_queue_length("tenant1") == 1
        assert await short_queue.get_running_count("tenant1") == 0


class TestConcurrencyControl:
    """
    Tests for the concurrency limit enforcement mechanism of the `InMemoryJobQueue`.
    """

    @pytest.mark.asyncio
    async def test_concurrent_limit_per_tenant(self, queue: InMemoryJobQueue):
        """
        Verifies that each tenant has independent concurrency limits,
        allowing one tenant to acquire jobs even if another is at its limit.
        """
        # Enqueue jobs for two different tenants.
        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")
        await queue.enqueue("tenant2", "job3")
        await queue.enqueue("tenant2", "job4")

        # Acquire max for tenant1 (limit=1).
        job_t1_1 = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job_t1_1 is not None
        assert job_t1_1.job_id == "job1"

        # Tenant2 should still be able to acquire a job, respecting its own limit.
        job_t2_1 = await queue.acquire_next("tenant2", max_concurrent=1)
        assert job_t2_1 is not None
        assert job_t2_1.job_id == "job3"

        # Tenant1 cannot acquire another job.
        job_t1_2_attempt = await queue.acquire_next("tenant1", max_concurrent=1)
        assert job_t1_2_attempt is None


class TestQueueStats:
    """
    Tests for the queue statistics retrieval functions (`get_queue_stats`, `get_queue_length`).
    """

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, queue: InMemoryJobQueue):
        """
        Verifies that `get_queue_stats` returns accurate counts for queued and running jobs,
        and lists the IDs of running jobs.
        """
        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")
        await queue.acquire_next("tenant1", max_concurrent=5)  # job1 is now running.

        stats = await queue.get_queue_stats("tenant1")
        assert stats["queued_count"] == 1  # job2 is queued.
        assert stats["running_count"] == 1  # job1 is running.
        assert "job1" in stats["running_job_ids"]

    @pytest.mark.asyncio
    async def test_get_queue_length(self, queue: InMemoryJobQueue):
        """
        Verifies that `get_queue_length` returns the correct number of
        jobs currently awaiting processing in the queue.
        """
        assert await queue.get_queue_length("tenant1") == 0

        await queue.enqueue("tenant1", "job1")
        await queue.enqueue("tenant1", "job2")

        assert await queue.get_queue_length("tenant1") == 2


class TestCancel:
    """
    Tests for the job cancellation functionality of the `InMemoryJobQueue`.
    """

    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, queue: InMemoryJobQueue):
        """
        Verifies that a job in the `QUEUED` state can be successfully cancelled.
        """
        await queue.enqueue("tenant1", "job1")

        result = await queue.cancel("job1")
        assert result is True
        assert await queue.get_job("job1") is None  # Cancelled job should be removed.
        assert await queue.get_queue_length("tenant1") == 0

    @pytest.mark.asyncio
    async def test_cancel_running_job(self, queue: InMemoryJobQueue):
        """
        Verifies that a job in the `RUNNING` state can be successfully cancelled.
        """
        await queue.enqueue("tenant1", "job1")
        await queue.acquire_next("tenant1")

        result = await queue.cancel("job1")
        assert result is True
        assert await queue.get_job("job1") is None  # Cancelled job should be removed.
        assert await queue.get_running_count("tenant1") == 0


class TestSingleton:
    """
    Tests for the singleton pattern implementation of the global job queue.
    """

    def test_get_job_queue_returns_instance(self):
        """
        Verifies that `get_job_queue()` successfully returns an instance
        of `InMemoryJobQueue`.
        """
        reset_job_queue()  # Ensure a fresh state.
        queue = get_job_queue()
        assert isinstance(queue, InMemoryJobQueue)

    def test_get_job_queue_returns_same_instance(self):
        """
        Ensures that repeated calls to `get_job_queue()` return the exact same
        instance, confirming the singleton behavior.
        """
        reset_job_queue()  # Ensure a fresh state.
        queue1 = get_job_queue()
        queue2 = get_job_queue()
        assert queue1 is queue2
