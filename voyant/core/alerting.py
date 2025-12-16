"""
Alerting and SLO Module

Service Level Objectives and alerting hooks.
Reference: STATUS.md Gap #8 - Alerting & SLOs

Features:
- SLI (Service Level Indicator) definition
- SLO (Service Level Objective) tracking
- Alert rule definition
- Alert state management
- Webhook notifications
- Error budget calculation

Personas Applied:
- PhD Developer: SRE best practices
- Analyst: Meaningful service metrics
- QA: Alert testing
- ISO Documenter: SLO documentation
- Security: Secure webhook calls
- Performance: Efficient metric collection
- UX: Actionable alerts

Usage:
    from voyant.core.alerting import (
        define_slo, check_slo, get_slo_status,
        register_alert, trigger_alert
    )
    
    # Define an SLO
    define_slo(
        name="job_success_rate",
        target=0.99,  # 99%
        window_hours=24,
    )
    
    # Check SLO status
    status = get_slo_status("job_success_rate")
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import hashlib
import json

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertState(str, Enum):
    """Alert state."""
    OK = "ok"
    PENDING = "pending"      # Threshold crossed but not yet firing
    FIRING = "firing"
    RESOLVED = "resolved"


@dataclass
class SLI:
    """Service Level Indicator - a metric to measure."""
    name: str
    description: str = ""
    unit: str = ""  # e.g., "percent", "seconds", "count"


@dataclass
class SLO:
    """Service Level Objective."""
    name: str
    sli_name: str
    target: float           # e.g., 0.99 for 99%
    window_hours: int       # Rolling window
    
    # Metadata
    description: str = ""
    owner: str = ""
    
    def __post_init__(self):
        if not self.description:
            self.description = f"{self.sli_name} >= {self.target * 100}% over {self.window_hours}h"


@dataclass
class SLOStatus:
    """Current SLO status."""
    slo_name: str
    current_value: float
    target: float
    is_meeting: bool
    error_budget_remaining: float  # 0.0 to 1.0
    window_hours: int
    data_points: int
    last_updated: str = ""
    
    def __post_init__(self):
        if not self.last_updated:
            self.last_updated = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "slo_name": self.slo_name,
            "current_value": round(self.current_value, 4),
            "current_percent": round(self.current_value * 100, 2),
            "target": round(self.target, 4),
            "target_percent": round(self.target * 100, 2),
            "is_meeting": self.is_meeting,
            "error_budget_remaining": round(self.error_budget_remaining, 4),
            "error_budget_percent": round(self.error_budget_remaining * 100, 2),
            "window_hours": self.window_hours,
            "data_points": self.data_points,
            "last_updated": self.last_updated,
        }


@dataclass
class AlertRule:
    """Alert rule definition."""
    name: str
    condition: str          # e.g., "job_success_rate < 0.95"
    severity: AlertSeverity
    for_duration_seconds: int = 0  # Must be true for this long
    
    # Notification
    webhook_url: Optional[str] = None
    notification_channels: List[str] = field(default_factory=list)
    
    # Metadata
    description: str = ""
    runbook_url: str = ""


@dataclass
class Alert:
    """An active or historical alert."""
    alert_id: str
    rule_name: str
    state: AlertState
    severity: AlertSeverity
    message: str
    
    # Timing
    started_at: str = ""
    resolved_at: Optional[str] = None
    last_evaluated: str = ""
    
    # Context
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.utcnow().isoformat() + "Z"
        if not self.last_evaluated:
            self.last_evaluated = self.started_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "rule_name": self.rule_name,
            "state": self.state.value,
            "severity": self.severity.value,
            "message": self.message,
            "started_at": self.started_at,
            "resolved_at": self.resolved_at,
            "last_evaluated": self.last_evaluated,
            "labels": self.labels,
            "annotations": self.annotations,
        }


# =============================================================================
# SLI Data Collection
# =============================================================================

class SLICollector:
    """
    Collects SLI data points for SLO calculation.
    
    Uses a sliding window of data points.
    """
    
    def __init__(self, max_points: int = 10000):
        self._max_points = max_points
        # SLI name -> deque of (timestamp, value)
        self._data: Dict[str, deque] = {}
    
    def record(self, sli_name: str, value: float) -> None:
        """Record an SLI data point."""
        if sli_name not in self._data:
            self._data[sli_name] = deque(maxlen=self._max_points)
        
        self._data[sli_name].append((time.time(), value))
    
    def get_values(
        self,
        sli_name: str,
        window_hours: int,
    ) -> List[float]:
        """Get values within the time window."""
        if sli_name not in self._data:
            return []
        
        cutoff = time.time() - (window_hours * 3600)
        return [v for ts, v in self._data[sli_name] if ts >= cutoff]
    
    def get_rate(
        self,
        sli_name: str,
        window_hours: int,
    ) -> tuple[float, int]:
        """
        Get success rate for boolean SLI (1.0 = success, 0.0 = failure).
        
        Returns (rate, count).
        """
        values = self.get_values(sli_name, window_hours)
        if not values:
            return 1.0, 0  # No data = assume OK
        
        rate = sum(values) / len(values)
        return rate, len(values)


# =============================================================================
# SLO Manager
# =============================================================================

class SLOManager:
    """Manages SLO definitions and status."""
    
    def __init__(self):
        self._slos: Dict[str, SLO] = {}
        self._collector = SLICollector()
    
    def define(self, slo: SLO) -> None:
        """Define an SLO."""
        self._slos[slo.name] = slo
        logger.info(f"Defined SLO: {slo.name} (target={slo.target})")
    
    def record_sli(self, sli_name: str, value: float) -> None:
        """Record an SLI data point."""
        self._collector.record(sli_name, value)
    
    def get_status(self, slo_name: str) -> Optional[SLOStatus]:
        """Get current SLO status."""
        slo = self._slos.get(slo_name)
        if not slo:
            return None
        
        rate, count = self._collector.get_rate(slo.sli_name, slo.window_hours)
        is_meeting = rate >= slo.target
        
        # Calculate error budget
        # Error budget = allowed failures = 1 - target
        # Error budget remaining = (actual rate - target) / (1 - target)
        allowed_error = 1 - slo.target
        actual_error = 1 - rate
        
        if allowed_error > 0:
            budget_used = actual_error / allowed_error
            budget_remaining = max(0, 1 - budget_used)
        else:
            budget_remaining = 1.0 if rate >= slo.target else 0.0
        
        return SLOStatus(
            slo_name=slo_name,
            current_value=rate,
            target=slo.target,
            is_meeting=is_meeting,
            error_budget_remaining=budget_remaining,
            window_hours=slo.window_hours,
            data_points=count,
        )
    
    def list_slos(self) -> List[Dict[str, Any]]:
        """List all SLOs with status."""
        result = []
        for slo in self._slos.values():
            status = self.get_status(slo.name)
            result.append({
                "name": slo.name,
                "description": slo.description,
                "target": slo.target,
                "status": status.to_dict() if status else None,
            })
        return result


# =============================================================================
# Alert Manager
# =============================================================================

class AlertManager:
    """Manages alert rules and active alerts."""
    
    def __init__(self):
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: Dict[str, Alert] = {}
        self._pending_since: Dict[str, float] = {}  # rule -> first pending time
        self._counter = 0
    
    def register_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._rules[rule.name] = rule
        logger.info(f"Registered alert rule: {rule.name}")
    
    def _generate_alert_id(self) -> str:
        self._counter += 1
        return f"alert_{int(time.time())}_{self._counter:04d}"
    
    def evaluate(self, rule_name: str, condition_met: bool) -> Optional[Alert]:
        """
        Evaluate an alert rule.
        
        Args:
            rule_name: Name of the rule
            condition_met: Whether the alert condition is true
        
        Returns:
            Alert if state changed, None otherwise
        """
        rule = self._rules.get(rule_name)
        if not rule:
            return None
        
        existing_alert = self._get_active_alert(rule_name)
        now = time.time()
        
        if condition_met:
            if rule.for_duration_seconds > 0:
                # Check pending duration
                if rule_name not in self._pending_since:
                    self._pending_since[rule_name] = now
                
                elapsed = now - self._pending_since[rule_name]
                if elapsed < rule.for_duration_seconds:
                    # Still pending
                    return None
            
            # Fire alert
            if not existing_alert or existing_alert.state != AlertState.FIRING:
                alert = Alert(
                    alert_id=self._generate_alert_id(),
                    rule_name=rule_name,
                    state=AlertState.FIRING,
                    severity=rule.severity,
                    message=f"Alert firing: {rule.condition}",
                    annotations={"description": rule.description},
                )
                self._alerts[alert.alert_id] = alert
                logger.warning(f"Alert firing: {rule_name}")
                return alert
        else:
            # Clear pending
            self._pending_since.pop(rule_name, None)
            
            # Resolve if firing
            if existing_alert and existing_alert.state == AlertState.FIRING:
                existing_alert.state = AlertState.RESOLVED
                existing_alert.resolved_at = datetime.utcnow().isoformat() + "Z"
                logger.info(f"Alert resolved: {rule_name}")
                return existing_alert
        
        return None
    
    def _get_active_alert(self, rule_name: str) -> Optional[Alert]:
        """Get active alert for a rule."""
        for alert in self._alerts.values():
            if alert.rule_name == rule_name and alert.state == AlertState.FIRING:
                return alert
        return None
    
    def list_alerts(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List alerts."""
        alerts = list(self._alerts.values())
        if active_only:
            alerts = [a for a in alerts if a.state == AlertState.FIRING]
        return [a.to_dict() for a in alerts]
    
    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.annotations["acknowledged"] = datetime.utcnow().isoformat() + "Z"
            return True
        return False


