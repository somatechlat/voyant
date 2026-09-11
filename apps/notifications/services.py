"""Notifications — Business logic services.

Provides NotificationService for creating, reading, and dispatching
notifications across multiple channels (in-app, email, Slack).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.utils import timezone as tz

if TYPE_CHECKING:
    from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Stateless service for notification operations.

    All methods accept an explicit ``tenant_id`` so they can be called
    from background tasks, event handlers, and API views alike.
    """

    # ── Creation ──────────────────────────────────────────────────────────

    @staticmethod
    def create(
        tenant_id: str,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "information",
        resource_type: str = "",
        resource_id: str = "",
        realm: str = "default",
    ) -> Notification:
        """
        Create a notification and dispatch it through enabled channels.

        In-app storage is always performed. Email and Slack channels are
        dispatched only when the user has an enabled preference for the
        given event type on that channel (stubs for now).

        Args:
            tenant_id: Tenant scope.
            user_id: Recipient user identifier.
            title: Short notification title.
            message: Full notification body.
            notification_type: One of ``information``, ``warning``, ``error``, ``success``.
            resource_type: Related resource type (optional).
            resource_id: Related resource id (optional).
            realm: RBAC realm (defaults to ``"default"``).

        Returns:
            The created ``Notification`` instance.
        """
        from apps.notifications.models import Notification

        notification = Notification.objects.create(
            tenant_id=tenant_id,
            realm=realm,
            user_id=user_id,
            type=notification_type,
            title=title,
            message=message,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        # Dispatch to non-in-app channels (stubs)
        NotificationService._dispatch_channels(
            tenant_id=tenant_id,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
        )

        # Publish real-time WebSocket notification
        NotificationService._publish_ws(tenant_id, user_id, notification)

        logger.info(
            "Notification created: id=%s user=%s type=%s title=%s",
            notification.id,
            user_id,
            notification_type,
            title,
        )
        return notification

    # ── Read management ───────────────────────────────────────────────────

    @staticmethod
    def mark_read(notification: Any) -> None:
        """Mark a single notification as read."""
        notification.mark_read()

    @staticmethod
    def mark_all_read(tenant_id: str, user_id: str) -> int:
        """
        Mark all unread notifications for a user as read.

        Returns:
            Number of notifications updated.
        """
        from apps.notifications.models import Notification

        now = tz.now()
        qs = Notification.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            is_read=False,
        )
        count = qs.update(is_read=True, read_at=now, updated_at=now)
        logger.info(
            "Marked all read: tenant=%s user=%s count=%d",
            tenant_id,
            user_id,
            count,
        )
        return count

    @staticmethod
    def get_unread_count(tenant_id: str, user_id: str) -> int:
        """Return the count of unread notifications for a user."""
        from apps.notifications.models import Notification

        return Notification.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            is_read=False,
        ).count()

    # ── Channel dispatchers ───────────────────────────────────────────────

    @staticmethod
    def _dispatch_channels(
        tenant_id: str,
        user_id: str,
        title: str,
        message: str,
        notification_type: str,
    ) -> None:
        """Dispatch notification to non-in-app channels based on user preferences."""
        from apps.notifications.models import NotificationPreference

        email_pref = NotificationPreference.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=notification_type,
            channel="email",
            enabled=True,
        ).first()
        if email_pref:
            NotificationService._send_email(user_id, title, message)

        slack_pref = NotificationPreference.objects.filter(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=notification_type,
            channel="slack",
            enabled=True,
        ).first()
        if slack_pref:
            NotificationService._send_slack(user_id, title, message)

    @staticmethod
    def _send_email(user_id: str, title: str, message: str) -> None:
        """Send notification email via Django's email backend."""
        from django.conf import settings
        from django.contrib.auth import get_user_model
        from django.core.mail import send_mail

        User = get_user_model()
        try:
            user = User.objects.get(pk=user_id)
            recipient = user.email
        except (User.DoesNotExist, ValueError):
            logger.debug("No Django user for id %s; skipping email dispatch", user_id)
            return

        if not recipient:
            logger.debug("No email for user %s; skipping email dispatch", user_id)
            return

        try:
            send_mail(
                subject=f"[Voyant] {title}",
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@voyant.io"),
                recipient_list=[recipient],
                fail_silently=False,
            )
            logger.info("Email sent to %s: %s", recipient, title)
        except Exception as exc:
            logger.error("Email dispatch failed for user %s: %s", user_id, exc)

    @staticmethod
    def _send_slack(user_id: str, title: str, message: str) -> None:
        """Send notification to Slack via incoming webhook."""
        import httpx
        from django.conf import settings

        webhook_url = getattr(settings, "VOYANT_SLACK_WEBHOOK_URL", "")
        if not webhook_url:
            logger.debug("No Slack webhook configured; skipping Slack dispatch")
            return

        payload = {
            "text": f"*{title}*\n{message}",
            "unfurl_links": False,
        }
        try:
            resp = httpx.post(webhook_url, json=payload, timeout=10.0)
            resp.raise_for_status()
            logger.info("Slack notification sent for user %s: %s", user_id, title)
        except Exception as exc:
            logger.error("Slack dispatch failed for user %s: %s", user_id, exc)

    @staticmethod
    def _publish_ws(tenant_id: str, user_id: str, notification: Any) -> None:
        """Publish a real-time notification event via the channel layer."""
        try:
            from apps.core.events import _group, _publish

            payload = {
                "id": str(notification.id),
                "user_id": user_id,
                "type": notification.type,
                "title": notification.title,
                "message": notification.message,
                "resource_type": notification.resource_type,
                "resource_id": notification.resource_id,
                "is_read": notification.is_read,
                "created_at": notification.created_at.isoformat(),
            }
            _publish(
                _group(tenant_id, "notifications"),
                "event_notification",
                payload,
            )
        except Exception as exc:
            logger.debug("Failed to publish WS notification: %s", exc)
