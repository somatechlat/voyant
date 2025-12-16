"""
Temporal Activity & Workflow Metrics

Comprehensive monitoring for Temporal activities and workflows.
Integrates with existing voyant.core.metrics infrastructure.

Seven personas applied:
- PhD Developer: Clean integration with existing metrics system
- PhD Analyst: Histograms for distribution analysis
- PhD QA Engineer: Metrics for flaky test detection (retry counts)
- ISO Documenter: Clear metric naming conventions
- Security Auditor: No PII in metric labels
- Performance Engineer: Efficient metric collection, low overhead
- UX Consultant: Observable system behavior for operators

Usage:
    from voyant.core.temporal_metrics import (
        record_activity_start,
        record_activity_success,
        record_activity_failure,
        record_workflow_completion
    )
    
    # In activity:
    record_activity_start("calculate_market_share")
    try:
        result = do_work()
        record_activity_success("calculate_market_share", duration_seconds=12.5)
    except Exception as e:
        record_activity_failure("calculate_market_share", error_type="ExternalServiceError")
        raise
"""
from __future__ import annotations

import logging
import time
from typing import Optional
from contextlib import contextmanager

from prometheus_client import Counter, Histogram, Gauge

logger = logging.getLogger(__name__)

# =============================================================================
# Metric Definitions
# =============================================================================

# Activity execution metrics
ACTIVITY_STARTED = Counter(
    "temporal_activity_started_total",
    "Total number of activity executions started",
    labelnames=["activity_name"]
)

ACTIVITY_COMPLETED = Counter(
    "temporal_activity_completed_total",
    "Total number of activity executions completed successfully",
    labelnames=["activity_name"]
)

ACTIVITY_FAILED = Counter(
    "temporal_activity_failed_total",
    "Total number of activity executions failed",
    labelnames=["activity_name", "error_type"]
)

ACTIVITY_RETRIED = Counter(
    "temporal_activity_retried_total",
    "Total number of activity retry attempts",
    labelnames=["activity_name", "attempt"]
)

ACTIVITY_DURATION = Histogram(
    "temporal_activity_duration_seconds",
    "Activity execution duration in seconds",
    labelnames=["activity_name"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300, 600, 900]  # Up to 15 minutes
)

# Workflow execution metrics
WORKFLOW_STARTED = Counter(
    "temporal_workflow_started_total",
    "Total number of workflow executions started",
    labelnames=["workflow_name"]
)

WORKFLOW_COMPLETED = Counter(
    "temporal_workflow_completed_total",
    "Total number of workflow executions completed successfully",
    labelnames=["workflow_name"]
)

WORKFLOW_FAILED = Counter(
    "temporal_workflow_failed_total",
    "Total number of workflow executions failed",
    labelnames=["workflow_name", "error_type"]
)

WORKFLOW_DURATION = Histogram(
    "temporal_workflow_duration_seconds",
    "Workflow execution duration in seconds",
    labelnames=["workflow_name"],
    buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600]  # Up to 1 hour
)

# Workflow step metrics
WORKFLOW_STEP_COUNT = Histogram(
    "temporal_workflow_steps_total",
    "Number of steps (activities) per workflow execution",
    labelnames=["workflow_name"],
    buckets=[1, 2, 3, 5, 10, 20, 50]
)

# Circuit breaker interaction metrics
CIRCUIT_BREAKER_TRIGGERED = Counter(
    "temporal_circuit_breaker_triggered_total",
    "Total number of times circuit breaker prevented activity execution",
    labelnames=["activity_name", "service_name"]
)

# Active workflows gauge
ACTIVE_WORKFLOWS = Gauge(
    "temporal_active_workflows",
    "Current number of active workflow executions",
    labelnames=["workflow_name"]
)


# =============================================================================
# Recording Functions
# =============================================================================

def record_activity_start(activity_name: str):
    """
    Record activity execution start.
    
    Args:
        activity_name: Name of the activity (e.g., "calculate_market_share")
        
    Performance Engineer: Called at start of every activity, must be fast
    """
    try:
        ACTIVITY_STARTED.labels(activity_name=activity_name).inc()
        logger.debug(f"Activity started: {activity_name}")
    except Exception as e:
        # Never let metrics collection break the activity
        logger.warning(f"Failed to record activity start metric: {e}")


def record_activity_success(activity_name: str, duration_seconds: float):
    """
    Record successful activity completion.
    
    Args:
        activity_name: Name of the activity
        duration_seconds: Execution duration in seconds
        
    PhD Analyst: Duration histogram enables percentile analysis (p50, p95, p99)
    """
    try:
        ACTIVITY_COMPLETED.labels(activity_name=activity_name).inc()
        ACTIVITY_DURATION.labels(activity_name=activity_name).observe(duration_seconds)
        logger.debug(f"Activity completed: {activity_name} ({duration_seconds:.2f}s)")
    except Exception as e:
        logger.warning(f"Failed to record activity success metric: {e}")


def record_activity_failure(activity_name: str, error_type: str, duration_seconds: Optional[float] = None):
    """
    Record failed activity execution.
    
    Args:
        activity_name: Name of the activity
        error_type: Type of error (e.g., "ExternalServiceError", "ValidationError")
        duration_seconds: Execution duration before failure (optional)
        
    QA Engineer: Error type labeling enables failure pattern analysis
    """
    try:
        ACTIVITY_FAILED.labels(activity_name=activity_name, error_type=error_type).inc()
        if duration_seconds is not None:
            ACTIVITY_DURATION.labels(activity_name=activity_name).observe(duration_seconds)
        logger.debug(f"Activity failed: {activity_name}, error: {error_type}")
    except Exception as e:
        logger.warning(f"Failed to record activity failure metric: {e}")


