"""
Capsule MCP Tools.

Exposes capsule discovery, installation, and execution to external AI agents.

NOTE: Do NOT add `from __future__ import annotations` here.
The MCP SDK's Tool.from_function calls issubclass() on parameter annotations,
which fails with stringified (PEP-563) annotations.
"""

import logging
from typing import Any, Dict, List, Optional

from django_mcp import mcp_app

from apps.capsules.models import Capsule, CapsuleInstallation
from apps.capsules.services.capsule_execution import (
    dispatch_capsule_workflow,
    execute_capsule_sync,
    get_instance_status,
    merge_parameters,
    validate_parameters,
)
from apps.capsules.services.capsule_registry import (
    discover_capsules,
    install_capsule,
    list_installed_capsules,
    uninstall_capsule,
)
from apps.core.security.auth import get_current_user as _get_current_user_raw

logger = logging.getLogger(__name__)


def _resolve_tenant(tenant_id: Optional[str] = None) -> tuple[str, str]:
    """Resolve tenant_id and realm from current user context."""
    try:
        # MCP context may not have a Django request; fall back to default
        user = _get_current_user_raw(None)  # type: ignore[arg-type]
    except Exception:
        user = None
    if user:
        return tenant_id or user.tenant_id, user.realm
    return tenant_id or "default", "default"


@mcp_app.tool(name="voyant.capsule.discover")
def tool_capsule_discover(category: Optional[str] = None, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Discover available capsules for the tenant."""
    tid, realm = _resolve_tenant(tenant_id)
    return discover_capsules(tid, realm, category, include_public=True)


@mcp_app.tool(name="voyant.capsule.install")
def tool_capsule_install(
    capsule_id: str, parameter_overrides: Optional[dict] = None, tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """Install a capsule into the tenant's workspace."""
    tid, realm = _resolve_tenant(tenant_id)
    try:
        user = _get_current_user_raw(None)  # type: ignore[arg-type]
    except Exception:
        user = None
    try:
        installation = install_capsule(
            capsule_id=capsule_id,
            tenant_id=tid,
            realm=realm,
            parameter_overrides=parameter_overrides or {},
            installed_by=getattr(user, "user_id", "") if user else "",
        )
        return {
            "installation_id": str(installation.id),
            "status": "installed",
            "capsule_name": installation.capsule.name,
            "version": installation.capsule.version,
        }
    except ValueError as exc:
        return {"error": str(exc)}


@mcp_app.tool(name="voyant.capsule.run")
def tool_capsule_run(
    installation_id: str, parameter_values: Optional[dict] = None, tenant_id: Optional[str] = None
) -> Dict[str, Any]:
    """Execute an installed capsule. Returns job_urn for polling."""
    tid, realm = _resolve_tenant(tenant_id)
    try:
        user = _get_current_user_raw(None)  # type: ignore[arg-type]
    except Exception:
        user = None
    try:
        installation = CapsuleInstallation.objects.select_related("capsule").get(
            id=installation_id, tenant_id=tid, realm=realm, is_enabled=True
        )
    except CapsuleInstallation.DoesNotExist:
        return {"error": "Installation not found"}

    capsule = installation.capsule
    if capsule.status != Capsule.STATUS_ACTIVE:
        return {"error": f"Capsule is not active: {capsule.status}"}

    # RBAC
    rbac = capsule.rbac_rules or {}
    required = rbac.get("required_permission", "execute:research")
    if user and not user.has_permission(required):
        return {"error": f"Permission '{required}' required"}

    # Merge and validate
    merged = merge_parameters(capsule, installation, parameter_values or {})
    valid, error = validate_parameters(capsule, merged)
    if not valid:
        return {"error": error}

    # Dispatch
    graph = capsule.execution_graph or []
    if len(graph) == 1:
        result = execute_capsule_sync(capsule, merged, tid)
    else:
        result = dispatch_capsule_workflow(capsule, merged, tid)

    return result


@mcp_app.tool(name="voyant.capsule.status")
def tool_capsule_status(instance_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Get status of a running capsule instance."""
    tid, _ = _resolve_tenant(tenant_id)
    try:
        return get_instance_status(instance_id)
    except ValueError as exc:
        return {"error": str(exc)}


@mcp_app.tool(name="voyant.capsule.list_installed")
def tool_capsule_list_installed(tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all capsules installed for this tenant."""
    tid, _ = _resolve_tenant(tenant_id)
    return list_installed_capsules(tid)


@mcp_app.tool(name="voyant.capsule.uninstall")
def tool_capsule_uninstall(installation_id: str, tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Remove a capsule installation."""
    tid, _ = _resolve_tenant(tenant_id)
    success = uninstall_capsule(installation_id, tid)
    return {"status": "uninstalled" if success else "not_found"}
