"""Dashboard Builder API — Django Ninja REST endpoints.

Provides CRUD for dashboards and widgets.
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone as tz
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

dashboards_router = Router(tags=["dashboards"], auth=require_permission("read:*"))


# ── Schemas ──────────────────────────────────────────────────────────────────


class DashboardCreateIn(Schema):
    name: str
    description: str = ""
    layout: dict[str, Any] = {}
    tags: list[str] = []
    is_public: bool = False


class DashboardUpdateIn(Schema):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    layout: dict[str, Any] | None = None
    tags: list[str] | None = None
    is_public: bool | None = None


class DashboardOut(Schema):
    id: str
    name: str
    description: str
    status: str
    layout: dict[str, Any]
    tags: list[str]
    is_public: bool
    created_by: str
    widget_count: int = 0
    tenant_id: str
    created_at: str
    updated_at: str


class WidgetCreateIn(Schema):
    widget_type: str
    title: str = ""
    config: dict[str, Any] = {}
    position_x: int = 0
    position_y: int = 0
    width: int = 6
    height: int = 4
    order: int = 0
    visible: bool = True


class WidgetUpdateIn(Schema):
    widget_type: str | None = None
    title: str | None = None
    config: dict[str, Any] | None = None
    position_x: int | None = None
    position_y: int | None = None
    width: int | None = None
    height: int | None = None
    order: int | None = None
    visible: bool | None = None


class WidgetOut(Schema):
    id: str
    dashboard_id: str
    widget_type: str
    title: str
    config: dict[str, Any]
    position_x: int
    position_y: int
    width: int
    height: int
    order: int
    visible: bool


# ── Helpers ──────────────────────────────────────────────────────────────────


def _to_dashboard_out(d: Any, widget_count: int = 0) -> dict[str, Any]:
    return {
        "id": str(d.id),
        "name": d.name,
        "description": d.description,
        "status": d.status,
        "layout": d.layout,
        "tags": d.tags,
        "is_public": d.is_public,
        "created_by": d.created_by,
        "widget_count": widget_count,
        "tenant_id": d.tenant_id,
        "created_at": d.created_at.isoformat(),
        "updated_at": d.updated_at.isoformat(),
    }


def _to_widget_out(w: Any) -> dict[str, Any]:
    return {
        "id": str(w.id),
        "dashboard_id": str(w.dashboard_id),
        "widget_type": w.widget_type,
        "title": w.title,
        "config": w.config,
        "position_x": w.position_x,
        "position_y": w.position_y,
        "width": w.width,
        "height": w.height,
        "order": w.order,
        "visible": w.visible,
    }


# ── Dashboard CRUD ───────────────────────────────────────────────────────────


@dashboards_router.post(
    "", response={201: DashboardOut}, auth=require_permission("write:dashboards")
)
def create_dashboard(request, payload: DashboardCreateIn):
    """Create a new dashboard."""
    from apps.dashboard_builder.models import Dashboard

    tenant_id = get_tenant_id(request)
    user = getattr(request, "user", None)
    created_by = user.username if user and user.is_authenticated else ""

    dashboard = Dashboard.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        layout=payload.layout,
        tags=payload.tags,
        is_public=payload.is_public,
        created_by=created_by,
    )
    return 201, _to_dashboard_out(dashboard, widget_count=0)


@dashboards_router.get("", response=list[DashboardOut])
def list_dashboards(
    request,
    status: str | None = None,
    is_public: bool | None = None,
    limit: int = 50,
):
    """List dashboards for the current tenant."""
    from apps.dashboard_builder.models import Dashboard

    tenant_id = get_tenant_id(request)
    qs = Dashboard.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
    if status:
        qs = qs.filter(status=status)
    if is_public is not None:
        qs = qs.filter(is_public=is_public)
    qs = qs.order_by("-created_at")[:limit]
    results = []
    for d in qs:
        widget_count = d.widgets.count() if hasattr(d, "widgets") else 0  # type: ignore[attr-defined]
        results.append(_to_dashboard_out(d, widget_count=widget_count))
    return results


@dashboards_router.get("/{dashboard_id}", response=DashboardOut)
def get_dashboard(request, dashboard_id: str):
    """Get dashboard details including layout and metadata."""
    from apps.dashboard_builder.models import Dashboard

    tenant_id = get_tenant_id(request)
    dashboard = Dashboard.objects.filter(
        id=dashboard_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not dashboard:
        raise HttpError(404, f"Dashboard {dashboard_id} not found")
    widget_count = dashboard.widgets.count() if hasattr(dashboard, "widgets") else 0  # type: ignore[attr-defined]
    return _to_dashboard_out(dashboard, widget_count=widget_count)


@dashboards_router.put(
    "/{dashboard_id}",
    response=DashboardOut,
    auth=require_permission("write:dashboards"),
)
def update_dashboard(request, dashboard_id: str, payload: DashboardUpdateIn):
    """Update a dashboard."""
    from apps.dashboard_builder.models import Dashboard

    tenant_id = get_tenant_id(request)
    dashboard = Dashboard.objects.filter(
        id=dashboard_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not dashboard:
        raise HttpError(404, f"Dashboard {dashboard_id} not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dashboard, field, value)
    dashboard.save()
    widget_count = dashboard.widgets.count() if hasattr(dashboard, "widgets") else 0  # type: ignore[attr-defined]
    return _to_dashboard_out(dashboard, widget_count=widget_count)


@dashboards_router.delete(
    "/{dashboard_id}", auth=require_permission("write:dashboards")
)
def delete_dashboard(request, dashboard_id: str):
    """Soft-delete a dashboard."""
    from apps.dashboard_builder.models import Dashboard

    tenant_id = get_tenant_id(request)
    dashboard = Dashboard.objects.filter(
        id=dashboard_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not dashboard:
        raise HttpError(404, f"Dashboard {dashboard_id} not found")

    dashboard.deleted_at = tz.now()
    dashboard.save(update_fields=["deleted_at"])
    return {"deleted": True, "id": dashboard_id}


# ── Widget CRUD ──────────────────────────────────────────────────────────────


@dashboards_router.post(
    "/{dashboard_id}/widgets",
    response={201: WidgetOut},
    auth=require_permission("write:dashboards"),
)
def create_widget(request, dashboard_id: str, payload: WidgetCreateIn):
    """Add a widget to a dashboard."""
    from apps.dashboard_builder.models import Dashboard, Widget

    tenant_id = get_tenant_id(request)
    dashboard = Dashboard.objects.filter(
        id=dashboard_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not dashboard:
        raise HttpError(404, f"Dashboard {dashboard_id} not found")

    widget = Widget.objects.create(
        dashboard=dashboard,
        widget_type=payload.widget_type,
        title=payload.title,
        config=payload.config,
        position_x=payload.position_x,
        position_y=payload.position_y,
        width=payload.width,
        height=payload.height,
        order=payload.order,
        visible=payload.visible,
    )
    return 201, _to_widget_out(widget)


@dashboards_router.get("/{dashboard_id}/widgets", response=list[WidgetOut])
def list_widgets(request, dashboard_id: str):
    """List all widgets on a dashboard."""
    from apps.dashboard_builder.models import Widget

    qs = Widget.objects.filter(dashboard_id=dashboard_id).order_by(
        "order", "position_y", "position_x"
    )
    return [_to_widget_out(w) for w in qs]


@dashboards_router.get("/widgets/{widget_id}", response=WidgetOut)
def get_widget(request, widget_id: str):
    """Get a specific widget."""
    from apps.dashboard_builder.models import Widget

    widget = Widget.objects.filter(id=widget_id).first()
    if not widget:
        raise HttpError(404, f"Widget {widget_id} not found")
    return _to_widget_out(widget)


@dashboards_router.put(
    "/widgets/{widget_id}",
    response=WidgetOut,
    auth=require_permission("write:dashboards"),
)
def update_widget(request, widget_id: str, payload: WidgetUpdateIn):
    """Update a widget's configuration or position."""
    from apps.dashboard_builder.models import Widget

    widget = Widget.objects.filter(id=widget_id).first()
    if not widget:
        raise HttpError(404, f"Widget {widget_id} not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(widget, field, value)
    widget.save()
    return _to_widget_out(widget)


@dashboards_router.delete(
    "/widgets/{widget_id}", auth=require_permission("write:dashboards")
)
def delete_widget(request, widget_id: str):
    """Delete a widget from a dashboard."""
    from apps.dashboard_builder.models import Widget

    widget = Widget.objects.filter(id=widget_id).first()
    if not widget:
        raise HttpError(404, f"Widget {widget_id} not found")

    widget.delete()
    return {"deleted": True, "id": widget_id}


@dashboards_router.post(
    "/{dashboard_id}/widgets/reorder",
    auth=require_permission("write:dashboards"),
)
def reorder_widgets(request, dashboard_id: str, payload: list[dict[str, Any]]):
    """Reorder widgets on a dashboard.

    Expects a list of {"id": "...", "order": N, "position_x": N, "position_y": N, "width": N, "height": N}.
    """
    from apps.dashboard_builder.models import Widget

    tenant_id = get_tenant_id(request)

    # Verify dashboard exists
    from apps.dashboard_builder.models import Dashboard

    dashboard = Dashboard.objects.filter(
        id=dashboard_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not dashboard:
        raise HttpError(404, f"Dashboard {dashboard_id} not found")

    updated = []
    for item in payload:
        widget_id = item.get("id")
        if not widget_id:
            continue
        widget = Widget.objects.filter(id=widget_id, dashboard_id=dashboard_id).first()
        if not widget:
            continue
        for field in ("order", "position_x", "position_y", "width", "height"):
            if field in item:
                setattr(widget, field, item[field])
        widget.save()
        updated.append(str(widget.id))

    return {"updated": updated}
