"""
Capsule Import Service.

Imports Capsule bundles from backup or transfer. Cross-compatible with somaAgent01.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from django.db import transaction

from apps.capsules.models import Capsule
from apps.capsules.services.capsule_export import verify_export_checksum

logger = logging.getLogger(__name__)


class ImportResult:
    """Result of a capsule import operation."""

    def __init__(
        self,
        success: bool,
        capsule: Capsule | None = None,
        error: str | None = None,
        warnings: list | None = None,
    ):
        self.success = success
        self.capsule = capsule
        self.error = error
        self.warnings = warnings or []

    def __repr__(self) -> str:
        if self.success:
            return f"ImportResult(success=True, capsule={self.capsule})"
        return f"ImportResult(success=False, error={self.error})"


def import_capsule(
    export_data: dict,
    target_tenant_id: str | None = None,
    target_realm: str = "default",
    version_suffix: str = ".imported",
    skip_checksum: bool = False,
) -> ImportResult:
    """Import a Capsule from an export bundle.

    Creates a new Capsule in DRAFT status. Must be re-certified before activation.
    """
    warnings: list[str] = []

    if not skip_checksum:
        if not verify_export_checksum(export_data):
            return ImportResult(
                success=False,
                error="Export checksum verification failed. Data may be corrupted.",
            )

    capsule_data = export_data.get("capsule")
    if not capsule_data:
        return ImportResult(success=False, error="No capsule data in export bundle")

    logger.info(
        "Importing Capsule %s:%s",
        capsule_data.get("name"),
        capsule_data.get("version"),
    )

    try:
        with transaction.atomic():
            tenant_id = target_tenant_id or capsule_data.get("tenant", "default")
            new_version = capsule_data.get("version", "1.0.0") + version_suffix

            # Resolve version conflict
            if Capsule.objects.filter(
                name=capsule_data.get("name"),
                version=new_version,
                tenant_id=tenant_id,
            ).exists():
                new_version = (
                    f"{new_version}.{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
                )
                warnings.append(f"Version conflict resolved: using {new_version}")

            soul = capsule_data.get("soul", {})
            body = capsule_data.get("body", {})

            # Validate imported realm matches target realm for non-public capsules
            import_realm = capsule_data.get("realm", target_realm)
            if import_realm != target_realm:
                warnings.append(
                    f"Imported capsule realm '{import_realm}'"
                    f" migrated to target realm '{target_realm}'"
                )

            new_capsule = Capsule.objects.create(
                name=capsule_data.get("name"),
                version=new_version,
                tenant_id=tenant_id,
                realm=target_realm,
                description=capsule_data.get("description", ""),
                status=Capsule.STATUS_DRAFT,
                system_prompt=soul.get("system_prompt", ""),
                personality_traits=soul.get("personality_traits", {}),
                neuromodulator_baseline=soul.get("neuromodulator_baseline", {}),
                capsule_type=body.get("capsule_type", "voyant.intelligence_recipe"),
                execution_graph=body.get("execution_graph", []),
                parameters_schema=body.get("parameters", {}),
                output_formats=body.get("output_formats", ["pdf", "markdown"]),
                rbac_rules=body.get("rbac", {}),
                capabilities_whitelist=body.get("capabilities_whitelist", []),
                resource_limits=body.get("resource_limits", {}),
                constitution=None,
                constitution_ref={},
                registry_signature=None,
                certified_at=None,
            )

            logger.info(
                "Created imported capsule: %s:%s (id=%s, status=DRAFT)",
                new_capsule.name,
                new_capsule.version,
                new_capsule.id,
            )

            return ImportResult(success=True, capsule=new_capsule, warnings=warnings)

    except Exception as e:
        logger.error("Capsule import failed: %s", str(e))
        return ImportResult(success=False, error=str(e), warnings=warnings)


def import_tenant_capsules(
    export_data: dict,
    target_tenant_id: str | None = None,
    target_realm: str = "default",
) -> dict:
    """Import all capsules from a tenant export bundle."""
    result = {
        "successful_imports": [],
        "failed_imports": [],
        "success_count": 0,
        "failure_count": 0,
    }

    if not verify_export_checksum(export_data):
        result["failed_imports"].append(
            {"error": "Tenant export checksum verification failed"}
        )
        result["failure_count"] = 1
        return result

    tenant_id = target_tenant_id or export_data.get("tenant", "default")
    capsules = export_data.get("capsules", [])

    logger.info("Importing %d capsules for tenant: %s", len(capsules), tenant_id)

    for capsule_export in capsules:
        import_result = import_capsule(
            capsule_export,
            target_tenant_id=tenant_id,
            target_realm=target_realm,
            skip_checksum=True,
        )

        if import_result.success and import_result.capsule:
            result["successful_imports"].append(
                {
                    "name": import_result.capsule.name,
                    "version": import_result.capsule.version,
                    "id": str(import_result.capsule.id),
                }
            )
            result["success_count"] += 1
        else:
            result["failed_imports"].append(
                {"error": import_result.error, "warnings": import_result.warnings}
            )
            result["failure_count"] += 1

    logger.info(
        "Tenant import complete: %d succeeded, %d failed",
        result["success_count"],
        result["failure_count"],
    )
    return result
