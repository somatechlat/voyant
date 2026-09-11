"""
Capsule API — Ninja REST routers.

Endpoints for capsule CRUD, installation, execution, and registry discovery.
All endpoints enforce RBAC via require_permission / require_role.
"""

from __future__ import annotations

import uuid
from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.capsules.models import Capsule, CapsuleInstallation, CapsuleInstance
from apps.capsules.schemas import (
    CapsuleCreateRequest,
    CapsuleInstallRequest,
    CapsuleRunRequest,
)
from apps.capsules.services.capsule_core import (
    activate_capsule,
    archive_capsule,
    certify_capsule,
    suspend_capsule,
    verify_capsule,
)
from apps.capsules.services.capsule_execution import (
    dispatch_capsule_workflow,
    execute_capsule_sync,
    get_instance_status,
    merge_parameters,
    validate_parameters,
)
from apps.capsules.services.capsule_export import export_capsule
from apps.capsules.services.capsule_import import import_capsule
from apps.capsules.services.capsule_registry import (
    discover_capsules,
    install_capsule,
    list_installed_capsules,
    uninstall_capsule,
)
from apps.core.security.auth import require_permission, require_role

# Router with auth
capsules_router = Router(auth=require_permission("read:*"))
router = capsules_router  # backward compat


# ── Registry / Discovery ────────────────────────────────────────────────────


@router.get("/registry", response=list[dict[str, Any]])
def list_registry(
    request,
    category: str | None = None,
    include_public: bool = True,
):
    """List all discoverable capsules for the tenant."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"
    realm = getattr(user, "realm", "default") if user else "default"
    return discover_capsules(tenant_id, realm, category, include_public)


@router.get("/registry/{capsule_id}", response=dict[str, Any])
def get_capsule_definition(request, capsule_id: str):
    """Get a single capsule definition."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"

    try:
        capsule = Capsule.objects.get(
            id=capsule_id,
            status=Capsule.STATUS_ACTIVE,
            is_active=True,
        )
    except Capsule.DoesNotExist:
        raise HttpError(404, "Capsule not found")

    # Tenant isolation: only own tenant or public
    if capsule.tenant_id not in (tenant_id, "public"):
        raise HttpError(403, "Access denied")

    return {
        "id": str(capsule.id),
        "name": capsule.name,
        "version": capsule.version,
        "description": capsule.description,
        "capsule_type": capsule.capsule_type,
        "execution_graph": capsule.execution_graph,
        "parameters_schema": capsule.parameters_schema,
        "output_formats": capsule.output_formats,
        "rbac_rules": capsule.rbac_rules,
        "capabilities_whitelist": capsule.capabilities_whitelist,
        "resource_limits": capsule.resource_limits,
    }


# ── Installation ────────────────────────────────────────────────────────────


@router.post("/install", auth=require_permission("install:capsule"))
def install_capsule_endpoint(request, payload: CapsuleInstallRequest):
    """Install a capsule for the tenant."""
    user = getattr(request, "auth", None)
    tenant_id = (
        getattr(user, "tenant_id", "default")
        if user
        else (payload.tenant_id or "default")
    )
    realm = getattr(user, "realm", "default") if user else "default"

    try:
        installation = install_capsule(
            capsule_id=payload.capsule_id,
            tenant_id=tenant_id,
            realm=realm,
            parameter_overrides=payload.parameter_overrides,
            installed_by=getattr(user, "user_id", "") if user else "",
        )
        return {
            "installation_id": str(installation.id),
            "status": "installed",
            "capsule_name": installation.capsule.name,
        }
    except ValueError as exc:
        raise HttpError(400, str(exc))


@router.get("/installed", response=list[dict[str, Any]])
def list_installed(request):
    """List all capsules installed for this tenant."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"
    return list_installed_capsules(tenant_id)


@router.delete(
    "/installed/{installation_id}", auth=require_permission("install:capsule")
)
def uninstall_capsule_endpoint(request, installation_id: str):
    """Uninstall a capsule."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"

    success = uninstall_capsule(installation_id, tenant_id)
    if not success:
        raise HttpError(404, "Installation not found")
    return {"status": "uninstalled"}


# ── Execution ───────────────────────────────────────────────────────────────


@router.post("/run", auth=require_permission("execute:research"))
def run_capsule(request, payload: CapsuleRunRequest):
    """Execute an installed capsule. Returns job_urn for polling."""
    user = getattr(request, "auth", None)
    tenant_id = (
        getattr(user, "tenant_id", "default")
        if user
        else (payload.tenant_id or "default")
    )
    realm = getattr(user, "realm", "default") if user else "default"

    try:
        installation = CapsuleInstallation.objects.select_related("capsule").get(
            id=payload.installation_id,
            tenant_id=tenant_id,
            realm=realm,
            is_enabled=True,
        )
    except CapsuleInstallation.DoesNotExist:
        raise HttpError(404, "Installation not found")

    capsule = installation.capsule
    if capsule.status != Capsule.STATUS_ACTIVE:
        raise HttpError(400, f"Capsule is not active: {capsule.status}")

    # Merge and validate parameters
    merged = merge_parameters(capsule, installation, payload.parameter_values)
    valid, error = validate_parameters(capsule, merged)
    if not valid:
        raise HttpError(400, error or "Invalid parameters")

    # RBAC: check required permission
    rbac = capsule.rbac_rules or {}
    required = rbac.get("required_permission", "execute:research")
    if user and not user.has_permission(required):
        raise HttpError(403, f"Permission '{required}' required")

    # Dispatch
    graph = capsule.execution_graph or []
    if not graph:
        raise HttpError(400, "Capsule has no execution graph")

    session_id = f"api-{uuid.uuid4().hex[:12]}"
    if len(graph) == 1:
        result = execute_capsule_sync(capsule, merged, tenant_id, session_id=session_id)
    else:
        result = dispatch_capsule_workflow(
            capsule, merged, tenant_id, session_id=session_id
        )

    return result


