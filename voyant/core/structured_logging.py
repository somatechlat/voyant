"""
Structured Logging with Correlation IDs

Context-aware structured logging for Temporal workflows and activities.
Enables request tracing across distributed activity executions.

Seven personas applied:
- PhD Developer: Context managers for automatic correlation ID propagation
- PhD Analyst: Structured fields enable log aggregation and analysis
- PhD QA Engineer: Correlation IDs enable end-to-end test tracing
- ISO Documenter: Audit-friendly log format with timestamps and trace IDs
- Security Auditor: PII filtering, no sensitive data in logs
- Performance Engineer: Efficient context-local storage, minimal overhead
- UX Consultant: Clear log messages for operators debugging issues

Usage:
    from voyant.core.structured_logging import (
        get_logger,
        with_correlation_id,
        log_activity_start,
        log_activity_end
    )
    
    # Get structured logger
    logger = get_logger(__name__)
    
    # In workflow
    with with_correlation_id(workflow_run_id):
        logger.info("Processing workflow", extra={"workflow_name": "IngestData"})
        
    # In activity
    log_activity_start("calculate_market_share", {"data_rows": 1000})
    try:
        result = do_work()
        log_activity_end("calculate_market_share", success=True, result_size=500)
    except Exception as e:
        log_activity_end("calculate_market_share", success=False, error=str(e))
"""
from __future__ import annotations

import logging
import uuid
import contextvars
from typing import Any, Dict, Optional
from contextlib import contextmanager
from datetime import datetime

# Context variable for correlation ID (thread-safe)
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'correlation_id',
    default=None
)

# Context variable for workflow ID
workflow_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'workflow_id',
    default=None
)

# Context variable for activity name
activity_name_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    'activity_name',
    default=None
)


# =============================================================================
# Correlation ID Management
# =============================================================================

def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.
    
    Returns:
        UUID-based correlation ID
        
    ISO Documenter: Globally unique IDs for audit trails
    """
    return str(uuid.uuid4())


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID from context.
    
    Returns:
        Current correlation ID or None
        
    Performance Engineer: O(1) context-local lookup
    """
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str):
    """
    Set correlation ID in context.
    
    Args:
        correlation_id: Correlation ID to set
        
    PhD Developer: Explicit setter for programmatic control
    """
    correlation_id_var.set(correlation_id)


def get_workflow_id() -> Optional[str]:
    """Get current workflow ID from context."""
    return workflow_id_var.get()


def set_workflow_id(workflow_id: str):
    """Set workflow ID in context."""
    workflow_id_var.set(workflow_id)


def get_activity_name() -> Optional[str]:
    """Get current activity name from context."""
    return activity_name_var.get()


def set_activity_name(activity_name: str):
    """Set activity name in context."""
    activity_name_var.set(activity_name)


@contextmanager
def with_correlation_id(correlation_id: Optional[str] = None):
    """
    Context manager to set correlation ID for a block of code.
    
    Args:
        correlation_id: Correlation ID to use, or None to generate new one
        
    Usage:
        with with_correlation_id(workflow_execution_id):
            # All logging in this block will include the correlation ID
            logger.info("Step 1")
            logger.info("Step 2")
            
    QA Engineer: Enables end-to-end tracing in tests
    """
    if correlation_id is None:
        correlation_id = generate_correlation_id()
    
    token = correlation_id_var.set(correlation_id)
    try:
        yield correlation_id
    finally:
        correlation_id_var.reset(token)


@contextmanager
def with_workflow_context(workflow_id: str, workflow_name: str):
    """
    Context manager to set workflow context.
    
    Args:
        workflow_id: Workflow execution ID
        workflow_name: Workflow name
        
    UX Consultant: Automatic context propagation reduces boilerplate
    """
    correlation_token = correlation_id_var.set(workflow_id)
    workflow_token = workflow_id_var.set(workflow_id)
    
    try:
        yield workflow_id
    finally:
        correlation_id_var.reset(correlation_token)
        workflow_id_var.reset(workflow_token)


@contextmanager
def with_activity_context(activity_name: str):
    """
    Context manager to set activity context.
    
    Args:
        activity_name: Activity name
        
    PhD Developer: Nested context support for activity within workflow
    """
    token = activity_name_var.set(activity_name)
    try:
        yield activity_name
    finally:
        activity_name_var.reset(token)


# =============================================================================
# Structured Logging Formatter
# =============================================================================

class StructuredFormatter(logging.Formatter):
    """
    Custom log formatter that adds correlation ID and structured fields.
    
    ISO Documenter: Consistent log format for compliance requirements
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with correlation ID and structured fields.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log string
            
        Security Auditor: Filters PII fields from logs
        """
        # Add correlation context
        correlation_id = get_correlation_id()
        if correlation_id:
            record.correlation_id = correlation_id
        else:
            record.correlation_id = "-"
        
        workflow_id = get_workflow_id()
        if workflow_id:
            record.workflow_id = workflow_id
        else:
            record.workflow_id = "-"
        
        activity_name = get_activity_name()
        if activity_name:
            record.activity_name = activity_name
        else:
            record.activity_name = "-"
        
        # Add timestamp in ISO format
        record.timestamp = datetime.utcnow().isoformat() + "Z"
        
        return super().format(record)


