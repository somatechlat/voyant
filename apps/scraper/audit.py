"""
Scrape Audit Log — tracks every step of a scraping job in real-time.

Records: navigation, scrolling, clicks, extractions, errors, timing.
Queryable via API for live progress monitoring.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScrapeStep:
    """A single step in a scrape execution."""

    step_number: int
    action: str  # navigate, scroll, click, wait, extract, error
    status: str  # running, succeeded, failed, skipped
    started_at: float
    finished_at: float = 0.0
    duration_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class ScrapeAuditLog:
    """
    In-memory audit log for a single scrape job.

    Tracks every step with timing, status, and details.
    Queryable for live progress monitoring.

    Usage:
        audit = ScrapeAuditLog(job_id)
        with audit.step("navigate", url="https://...") as s:
            page.goto(url)
            s.detail("status_code", 200)
            s.detail("page_title", "Example")
    """

    def __init__(self, job_id: str):
        self.job_id = job_id
        self.steps: list[ScrapeStep] = []
        self.started_at = time.time()
        self.finished_at = 0.0
        self._counter = 0

    def step(self, action: str, **initial_details: Any) -> _StepContext:
        """Start tracking a new step. Use as context manager."""
        self._counter += 1
        s = ScrapeStep(
            step_number=self._counter,
            action=action,
            status="running",
            started_at=time.time(),
            details=dict(initial_details),
        )
        self.steps.append(s)
        return _StepContext(self, s)

    def to_dict(self) -> dict[str, Any]:
        """Export full audit log as dict."""
        return {
            "job_id": self.job_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_duration_ms": (self.finished_at or time.time() - self.started_at)
            * 1000,
            "step_count": len(self.steps),
            "steps": [
                {
                    "step": s.step_number,
                    "action": s.action,
                    "status": s.status,
                    "duration_ms": s.duration_ms,
                    "details": s.details,
                    "error": s.error,
                }
                for s in self.steps
            ],
        }

    def to_live_feed(self) -> list[str]:
        """Export as human-readable live feed lines."""
        lines = []
        for s in self.steps:
            status_icon = {
                "running": "⏳",
                "succeeded": "✅",
                "failed": "❌",
                "skipped": "⏭️",
            }.get(s.status, "?")
            detail_str = ""
            if s.details:
                parts = [f"{k}={v}" for k, v in list(s.details.items())[:3]]
                detail_str = f" ({', '.join(parts)})"
            error_str = f" ERROR: {s.error}" if s.error else ""
            duration = f" [{s.duration_ms:.0f}ms]" if s.duration_ms else ""
            lines.append(
                f"{status_icon} Step {s.step_number}: {s.action}{detail_str}{duration}{error_str}"
            )
        return lines

    def summary(self) -> dict[str, Any]:
        """Quick summary of the scrape execution."""
        succeeded = sum(1 for s in self.steps if s.status == "succeeded")
        failed = sum(1 for s in self.steps if s.status == "failed")
        extracted = 0
        for s in self.steps:
            if s.action == "extract" and s.status == "succeeded":
                extracted += len(s.details.get("fields", []))
        return {
            "job_id": self.job_id,
            "total_steps": len(self.steps),
            "succeeded": succeeded,
            "failed": failed,
            "fields_extracted": extracted,
            "total_duration_ms": (self.finished_at or time.time() - self.started_at)
            * 1000,
            "pages_scraped": sum(
                1
                for s in self.steps
                if s.action == "navigate" and s.status == "succeeded"
            ),
        }


class _StepContext:
    """Context manager for a single audit step."""

    def __init__(self, log: ScrapeAuditLog, step: ScrapeStep):
        self._log = log
        self._step = step

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._step.finished_at = time.time()
        self._step.duration_ms = (self._step.finished_at - self._step.started_at) * 1000
        if exc_type:
            self._step.status = "failed"
            self._step.error = str(exc_val)[:500]
        elif self._step.status == "running":
            self._step.status = "succeeded"
        return False  # Don't suppress exceptions

    def detail(self, key: str, value: Any) -> None:
        """Add a detail to the current step."""
        self._step.details[key] = value

    def fail(self, error: str) -> None:
        """Mark step as failed."""
        self._step.status = "failed"
        self._step.error = error

    def skip(self, reason: str = "") -> None:
        """Mark step as skipped."""
        self._step.status = "skipped"
        if reason:
            self._step.details["skip_reason"] = reason


# In-memory store for active audit logs (keyed by job_id)
_active_logs: dict[str, ScrapeAuditLog] = {}


def get_audit_log(job_id: str) -> ScrapeAuditLog | None:
    """Get an active audit log by job ID."""
    return _active_logs.get(job_id)


def create_audit_log(job_id: str) -> ScrapeAuditLog:
    """Create and register a new audit log."""
    log = ScrapeAuditLog(job_id)
    _active_logs[job_id] = log
    return log


def finalize_audit_log(job_id: str) -> dict[str, Any] | None:
    """Finalize and export an audit log, removing it from active store."""
    log = _active_logs.pop(job_id, None)
    if log:
        log.finished_at = time.time()
        return log.to_dict()
    return None