@router.get("/instances/{instance_id}", response=dict[str, Any])
def get_instance(request, instance_id: str):
    """Get status of a running capsule instance."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"

    try:
        instance = CapsuleInstance.objects.select_related("capsule").get(id=instance_id)
    except CapsuleInstance.DoesNotExist:
        raise HttpError(404, "Instance not found")

    if instance.tenant_id != tenant_id and not (user and "voyant-admin" in user.roles):
        raise HttpError(403, "Access denied")

    return get_instance_status(instance_id)


# ── CRUD (Admin) ────────────────────────────────────────────────────────────


@router.post("/create", auth=require_role("voyant-engineer"))
def create_capsule(request, payload: CapsuleCreateRequest):
    """Create a new capsule (DRAFT status)."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"
    realm = getattr(user, "realm", "default") if user else "default"

    capsule = Capsule.objects.create(
        name=payload.name,
        version=payload.version,
        tenant_id=tenant_id,
        realm=realm,
        description=payload.description,
        status=Capsule.STATUS_DRAFT,
        system_prompt=payload.soul.system_prompt,
        personality_traits=payload.soul.personality_traits,
        neuromodulator_baseline=payload.soul.neuromodulator_baseline,
        capsule_type=payload.body.capsule_type,
        execution_graph=[step.model_dump() for step in payload.body.execution_graph],
        parameters_schema={
            k: v.model_dump() for k, v in payload.body.parameters.items()
        },
        output_formats=payload.body.output_formats,
        rbac_rules=payload.body.rbac.model_dump(),
        capabilities_whitelist=payload.body.capabilities_whitelist,
        resource_limits=payload.body.resource_limits,
    )
    return {
        "id": str(capsule.id),
        "name": capsule.name,
        "version": capsule.version,
        "status": capsule.status,
    }


@router.post("/{capsule_id}/certify", auth=require_role("voyant-admin"))
def certify_capsule_endpoint(request, capsule_id: str):
    """Certify a draft capsule."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"

    try:
        capsule = Capsule.objects.get(id=capsule_id, tenant_id=tenant_id)
    except Capsule.DoesNotExist:
        raise HttpError(404, "Capsule not found")

    if not verify_capsule(capsule):
        raise HttpError(400, "Capsule failed integrity verification")

    certified = certify_capsule(capsule)
    certified_at = (
        certified.certified_at.isoformat() if certified.certified_at else None
    )
    return {
        "id": str(certified.id),
        "status": certified.status,
        "certified_at": certified_at,
    }


@router.post("/{capsule_id}/activate", auth=require_role("voyant-admin"))
def activate_capsule_endpoint(request, capsule_id: str):
    """Activate a certified capsule."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"

    try:
        capsule = Capsule.objects.get(id=capsule_id, tenant_id=tenant_id)
    except Capsule.DoesNotExist:
        raise HttpError(404, "Capsule not found")

    activated = activate_capsule(capsule)
    return {"id": str(activated.id), "status": activated.status}


@router.post("/{capsule_id}/suspend", auth=require_role("voyant-admin"))
def suspend_capsule_endpoint(request, capsule_id: str, reason: str = ""):
    """Suspend a capsule."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"

    try:
        capsule = Capsule.objects.get(id=capsule_id, tenant_id=tenant_id)
    except Capsule.DoesNotExist:
        raise HttpError(404, "Capsule not found")

    suspended = suspend_capsule(capsule, reason)
    return {"id": str(suspended.id), "status": suspended.status}


@router.post("/{capsule_id}/archive", auth=require_role("voyant-admin"))
def archive_capsule_endpoint(request, capsule_id: str):
    """Archive a capsule."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"

    try:
        capsule = Capsule.objects.get(id=capsule_id, tenant_id=tenant_id)
    except Capsule.DoesNotExist:
        raise HttpError(404, "Capsule not found")

    archived = archive_capsule(capsule)
    return {"id": str(archived.id), "status": archived.status}


# ── Import / Export ─────────────────────────────────────────────────────────


@router.post("/import", auth=require_role("voyant-engineer"))
def import_capsule_endpoint(request, payload: dict):
    """Import a capsule from a JSON bundle."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"
    realm = getattr(user, "realm", "default") if user else "default"

    result = import_capsule(
        export_data=payload,
        target_tenant_id=tenant_id,
        target_realm=realm,
    )
    return {
        "success": result.success,
        "capsule_id": str(result.capsule.id) if result.capsule else None,
        "error": result.error,
        "warnings": result.warnings,
    }


@router.post("/export/{capsule_id}", auth=require_role("voyant-engineer"))
def export_capsule_endpoint(request, capsule_id: str):
    """Export a capsule to a JSON bundle."""
    user = getattr(request, "auth", None)
    tenant_id = getattr(user, "tenant_id", "default") if user else "default"

    try:
        capsule = Capsule.objects.get(id=capsule_id, tenant_id=tenant_id)
    except Capsule.DoesNotExist:
        raise HttpError(404, "Capsule not found")

    return export_capsule(capsule.id)
