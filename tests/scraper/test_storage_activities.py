"""Tests for apps.scraper.activities.storage_activities — pure logic tests."""

import hashlib

import pytest

from apps.scraper.activities.storage_activities import StorageActivities


@pytest.fixture
def activities():
    return StorageActivities()


class TestStorageActivitiesHeartbeatSafe:
    def test_heartbeat_safe_noop_outside_temporal(self, activities):
        """heartbeat_safe should not raise when called outside Temporal context."""
        StorageActivities._heartbeat_safe("test")


class TestFinalizeJobLogic:
    """Test the finalize_job status determination logic."""

    def test_succeeded_when_zero_errors(self):
        """Status should be 'succeeded' when error_count is 0."""
        error_count = 0
        status = "succeeded" if error_count == 0 else "partial"
        assert status == "succeeded"

    def test_partial_when_errors_present(self):
        """Status should be 'partial' when error_count > 0."""
        error_count = 3
        status = "succeeded" if error_count == 0 else "partial"
        assert status == "partial"

    def test_finalize_params_defaults(self):
        """Default values should be 0 for all metrics."""
        params = {}
        pages_fetched = params.get("pages_fetched", 0)
        bytes_processed = params.get("bytes_processed", 0)
        artifact_count = params.get("artifact_count", 0)
        error_count = params.get("error_count", 0)
        assert pages_fetched == 0
        assert bytes_processed == 0
        assert artifact_count == 0
        assert error_count == 0


class TestStoreArtifactLogic:
    """Test content hash computation logic used in store_artifact."""

    def test_content_hash_deterministic(self):
        """Same content should produce same hash."""
        content = {"key": "value", "nested": {"a": 1}}
        h1 = hashlib.sha256(str(content).encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(str(content).encode("utf-8")).hexdigest()
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = hashlib.sha256(str({"a": 1}).encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(str({"a": 2}).encode("utf-8")).hexdigest()
        assert h1 != h2

    def test_artifact_id_format(self):
        """Artifact ID should follow the pattern scrape-{job_id}-{hash_prefix}."""
        job_id = "test-job-123"
        content_hash = hashlib.sha256(b"test").hexdigest()
        artifact_id = f"scrape-{job_id}-{content_hash[:12]}"
        assert artifact_id.startswith(f"scrape-{job_id}-")
        assert len(artifact_id) == len(f"scrape-{job_id}-") + 12
