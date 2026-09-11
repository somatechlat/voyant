"""Notifications API — Django Ninja REST endpoints.

Provides endpoints for managing notifications and notification preferences.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

notifications_router = Router(tags=["notifications"], auth=require_permission("read:*"))


# ── Schemas ──────────────────────────────────────────────────────────────────


class NotificationCreateIn(Schema):
    user_id: str
    type: str = "information"
    title: str
    message: str
    resource_type: str = ""
    resource_id: str = ""


class NotificationOut(Schema):
    id: str
    user_id: str
    type: str
    title: str
    message: str
    resource_type: str
    resource_id: str
    is_read: bool
    read_at: str | None
    tenant_id: str
    created_at: str
    updated_at: str


class NotificationListOut(Schema):
    items: list[NotificationOut]
    total: int
    unread_count: int


class PreferenceIn(Schema):
    event_type: str
    channel: str
    enabled: bool = True


class PreferenceOut(Schema):
    id: str
    user_id: str
    event_type: str
    channel: str
    enabled: bool


class PreferenceUpdateIn(Schema):
    preferences: list[PreferenceIn]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _to_notification_out(n: Any) -> dict[str, Any]:
    return {
        "id": str(n.id),
        "user_id": n.user_id,
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "resource_type": n.resource_type,
        "resource_id": n.resource_id,
        "is_read": n.is_read,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "tenant_id": n.tenant_id,
        "created_at": n.created_at.isoformat(),
        "updated_at": n.updated_at.isoformat(),
    }


def _to_preference_out(p: Any) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "user_id": p.user_id,
        "event_type": p.event_type,
        "channel": p.channel,
        "enabled": p.enabled,
    }


def _get_user_id(request) -> str:
    """Extract user_id from the authenticated request."""
    user = getattr(request, "user", None)
    if user and hasattr(user, "user_id"):
        return user.user_id
    if user and hasattr(user, "username"):
        return user.username
    return ""


# ── Notification endpoints ───────────────────────────────────────────────────


@notifications_router.get("", response=NotificationListOut)
def list_notifications(
    request,
    notification_type: str | None = None,
    is_read: bool | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List the current user's notifications (paginated, filterable)."""
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    if not user_id:
        raise HttpError(401, "Authentication required")

    qs = Notification.objects.filter(tenant_id=tenant_id, user_id=user_id)
    if notification_type:
        qs = qs.filter(type=notification_type)
    if is_read is not None:
        qs = qs.filter(is_read=is_read)

    total = qs.count()
    unread_count = NotificationService.get_unread_count(tenant_id, user_id)
    items = [_to_notification_out(n) for n in qs[offset : offset + limit]]

    return {
        "items": items,
        "total": total,
        "unread_count": unread_count,
    }


@notifications_router.post("", response={201: NotificationOut})
def create_notification(request, payload: NotificationCreateIn):
    """Create a notification (system use)."""
    from apps.notifications.services import NotificationService

    tenant_id = get_tenant_id(request)
    notification = NotificationService.create(
        tenant_id=tenant_id,
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        notification_type=payload.type,
        resource_type=payload.resource_type,
        resource_id=payload.resource_id,
    )
    return 201, _to_notification_out(notification)


@notifications_router.put("/{notification_id}/read")
def mark_notification_read(request, notification_id: str):
    """Mark a single notification as read."""
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    if not user_id:
        raise HttpError(401, "Authentication required")

    notification = Notification.objects.filter(
        id=notification_id, tenant_id=tenant_id, user_id=user_id
    ).first()
    if not notification:
        raise HttpError(404, f"Notification {notification_id} not found")

    NotificationService.mark_read(notification)
    return _to_notification_out(notification)


@notifications_router.put("/read-all")
def mark_all_notifications_read(request):
    """Mark all of the current user's notifications as read."""
    from apps.notifications.services import NotificationService

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    if not user_id:
        raise HttpError(401, "Authentication required")

    count = NotificationService.mark_all_read(tenant_id, user_id)
    return {"marked_read": count}


@notifications_router.delete("/{notification_id}")
def delete_notification(request, notification_id: str):
    """Delete a notification."""
    from apps.notifications.models import Notification

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    if not user_id:
        raise HttpError(401, "Authentication required")

    notification = Notification.objects.filter(
        id=notification_id, tenant_id=tenant_id, user_id=user_id
    ).first()
    if not notification:
        raise HttpError(404, f"Notification {notification_id} not found")

    notification.delete()
    return {"deleted": True, "id": notification_id}


# ── Preference endpoints ─────────────────────────────────────────────────────


@notifications_router.get("/preferences", response=list[PreferenceOut])
def list_preferences(request):
    """List the current user's notification preferences."""
    from apps.notifications.models import NotificationPreference

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    if not user_id:
        raise HttpError(401, "Authentication required")

    qs = NotificationPreference.objects.filter(
        tenant_id=tenant_id, user_id=user_id
    ).order_by("event_type", "channel")
    return [_to_preference_out(p) for p in qs]


@notifications_router.put("/preferences", response=list[PreferenceOut])
def update_preferences(request, payload: PreferenceUpdateIn):
    """Create or update the current user's notification preferences."""
    from apps.notifications.models import NotificationPreference

    tenant_id = get_tenant_id(request)
    user_id = _get_user_id(request)
    if not user_id:
        raise HttpError(401, "Authentication required")

    results = []
    for pref in payload.preferences:
        obj, _ = NotificationPreference.objects.update_or_create(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=pref.event_type,
            channel=pref.channel,
            defaults={"enabled": pref.enabled},
        )
        results.append(_to_preference_out(obj))
    return results
