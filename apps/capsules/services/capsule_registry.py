"""
Capsule Registry Service.

Discovery, listing, and validation of capsules.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from django.db import models

from apps.capsules.models import Capsule, CapsuleInstallation
from apps.capsules.schemas import CapsuleCreateRequest

logger = logging.getLogger(__name__)

# System capsules directory
_REGISTRY_DIR = os.path.join(os.path.dirname(__file__), "..", "registry")


def discover_capsules(
    tenant_id: str,
    realm: str = "default",
    category: str | None = None,
    include_public: bool = True,
) -> list[dict[str, Any]]:
    """Discover all capsules available to a tenant."""
    q = Capsule.objects.filter(
        status=Capsule.STATUS_ACTIVE,
        is_active=True,
    )

    tenant_filter = {"tenant_id": tenant_id, "realm": realm}
    if include_public:
        q = q.filter(
            models.Q(**tenant_filter) | models.Q(tenant_id="public", realm=realm)
        )
    else:
        q = q.filter(**tenant_filter)

    if category:
        q = q.filter(capsule_type__startswith=category)

    results = []
    for capsule in q.order_by("-install_count"):
        results.append(
            {
                "id": str(capsule.id),
                "name": capsule.name,
                "version": capsule.version,
                "description": capsule.description,
                "capsule_type": capsule.capsule_type,
                "parameters": capsule.parameters_schema,
                "rbac": capsule.rbac_rules,
                "install_count": capsule.install_count,
                "execution_count": capsule.execution_count,
                "created_at": (
                    capsule.created_at.isoformat() if capsule.created_at else ""
                ),
            }
        )
    return results


def list_installed_capsules(tenant_id: str) -> list[dict[str, Any]]:
    """List all capsules installed for a tenant."""
    installations = (
        CapsuleInstallation.objects.filter(tenant_id=tenant_id, is_enabled=True)
        .select_related("capsule")
        .order_by("-installed_at")
    )

    results = []
    for inst in installations:
        capsule = inst.capsule
        results.append(
            {
                "installation_id": str(inst.id),
                "capsule_id": str(capsule.id),
                "name": capsule.name,
                "version": capsule.version,
                "description": capsule.description,
                "status": capsule.status,
                "parameter_overrides": inst.parameter_overrides,
                "installed_at": inst.created_at.isoformat() if inst.created_at else "",
            }
        )
    return results


def load_system_capsules() -> list[dict[str, Any]]:
    """Load system capsule definitions from registry/ directory."""
    capsules = []
    reg_dir = os.path.abspath(_REGISTRY_DIR)
    if not os.path.isdir(reg_dir):
        logger.warning("System capsule registry directory not found: %s", reg_dir)
        return capsules

    for filename in sorted(os.listdir(reg_dir)):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(reg_dir, filename)
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            capsules.append(data)
            logger.debug("Loaded system capsule: %s", filename)
        except Exception as exc:
            logger.warning("Failed to load system capsule %s: %s", filename, exc)

    return capsules


def validate_capsule_definition(data: dict) -> tuple[bool, str | None]:
    """Validate a capsule definition against the Pydantic schema."""
    try:
        CapsuleCreateRequest(**data)
        return True, None
    except Exception as exc:
        return False, str(exc)


def install_capsule(
    capsule_id: str,
    tenant_id: str,
    realm: str = "default",
    parameter_overrides: dict | None = None,
    installed_by: str = "",
) -> CapsuleInstallation:
    """Install a capsule for a tenant."""
    try:
        capsule = Capsule.objects.get(
            id=capsule_id,
            status=Capsule.STATUS_ACTIVE,
            is_active=True,
        )
    except Capsule.DoesNotExist:
        raise ValueError(f"Capsule {capsule_id} not found or not active")

    # Realm isolation: tenant can only install capsules from matching realm
    if capsule.tenant_id != "public" and capsule.realm != realm:
        raise PermissionError(
            f"Capsule realm '{capsule.realm}' does not match tenant realm '{realm}'"
        )

    # Check if already installed
    existing = CapsuleInstallation.objects.filter(
        capsule=capsule, tenant_id=tenant_id, realm=realm
    ).first()
    if existing:
        return existing

    installation = CapsuleInstallation.objects.create(
        capsule=capsule,
        tenant_id=tenant_id,
        realm=realm,
        installed_by=installed_by,
        parameter_overrides=parameter_overrides or {},
    )
    capsule.install_count += 1
    capsule.save(update_fields=["install_count"])
    logger.info(
        "Installed capsule %s:%s for tenant %s realm %s",
        capsule.name,
        capsule.version,
        tenant_id,
        realm,
    )
    return installation


def load_capsule_by_id(
    capsule_id: str, tenant_id: str, realm: str = "default"
) -> Capsule:
    """Load a capsule by ID, checking tenant + realm access."""
    try:
        capsule = Capsule.objects.get(id=capsule_id)
    except Capsule.DoesNotExist:
        raise ValueError(f"Capsule {capsule_id} not found")

    # Tenant isolation: own tenant or public
    if capsule.tenant_id not in (tenant_id, "public"):
        raise ValueError(f"Access denied to capsule {capsule_id}")

    # Realm isolation: public capsules must still match realm
    if capsule.tenant_id == "public" and capsule.realm != realm:
        raise ValueError(
            f"Capsule {capsule_id} is public but in realm '{capsule.realm}'; "
            f"requested realm '{realm}'"
        )

    return capsule


def uninstall_capsule(installation_id: str, tenant_id: str) -> bool:
    """Uninstall a capsule from a tenant."""
    try:
        inst = CapsuleInstallation.objects.get(id=installation_id, tenant_id=tenant_id)
    except CapsuleInstallation.DoesNotExist:
        return False

    inst.delete()
    logger.info(
        "Uninstalled capsule installation %s for tenant %s", installation_id, tenant_id
    )
    return True
