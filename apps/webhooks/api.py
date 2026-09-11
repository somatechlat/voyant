"""Webhook REST API — CRUD for webhooks and delivery listing."""

from __future__ import annotations

import logging
import secrets
from typing import Any

from ninja import Field, Router, Schema
from ninja.errors import HttpError

from apps.core.api_utils import auth_guard
from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

webhooks_router = Router(tags=["webhooks"], auth=require_permission("read:*"))

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class WebhookItem(Schema):
    id: str
    url: str
    events: list[str] = Field(default_factory=list)
    status: str
    description: str = ""
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, Any] = Field(default_factory=dict)
    failure_count: int = 0
    last_triggered_at: str | None = None


class WebhookCreateRequest(Schema):
    url: str
    events: list[str] = Field(default_factory=list)
    secret: str | None = None  # Auto-generated if not provided
    description: str = ""
    retry_policy: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


class WebhookUpdateRequest(Schema):
    url: str | None = None
    events: list[str] | None = None
    secret: str | None = None
    description: str | None = None
    retry_policy: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None
    status: str | None = None


class WebhookDeliveryItem(Schema):
    id: str
    webhook_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    status: str
    attempts: int = 0
    max_retries: int = 3
    last_response_code: int | None = None
    last_error: str = ""
    delivered_at: str | None = None


# ---------------------------------------------------------------------------
# CRUD — Webhooks
# ---------------------------------------------------------------------------


@webhooks_router.get(
    "/",
    response=list[WebhookItem],
    auth=auth_guard,
)
def list_webhooks(request):
    """List all webhooks for the current tenant."""
    from apps.webhooks.models import Webhook

    tenant_id = get_tenant_id(request)
    webhooks = Webhook.objects.filter(tenant_id=tenant_id)
    return [
        WebhookItem(
            id=str(wh.id),
            url=wh.url,
            events=wh.events or [],
            status=wh.status,
            description=wh.description,
            retry_policy=wh.retry_policy or {},
            headers=wh.headers or {},
            failure_count=wh.failure_count,
            last_triggered_at=(
                wh.last_triggered_at.isoformat() if wh.last_triggered_at else None
            ),
        )
        for wh in webhooks
    ]


@webhooks_router.post(
    "/",
    response=WebhookItem,
    auth=auth_guard,
)
def create_webhook(request, payload: WebhookCreateRequest):
    """Create a new webhook subscription."""
    from apps.webhooks.models import Webhook

    tenant_id = get_tenant_id(request)
    secret = payload.secret or secrets.token_hex(32)

    webhook = Webhook.objects.create(
        tenant_id=tenant_id,
        url=payload.url,
        events=payload.events,
        secret=secret,
        description=payload.description,
        retry_policy=payload.retry_policy,
        headers=payload.headers,
        status=payload.status,
    )
    return WebhookItem(
        id=str(webhook.id),
        url=webhook.url,
        events=webhook.events or [],
        status=webhook.status,
        description=webhook.description,
        retry_policy=webhook.retry_policy or {},
        headers=webhook.headers or {},
        failure_count=0,
    )


@webhooks_router.get(
    "/{webhook_id}",
    response=WebhookItem,
    auth=auth_guard,
)
def get_webhook(request, webhook_id: str):
    """Get a single webhook by ID."""
    from apps.webhooks.models import Webhook

    tenant_id = get_tenant_id(request)
    try:
        wh = Webhook.objects.get(id=webhook_id, tenant_id=tenant_id)
    except Webhook.DoesNotExist:
        raise HttpError(404, "Webhook not found")
    return WebhookItem(
        id=str(wh.id),
        url=wh.url,
        events=wh.events or [],
        status=wh.status,
        description=wh.description,
        retry_policy=wh.retry_policy or {},
        headers=wh.headers or {},
        failure_count=wh.failure_count,
        last_triggered_at=(
            wh.last_triggered_at.isoformat() if wh.last_triggered_at else None
        ),
    )


@webhooks_router.put(
    "/{webhook_id}",
    response=WebhookItem,
    auth=auth_guard,
)
def update_webhook(request, webhook_id: str, payload: WebhookUpdateRequest):
    """Update an existing webhook."""
    from apps.webhooks.models import Webhook

    tenant_id = get_tenant_id(request)
    try:
        wh = Webhook.objects.get(id=webhook_id, tenant_id=tenant_id)
    except Webhook.DoesNotExist:
        raise HttpError(404, "Webhook not found")

    for field_name, value in payload.dict(exclude_unset=True).items():
        setattr(wh, field_name, value)
    wh.save()

    return WebhookItem(
        id=str(wh.id),
        url=wh.url,
        events=wh.events or [],
        status=wh.status,
        description=wh.description,
        retry_policy=wh.retry_policy or {},
        headers=wh.headers or {},
        failure_count=wh.failure_count,
        last_triggered_at=(
            wh.last_triggered_at.isoformat() if wh.last_triggered_at else None
        ),
    )


@webhooks_router.delete(
    "/{webhook_id}",
    response=dict[str, str],
    auth=auth_guard,
)
def delete_webhook(request, webhook_id: str):
    """Delete a webhook."""
    from apps.webhooks.models import Webhook

    tenant_id = get_tenant_id(request)
    try:
        wh = Webhook.objects.get(id=webhook_id, tenant_id=tenant_id)
    except Webhook.DoesNotExist:
        raise HttpError(404, "Webhook not found")
    wh.delete()
    return {"id": webhook_id, "status": "deleted"}


# ---------------------------------------------------------------------------
# Deliveries
# ---------------------------------------------------------------------------


@webhooks_router.get(
    "/{webhook_id}/deliveries",
    response=list[WebhookDeliveryItem],
    auth=auth_guard,
)
def list_deliveries(request, webhook_id: str, limit: int = 50):
    """List deliveries for a specific webhook."""
    from apps.webhooks.models import Webhook, WebhookDelivery

    tenant_id = get_tenant_id(request)
    try:
        Webhook.objects.get(id=webhook_id, tenant_id=tenant_id)
    except Webhook.DoesNotExist:
        raise HttpError(404, "Webhook not found")

    deliveries = WebhookDelivery.objects.filter(
        webhook_id=webhook_id,
        tenant_id=tenant_id,
    )[:limit]

    return [
        WebhookDeliveryItem(
            id=str(d.id),
            webhook_id=str(d.webhook_id),
            event_type=d.event_type,
            payload=d.payload,
            status=d.status,
            attempts=d.attempts,
            max_retries=d.max_retries,
            last_response_code=d.last_response_code,
            last_error=d.last_error,
            delivered_at=d.delivered_at.isoformat() if d.delivered_at else None,
        )
        for d in deliveries
    ]
