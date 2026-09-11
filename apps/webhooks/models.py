"""Webhook models — subscription endpoints and delivery tracking."""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel

__all__ = ["Webhook", "WebhookDelivery"]


class Webhook(TenantModel, UUIDModel):
    """A registered webhook endpoint.

    Subscribes to one or more event types. When a matching event fires,
    the webhook service sends an HTTP POST with a JSON payload and an
    HMAC-SHA256 signature header.
    """

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    url = models.URLField(
        max_length=2048,
        help_text="Target URL to receive POST requests",
    )
    events = models.JSONField(
        default=list,
        help_text='List of subscribed event types: ["job.completed", "pipeline.failed"]',
    )
    secret = models.CharField(
        max_length=255,
        help_text="Shared secret for HMAC-SHA256 signature verification",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )
    description = models.TextField(blank=True, default="")

    # Retry policy
    retry_policy = models.JSONField(
        default=dict,
        help_text=(
            'Retry config: {"max_retries": 3, "initial_backoff_seconds": 1, '
            '"backoff_multiplier": 2}'
        ),
    )

    # Metadata
    headers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional HTTP headers to include in delivery requests",
    )
    last_triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of last delivery attempt",
    )
    failure_count = models.IntegerField(
        default=0,
        help_text="Consecutive failure count; auto-disabled after threshold",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "voyant_webhook"
        verbose_name = "Webhook"
        verbose_name_plural = "Webhooks"
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"Webhook({self.url} → {self.events})"


class WebhookDelivery(TenantModel, UUIDModel):
    """A single delivery attempt for a webhook event.

    Tracks status, attempts, and error details for auditability and
    debugging of webhook delivery failures.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"

    webhook = models.ForeignKey(
        Webhook,
        on_delete=models.CASCADE,
        related_name="deliveries",
        help_text="Parent webhook subscription",
    )
    event_type = models.CharField(
        max_length=128,
        db_index=True,
        help_text="Event type that triggered this delivery",
    )
    payload = models.JSONField(
        default=dict,
        help_text="Full event payload sent (or to be sent) to the endpoint",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    attempts = models.IntegerField(
        default=0,
        help_text="Number of delivery attempts so far",
    )
    max_retries = models.IntegerField(
        default=3,
        help_text="Maximum retry attempts for this delivery",
    )
    last_response_code = models.IntegerField(
        null=True,
        blank=True,
        help_text="HTTP status code from the last attempt",
    )
    last_error = models.TextField(
        blank=True,
        default="",
        help_text="Error message from the last failed attempt",
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when delivery succeeded",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "voyant_webhook_delivery"
        verbose_name = "Webhook Delivery"
        verbose_name_plural = "Webhook Deliveries"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["webhook", "status"]),
            models.Index(fields=["tenant_id", "event_type", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"Delivery({self.event_type} → {self.status} [{self.attempts} attempts])"
