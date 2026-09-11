"""
Alerting Rules Engine for Voyant.

Provides a rule-based alerting system that evaluates conditions against
Prometheus metrics and application events, fires notifications through
configurable channels, and exposes API endpoints for rule management
and notification tracking.
"""

from __future__ import annotations

import logging
import operator
from typing import Any

from django.db import models
from django.utils import timezone

from apps.core.models import TenantModel, UUIDModel

logger = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================


class AlertRule(TenantModel, UUIDModel):
    """
    An alerting rule that defines a condition to monitor.

    Rules are evaluated periodically by the AlertEngine against
    current metrics and application state.
    """

    class Severity(models.TextChoices):
        """Alert severity levels."""

        INFO = "info", "Info"
        WARNING = "warning", "Warning"
        ERROR = "error", "Error"
        CRITICAL = "critical", "Critical"

    class Status(models.TextChoices):
        """Rule status."""

        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        DISABLED = "disabled", "Disabled"

    name = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Human-readable rule name",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Description of what this rule monitors",
    )
    condition = models.JSONField(
        help_text=(
            "Condition definition as JSON. "
            "Structure: {metric, operator, threshold, duration_seconds, labels}"
        ),
    )
    severity = models.CharField(
        max_length=16,
        choices=Severity.choices,
        default=Severity.WARNING,
        db_index=True,
    )
    channels = models.JSONField(
        default=list,
        help_text=(
            "List of notification channels: "
            "[{'type': 'email', 'target': 'ops@company.com'}, "
            "{'type': 'webhook', 'url': 'https://hooks.example.com/alert'}]"
        ),
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    enabled = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this rule is actively evaluated",
    )
    cooldown_seconds = models.PositiveIntegerField(
        default=300,
        help_text="Minimum seconds between consecutive alerts for this rule",
    )
    labels = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional labels for filtering and grouping",
    )
    last_evaluated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this rule was last evaluated",
    )
    last_fired_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this rule last fired an alert",
    )
    fire_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of times this rule has fired",
    )
    created_by = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="User or service that created this rule",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_alert_rule"
        verbose_name = "Alert Rule"
        verbose_name_plural = "Alert Rules"
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "-updated_at"]),
            models.Index(fields=["tenant_id", "enabled", "severity"]),
            models.Index(fields=["tenant_id", "-last_fired_at"]),
        ]

    def __str__(self) -> str:
        return f"AlertRule({self.name} [{self.severity}] {self.status})"

    def is_in_cooldown(self) -> bool:
        """Check if the rule is in cooldown period."""
        if not self.last_fired_at:
            return False
        elapsed = (timezone.now() - self.last_fired_at).total_seconds()
        return elapsed < self.cooldown_seconds


class AlertNotification(TenantModel, UUIDModel):
    """
    A notification generated when an alert rule fires.

    Tracks the alert lifecycle from firing to acknowledgment.
    """

    class Status(models.TextChoices):
        """Notification status."""

        FIRING = "firing", "Firing"
        ACKNOWLEDGED = "acknowledged", "Acknowledged"
        RESOLVED = "resolved", "Resolved"
        SILENCED = "silenced", "Silenced"

    rule = models.ForeignKey(
        AlertRule,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="The rule that generated this notification",
    )
    severity = models.CharField(
        max_length=16,
        choices=AlertRule.Severity.choices,
        db_index=True,
        help_text="Severity of the alert",
    )
    message = models.TextField(
        help_text="Human-readable alert message",
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.FIRING,
        db_index=True,
    )
    metric_value = models.FloatField(
        null=True,
        blank=True,
        help_text="The metric value that triggered the alert",
    )
    threshold = models.FloatField(
        null=True,
        blank=True,
        help_text="The threshold that was breached",
    )
    labels = models.JSONField(
        default=dict,
        blank=True,
        help_text="Labels from the rule and metric at time of firing",
    )
    context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional context (metric name, duration, etc.)",
    )
    acknowledged_by = models.CharField(
        max_length=256,
        blank=True,
        default="",
        help_text="User who acknowledged this alert",
    )
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this alert was acknowledged",
    )
    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When this alert was resolved",
    )
    channel_results = models.JSONField(
        default=list,
        blank=True,
        help_text="Results of notification delivery per channel",
    )

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        db_table = "voyant_alert_notification"
        verbose_name = "Alert Notification"
        verbose_name_plural = "Alert Notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant_id", "status", "-created_at"]),
            models.Index(fields=["rule", "-created_at"]),
            models.Index(fields=["tenant_id", "severity", "-created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"AlertNotification({self.rule.name if self.rule_id else 'unknown'} "
            f"[{self.severity}] {self.status})"
        )

    def acknowledge(self, user: str) -> None:
        """Mark this notification as acknowledged."""
        self.status = self.Status.ACKNOWLEDGED
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "acknowledged_by",
                "acknowledged_at",
                "updated_at",
            ]
        )

    def resolve(self) -> None:
        """Mark this notification as resolved."""
        self.status = self.Status.RESOLVED
        self.resolved_at = timezone.now()
        self.save(
            update_fields=["status", "resolved_at", "updated_at"]
        )


