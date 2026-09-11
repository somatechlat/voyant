"""Webhook delivery service with HMAC-SHA256 signing and exponential backoff."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from apps.webhooks.models import Webhook, WebhookDelivery

logger = logging.getLogger("voyant.webhooks")

__all__ = ["WebhookService", "dispatch"]


# Default retry policy
_DEFAULT_RETRY_POLICY = {
    "max_retries": 3,
    "initial_backoff_seconds": 1,
    "backoff_multiplier": 2,
}


class WebhookService:
    """Dispatches webhook events to registered endpoints.

    For each subscribed webhook the service:
    1. Creates a WebhookDelivery record (status=pending).
    2. Sends an HTTP POST with JSON payload and HMAC-SHA256 signature.
    3. On failure, retries with exponential backoff (up to max_retries).
    4. Updates delivery status after each attempt.

    Usage::

        service = WebhookService(tenant_id="t1")
        service.dispatch("job.completed", {"job_id": "j1", "status": "done"})
    """

    def __init__(self, tenant_id: str | None = None) -> None:
        self._tenant_id = tenant_id

    def dispatch(self, event_type: str, payload: dict[str, Any]) -> list[WebhookDelivery]:
        """Dispatch an event to all subscribed active webhooks.

        Parameters
        ----------
        event_type:
            The event type string (e.g. ``"job.completed"``).
        payload:
            Event payload as a dict.

        Returns
        -------
        list[WebhookDelivery]
            List of delivery records created.
        """
        webhooks = self._get_subscribed_webhooks(event_type)
        deliveries: list[WebhookDelivery] = []

        for webhook in webhooks:
            delivery = self._create_delivery(webhook, event_type, payload)
            deliveries.append(delivery)
            self._attempt_delivery(webhook, delivery)

        return deliveries

    def retry_failed(self) -> int:
        """Retry all pending/failed deliveries that haven't exceeded max retries.

        Returns
        -------
        int
            Number of deliveries retried.
        """
        qs = WebhookDelivery.objects.filter(
            status__in=[
                WebhookDelivery.Status.PENDING,
                WebhookDelivery.Status.FAILED,
                WebhookDelivery.Status.RETRYING,
            ],
        )
        if self._tenant_id:
            qs = qs.filter(tenant_id=self._tenant_id)

        retried = 0
        for delivery in qs.select_related("webhook"):
            if delivery.attempts >= delivery.max_retries:
                continue
            delivery.status = WebhookDelivery.Status.RETRYING
            delivery.save(update_fields=["status", "updated_at"])
            self._attempt_delivery(delivery.webhook, delivery)
            retried += 1

        return retried

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_subscribed_webhooks(self, event_type: str) -> list[Webhook]:
        """Fetch active webhooks subscribed to the given event type."""
        try:
            qs = Webhook.objects.filter(status=Webhook.STATUS_ACTIVE)
            if self._tenant_id:
                qs = qs.filter(tenant_id=self._tenant_id)

            # Filter in Python since events is a JSON array
            webhooks: list[Webhook] = []
            for wh in qs:
                events = wh.events or []
                if event_type in events or "*" in events:
                    webhooks.append(wh)
            return webhooks
        except Exception:
            logger.debug("Webhook query failed", exc_info=True)
            return []

    def _create_delivery(
        self, webhook: Webhook, event_type: str, payload: dict[str, Any]
    ) -> WebhookDelivery:
        """Create a WebhookDelivery record."""
        retry_cfg = webhook.retry_policy or _DEFAULT_RETRY_POLICY
        max_retries = retry_cfg.get("max_retries", 3)

        return WebhookDelivery.objects.create(
            webhook=webhook,
            event_type=event_type,
            payload=payload,
            status=WebhookDelivery.Status.PENDING,
            max_retries=max_retries,
            tenant_id=webhook.tenant_id,
        )

    def _attempt_delivery(
        self, webhook: Webhook, delivery: WebhookDelivery
    ) -> None:
        """Attempt to deliver the webhook payload with retries and backoff."""
        retry_cfg = webhook.retry_policy or _DEFAULT_RETRY_POLICY
        max_retries = retry_cfg.get("max_retries", 3)
        initial_backoff = retry_cfg.get("initial_backoff_seconds", 1)
        backoff_multiplier = retry_cfg.get("backoff_multiplier", 2)

        for attempt in range(max_retries):
            delivery.attempts = attempt + 1
            delivery.status = WebhookDelivery.Status.RETRYING

            try:
                response_code, error = self._send(webhook, delivery)
                delivery.last_response_code = response_code

                if 200 <= response_code < 300:
                    delivery.status = WebhookDelivery.Status.SUCCESS
                    delivery.last_error = ""
                    webhook.failure_count = 0
                    webhook.save(update_fields=["failure_count", "updated_at"])
                    logger.info(
                        "Webhook delivered: event=%s url=%s code=%d",
                        delivery.event_type,
                        webhook.url,
                        response_code,
                    )
                    break
                else:
                    delivery.last_error = error or f"HTTP {response_code}"
                    logger.warning(
                        "Webhook delivery failed: event=%s url=%s code=%d attempt=%d",
                        delivery.event_type,
                        webhook.url,
                        response_code,
                        attempt + 1,
                    )
            except Exception as exc:
                delivery.last_error = str(exc)
                logger.warning(
                    "Webhook delivery error: event=%s url=%s error=%s attempt=%d",
                    delivery.event_type,
                    webhook.url,
                    exc,
                    attempt + 1,
                )

            # Exponential backoff before next retry
            if attempt < max_retries - 1:
                backoff = initial_backoff * (backoff_multiplier ** attempt)
                time.sleep(min(backoff, 30))  # Cap at 30 seconds
        else:
            # All retries exhausted
            delivery.status = WebhookDelivery.Status.FAILED
            webhook.failure_count += 1
            webhook.save(update_fields=["failure_count", "updated_at"])

            # Auto-disable after 10 consecutive failures
            if webhook.failure_count >= 10:
                webhook.status = Webhook.STATUS_INACTIVE
                webhook.save(update_fields=["status", "updated_at"])
                logger.error(
                    "Webhook auto-disabled after 10 consecutive failures: %s",
                    webhook.url,
                )

        delivery.save(
            update_fields=[
                "status",
                "attempts",
                "last_response_code",
                "last_error",
                "updated_at",
            ]
        )

        # Update last_triggered_at
        from django.utils import timezone

        webhook.last_triggered_at = timezone.now()
        webhook.save(update_fields=["last_triggered_at", "updated_at"])

    @staticmethod
    def _sign_payload(payload_bytes: bytes, secret: str) -> str:
        """Generate HMAC-SHA256 signature for the payload."""
        return hmac.new(
            secret.encode("utf-8"),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def _send(
        webhook: Webhook, delivery: WebhookDelivery
    ) -> tuple[int, str]:
        """Send the HTTP POST to the webhook URL.

        Returns (status_code, error_message).
        """
        payload_bytes = json.dumps(delivery.payload, default=str).encode("utf-8")
        signature = WebhookService._sign_payload(payload_bytes, webhook.secret)

        headers = {
            "Content-Type": "application/json",
            "X-Voyant-Event": delivery.event_type,
            "X-Voyant-Signature": f"sha256={signature}",
            "X-Voyant-Delivery-ID": str(delivery.id),
            "User-Agent": "Voyant-Webhooks/1.0",
        }
        # Merge custom headers
        headers.update(webhook.headers or {})

        with httpx.Client(timeout=10.0) as client:
            response = client.post(
                webhook.url,
                content=payload_bytes,
                headers=headers,
            )
            return response.status_code, ""


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def dispatch(
    event_type: str,
    payload: dict[str, Any],
    tenant_id: str | None = None,
) -> list[WebhookDelivery]:
    """Convenience function to dispatch a webhook event.

    Parameters
    ----------
    event_type:
        Event type string.
    payload:
        Event payload.
    tenant_id:
        Optional tenant scope.

    Returns
    -------
    list[WebhookDelivery]
    """
    service = WebhookService(tenant_id=tenant_id)
    return service.dispatch(event_type, payload)
