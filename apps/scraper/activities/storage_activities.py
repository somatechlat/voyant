"""
Voyant Scraper — Storage Activities.

Temporal activities for artifact persistence and job finalization.
Bridges scrape results to the Django ORM and MinIO artifact store.

Extracted from scraper/activities.py (Rule 245 compliance — 949-line split).
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict

from temporalio import activity

from apps.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageActivities:
    """
    Artifact storage and job lifecycle activities.

    Handles: JSON artifact persistence to MinIO via artifact_store,
    ScrapeArtifact ORM record creation, and ScrapeJob status finalization.
    All storage operations are idempotent via update_or_create.
    """

    @staticmethod
    def _load_models():
        """Lazy-load Django models to avoid import-time DB access."""
        from apps.scraper.models import ScrapeArtifact, ScrapeJob

        return ScrapeJob, ScrapeArtifact

    @staticmethod
    def _heartbeat_safe(message: str) -> None:
        """Emit Temporal heartbeat only when running inside activity context."""
        try:
            activity.heartbeat(message)
        except RuntimeError:
            return

    @activity.defn(name="store_artifact")
    def store_artifact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store extracted scrape data as a JSON artifact in MinIO.

        Creates or updates a ScrapeArtifact ORM record keyed by content hash
        to ensure idempotent storage regardless of retry count.

        Args:
            params:
                - job_id (str): Parent job ID.
                - tenant_id (str): Tenant ID for partitioning.
                - url (str): Original source URL.
                - data (dict): Extracted data to persist.

        Returns:
            Dict with artifact_id, storage_path, content_hash, size_bytes, url.
        """
        from apps.core.lib.artifact_store import store_artifact

        _, ScrapeArtifact = self._load_models()
        job_id = params.get("job_id")
        tenant_id = params.get("tenant_id", settings.default_tenant_id)
        url = params.get("url", "")
        data = params.get("data", {})

        self._heartbeat_safe(f"Storing artifact for {url}")

        ref = store_artifact(
            content=data,
            artifact_type="scrape_json",
            metadata={"job_id": job_id, "tenant_id": tenant_id, "source_url": url},
        )
        content_hash = hashlib.sha256(str(ref.hash).encode("utf-8")).hexdigest()
        artifact_id = f"scrape-{job_id}-{content_hash[:12]}"
        storage_path = ref.hash

        ScrapeArtifact.objects.update_or_create(
            artifact_id=artifact_id,
            defaults={
                "job_id": job_id,
                "artifact_type": ScrapeArtifact.ArtifactType.JSON,
                "format": "json",
                "storage_path": storage_path,
                "content_hash": ref.hash,
                "size_bytes": ref.size_bytes,
                "source_url": url,
                "metadata": {"artifact_ref": ref.to_dict()},
            },
        )

        return {
            "artifact_id": artifact_id,
            "storage_path": storage_path,
            "content_hash": ref.hash,
            "size_bytes": ref.size_bytes,
            "url": url,
        }

    @activity.defn(name="finalize_job")
    def finalize_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finalize a scrape job by updating its ORM status and recording metrics.

        Sets status to 'succeeded' if zero errors occurred, 'partial' otherwise.
        This activity is idempotent — safe to retry on failure.

        Args:
            params:
                - job_id (str): Job ID to finalize.
                - pages_fetched (int): Total pages successfully fetched.
                - bytes_processed (int): Total bytes processed.
                - artifact_count (int): Total artifacts created.
                - error_count (int): Total errors encountered.

        Returns:
            Summary dict with final status and all metrics.
        """
        job_id = params.get("job_id")
        pages_fetched = params.get("pages_fetched", 0)
        bytes_processed = params.get("bytes_processed", 0)
        artifact_count = params.get("artifact_count", 0)
        error_count = params.get("error_count", 0)

        self._heartbeat_safe(f"Finalizing job {job_id}")
        status = "succeeded" if error_count == 0 else "partial"

        ScrapeJob, _ = self._load_models()
        ScrapeJob.objects.filter(job_id=job_id).update(
            status=status,
            pages_fetched=pages_fetched,
            bytes_processed=bytes_processed,
            artifact_count=artifact_count,
            error_count=error_count,
            finished_at=datetime.utcnow(),
        )

        return {
            "job_id": job_id,
            "status": status,
            "pages_fetched": pages_fetched,
            "bytes_processed": bytes_processed,
            "artifact_count": artifact_count,
            "error_count": error_count,
            "finished_at": datetime.utcnow().isoformat(),
        }