# =============================================================================
# Condition Operators
# =============================================================================

_OPERATORS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}


# =============================================================================
# Alert Engine
# =============================================================================


class AlertEngine:
    """
    Evaluates alert rules against current metrics and application state.

    The engine:
    1. Loads active, enabled rules from the database.
    2. Evaluates each rule's condition against current metric values.
    3. Fires notifications for triggered rules (respecting cooldown).
    4. Delivers notifications through configured channels.
    5. Integrates with Prometheus metrics for real-time evaluation.
    """

    @staticmethod
    def evaluate_rule(rule: AlertRule) -> dict[str, Any]:
        """
        Evaluate a single alert rule against current metrics.

        Args:
            rule: The AlertRule to evaluate.

        Returns:
            Dict with evaluation result:
            {
                'triggered': bool,
                'metric_value': float | None,
                'threshold': float,
                'operator': str,
                'metric_name': str,
                'message': str,
            }
        """
        condition = rule.condition
        if not condition:
            return {
                "triggered": False,
                "metric_value": None,
                "threshold": 0,
                "operator": "",
                "metric_name": "",
                "message": "No condition defined",
            }

        metric_name = condition.get("metric", "")
        op_str = condition.get("operator", ">")
        threshold = condition.get("threshold", 0)
        labels = condition.get("labels", {})

        # Get current metric value
        metric_value = AlertEngine._get_metric_value(metric_name, labels)

        if metric_value is None:
            return {
                "triggered": False,
                "metric_value": None,
                "threshold": threshold,
                "operator": op_str,
                "metric_name": metric_name,
                "message": f"Metric '{metric_name}' not found or not available",
            }

        # Evaluate the condition
        op_func = _OPERATORS.get(op_str)
        if op_func is None:
            return {
                "triggered": False,
                "metric_value": metric_value,
                "threshold": threshold,
                "operator": op_str,
                "metric_name": metric_name,
                "message": f"Unknown operator: {op_str}",
            }

        triggered = op_func(metric_value, threshold)

        message = ""
        if triggered:
            message = (
                f"Alert: {rule.name} - "
                f"Metric '{metric_name}' value {metric_value} "
                f"{op_str} threshold {threshold}"
            )

        return {
            "triggered": triggered,
            "metric_value": metric_value,
            "threshold": threshold,
            "operator": op_str,
            "metric_name": metric_name,
            "message": message,
        }

    @staticmethod
    def _get_metric_value(
        metric_name: str, labels: dict[str, str] | None = None
    ) -> float | None:
        """
        Get the current value of a Prometheus metric.

        Integrates with the existing Prometheus client metrics
        from apps.core.lib.metrics.
        """
        try:
            from prometheus_client import REGISTRY

            # Collect all metrics from the registry
            for metric_family in REGISTRY.collect():
                if metric_family.name == metric_name:
                    for sample in metric_family.samples:
                        # Check if labels match
                        sample_labels = {
                            k: v
                            for k, v in sample.labels.items()
                            if k != "__name__"
                        }
                        if labels:
                            if all(
                                sample_labels.get(k) == v
                                for k, v in labels.items()
                            ):
                                return float(sample.value)
                        else:
                            return float(sample.value)

            return None
        except Exception as exc:
            logger.debug("Failed to get metric '%s': %s", metric_name, exc)
            return None

    @staticmethod
    def evaluate_all_rules(tenant_id: str | None = None) -> list[dict[str, Any]]:
        """
        Evaluate all active, enabled rules.

        Args:
            tenant_id: Optional tenant filter.

        Returns:
            List of evaluation results for each rule.
        """
        qs = AlertRule.objects.filter(enabled=True, status="active")
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)

        results: list[dict[str, Any]] = []
        for rule in qs:
            try:
                result = AlertEngine.evaluate_rule(rule)

                # Update last evaluated timestamp
                rule.last_evaluated_at = timezone.now()
                rule.save(update_fields=["last_evaluated_at"])

                if result["triggered"] and not rule.is_in_cooldown():
                    notification = AlertEngine._fire_alert(rule, result)
                    result["notification_id"] = str(notification.id)
                    results.append(result)
                elif result["triggered"]:
                    result["message"] = "Rule triggered but in cooldown"
                    results.append(result)
                else:
                    results.append(result)
            except Exception as exc:
                logger.error(
                    "Error evaluating rule %s: %s", rule.id, exc
                )
                results.append(
                    {
                        "rule_id": str(rule.id),
                        "triggered": False,
                        "error": str(exc),
                    }
                )

        return results

    @staticmethod
    def _fire_alert(
        rule: AlertRule, evaluation: dict[str, Any]
    ) -> AlertNotification:
        """
        Create an alert notification and deliver through configured channels.

        Args:
            rule: The rule that triggered.
            evaluation: The evaluation result.

        Returns:
            The created AlertNotification.
        """
        notification = AlertNotification.objects.create(
            rule=rule,
            severity=rule.severity,
            message=evaluation.get("message", ""),
            metric_value=evaluation.get("metric_value"),
            threshold=evaluation.get("threshold"),
            labels=rule.labels,
            context={
                "metric_name": evaluation.get("metric_name", ""),
                "operator": evaluation.get("operator", ""),
                "rule_condition": rule.condition,
            },
            status="firing",
            tenant_id=rule.tenant_id,
        )

        # Update rule fire tracking
        rule.last_fired_at = timezone.now()
        rule.fire_count += 1
        rule.save(update_fields=["last_fired_at", "fire_count", "updated_at"])

        # Deliver notifications through configured channels
        channel_results = AlertEngine._deliver_notifications(
            rule.channels, notification
        )
        notification.channel_results = channel_results
        notification.save(update_fields=["channel_results"])

        logger.warning(
            "ALERT FIRED: %s [%s] - %s (notification=%s)",
            rule.name,
            rule.severity,
            evaluation.get("message", ""),
            notification.id,
        )

        return notification

    @staticmethod
    def _deliver_notifications(
        channels: list[dict[str, Any]], notification: AlertNotification
    ) -> list[dict[str, Any]]:
        """
        Deliver notifications through configured channels.

        Supported channel types:
        - email: Send email notification
        - webhook: POST to a webhook URL
        - log: Log-based notification (default)

        Args:
            channels: List of channel configurations.
            notification: The alert notification to deliver.

        Returns:
            List of delivery results per channel.
        """
        results: list[dict[str, Any]] = []

        for channel in channels:
            channel_type = channel.get("type", "log")
            result: dict[str, Any] = {
                "channel": channel_type,
                "delivered": False,
            }

            try:
                if channel_type == "webhook":
                    result.update(
                        AlertEngine._deliver_webhook(channel, notification)
                    )
                elif channel_type == "email":
                    result.update(
                        AlertEngine._deliver_email(channel, notification)
                    )
                else:
                    # Default: log-based delivery
                    logger.info(
                        "Alert notification [%s] %s: %s",
                        notification.severity,
                        notification.rule.name if notification.rule_id else "unknown",
                        notification.message,
                    )
                    result["delivered"] = True
                    result["method"] = "log"

            except Exception as exc:
                result["error"] = str(exc)
                logger.error(
                    "Failed to deliver alert via %s: %s",
                    channel_type,
                    exc,
                )

            results.append(result)

        return results

    @staticmethod
    def _deliver_webhook(
        channel: dict[str, Any], notification: AlertNotification
    ) -> dict[str, Any]:
        """Deliver alert notification via webhook."""
        import httpx

        url = channel.get("url", "")
        if not url:
            return {"error": "No webhook URL configured"}

        payload = {
            "notification_id": str(notification.id),
            "rule_name": notification.rule.name if notification.rule_id else "",
            "severity": notification.severity,
            "message": notification.message,
            "metric_value": notification.metric_value,
            "threshold": notification.threshold,
            "status": notification.status,
            "created_at": notification.created_at.isoformat(),
            "labels": notification.labels,
        }

        try:
            response = httpx.post(
                url,
                json=payload,
                timeout=10.0,
                headers={"Content-Type": "application/json"},
            )
            return {
                "delivered": response.status_code < 300,
                "status_code": response.status_code,
                "url": url,
            }
        except httpx.RequestError as exc:
            return {"delivered": False, "error": str(exc), "url": url}

    @staticmethod
    def _deliver_email(
        channel: dict[str, Any], notification: AlertNotification
    ) -> dict[str, Any]:
        """Deliver alert notification via email (Django email backend)."""
        try:
            from django.core.mail import send_mail

            target = channel.get("target", "")
            if not target:
                return {"error": "No email target configured"}

            subject = (
                f"[{notification.severity.upper()}] "
                f"Alert: {notification.rule.name if notification.rule_id else 'Unknown'}"
            )
            body = (
                f"Alert: {notification.message}\n\n"
                f"Severity: {notification.severity}\n"
                f"Metric Value: {notification.metric_value}\n"
                f"Threshold: {notification.threshold}\n"
                f"Time: {notification.created_at.isoformat()}\n"
            )

            send_mail(
                subject=subject,
                message=body,
                from_email="voyant-alerts@localhost",
                recipient_list=[target],
                fail_silently=False,
            )
            return {"delivered": True, "target": target, "method": "email"}
        except Exception as exc:
            return {"delivered": False, "error": str(exc)}

    @staticmethod
    def check_metric_threshold(
        metric_name: str,
        threshold: float,
        op: str = ">",
        labels: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Quick check if a metric exceeds a threshold.

        Convenience method for ad-hoc metric monitoring without
        creating a full alert rule.

        Args:
            metric_name: The Prometheus metric name.
            threshold: The threshold value.
            op: Comparison operator.
            labels: Optional label filters.

        Returns:
            Dict with check result.
        """
        metric_value = AlertEngine._get_metric_value(metric_name, labels)
        if metric_value is None:
            return {
                "checked": False,
                "metric_name": metric_name,
                "message": "Metric not found",
            }

        op_func = _OPERATORS.get(op, operator.gt)
        triggered = op_func(metric_value, threshold)

        return {
            "checked": True,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "threshold": threshold,
            "operator": op,
            "triggered": triggered,
        }


# =============================================================================
# API Endpoints (Ninja Router)
# =============================================================================


def get_alerting_router():
    """
    Get the alerting API router.

    Separated to avoid circular imports.
    """
    from ninja import Field, Router, Schema

    from apps.core.middleware import get_tenant_id
    from apps.core.security.auth import require_permission

    router = Router(tags=["alerting"], auth=require_permission("read:*"))

    # ------------------------------------------------------------------
    # Schemas
    # ------------------------------------------------------------------

    class AlertRuleCreateRequest(Schema):
        """Request to create an alert rule."""

        name: str = Field(..., description="Rule name")
        description: str = Field("", description="Rule description")
        condition: dict[str, Any] = Field(
            ...,
            description="Condition: {metric, operator, threshold, labels}",
        )
        severity: str = Field("warning", description="Severity level")
        channels: list[dict[str, Any]] = Field(
            default_factory=list,
            description="Notification channels",
        )
        enabled: bool = Field(True, description="Whether the rule is enabled")
        cooldown_seconds: int = Field(
            300, description="Cooldown period in seconds"
        )
        labels: dict[str, Any] = Field(
            default_factory=dict, description="Additional labels"
        )

    class AlertRuleUpdateRequest(Schema):
        """Request to update an alert rule."""

        name: str | None = None
        description: str | None = None
        condition: dict[str, Any] | None = None
        severity: str | None = None
        channels: list[dict[str, Any]] | None = None
        enabled: bool | None = None
        cooldown_seconds: int | None = None
        labels: dict[str, Any] | None = None
        status: str | None = None

    class AlertRuleResponse(Schema):
        """Response for an alert rule."""

        id: str
        name: str
        description: str
        condition: dict[str, Any]
        severity: str
        channels: list[dict[str, Any]]
        status: str
        enabled: bool
        cooldown_seconds: int
        labels: dict[str, Any]
        fire_count: int
        last_evaluated_at: str | None
        last_fired_at: str | None
        created_by: str
        created_at: str
        updated_at: str

    class AlertRuleListResponse(Schema):
        """List of alert rules."""

        rules: list[AlertRuleResponse]
        total: int

    class AlertNotificationResponse(Schema):
        """Response for an alert notification."""

        id: str
        rule_id: str
        rule_name: str = ""
        severity: str
        message: str
        status: str
        metric_value: float | None
        threshold: float | None
        labels: dict[str, Any]
        context: dict[str, Any]
        acknowledged_by: str
        acknowledged_at: str | None
        resolved_at: str | None
        channel_results: list[dict[str, Any]]
        created_at: str

    class AlertNotificationListResponse(Schema):
        """List of alert notifications."""

        notifications: list[AlertNotificationResponse]
        total: int

    class AcknowledgeRequest(Schema):
        """Request to acknowledge an alert notification."""

        acknowledged_by: str = Field(..., description="User acknowledging")

    class EvaluateResponse(Schema):
        """Response from rule evaluation."""

        evaluated: int
        triggered: int
        results: list[dict[str, Any]]

    class MetricCheckRequest(Schema):
        """Request to check a metric threshold."""

        metric_name: str = Field(..., description="Prometheus metric name")
        threshold: float = Field(..., description="Threshold value")
        operator: str = Field(">", description="Comparison operator")
        labels: dict[str, str] = Field(
            default_factory=dict, description="Label filters"
        )

    class MetricCheckResponse(Schema):
        """Response from metric threshold check."""

        checked: bool
        metric_name: str
        metric_value: float | None = None
        threshold: float = 0
        operator: str = ""
        triggered: bool = False
        message: str = ""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _rule_to_response(rule: AlertRule) -> AlertRuleResponse:
        return AlertRuleResponse(
            id=str(rule.id),
            name=rule.name,
            description=rule.description,
            condition=rule.condition,
            severity=rule.severity,
            channels=rule.channels or [],
            status=rule.status,
            enabled=rule.enabled,
            cooldown_seconds=rule.cooldown_seconds,
            labels=rule.labels or {},
            fire_count=rule.fire_count,
            last_evaluated_at=(
                rule.last_evaluated_at.isoformat()
                if rule.last_evaluated_at
                else None
            ),
            last_fired_at=(
                rule.last_fired_at.isoformat() if rule.last_fired_at else None
            ),
            created_by=rule.created_by,
            created_at=rule.created_at.isoformat(),
            updated_at=rule.updated_at.isoformat(),
        )

    def _notif_to_response(
        notif: AlertNotification,
    ) -> AlertNotificationResponse:
        return AlertNotificationResponse(
            id=str(notif.id),
            rule_id=str(notif.rule_id),
            rule_name=notif.rule.name if notif.rule_id else "",
            severity=notif.severity,
            message=notif.message,
            status=notif.status,
            metric_value=notif.metric_value,
            threshold=notif.threshold,
            labels=notif.labels or {},
            context=notif.context or {},
            acknowledged_by=notif.acknowledged_by,
            acknowledged_at=(
                notif.acknowledged_at.isoformat()
                if notif.acknowledged_at
                else None
            ),
            resolved_at=(
                notif.resolved_at.isoformat() if notif.resolved_at else None
            ),
            channel_results=notif.channel_results or [],
            created_at=notif.created_at.isoformat(),
        )

    # ------------------------------------------------------------------
    # Alert Rules CRUD
    # ------------------------------------------------------------------

    @router.post(
        "/rules",
        response=AlertRuleResponse,
        auth=require_permission("write:alerting"),
    )
    def create_alert_rule(request, payload: AlertRuleCreateRequest):
        """Create a new alert rule."""
        tenant_id = get_tenant_id(request)

        # Validate condition structure
        condition = payload.condition
        if "metric" not in condition:
            from ninja.errors import HttpError

            raise HttpError(400, "Condition must include 'metric' field")
        if "operator" not in condition:
            from ninja.errors import HttpError

            raise HttpError(400, "Condition must include 'operator' field")
        if "threshold" not in condition:
            from ninja.errors import HttpError

            raise HttpError(400, "Condition must include 'threshold' field")

        rule = AlertRule.objects.create(
            name=payload.name,
            description=payload.description,
            condition=payload.condition,
            severity=payload.severity,
            channels=payload.channels,
            enabled=payload.enabled,
            cooldown_seconds=payload.cooldown_seconds,
            labels=payload.labels,
            tenant_id=tenant_id,
            status="active",
        )

        logger.info(
            "Created alert rule '%s' (id=%s) for tenant %s",
            rule.name,
            rule.id,
            tenant_id,
        )
        return _rule_to_response(rule)

    @router.get(
        "/rules",
        response=AlertRuleListResponse,
    )
    def list_alert_rules(
        request,
        severity: str | None = None,
        enabled: bool | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ):
        """List alert rules with optional filtering."""
        tenant_id = get_tenant_id(request)
        qs = AlertRule.objects.filter(tenant_id=tenant_id)

        if severity:
            qs = qs.filter(severity=severity)
        if enabled is not None:
            qs = qs.filter(enabled=enabled)
        if status:
            qs = qs.filter(status=status)

        total = qs.count()
        rules = qs[offset : offset + limit]

        return AlertRuleListResponse(
            rules=[_rule_to_response(r) for r in rules],
            total=total,
        )

    @router.get(
        "/rules/{rule_id}",
        response=AlertRuleResponse,
    )
    def get_alert_rule(request, rule_id: str):
        """Get an alert rule by ID."""
        tenant_id = get_tenant_id(request)
        rule = AlertRule.objects.filter(
            id=rule_id, tenant_id=tenant_id
        ).first()
        if not rule:
            from ninja.errors import HttpError

            raise HttpError(404, f"Alert rule {rule_id} not found")
        return _rule_to_response(rule)

    @router.put(
        "/rules/{rule_id}",
        response=AlertRuleResponse,
        auth=require_permission("write:alerting"),
    )
    def update_alert_rule(
        request, rule_id: str, payload: AlertRuleUpdateRequest
    ):
        """Update an existing alert rule."""
        tenant_id = get_tenant_id(request)
        rule = AlertRule.objects.filter(
            id=rule_id, tenant_id=tenant_id
        ).first()
        if not rule:
            from ninja.errors import HttpError

            raise HttpError(404, f"Alert rule {rule_id} not found")

        update_fields = []
        for field_name, value in payload.dict(exclude_unset=True).items():
            if value is not None:
                setattr(rule, field_name, value)
                update_fields.append(field_name)

        if update_fields:
            update_fields.append("updated_at")
            rule.save(update_fields=update_fields)

        return _rule_to_response(rule)

    @router.delete(
        "/rules/{rule_id}",
        auth=require_permission("write:alerting"),
    )
    def delete_alert_rule(request, rule_id: str):
        """Delete an alert rule."""
        tenant_id = get_tenant_id(request)
        rule = AlertRule.objects.filter(
            id=rule_id, tenant_id=tenant_id
        ).first()
        if not rule:
            from ninja.errors import HttpError

            raise HttpError(404, f"Alert rule {rule_id} not found")

        rule.delete()
        return {"status": "deleted", "rule_id": rule_id}

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    @router.get(
        "/notifications",
        response=AlertNotificationListResponse,
    )
    def list_notifications(
        request,
        rule_id: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ):
        """List alert notifications with optional filtering."""
        tenant_id = get_tenant_id(request)
        qs = AlertNotification.objects.filter(
            tenant_id=tenant_id
        ).select_related("rule")

        if rule_id:
            qs = qs.filter(rule_id=rule_id)
        if severity:
            qs = qs.filter(severity=severity)
        if status:
            qs = qs.filter(status=status)

        total = qs.count()
        notifs = qs[offset : offset + limit]

        return AlertNotificationListResponse(
            notifications=[_notif_to_response(n) for n in notifs],
            total=total,
        )

    @router.post(
        "/notifications/{notification_id}/acknowledge",
        auth=require_permission("write:alerting"),
    )
    def acknowledge_notification(
        request, notification_id: str, payload: AcknowledgeRequest
    ):
        """Acknowledge an alert notification."""
        tenant_id = get_tenant_id(request)
        notif = AlertNotification.objects.filter(
            id=notification_id, tenant_id=tenant_id
        ).first()
        if not notif:
            from ninja.errors import HttpError

            raise HttpError(404, f"Notification {notification_id} not found")

        if notif.status != "firing":
            from ninja.errors import HttpError

            raise HttpError(
                400,
                f"Notification is {notif.status}, only firing alerts can be acknowledged",
            )

        notif.acknowledge(payload.acknowledged_by)
        return {
            "status": "acknowledged",
            "notification_id": notification_id,
            "acknowledged_by": payload.acknowledged_by,
        }

    # ------------------------------------------------------------------
    # Evaluation & Metric Checking
    # ------------------------------------------------------------------

    @router.post(
        "/evaluate",
        response=EvaluateResponse,
        auth=require_permission("write:alerting"),
    )
    def evaluate_rules(request):
        """Evaluate all active alert rules."""
        tenant_id = get_tenant_id(request)
        results = AlertEngine.evaluate_all_rules(tenant_id)
        triggered_count = sum(1 for r in results if r.get("triggered"))

        return EvaluateResponse(
            evaluated=len(results),
            triggered=triggered_count,
            results=results,
        )

    @router.post(
        "/check-metric",
        response=MetricCheckResponse,
    )
    def check_metric(request, payload: MetricCheckRequest):
        """
        Quick-check a metric against a threshold.

        Useful for ad-hoc monitoring and dashboard widgets.
        """
        result = AlertEngine.check_metric_threshold(
            metric_name=payload.metric_name,
            threshold=payload.threshold,
            op=payload.operator,
            labels=payload.labels or None,
        )
        return MetricCheckResponse(
            checked=result.get("checked", False),
            metric_name=result.get("metric_name", ""),
            metric_value=result.get("metric_value"),
            threshold=result.get("threshold", 0),
            operator=result.get("operator", ""),
            triggered=result.get("triggered", False),
            message=result.get("message", ""),
        )

    return router
