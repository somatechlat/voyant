"""
Ontology Branching & Scenarios API — Django Ninja REST endpoints.

Exposes branch management, diff, merge, and scenario what-if analysis
through the ontology router.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router, Schema

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.ontology.branching import BranchingService
from apps.ontology.scenarios import ScenarioService

logger = logging.getLogger(__name__)

branching_router = Router(tags=["ontology-branches"], auth=require_permission("read:*"))
scenario_router = Router(tags=["ontology-scenarios"], auth=require_permission("read:*"))


# ── Branch Schemas ───────────────────────────────────────────────────────────


class CreateBranchIn(Schema):
    name: str
    parent_branch: str = "main"
    description: str = ""


class ApplyBranchChangeIn(Schema):
    change_type: str
    payload: dict[str, Any]


class BranchOut(Schema):
    id: str
    name: str
    description: str
    parent_branch: str
    created_from_version: int
    status: str
    changes_count: int = 0
    created_at: str | None = None
    created_by: str = ""


# ── Scenario Schemas ─────────────────────────────────────────────────────────


class CreateScenarioIn(Schema):
    name: str
    description: str = ""


class ApplyScenarioChangeIn(Schema):
    change_type: str
    payload: dict[str, Any]


class ScenarioOut(Schema):
    id: str
    name: str
    description: str
    status: str
    changes_count: int = 0
    created_at: str | None = None
    created_by: str = ""


# ── Branch Endpoints ─────────────────────────────────────────────────────────


@branching_router.get("/branches", response=list[BranchOut])
def list_branches(request, status: str | None = None):
    """List all ontology branches."""
    tenant_id = get_tenant_id(request)
    svc = BranchingService(tenant_id=tenant_id)
    branches = svc.list_branches(status=status)
    return [
        BranchOut(
            id=b.id,
            name=b.name,
            description=b.description,
            parent_branch=b.parent_branch,
            created_from_version=b.created_from_version,
            status=b.status,
            changes_count=len(b.changes),
            created_at=b.created_at.isoformat() if b.created_at else None,
            created_by=b.created_by,
        )
        for b in branches
    ]


@branching_router.post("/branches", response=BranchOut, auth=require_permission("write:ontology"))
def create_branch(request, payload: CreateBranchIn):
    """Create a new ontology branch."""
    tenant_id = get_tenant_id(request)
    svc = BranchingService(tenant_id=tenant_id)
    try:
        branch = svc.create_branch(
            name=payload.name,
            parent_branch=payload.parent_branch,
            description=payload.description,
        )
        return BranchOut(
            id=branch.id,
            name=branch.name,
            description=branch.description,
            parent_branch=branch.parent_branch,
            created_from_version=branch.created_from_version,
            status=branch.status,
            changes_count=0,
            created_at=branch.created_at.isoformat() if branch.created_at else None,
            created_by=branch.created_by,
        )
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(400, str(exc))


@branching_router.get("/branches/{branch_name}")
def get_branch(request, branch_name: str):
    """Get a single branch by name."""
    tenant_id = get_tenant_id(request)
    svc = BranchingService(tenant_id=tenant_id)
    try:
        branch = svc.get_branch(branch_name)
        return branch.to_dict()
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(404, str(exc))


@branching_router.post("/branches/{branch_name}/changes", auth=require_permission("write:ontology"))
def apply_branch_change(request, branch_name: str, payload: ApplyBranchChangeIn):
    """Apply a change to a branch."""
    tenant_id = get_tenant_id(request)
    svc = BranchingService(tenant_id=tenant_id)
    try:
        svc.apply_change(branch_name, payload.change_type, payload.payload)
        return {"status": "ok", "branch": branch_name, "change_type": payload.change_type}
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(400, str(exc))


@branching_router.post("/branches/{branch_name}/merge", auth=require_permission("write:ontology"))
def merge_branch(request, branch_name: str):
    """Merge a branch into main."""
    tenant_id = get_tenant_id(request)
    svc = BranchingService(tenant_id=tenant_id)
    try:
        result = svc.merge_branch(branch_name)
        return result.to_dict()
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(400, str(exc))


@branching_router.get("/branches/diff/{branch_from}/{branch_to}")
def diff_branches(request, branch_from: str, branch_to: str):
    """Compare two branches to see schema differences."""
    tenant_id = get_tenant_id(request)
    svc = BranchingService(tenant_id=tenant_id)
    diff = svc.diff_branches(branch_from, branch_to)
    return diff.to_dict()


@branching_router.delete("/branches/{branch_name}", auth=require_permission("write:ontology"))
def delete_branch(request, branch_name: str):
    """Abandon a branch."""
    tenant_id = get_tenant_id(request)
    svc = BranchingService(tenant_id=tenant_id)
    try:
        svc.delete_branch(branch_name)
        return {"status": "abandoned", "branch": branch_name}
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(400, str(exc))


# ── Scenario Endpoints ───────────────────────────────────────────────────────


@scenario_router.get("/scenarios", response=list[ScenarioOut])
def list_scenarios(request, status: str | None = None):
    """List all ontology scenarios."""
    tenant_id = get_tenant_id(request)
    svc = ScenarioService(tenant_id=tenant_id)
    scenarios = svc.list_scenarios(status=status)
    return [
        ScenarioOut(
            id=s.id,
            name=s.name,
            description=s.description,
            status=s.status,
            changes_count=len(s.changes),
            created_at=s.created_at.isoformat() if s.created_at else None,
            created_by=s.created_by,
        )
        for s in scenarios
    ]


@scenario_router.post("/scenarios", response=ScenarioOut, auth=require_permission("write:ontology"))
def create_scenario(request, payload: CreateScenarioIn):
    """Create a new scenario with a snapshot of the current ontology."""
    tenant_id = get_tenant_id(request)
    svc = ScenarioService(tenant_id=tenant_id)
    scenario = svc.create_scenario(
        name=payload.name,
        description=payload.description,
    )
    return ScenarioOut(
        id=scenario.id,
        name=scenario.name,
        description=scenario.description,
        status=scenario.status,
        changes_count=0,
        created_at=scenario.created_at.isoformat() if scenario.created_at else None,
        created_by=scenario.created_by,
    )


@scenario_router.get("/scenarios/{scenario_id}")
def get_scenario(request, scenario_id: str):
    """Get a single scenario by ID with all its changes."""
    tenant_id = get_tenant_id(request)
    svc = ScenarioService(tenant_id=tenant_id)
    try:
        scenario = svc.get_scenario(scenario_id)
        return scenario.to_dict()
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(404, str(exc))


@scenario_router.post("/scenarios/{scenario_id}/changes", auth=require_permission("write:ontology"))
def apply_scenario_change(request, scenario_id: str, payload: ApplyScenarioChangeIn):
    """Apply a hypothetical change to a scenario."""
    tenant_id = get_tenant_id(request)
    svc = ScenarioService(tenant_id=tenant_id)
    try:
        svc.apply_change(scenario_id, payload.change_type, payload.payload)
        return {"status": "ok", "scenario": scenario_id, "change_type": payload.change_type}
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(400, str(exc))


@scenario_router.get("/scenarios/{scenario_id}/compare")
def compare_scenario(request, scenario_id: str):
    """Compare a scenario with its base ontology snapshot."""
    tenant_id = get_tenant_id(request)
    svc = ScenarioService(tenant_id=tenant_id)
    try:
        comparison = svc.compare_with_base(scenario_id)
        return comparison.to_dict()
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(404, str(exc))


@scenario_router.post("/scenarios/{scenario_id}/merge", auth=require_permission("write:ontology"))
def merge_scenario(request, scenario_id: str):
    """Merge an approved scenario into the main ontology."""
    tenant_id = get_tenant_id(request)
    svc = ScenarioService(tenant_id=tenant_id)
    try:
        result = svc.merge_to_main(scenario_id)
        return result.to_dict()
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(400, str(exc))


@scenario_router.delete("/scenarios/{scenario_id}", auth=require_permission("write:ontology"))
def delete_scenario(request, scenario_id: str):
    """Delete a draft scenario."""
    tenant_id = get_tenant_id(request)
    svc = ScenarioService(tenant_id=tenant_id)
    try:
        svc.delete_scenario(scenario_id)
        return {"status": "deleted", "scenario": scenario_id}
    except ValueError as exc:
        from ninja.errors import HttpError
        raise HttpError(400, str(exc))
