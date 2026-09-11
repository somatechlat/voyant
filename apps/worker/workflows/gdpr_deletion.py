"""
GDPR Deletion Workflow: Orchestrates Right-to-Erasure Across All Apps.

This Temporal workflow implements the GDPR Article 17 "Right to Erasure"
process.  It coordinates deletion of all user-associated data across the
Voyant platform, verifies completeness, and generates a tamper-evident
deletion certificate stored in MinIO.

Domain activities:
  - delete_ontology_objects   → removes ontology entities linked to user
  - delete_scraper_jobs       → removes scraper jobs/runs for user
  - delete_ml_runs            → removes ML experiment runs and artifacts
  - anonymize_audit_logs      → redacts PII from audit log entries
  - verify_deletion           → confirms no residual user data remains
  - generate_deletion_cert    → produces JSON deletion certificate
  - store_certificate         → uploads certificate to MinIO via artifact_store
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

with workflow.unsafe.imports_passed_through():
    pass


@workflow.defn
class GDPRDeletionWorkflow:
    """Temporal workflow implementing GDPR Article 17 right-to-erasure.

    Accepts a ``tenant_id`` and ``user_id``, deletes every piece of user
    data across the platform, verifies completeness, and stores a signed
    deletion certificate in MinIO.
    """

    @workflow.run
    async def run(self, params: dict[str, Any]) -> dict[str, Any]:
        """Execute the GDPR deletion pipeline.

        Parameters
        ----------
        params : dict
            ``tenant_id`` – owning tenant
            ``user_id``   – subject whose data must be erased

        Returns
        -------
        dict
            Deletion report with per-domain counts and certificate path.
        """
        tenant_id: str = params["tenant_id"]
        user_id: str = params["user_id"]

        workflow.logger.info(
            "GDPRDeletionWorkflow started for tenant=%s user=%s",
            tenant_id,
            user_id,
        )

        retry_policy = RetryPolicy(
            initial_interval=timedelta(seconds=1),
            backoff_coefficient=2.0,
            maximum_interval=timedelta(seconds=30),
            maximum_attempts=3,
            non_retryable_error_types=["ApplicationError", "ValidationError"],
        )

        deletion_report: dict[str, Any] = {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "domains": {},
            "verified": False,
            "certificate_path": None,
        }

        # ── Step 1: Delete ontology objects ──────────────────────────────
        ontology_result = await workflow.execute_activity(
            "delete_ontology_objects",
            {"tenant_id": tenant_id, "user_id": user_id},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )
        deletion_report["domains"]["ontology"] = ontology_result

        # ── Step 2: Delete scraper jobs ──────────────────────────────────
        scraper_result = await workflow.execute_activity(
            "delete_scraper_jobs",
            {"tenant_id": tenant_id, "user_id": user_id},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )
        deletion_report["domains"]["scraper"] = scraper_result

        # ── Step 3: Delete ML runs ──────────────────────────────────────
        ml_result = await workflow.execute_activity(
            "delete_ml_runs",
            {"tenant_id": tenant_id, "user_id": user_id},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )
        deletion_report["domains"]["ml"] = ml_result

        # ── Step 4: Anonymize audit logs ────────────────────────────────
        audit_result = await workflow.execute_activity(
            "anonymize_audit_logs",
            {"tenant_id": tenant_id, "user_id": user_id},
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=retry_policy,
        )
        deletion_report["domains"]["audit"] = audit_result

        # ── Step 5: Verify deletion completeness ────────────────────────
        verification = await workflow.execute_activity(
            "verify_deletion",
            {"tenant_id": tenant_id, "user_id": user_id},
            start_to_close_timeout=timedelta(minutes=3),
            retry_policy=retry_policy,
        )

        if not verification.get("complete", False):
            raise ApplicationError(
                f"Deletion verification failed: {verification.get('reason', 'unknown')}"
            )

        deletion_report["verified"] = True
        deletion_report["verification"] = verification

        # ── Step 6: Generate deletion certificate ───────────────────────
        certificate = await workflow.execute_activity(
            "generate_deletion_cert",
            {"deletion_report": deletion_report},
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        # ── Step 7: Store certificate in MinIO ──────────────────────────
        store_result = await workflow.execute_activity(
            "store_certificate",
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "certificate": certificate,
            },
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=retry_policy,
        )

        deletion_report["certificate_path"] = store_result.get("storage_path")
        deletion_report["certificate_id"] = store_result.get("certificate_id")

        workflow.logger.info(
            "GDPRDeletionWorkflow completed for tenant=%s user=%s cert=%s",
            tenant_id,
            user_id,
            deletion_report["certificate_path"],
        )
        return deletion_report
