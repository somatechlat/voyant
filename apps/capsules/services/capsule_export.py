"""
Capsule Export Service.

Exports Capsule bundles compatible with somaAgent01 format v1.0.0.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from apps.capsules.models import Capsule, CapsuleInstance

logger = logging.getLogger(__name__)


@dataclass
class CapsuleSoulExport:
    system_prompt: str
    personality_traits: dict
    neuromodulator_baseline: dict


@dataclass
class CapsuleBodyExport:
    capsule_type: str
    capabilities_whitelist: list
    resource_limits: dict
    json_schema: dict
    config: dict
    execution_graph: list
    parameters: dict
    rbac: dict
    output_formats: list
    triggers: list


@dataclass
class CapsuleGovernanceExport:
    constitution_ref: dict
    registry_signature: str | None
    certified_at: str | None


@dataclass
class CapsuleExport:
    id: str
    name: str
    version: str
    tenant: str
    description: str
    status: str
    parent_id: str | None
    soul: CapsuleSoulExport
    body: CapsuleBodyExport
    governance: CapsuleGovernanceExport
    created_at: str
    updated_at: str


@dataclass
class CapsuleInstanceExport:
    id: str
    session_id: str
    state: dict
    status: str
    started_at: str
    completed_at: str | None


@dataclass
class CapsuleBundleExport:
    export_version: str = "1.0.0"
    exported_at: str = ""
    export_checksum: str = ""
    capsule: CapsuleExport | None = None
    instances: list = field(default_factory=list)


def export_capsule(
    capsule_id: UUID,
    include_instances: bool = True,
) -> dict:
    """Export a complete Capsule bundle."""
    capsule = Capsule.objects.select_related("constitution", "parent").get(id=capsule_id)

    logger.info(
        "Exporting Capsule %s:%s (tenant=%s)",
        capsule.name,
        capsule.version,
        capsule.tenant_id,
    )

    bundle = CapsuleBundleExport(
        export_version="1.0.0",
        exported_at=datetime.now(UTC).isoformat(),
        capsule=_export_capsule_core(capsule),
    )

    if include_instances:
        bundle.instances = _export_instances(capsule)

    export_dict = _bundle_to_dict(bundle)
    export_dict["export_checksum"] = _compute_checksum(export_dict)

    logger.info(
        "Capsule export complete: %s:%s, checksum=%s",
        capsule.name,
        capsule.version,
        export_dict["export_checksum"][:16],
    )
    return export_dict


def export_tenant_capsules(tenant_id: str) -> dict:
    """Export all active capsules for a tenant."""
    capsules = Capsule.objects.filter(tenant_id=tenant_id, status=Capsule.STATUS_ACTIVE)
    exports = []
    for capsule in capsules:
        try:
            exports.append(export_capsule(capsule.id, include_instances=False))
        except Exception as e:
            logger.error("Failed to export capsule %s: %s", capsule.id, e)

    export = {
        "tenant_export_version": "1.0.0",
        "tenant": tenant_id,
        "exported_at": datetime.now(UTC).isoformat(),
        "capsule_count": len(exports),
        "capsules": exports,
    }
    export["export_checksum"] = _compute_checksum(export)
    return export


def verify_export_checksum(export_data: dict) -> bool:
    """Verify the integrity of an export bundle."""
    stored = export_data.get("export_checksum", "")
    computed = _compute_checksum(export_data)
    return stored == computed


def _export_capsule_core(capsule: Capsule) -> CapsuleExport:
    return CapsuleExport(
        id=str(capsule.id),
        name=capsule.name,
        version=capsule.version,
        tenant=capsule.tenant_id,
        description=capsule.description,
        status=capsule.status,
        parent_id=str(capsule.parent.id) if capsule.parent else None,
        soul=CapsuleSoulExport(
            system_prompt=capsule.system_prompt,
            personality_traits=capsule.personality_traits,
            neuromodulator_baseline=capsule.neuromodulator_baseline,
        ),
        body=CapsuleBodyExport(
            capsule_type=capsule.capsule_type,
            capabilities_whitelist=capsule.capabilities_whitelist,
            resource_limits=capsule.resource_limits,
            json_schema={},
            config={},
            execution_graph=capsule.execution_graph,
            parameters=capsule.parameters_schema,
            rbac=capsule.rbac_rules,
            output_formats=capsule.output_formats,
            triggers=[],
        ),
        governance=CapsuleGovernanceExport(
            constitution_ref=capsule.constitution_ref,
            registry_signature=capsule.registry_signature,
            certified_at=capsule.certified_at.isoformat() if capsule.certified_at else None,
        ),
        created_at=capsule.created_at.isoformat() if capsule.created_at else "",
        updated_at=capsule.updated_at.isoformat() if capsule.updated_at else "",
    )


def _export_instances(capsule: Capsule) -> list:
    instances = CapsuleInstance.objects.filter(capsule=capsule)
    return [
        {
            "id": str(inst.id),
            "session_id": inst.session_id,
            "state": inst.state,
            "status": inst.status,
            "started_at": inst.started_at.isoformat() if inst.started_at else "",
            "completed_at": inst.completed_at.isoformat() if inst.completed_at else None,
        }
        for inst in instances
    ]


def _bundle_to_dict(bundle: CapsuleBundleExport) -> dict:
    def convert(obj: Any) -> Any:
        if hasattr(obj, "__dataclass_fields__"):
            return {k: convert(v) for k, v in asdict(obj).items()}
        if isinstance(obj, list):
            return [convert(item) for item in obj]
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        return obj

    return convert(bundle)


def _compute_checksum(data: dict) -> str:
    data_copy = {k: v for k, v in data.items() if k != "export_checksum"}
    json_bytes = json.dumps(data_copy, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(json_bytes).hexdigest()
