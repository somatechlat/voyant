"""
Unit tests for apps.core.lib.job_queue — In-memory job queue with concurrency control.

Real in-memory queue. No mocks, no external services.
"""

import asyncio

import pytest

from apps.core.lib.job_queue import (
    InMemoryJobQueue,
    JobStatus,
    QueuedJob,
)


@pytest.fixture
def queue():
    return InMemoryJobQueue(default_lease_seconds=300)


# =============================================================================
# QueuedJob Tests
# =============================================================================


class TestQueuedJob:
    def test_creation(self):
        job = QueuedJob(
            job_id="j1", tenant_id="t1", job_type="analyze",
        )
        assert job.job_id == "j1"
        assert job.tenant_id == "t1"
        assert job.job_type == "analyze"
        assert job.priority == 0
        assert job.status == JobStatus.QUEUED
        assert job.created_at > 0
        assert job.metadata == {}

    def test_to_dict(self):
        job = QueuedJob(job_id="j1", tenant_id="t1", job_type="analyze")
        d = job.to_dict()
        assert d["job_id"] == "j1"
        assert d["tenant_id"] == "t1"
        assert d["status"] == "queued"
        assert d["priority"] == 0

    def test_from_dict_roundtrip(self):
        job = QueuedJob(
            job_id="j1", tenant_id="t1", job_type="analyze",
            priority=5, metadata={"key": "val"},
        )
        d = job.to_dict()
        restored = QueuedJob.from_dict(d)
        assert restored.job_id == job.job_id
        assert restored.tenant_id == job.tenant_id
        assert restored.priority == job.priority
        assert restored.metadata == job.metadata

    def test_from_dict_defaults(self):
        d = {"job_id": "j1", "tenant_id": "t1", "job_type": "analyze"}
        job = QueuedJob.from_dict(d)
        assert job.priority == 0
        assert job.status == JobStatus.QUEUED


# =============================================================================
# InMemoryJobQueue — Enqueue & Acquire
# =============================================================================


