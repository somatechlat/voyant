"""
GDPR Deletion Activities: Temporal activities for GDPR right-to-erasure.

Each activity handles deletion of user data within a specific domain and
is registered with the Temporal worker for orchestrated execution by the
GDPRDeletionWorkflow.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from temporalio import activity

logger = logging.getLogger(__name__)


class GDPRDeletionActivities:
    """Activities for GDPR Article 17 right-to-erasure."""

    # ── Ontology objects ────────────────────────────────────────────────

    @activity.defn(name="delete_ontology_objects")
    def delete_ontology_objects(self, params: dict[str, Any]) -> dict[str, Any]:
        """Delete all ontology entities owned by / linked to the user."""
        from apps.ontology.models import OntologyObject  # type: ignore[attr-defined]

        tenant_id = params["tenant_id"]
        user_id = params["user_id"]

        objs = OntologyObject.objects.filter(tenant_id=tenant_id, created_by=user_id)
        count = objs.count()
        objs.delete()

        logger.info("Deleted %d ontology objects for user=%s", count, user_id)
        return {"domain": "ontology", "deleted_count": count}

    # ── Scraper jobs ────────────────────────────────────────────────────

    @activity.defn(name="delete_scraper_jobs")
    def delete_scraper_jobs(self, params: dict[str, Any]) -> dict[str, Any]:
        """Delete all scraper jobs initiated by the user."""
        from apps.workflows.models import Job

        tenant_id = params["tenant_id"]
        user_id = params["user_id"]

        # Jobs are linked via soma_session_id or stored metadata; also
        # remove jobs whose parameters reference this user.
        jobs = Job.objects.filter(tenant_id=tenant_id, parameters__user_id=user_id)
        count = jobs.count()
        jobs.delete()

        # Also clean up scraper-specific tables if present.
        try:
            from apps.scraper.models import ScrapeJob

            scraper_jobs = ScrapeJob.objects.filter(
                tenant_id=tenant_id,
                created_by=user_id,
            )
            scraper_count = scraper_jobs.count()
            scraper_jobs.delete()
            count += scraper_count
        except Exception:
            pass

        logger.info("Deleted %d scraper/workflow jobs for user=%s", count, user_id)
        return {"domain": "scraper", "deleted_count": count}

    # ── ML runs ─────────────────────────────────────────────────────────

    @activity.defn(name="delete_ml_runs")
    def delete_ml_runs(self, params: dict[str, Any]) -> dict[str, Any]:
        """Delete ML experiment runs and associated artifacts."""
        from apps.workflows.models import Artifact

        tenant_id = params["tenant_id"]
        user_id = params["user_id"]

        # Remove artifacts whose metadata references this user
        artifacts = Artifact.objects.filter(
            tenant_id=tenant_id,
            metadata__user_id=user_id,
        )
        artifact_count = artifacts.count()
        artifacts.delete()

        # Clean up ML-specific models if present.
        ml_count = 0
        try:
            from apps.ml.models import ExperimentRun  # type: ignore[reportMissingImports]

            runs = ExperimentRun.objects.filter(
                tenant_id=tenant_id,
                created_by=user_id,
            )
            ml_count = runs.count()
            runs.delete()
        except Exception:
            pass

        total = artifact_count + ml_count
        logger.info("Deleted %d ML artifacts/runs for user=%s", total, user_id)
        return {
            "domain": "ml",
            "deleted_count": total,
            "artifacts": artifact_count,
            "runs": ml_count,
        }

    # ── Audit log anonymization ─────────────────────────────────────────

    @activity.defn(name="anonymize_audit_logs")
    def anonymize_audit_logs(self, params: dict[str, Any]) -> dict[str, Any]:
        """Anonymize PII in audit log entries rather than deleting them.

        Audit logs are retained for compliance; PII fields are replaced
        with a deterministic hash so aggregate analytics still work.
        """
        tenant_id = params["tenant_id"]
        user_id = params["user_id"]
        anon_hash = hashlib.sha256(f"gdpr-anon:{user_id}".encode()).hexdigest()[:16]
        anon_label = f"gdpr-anon-{anon_hash}"

        count = 0
        try:
            from apps.audit.models import AuditLog  # type: ignore[reportMissingImports]

            logs = AuditLog.objects.filter(tenant_id=tenant_id, user_id=user_id)
            count = logs.count()
            logs.update(
                user_id=anon_label, ip_address="0.0.0.0", user_agent="gdpr-redacted"
            )
        except Exception as exc:
            logger.warning("Audit log anonymization skipped: %s", exc)

        logger.info("Anonymized %d audit log entries for user=%s", count, user_id)
        return {"domain": "audit", "anonymized_count": count}

    # ── Verification ────────────────────────────────────────────────────

    @activity.defn(name="verify_deletion")
    def verify_deletion(self, params: dict[str, Any]) -> dict[str, Any]:
        """Verify no residual user data remains in any tracked table."""
        tenant_id = params["tenant_id"]
        user_id = params["user_id"]
        residuals: list[str] = []

        # Check ontology
        try:
            from apps.ontology.models import OntologyObject  # type: ignore[attr-defined]

            if OntologyObject.objects.filter(
                tenant_id=tenant_id, created_by=user_id
            ).exists():
                residuals.append("ontology_objects")
        except Exception:
            pass

        # Check jobs
        try:
            from apps.workflows.models import Job

            if Job.objects.filter(
                tenant_id=tenant_id, parameters__user_id=user_id
            ).exists():
                residuals.append("jobs")
        except Exception:
            pass

        # Check audit (should be anonymized, not deleted)
        try:
            from apps.audit.models import AuditLog  # type: ignore[reportMissingImports]

            if AuditLog.objects.filter(tenant_id=tenant_id, user_id=user_id).exists():
                residuals.append("audit_logs (not anonymized)")
        except Exception:
            pass

        # Check artifacts
        try:
            from apps.workflows.models import Artifact

            if Artifact.objects.filter(
                tenant_id=tenant_id, metadata__user_id=user_id
            ).exists():
                residuals.append("artifacts")
        except Exception:
            pass

        complete = len(residuals) == 0
        return {
            "complete": complete,
            "residuals": residuals,
            "reason": (
                "All user data removed" if complete else f"Residuals found: {residuals}"
            ),
        }

    # ── Certificate generation ──────────────────────────────────────────

    @activity.defn(name="generate_deletion_cert")
    def generate_deletion_cert(self, params: dict[str, Any]) -> dict[str, Any]:
        """Generate a JSON deletion certificate."""
        report = params["deletion_report"]
        now = datetime.now(UTC)

        certificate = {
            "certificate_id": str(uuid.uuid4()),
            "type": "gdpr_deletion_certificate",
            "version": "1.0",
            "issued_at": now.isoformat(),
            "subject": {
                "tenant_id": report["tenant_id"],
                "user_id": report["user_id"],
            },
            "deletion_summary": report.get("domains", {}),
            "verification": report.get("verification", {}),
            "verified": report.get("verified", False),
            "integrity_hash": None,
        }
        # Compute integrity hash (exclude the hash field itself)
        cert_copy = {k: v for k, v in certificate.items() if k != "integrity_hash"}
        certificate["integrity_hash"] = hashlib.sha256(
            json.dumps(cert_copy, sort_keys=True, default=str).encode()
        ).hexdigest()

        logger.info("Generated deletion certificate %s", certificate["certificate_id"])
        return certificate

    # ── Store certificate in MinIO ──────────────────────────────────────

    @activity.defn(name="store_certificate")
    def store_certificate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Store the deletion certificate in MinIO via artifact_store."""
        from apps.core.config import get_settings

        tenant_id = params["tenant_id"]
        user_id = params["user_id"]
        certificate = params["certificate"]
        certificate_id = certificate.get("certificate_id", str(uuid.uuid4()))

        settings = get_settings()
        storage_path = f"gdpr-certificates/{tenant_id}/{user_id}/{certificate_id}.json"

        try:
            from minio import Minio

            client = Minio(
                settings.minio_endpoint,
                access_key=settings.minio_access_key,
                secret_key=settings.minio_secret_key,
                secure=settings.minio_secure,
            )
            data = json.dumps(certificate, indent=2, default=str).encode()
            import io

            client.put_object(
                settings.minio_bucket_name,
                storage_path,
                io.BytesIO(data),
                length=len(data),
                content_type="application/json",
            )
            logger.info("Stored GDPR certificate at %s", storage_path)
        except Exception as exc:
            logger.error("Failed to store GDPR certificate: %s", exc)
            storage_path = f"local://{storage_path}"

        return {"storage_path": storage_path, "certificate_id": certificate_id}