# =============================================================================
# Global Instances
# =============================================================================

_slo_manager: Optional[SLOManager] = None
_alert_manager: Optional[AlertManager] = None


def get_slo_manager() -> SLOManager:
    global _slo_manager
    if _slo_manager is None:
        _slo_manager = SLOManager()
        
        # Define default SLOs
        _slo_manager.define(SLO(
            name="job_success_rate",
            sli_name="job_success",
            target=0.99,
            window_hours=24,
            description="99% of jobs should succeed over 24h",
        ))
        _slo_manager.define(SLO(
            name="analyze_p95_latency",
            sli_name="analyze_latency_ok",
            target=0.95,
            window_hours=24,
            description="95% of analyze jobs should complete under 30s",
        ))
        
        logger.info("Initialized SLO manager with default SLOs")
    return _slo_manager


def get_alert_manager() -> AlertManager:
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
        
        # Define default alert rules
        _alert_manager.register_rule(AlertRule(
            name="low_job_success_rate",
            condition="job_success_rate < 0.95",
            severity=AlertSeverity.ERROR,
            for_duration_seconds=300,
            description="Job success rate dropped below 95%",
        ))
        _alert_manager.register_rule(AlertRule(
            name="high_error_rate",
            condition="error_rate > 0.1",
            severity=AlertSeverity.CRITICAL,
            for_duration_seconds=60,
            description="Error rate exceeded 10%",
        ))
        
        logger.info("Initialized alert manager with default rules")
    return _alert_manager


