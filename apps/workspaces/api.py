"""Workspaces API — Django Ninja REST endpoints.

Provides CRUD for workspaces, member management, asset sharing,
comments, and activity feeds.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

workspaces_router = Router(tags=["workspaces"], auth=require_permission("read:*"))


# ── Schemas ──────────────────────────────────────────────────────────────────


class WorkspaceCreateIn(Schema):
    name: str
    description: str = ""
    is_public: bool = False
    tags: list[str] = []


class WorkspaceUpdateIn(Schema):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None
    tags: list[str] | None = None


class WorkspaceOut(Schema):
    id: str
    name: str
    description: str
    owner_id: str
    is_public: bool
    tags: list[str]
    tenant_id: str
    created_at: str
    updated_at: str


class MemberIn(Schema):
    user_id: str
    role: str = "member"


class MemberOut(Schema):
    id: str
    workspace_id: str
    user_id: str
    role: str
    joined_at: str


class AssetIn(Schema):
    asset_type: str
    asset_id: str


class AssetOut(Schema):
    id: str
    workspace_id: str
    asset_type: str
    asset_id: str
    shared_by: str
    shared_at: str


class CommentCreateIn(Schema):
    content: str
    asset_type: str = ""
    asset_id: str = ""
    parent_comment_id: str | None = None
    mentions: list[str] = []


class CommentUpdateIn(Schema):
    content: str


class CommentOut(Schema):
    id: str
    workspace_id: str | None
    asset_type: str
    asset_id: str
    content: str
    parent_comment_id: str | None
    mentions: list[str]
    created_by: str
    tenant_id: str
    created_at: str
    updated_at: str


class ActivityItemOut(Schema):
    action: str
    actor: str
    resource_type: str
    resource_id: str
    timestamp: str
    details: dict[str, Any] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────


def _to_workspace_out(w: Any) -> dict[str, Any]:
    return {
        "id": str(w.id),
        "name": w.name,
        "description": w.description,
        "owner_id": w.owner_id,
        "is_public": w.is_public,
        "tags": w.tags,
        "tenant_id": w.tenant_id,
        "created_at": w.created_at.isoformat(),
        "updated_at": w.updated_at.isoformat(),
    }


def _to_member_out(m: Any) -> dict[str, Any]:
    return {
        "id": str(m.id),
        "workspace_id": str(m.workspace_id),
        "user_id": m.user_id,
        "role": m.role,
        "joined_at": m.joined_at.isoformat(),
    }


def _to_asset_out(a: Any) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "workspace_id": str(a.workspace_id),
        "asset_type": a.asset_type,
        "asset_id": a.asset_id,
        "shared_by": a.shared_by,
        "shared_at": a.shared_at.isoformat(),
    }


def _to_comment_out(c: Any) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "workspace_id": str(c.workspace_id) if c.workspace_id else None,
        "asset_type": c.asset_type,
        "asset_id": c.asset_id,
        "content": c.content,
        "parent_comment_id": str(c.parent_comment_id) if c.parent_comment_id else None,
        "mentions": c.mentions,
        "created_by": c.created_by,
        "tenant_id": c.tenant_id,
        "created_at": c.created_at.isoformat(),
        "updated_at": c.updated_at.isoformat(),
    }


def _get_user_id(request) -> str:
    """Extract user_id from the authenticated request."""
    user = getattr(request, "user", None)
    if user and hasattr(user, "user_id"):
        return user.user_id
    if user and hasattr(user, "username"):
        return user.username
    return ""


def _get_workspace_or_404(tenant_id: str, workspace_id: str):
    """Fetch a workspace or raise 404."""
    from apps.workspaces.models import Workspace

    ws = Workspace.objects.filter(id=workspace_id, tenant_id=tenant_id).first()
    if not ws:
        raise HttpError(404, f"Workspace {workspace_id} not found")
    return ws


def _check_member(workspace, user_id: str, min_role: str = "viewer"):
    """Verify user is a member with at least the given role level."""
    from apps.workspaces.models import WorkspaceMember

    role_hierarchy = {"owner": 4, "admin": 3, "member": 2, "viewer": 1}
    membership = WorkspaceMember.objects.filter(
        workspace=workspace, user_id=user_id
    ).first()
    if not membership:
        raise HttpError(403, "You are not a member of this workspace")
    if role_hierarchy.get(membership.role, 0) < role_hierarchy.get(min_role, 0):
        raise HttpError(403, f"Insufficient role: requires {min_role} or higher")
    return membership


# ── Workspace CRUD ───────────────────────────────────────────────────────────


@workspaces_router.post("", response={201: WorkspaceOut})
def create_workspace(request, payload: WorkspaceCreateIn):
    """Create a new workspace. Creator becomes the owner."""
    from apps.workspaces.models import Workspace, WorkspaceMember

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    if not user_id:
        raise HttpError(401, "Authentication required")

    workspace = Workspace.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        owner_id=user_id,
        is_public=payload.is_public,
        tags=payload.tags,
    )
    # Auto-add creator as owner
    WorkspaceMember.objects.create(
        tenant_id=tenant_id,
        workspace=workspace,
        user_id=user_id,
        role="owner",
    )
    return 201, _to_workspace_out(workspace)


@workspaces_router.get("", response=list[WorkspaceOut])
def list_workspaces(request, is_public: bool | None = None, limit: int = 50):
    """List workspaces accessible to the current user."""
    from apps.workspaces.models import Workspace, WorkspaceMember

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    if not user_id:
        raise HttpError(401, "Authentication required")

    # Workspaces the user is a member of, plus public ones
    member_ws_ids = WorkspaceMember.objects.filter(
        tenant_id=tenant_id, user_id=user_id
    ).values_list("workspace_id", flat=True)

    from django.db.models import Q

    qs = Workspace.objects.filter(tenant_id=tenant_id).filter(
        Q(id__in=member_ws_ids) | Q(is_public=True)
    )
    if is_public is not None:
        qs = qs.filter(is_public=is_public)
    qs = qs.order_by("-created_at")[:limit]
    return [_to_workspace_out(w) for w in qs]


@workspaces_router.get("/{workspace_id}", response=WorkspaceOut)
def get_workspace(request, workspace_id: str):
    """Get workspace details."""
    tenant_id = get_tenant_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)
    return _to_workspace_out(ws)


@workspaces_router.put("/{workspace_id}", response=WorkspaceOut)
def update_workspace(request, workspace_id: str, payload: WorkspaceUpdateIn):
    """Update a workspace (owner/admin only)."""
    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)
    _check_member(ws, user_id, min_role="admin")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ws, field, value)
    ws.save()
    return _to_workspace_out(ws)


@workspaces_router.delete("/{workspace_id}")
def delete_workspace(request, workspace_id: str):
    """Delete a workspace (owner only)."""
    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)
    _check_member(ws, user_id, min_role="owner")

    ws.delete()
    return {"deleted": True, "id": workspace_id}


# ── Member management ────────────────────────────────────────────────────────


@workspaces_router.post("/{workspace_id}/members", response={201: MemberOut})
def add_member(request, workspace_id: str, payload: MemberIn):
    """Add a member to the workspace (admin/owner only)."""
    from apps.workspaces.models import WorkspaceMember

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)
    _check_member(ws, user_id, min_role="admin")

    if WorkspaceMember.objects.filter(
        workspace=ws, user_id=payload.user_id
    ).exists():
        raise HttpError(409, f"User {payload.user_id} is already a member")

    member = WorkspaceMember.objects.create(
        tenant_id=tenant_id,
        workspace=ws,
        user_id=payload.user_id,
        role=payload.role,
    )
    return 201, _to_member_out(member)


@workspaces_router.get("/{workspace_id}/members", response=list[MemberOut])
def list_members(request, workspace_id: str):
    """List all members of a workspace."""
    from apps.workspaces.models import WorkspaceMember

    tenant_id = get_tenant_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)

    qs = WorkspaceMember.objects.filter(workspace=ws).order_by("joined_at")
    return [_to_member_out(m) for m in qs]


@workspaces_router.delete("/{workspace_id}/members/{member_user_id}")
def remove_member(request, workspace_id: str, member_user_id: str):
    """Remove a member from a workspace (admin/owner only)."""
    from apps.workspaces.models import WorkspaceMember

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)
    _check_member(ws, user_id, min_role="admin")

    member = WorkspaceMember.objects.filter(
        workspace=ws, user_id=member_user_id
    ).first()
    if not member:
        raise HttpError(404, f"Member {member_user_id} not found")
    if member.role == "owner":
        raise HttpError(400, "Cannot remove the workspace owner")

    member.delete()
    return {"removed": True, "user_id": member_user_id}


# ── Asset sharing ────────────────────────────────────────────────────────────


@workspaces_router.post("/{workspace_id}/assets", response={201: AssetOut})
def share_asset(request, workspace_id: str, payload: AssetIn):
    """Share an asset into a workspace."""
    from apps.workspaces.models import WorkspaceAsset

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)
    _check_member(ws, user_id, min_role="member")

    asset = WorkspaceAsset.objects.create(
        tenant_id=tenant_id,
        workspace=ws,
        asset_type=payload.asset_type,
        asset_id=payload.asset_id,
        shared_by=user_id,
    )
    return 201, _to_asset_out(asset)


@workspaces_router.get("/{workspace_id}/assets", response=list[AssetOut])
def list_assets(
    request,
    workspace_id: str,
    asset_type: str | None = None,
):
    """List shared assets in a workspace."""
    from apps.workspaces.models import WorkspaceAsset

    tenant_id = get_tenant_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)

    qs = WorkspaceAsset.objects.filter(tenant_id=tenant_id, workspace=ws)
    if asset_type:
        qs = qs.filter(asset_type=asset_type)
    qs = qs.order_by("-shared_at")
    return [_to_asset_out(a) for a in qs]


@workspaces_router.delete("/{workspace_id}/assets/{asset_id}")
def remove_asset(request, workspace_id: str, asset_id: str):
    """Remove a shared asset from a workspace."""
    from apps.workspaces.models import WorkspaceAsset

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)
    _check_member(ws, user_id, min_role="member")

    asset = WorkspaceAsset.objects.filter(
        id=asset_id, tenant_id=tenant_id, workspace=ws
    ).first()
    if not asset:
        raise HttpError(404, f"Asset {asset_id} not found")

    asset.delete()
    return {"deleted": True, "id": asset_id}


# ── Comments ─────────────────────────────────────────────────────────────────


@workspaces_router.post("/{workspace_id}/comments", response={201: CommentOut})
def create_comment(request, workspace_id: str, payload: CommentCreateIn):
    """Create a comment within a workspace context."""
    from apps.workspaces.models import Comment

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    if not user_id:
        raise HttpError(401, "Authentication required")
    ws = _get_workspace_or_404(tenant_id, workspace_id)
    _check_member(ws, user_id, min_role="viewer")

    # Validate parent comment if provided
    if payload.parent_comment_id:
        parent = Comment.objects.filter(
            id=payload.parent_comment_id, workspace=ws
        ).first()
        if not parent:
            raise HttpError(404, "Parent comment not found")

    comment = Comment.objects.create(
        tenant_id=tenant_id,
        workspace=ws,
        asset_type=payload.asset_type,
        asset_id=payload.asset_id,
        content=payload.content,
        parent_comment_id=payload.parent_comment_id,
        mentions=payload.mentions,
        created_by=user_id,
    )
    return 201, _to_comment_out(comment)


@workspaces_router.get("/{workspace_id}/comments", response=list[CommentOut])
def list_comments(
    request,
    workspace_id: str,
    asset_type: str | None = None,
    asset_id: str | None = None,
    limit: int = 50,
):
    """List comments in a workspace, optionally filtered by asset."""
    from apps.workspaces.models import Comment

    tenant_id = get_tenant_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)

    qs = Comment.objects.filter(tenant_id=tenant_id, workspace=ws)
    if asset_type:
        qs = qs.filter(asset_type=asset_type)
    if asset_id:
        qs = qs.filter(asset_id=asset_id)
    qs = qs.order_by("created_at")[:limit]
    return [_to_comment_out(c) for c in qs]


@workspaces_router.put(
    "/{workspace_id}/comments/{comment_id}", response=CommentOut
)
def update_comment(
    request, workspace_id: str, comment_id: str, payload: CommentUpdateIn
):
    """Update a comment (author only)."""
    from apps.workspaces.models import Comment

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)

    comment = Comment.objects.filter(
        id=comment_id, tenant_id=tenant_id, workspace=ws
    ).first()
    if not comment:
        raise HttpError(404, f"Comment {comment_id} not found")
    if comment.created_by != user_id:
        raise HttpError(403, "Only the author can edit this comment")

    comment.content = payload.content
    comment.save(update_fields=["content", "updated_at"])
    return _to_comment_out(comment)


@workspaces_router.delete("/{workspace_id}/comments/{comment_id}")
def delete_comment(request, workspace_id: str, comment_id: str):
    """Delete a comment (author or admin)."""
    from apps.workspaces.models import Comment

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)

    comment = Comment.objects.filter(
        id=comment_id, tenant_id=tenant_id, workspace=ws
    ).first()
    if not comment:
        raise HttpError(404, f"Comment {comment_id} not found")
    if comment.created_by != user_id:
        # Allow admins/owners to delete others' comments
        _check_member(ws, user_id, min_role="admin")

    comment.delete()
    return {"deleted": True, "id": comment_id}


# ── Activity feed ────────────────────────────────────────────────────────────


@workspaces_router.get("/{workspace_id}/activity", response=list[ActivityItemOut])
def get_activity(request, workspace_id: str, limit: int = 50):
    """
    Get a unified activity feed for a workspace.

    Aggregates recent member joins, asset shares, and comments into a
    single chronological feed.
    """
    from apps.workspaces.models import Comment, WorkspaceAsset, WorkspaceMember

    tenant_id = get_tenant_id(request)
    ws = _get_workspace_or_404(tenant_id, workspace_id)

    activities: list[dict[str, Any]] = []

    # Recent member additions
    for m in WorkspaceMember.objects.filter(
        tenant_id=tenant_id, workspace=ws
    ).order_by("-joined_at")[:limit]:
        activities.append(
            {
                "action": "member.joined",
                "actor": m.user_id,
                "resource_type": "member",
                "resource_id": m.user_id,
                "timestamp": m.joined_at.isoformat(),
                "details": {"role": m.role},
            }
        )

    # Recent asset shares
    for a in WorkspaceAsset.objects.filter(
        tenant_id=tenant_id, workspace=ws
    ).order_by("-shared_at")[:limit]:
        activities.append(
            {
                "action": "asset.shared",
                "actor": a.shared_by,
                "resource_type": a.asset_type,
                "resource_id": a.asset_id,
                "timestamp": a.shared_at.isoformat(),
                "details": {},
            }
        )

    # Recent comments
    for c in Comment.objects.filter(
        tenant_id=tenant_id, workspace=ws
    ).order_by("-created_at")[:limit]:
        activities.append(
            {
                "action": "comment.created",
                "actor": c.created_by,
                "resource_type": "comment",
                "resource_id": str(c.id),
                "timestamp": c.created_at.isoformat(),
                "details": {
                    "asset_type": c.asset_type,
                    "asset_id": c.asset_id,
                },
            }
        )

    # Sort all activities by timestamp descending, then limit
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:limit]
