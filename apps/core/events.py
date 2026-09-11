"""
Channel-layer event publishers for real-time WebSocket subscriptions.

These helpers publish events to Django Channels groups so connected
WebSocket clients receive live updates.  They are designed to be called
alongside the existing Kafka emitters in ``apps.core.lib.events``.

Group naming convention: ``voyant_{tenant_id}_{channel}``
"""

from __future__ import annotations

import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


def _get_layer():
    """Return the default channel layer, or None if channels is unconfigured."""
    try:
        return get_channel_layer()
    except Exception:
        logger.debug("Channel layer not available")
        return None


def _publish(group: str, event_type: str, data: dict[str, Any]) -> None:
    """Send a message to a channel-layer group."""
    layer = _get_layer()
    if layer is None:
        return
    try:
        async_to_sync(layer.group_send)(
            group,
            {
                "type": event_type,
                "data": data,
            },
        )
    except Exception as exc:
        logger.warning("Failed to publish to group %s: %s", group, exc)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def _group(tenant_id: str, channel: str) -> str:
    """Build a tenant-scoped group name."""
    return f"voyant_{tenant_id or 'global'}_{channel}"


def publish_ontology_change(
    tenant_id: str,
    event_type: str,
    object_type: str,
    object_id: str = "",
    data: dict[str, Any] | None = None,
) -> None:
    """
    Publish an ontology change notification.

    Args:
        tenant_id: Tenant scope.
        event_type: e.g. ``"object_type.created"``, ``"object.updated"``.
        object_type: The ontology entity kind (``ObjectType``, ``Object``, ``LinkType``, ``Link``).
        object_id: ID of the changed entity.
        data: Arbitrary payload to forward to clients.
    """
    payload = {
        "event_type": event_type,
        "object_type": object_type,
        "object_id": object_id,
        **(data or {}),
    }
    _publish(_group(tenant_id, "ontology_changes"), "event_ontology_change", payload)


def publish_job_status(
    tenant_id: str,
    job_id: str,
    status: str,
    progress: int = 0,
    data: dict[str, Any] | None = None,
    user_id: str = "",
) -> None:
    """
    Publish a job status update.

    Args:
        tenant_id: Tenant scope.
        job_id: The job's unique identifier.
        status: New status string (``queued``, ``running``, ``completed``, ``failed``).
        progress: Integer progress percentage (0-100).
        data: Additional payload fields.
        user_id: User to notify (if empty, no notification is created).
    """
    payload = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        **(data or {}),
    }
    _publish(_group(tenant_id, "job_status"), "event_job_status", payload)

    # Create an in-app notification for terminal job states
    if user_id and status in ("completed", "failed"):
        _create_job_notification(tenant_id, job_id, status, user_id, data)


def _create_job_notification(
    tenant_id: str,
    job_id: str,
    status: str,
    user_id: str,
    data: dict[str, Any] | None = None,
) -> None:
    """
    Create an in-app notification for a job status change.

    Called internally by :func:`publish_job_status` when a job reaches
    a terminal state (completed or failed).
    """
    try:
        from apps.notifications.services import NotificationService

        job_name = (data or {}).get("job_name", job_id)
        if status == "completed":
            title = f"Job completed: {job_name}"
            message = f"Your job '{job_name}' has completed successfully."
            notification_type = "success"
        else:
            title = f"Job failed: {job_name}"
            message = f"Your job '{job_name}' has failed. Check the job details for more information."
            notification_type = "error"

        NotificationService.create(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            resource_type="job",
            resource_id=job_id,
        )
    except Exception as exc:
        # Notification creation is fire-and-forget; never block the event pipeline
        logger.debug("Failed to create job notification: %s", exc)


def publish_agent_event(
    tenant_id: str,
    agent_id: str,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> None:
    """
    Publish an agent platform event.

    Args:
        tenant_id: Tenant scope.
        agent_id: Agent identifier.
        event_type: e.g. ``"agent.started"``, ``"agent.tool_called"``.
        data: Arbitrary payload.
    """
    payload = {
        "agent_id": agent_id,
        "event_type": event_type,
        **(data or {}),
    }
    _publish(_group(tenant_id, "agent_events"), "event_agent_event", payload)


def publish_scraper_event(
    tenant_id: str,
    event_type: str,
    template_id: str = "",
    template_name: str = "",
    data: dict[str, Any] | None = None,
) -> None:
    """
    Publish a scraper event.

    Args:
        tenant_id: Tenant scope.
        event_type: e.g. ``"scrape.started"``, ``"scrape.completed"``.
        template_id: Scraper template identifier.
        template_name: Human-readable template name.
        data: Arbitrary payload.
    """
    payload = {
        "event_type": event_type,
        "template_id": template_id,
        "template_name": template_name,
        **(data or {}),
    }
    _publish(_group(tenant_id, "scraper_events"), "event_scraper_event", payload)