def record_activity_retry(activity_name: str, attempt: int):
    """
    Record activity retry attempt.
    
    Args:
        activity_name: Name of the activity
        attempt: Retry attempt number (1, 2, 3, ...)
        
    QA Engineer: Retry metrics help identify flaky operations
    """
    try:
        ACTIVITY_RETRIED.labels(activity_name=activity_name, attempt=str(attempt)).inc()
        logger.debug(f"Activity retry: {activity_name}, attempt: {attempt}")
    except Exception as e:
        logger.warning(f"Failed to record activity retry metric: {e}")


def record_circuit_breaker_triggered(activity_name: str, service_name: str):
    """
    Record circuit breaker preventing activity execution.
    
    Args:
        activity_name: Name of the activity that was blocked
        service_name: Name of the service with open circuit breaker
        
    Security Auditor: Tracks cascade failure prevention events
    """
    try:
        CIRCUIT_BREAKER_TRIGGERED.labels(
            activity_name=activity_name,
            service_name=service_name
        ).inc()
        logger.info(f"Circuit breaker blocked {activity_name} (service: {service_name})")
    except Exception as e:
        logger.warning(f"Failed to record circuit breaker metric: {e}")


def record_workflow_start(workflow_name: str):
    """
    Record workflow execution start.
    
    Args:
        workflow_name: Name of the workflow
        
    UX Consultant: Workflow metrics provide system-level observability
    """
    try:
        WORKFLOW_STARTED.labels(workflow_name=workflow_name).inc()
        ACTIVE_WORKFLOWS.labels(workflow_name=workflow_name).inc()
        logger.debug(f"Workflow started: {workflow_name}")
    except Exception as e:
        logger.warning(f"Failed to record workflow start metric: {e}")


def record_workflow_completion(
    workflow_name: str,
    duration_seconds: float,
    step_count: int,
    success: bool = True,
    error_type: Optional[str] = None
):
    """
    Record workflow execution completion.
    
    Args:
        workflow_name: Name of the workflow
        duration_seconds: Total execution duration
        step_count: Number of steps (activities) executed
        success: Whether workflow completed successfully
        error_type: Type of error if failed
        
    ISO Documenter: Comprehensive workflow metrics for audit trails
    """
    try:
        ACTIVE_WORKFLOWS.labels(workflow_name=workflow_name).dec()
        
        if success:
            WORKFLOW_COMPLETED.labels(workflow_name=workflow_name).inc()
        else:
            WORKFLOW_FAILED.labels(
                workflow_name=workflow_name,
                error_type=error_type or "Unknown"
            ).inc()
        
        WORKFLOW_DURATION.labels(workflow_name=workflow_name).observe(duration_seconds)
        WORKFLOW_STEP_COUNT.labels(workflow_name=workflow_name).observe(step_count)
        
        status = "completed" if success else f"failed ({error_type})"
        logger.info(
            f"Workflow {status}: {workflow_name} "
            f"({duration_seconds:.2f}s, {step_count} steps)"
        )
    except Exception as e:
        logger.warning(f"Failed to record workflow completion metric: {e}")


# =============================================================================
# Context Managers
# =============================================================================

@contextmanager
def track_activity_execution(activity_name: str):
    """
    Context manager to automatically track activity execution metrics.
    
    Usage:
        with track_activity_execution("my_activity"):
            result = do_work()
            return result
    
    Performance Engineer: Minimal overhead, exception-safe
    """
    start_time = time.time()
    record_activity_start(activity_name)
    
    try:
        yield
        # Success
        duration = time.time() - start_time
        record_activity_success(activity_name, duration)
    except Exception as e:
        # Failure
        duration = time.time() - start_time
        error_type = type(e).__name__
        record_activity_failure(activity_name, error_type, duration)
        raise


@contextmanager
def track_workflow_execution(workflow_name: str):
    """
    Context manager to automatically track workflow execution metrics.
    
    Usage:
        with track_workflow_execution("IngestDataWorkflow"):
            # Execute workflow steps
            step_count = 5
            # Return step_count at the end
    
    UX Consultant: Automatic metric collection reduces operator burden
    """
    start_time = time.time()
    record_workflow_start(workflow_name)
    step_count = 0
    
    try:
        yield
        # Success
        duration = time.time() - start_time
        record_workflow_completion(workflow_name, duration, step_count, success=True)
    except Exception as e:
        # Failure
        duration = time.time() - start_time
        error_type = type(e).__name__
        record_workflow_completion(
            workflow_name, duration, step_count,
            success=False, error_type=error_type
        )
        raise


# =============================================================================
# Integration Helpers
# =============================================================================

def get_activity_metrics_summary() -> dict:
    """
    Get summary of activity metrics for dashboards.
    
    Returns:
        Dictionary with metric counts
        
    ISO Documenter: Provides structured metrics for reporting
    """
    # Note: This is a simplified version. In production, you'd query Prometheus
    # directly or use the REGISTRY to introspect current values.
    return {
        "note": "Query Prometheus for actual values",
        "metrics_available": [
            "temporal_activity_started_total",
            "temporal_activity_completed_total",
            "temporal_activity_failed_total",
            "temporal_activity_retried_total",
            "temporal_activity_duration_seconds",
            "temporal_workflow_started_total",
            "temporal_workflow_completed_total",
            "temporal_workflow_failed_total",
            "temporal_workflow_duration_seconds",
            "temporal_circuit_breaker_triggered_total"
        ]
    }