class TestJobQueueEnqueueAcquire:
    @pytest.mark.asyncio
    async def test_enqueue_and_acquire(self, queue):
        pos = await queue.enqueue("t1", "j1", "analyze")
        assert pos == 0

        job = await queue.acquire_next("t1")
        assert job is not None
        assert job.job_id == "j1"
        assert job.status == JobStatus.RUNNING
        assert job.worker_id == "default"
        assert job.lease_expires_at is not None

    @pytest.mark.asyncio
    async def test_enqueue_multiple_priority_ordering(self, queue):
        await queue.enqueue("t1", "j_low", "analyze", priority=10)
        await queue.enqueue("t1", "j_high", "analyze", priority=1)
        await queue.enqueue("t1", "j_mid", "analyze", priority=5)

        # Use high concurrency to acquire all without releasing
        job1 = await queue.acquire_next("t1", max_concurrent=10)
        assert job1.job_id == "j_high"
        job2 = await queue.acquire_next("t1", max_concurrent=10)
        assert job2.job_id == "j_mid"
        job3 = await queue.acquire_next("t1", max_concurrent=10)
        assert job3.job_id == "j_low"

    @pytest.mark.asyncio
    async def test_acquire_empty_queue(self, queue):
        job = await queue.acquire_next("t1")
        assert job is None

    @pytest.mark.asyncio
    async def test_concurrency_limit(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.enqueue("t1", "j2", "analyze")

        job1 = await queue.acquire_next("t1", max_concurrent=1)
        assert job1 is not None

        job2 = await queue.acquire_next("t1", max_concurrent=1)
        assert job2 is None

    @pytest.mark.asyncio
    async def test_concurrency_limit_allows_after_release(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.enqueue("t1", "j2", "analyze")

        job1 = await queue.acquire_next("t1", max_concurrent=1)
        assert job1 is not None

        await queue.release("j1", JobStatus.COMPLETED)

        job2 = await queue.acquire_next("t1", max_concurrent=1)
        assert job2 is not None
        assert job2.job_id == "j2"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.enqueue("t2", "j2", "analyze")

        job_t1 = await queue.acquire_next("t1")
        assert job_t1.job_id == "j1"

        job_t2 = await queue.acquire_next("t2")
        assert job_t2.job_id == "j2"

    @pytest.mark.asyncio
    async def test_worker_id(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        job = await queue.acquire_next("t1", worker_id="worker-42")
        assert job.worker_id == "worker-42"


# =============================================================================
# InMemoryJobQueue — Release
# =============================================================================


class TestJobQueueRelease:
    @pytest.mark.asyncio
    async def test_release_completed(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.acquire_next("t1")

        result = await queue.release("j1", JobStatus.COMPLETED)
        assert result is True

        job = await queue.get_job("j1")
        assert job.status == JobStatus.COMPLETED
        assert job.lease_expires_at is None

    @pytest.mark.asyncio
    async def test_release_with_result(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.acquire_next("t1")

        await queue.release("j1", JobStatus.COMPLETED, result={"output": "done"})
        job = await queue.get_job("j1")
        assert job.metadata["result"] == {"output": "done"}

    @pytest.mark.asyncio
    async def test_release_failed(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.acquire_next("t1")

        result = await queue.release("j1", JobStatus.FAILED)
        assert result is True

        job = await queue.get_job("j1")
        assert job.status == JobStatus.FAILED

    @pytest.mark.asyncio
    async def test_release_nonexistent(self, queue):
        result = await queue.release("nonexistent")
        assert result is False


# =============================================================================
# InMemoryJobQueue — Lease Management
# =============================================================================


class TestJobQueueLease:
    @pytest.mark.asyncio
    async def test_renew_lease(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        job = await queue.acquire_next("t1")
        old_expiry = job.lease_expires_at

        result = await queue.renew_lease("j1")
        assert result is True

        job = await queue.get_job("j1")
        assert job.lease_expires_at >= old_expiry

    @pytest.mark.asyncio
    async def test_renew_lease_nonexistent(self, queue):
        result = await queue.renew_lease("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_requeue_expired_leases(self, queue):
        queue.lease_duration = 0  # Immediate expiry
        await queue.enqueue("t1", "j1", "analyze")
        await queue.acquire_next("t1")

        # Wait a tiny bit for lease to expire
        await asyncio.sleep(0.01)

        requeued = await queue.requeue_expired_leases()
        assert requeued == 1

        # Job should be back in queue
        length = await queue.get_queue_length("t1")
        assert length == 1

        # Should be acquirable again
        job = await queue.acquire_next("t1")
        assert job is not None
        assert job.job_id == "j1"

    @pytest.mark.asyncio
    async def test_requeue_no_expired(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.acquire_next("t1")

        requeued = await queue.requeue_expired_leases()
        assert requeued == 0


# =============================================================================
# InMemoryJobQueue — Cancel
# =============================================================================


class TestJobQueueCancel:
    @pytest.mark.asyncio
    async def test_cancel_queued_job(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        result = await queue.cancel("j1")
        assert result is True

        length = await queue.get_queue_length("t1")
        assert length == 0

    @pytest.mark.asyncio
    async def test_cancel_running_job(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.acquire_next("t1")

        result = await queue.cancel("j1")
        assert result is True

        running = await queue.get_running_count("t1")
        assert running == 0

    @pytest.mark.asyncio
    async def test_cancel_nonexistent(self, queue):
        result = await queue.cancel("nonexistent")
        assert result is False


# =============================================================================
# InMemoryJobQueue — Stats & Queries
# =============================================================================


class TestJobQueueStats:
    @pytest.mark.asyncio
    async def test_get_queue_length(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.enqueue("t1", "j2", "analyze")
        length = await queue.get_queue_length("t1")
        assert length == 2

    @pytest.mark.asyncio
    async def test_get_queue_length_empty(self, queue):
        length = await queue.get_queue_length("nonexistent")
        assert length == 0

    @pytest.mark.asyncio
    async def test_get_running_count(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.enqueue("t1", "j2", "analyze")
        await queue.acquire_next("t1")

        count = await queue.get_running_count("t1")
        assert count == 1

    @pytest.mark.asyncio
    async def test_get_job(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        job = await queue.get_job("j1")
        assert job is not None
        assert job.job_id == "j1"

    @pytest.mark.asyncio
    async def test_get_job_nonexistent(self, queue):
        job = await queue.get_job("nonexistent")
        assert job is None

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.enqueue("t1", "j2", "analyze")
        await queue.acquire_next("t1")

        stats = await queue.get_queue_stats("t1")
        assert stats["tenant_id"] == "t1"
        assert stats["queued_count"] == 1
        assert stats["running_count"] == 1
        assert len(stats["running_job_ids"]) == 1

    @pytest.mark.asyncio
    async def test_get_queue_stats_empty(self, queue):
        stats = await queue.get_queue_stats("t1")
        assert stats["queued_count"] == 0
        assert stats["running_count"] == 0


# =============================================================================
# InMemoryJobQueue — Clear
# =============================================================================


class TestJobQueueClear:
    @pytest.mark.asyncio
    async def test_clear_tenant(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.enqueue("t1", "j2", "analyze")
        await queue.enqueue("t2", "j3", "analyze")

        count = await queue.clear_tenant("t1")
        assert count == 2

        length = await queue.get_queue_length("t1")
        assert length == 0

        # t2 should be unaffected
        length_t2 = await queue.get_queue_length("t2")
        assert length_t2 == 1

    @pytest.mark.asyncio
    async def test_clear_tenant_with_running(self, queue):
        await queue.enqueue("t1", "j1", "analyze")
        await queue.acquire_next("t1")

        count = await queue.clear_tenant("t1")
        assert count == 1