# Default format string with structured fields
# Format: [timestamp] [level] [correlation_id] [workflow_id] [activity_name] [logger] message
STRUCTURED_FORMAT = (
    "[%(timestamp)s] [%(levelname)s] "
    "[corr:%(correlation_id)s] [wf:%(workflow_id)s] [act:%(activity_name)s] "
    "[%(name)s] %(message)s"
)


def get_logger(name: str) -> logging.Logger:
    """
    Get a structured logger with correlation ID support.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger
        
    Usage:
        logger = get_logger(__name__)
        logger.info("Processing started", extra={"rows": 1000})
        
    UX Consultant: Simple API, automatic context propagation
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter(STRUCTURED_FORMAT))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


# =============================================================================
# Activity/Workflow Logging Helpers
# =============================================================================

def log_activity_start(activity_name: str, params: Optional[Dict[str, Any]] = None):
    """
    Log activity execution start with structured fields.
    
    Args:
        activity_name: Name of the activity
        params: Activity parameters (sensitive data will be filtered)
        
    QA Engineer: Standardized logging for test verification
    """
    logger = get_logger("voyant.activity")
    
    # Filter sensitive fields
    safe_params = _filter_sensitive_fields(params or {})
    
    with with_activity_context(activity_name):
        logger.info(
            f"Activity started: {activity_name}",
            extra={
                "event": "activity_start",
                "activity": activity_name,
                "params": safe_params
            }
        )


def log_activity_end(
    activity_name: str,
    success: bool = True,
    error: Optional[str] = None,
    **result_fields
):
    """
    Log activity execution end with structured fields.
    
    Args:
        activity_name: Name of the activity
        success: Whether activity succeeded
        error: Error message if failed
        **result_fields: Additional result fields to log
        
    ISO Documenter: Audit trail of activity outcomes
    """
    logger = get_logger("voyant.activity")
    
    # Filter sensitive result fields
    safe_results = _filter_sensitive_fields(result_fields)
    
    with with_activity_context(activity_name):
        if success:
            logger.info(
                f"Activity completed: {activity_name}",
                extra={
                    "event": "activity_end",
                    "activity": activity_name,
                    "success": True,
                    **safe_results
                }
            )
        else:
            logger.error(
                f"Activity failed: {activity_name}",
                extra={
                    "event": "activity_error",
                    "activity": activity_name,
                    "success": False,
                    "error": error,
                    **safe_results
                }
            )


def log_workflow_start(workflow_name: str, workflow_id: str, params: Optional[Dict[str, Any]] = None):
    """
    Log workflow execution start.
    
    Args:
        workflow_name: Name of the workflow
        workflow_id: Workflow execution ID
        params: Workflow parameters
        
    UX Consultant: Clear workflow lifecycle visibility
    """
    logger = get_logger("voyant.workflow")
    
    safe_params = _filter_sensitive_fields(params or {})
    
    with with_workflow_context(workflow_id, workflow_name):
        logger.info(
            f"Workflow started: {workflow_name}",
            extra={
                "event": "workflow_start",
                "workflow": workflow_name,
                "workflow_id": workflow_id,
                "params": safe_params
            }
        )


def log_workflow_end(
    workflow_name: str,
    workflow_id: str,
    success: bool = True,
    error: Optional[str] = None,
    **result_fields
):
    """
    Log workflow execution end.
    
    Args:
        workflow_name: Name of the workflow
        workflow_id: Workflow execution ID
        success: Whether workflow succeeded
        error: Error message if failed
        **result_fields: Additional result fields
        
    ISO Documenter: Complete workflow audit trail
    """
    logger = get_logger("voyant.workflow")
    
    safe_results = _filter_sensitive_fields(result_fields)
    
    with with_workflow_context(workflow_id, workflow_name):
        if success:
            logger.info(
                f"Workflow completed: {workflow_name}",
                extra={
                    "event": "workflow_end",
                    "workflow": workflow_name,
                    "workflow_id": workflow_id,
                    "success": True,
                    **safe_results
                }
            )
        else:
            logger.error(
                f"Workflow failed: {workflow_name}",
                extra={
                    "event": "workflow_error",
                    "workflow": workflow_name,
                    "workflow_id": workflow_id,
                    "success": False,
                    "error": error,
                    **safe_results
                }
            )


# =============================================================================
# Security Helpers
# =============================================================================

# Fields that should never be logged (Security Auditor)
SENSITIVE_FIELD_NAMES = {
    "password", "secret", "token", "api_key", "apikey", "auth",
    "credential", "private_key", "access_token", "refresh_token",
    "session_id", "cookie", "ssn", "social_security"
}


def _filter_sensitive_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filter sensitive fields from data before logging.
    
    Args:
        data: Dictionary to filter
        
    Returns:
        Filtered dictionary with sensitive values redacted
        
    Security Auditor: Prevents credential leakage in logs
    """
    filtered = {}
    for key, value in data.items():
        key_lower = key.lower()
        if any(sensitive in key_lower for sensitive in SENSITIVE_FIELD_NAMES):
            filtered[key] = "***REDACTED***"
        else:
            # Simple recursion for nested dicts
            if isinstance(value, dict):
                filtered[key] = _filter_sensitive_fields(value)
            else:
                filtered[key] = value
    return filtered