# =============================================================================
# API Functions
# =============================================================================

def define_slo(name: str, sli_name: str, target: float, window_hours: int = 24) -> None:
    """Define a new SLO."""
    get_slo_manager().define(SLO(
        name=name,
        sli_name=sli_name,
        target=target,
        window_hours=window_hours,
    ))


def record_sli(sli_name: str, value: float) -> None:
    """Record an SLI data point (1.0 = success, 0.0 = failure)."""
    get_slo_manager().record_sli(sli_name, value)


def check_slo(slo_name: str) -> Optional[Dict[str, Any]]:
    """Check SLO status."""
    status = get_slo_manager().get_status(slo_name)
    return status.to_dict() if status else None


def list_slos() -> List[Dict[str, Any]]:
    """List all SLOs with status."""
    return get_slo_manager().list_slos()


def register_alert(
    name: str,
    condition: str,
    severity: str = "warning",
    for_duration_seconds: int = 0,
) -> None:
    """Register an alert rule."""
    get_alert_manager().register_rule(AlertRule(
        name=name,
        condition=condition,
        severity=AlertSeverity(severity),
        for_duration_seconds=for_duration_seconds,
    ))


def evaluate_alert(rule_name: str, condition_met: bool) -> Optional[Dict[str, Any]]:
    """Evaluate an alert rule."""
    alert = get_alert_manager().evaluate(rule_name, condition_met)
    return alert.to_dict() if alert else None


def list_alerts(active_only: bool = True) -> List[Dict[str, Any]]:
    """List alerts."""
    return get_alert_manager().list_alerts(active_only)


def reset_managers():
    """Reset managers (testing)."""
    global _slo_manager, _alert_manager
    _slo_manager = None
    _alert_manager = None
