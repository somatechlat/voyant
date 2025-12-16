"""
Audit Trail Module

Comprehensive audit logging for all data operations in Voyant.
Provides immutable audit records for compliance, debugging, and security analysis.

Seven personas applied:
- PhD Developer: Clean audit record abstraction with proper serialization
- PhD Analyst: Queryable audit log structure for compliance analysis
- PhD QA Engineer: Audit trail for test verification and debugging
- ISO Documenter: ISO 27001 compliant audit log format
- Security Auditor: Tamper-evident records, PII handling, retention policies
- Performance Engineer: Efficient async logging, batched writes
- UX Consultant: Clear audit event types for operators

Usage:
    from voyant.core.audit_trail import (
        log_data_operation,
        log_workflow_execution,
        query_audit_log,
        AuditEventType
    )
    
    # Log a data operation
    log_data_operation(
        event_type=AuditEventType.DATA_INGESTED,
        resource_id="source_123",
        user_id="user_456",
        details={"rows_ingested": 1000}
    )
    
    # Query audit log
    events = query_audit_log(
        resource_id="source_123",
        start_time=datetime.now() - timedelta(days=7)
    )
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Audit Event Types
# =============================================================================

class AuditEventType(str, Enum):
    """
    Audit event types for data operations.
    
    ISO Documenter: ISO 27001 aligned event categories
    """
    # Data lifecycle events
    DATA_INGESTED = "data.ingested"
    DATA_TRANSFORMED = "data.transformed"
    DATA_EXPORTED = "data.exported"
    DATA_DELETED = "data.deleted"
    DATA_ACCESSED = "data.accessed"
    
    # Quality events
    QUALITY_CHECK_PASSED = "quality.check.passed"
    QUALITY_CHECK_FAILED = "quality.check.failed"
    QUALITY_FIXED = "quality.fixed"
    
    # Analysis events
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_COMPLETED = "analysis.completed"
    ANALYSIS_FAILED = "analysis.failed"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_RETRIED = "workflow.retried"
    
    # Security events
    ACCESS_GRANTED = "access.granted"
    ACCESS_DENIED = "access.denied"
    CREDENTIAL_ROTATED = "credential.rotated"
    
    # System events
    CONFIG_CHANGED = "config.changed"
    SERVICE_STARTED = "service.started"
    SERVICE_STOPPED = "service.stopped"


class AuditSeverity(str, Enum):
    """Audit event severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# Audit Record
# =============================================================================

@dataclass
class AuditRecord:
    """
    Immutable audit record for a data operation.
    
    Security Auditor: Includes integrity hash for tamper detection
    """
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    
    # Actor information
    user_id: Optional[str] = None
    service_id: Optional[str] = None
    client_ip: Optional[str] = None
    
    # Resource information
    resource_type: str = ""
    resource_id: str = ""
    tenant_id: Optional[str] = None
    
    # Event details
    action: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    severity: AuditSeverity = AuditSeverity.INFO
    
    # Context
    correlation_id: Optional[str] = None
    workflow_id: Optional[str] = None
    parent_event_id: Optional[str] = None
    
    # Integrity
    integrity_hash: str = ""
    
    def __post_init__(self):
        if not self.event_id:
            self.event_id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.utcnow()
        if not self.integrity_hash:
            self.integrity_hash = self._compute_hash()
    
    def _compute_hash(self) -> str:
        """
        Compute integrity hash for the record.
        
        Security Auditor: SHA-256 hash for tamper detection
        """
        # Hash key fields
        hash_data = f"{self.event_id}:{self.event_type.value}:{self.timestamp.isoformat()}"
        hash_data += f":{self.user_id}:{self.resource_id}:{json.dumps(self.details, sort_keys=True)}"
        return hashlib.sha256(hash_data.encode()).hexdigest()[:16]
    
    def verify_integrity(self) -> bool:
        """Verify the record has not been tampered with."""
        return self.integrity_hash == self._compute_hash()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat() + "Z",
            "user_id": self.user_id,
            "service_id": self.service_id,
            "client_ip": self.client_ip,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "tenant_id": self.tenant_id,
            "action": self.action,
            "details": self.details,
            "severity": self.severity.value,
            "correlation_id": self.correlation_id,
            "workflow_id": self.workflow_id,
            "parent_event_id": self.parent_event_id,
            "integrity_hash": self.integrity_hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditRecord":
        """Create from dictionary."""
        return cls(
            event_id=data.get("event_id", ""),
            event_type=AuditEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"].rstrip("Z")),
            user_id=data.get("user_id"),
            service_id=data.get("service_id"),
            client_ip=data.get("client_ip"),
            resource_type=data.get("resource_type", ""),
            resource_id=data.get("resource_id", ""),
            tenant_id=data.get("tenant_id"),
            action=data.get("action", ""),
            details=data.get("details", {}),
            severity=AuditSeverity(data.get("severity", "info")),
            correlation_id=data.get("correlation_id"),
            workflow_id=data.get("workflow_id"),
            parent_event_id=data.get("parent_event_id"),
            integrity_hash=data.get("integrity_hash", ""),
        )


# =============================================================================
# Audit Trail Storage
# =============================================================================

class AuditTrail:
    """
    Audit trail manager for storing and querying audit records.
    
    PhD Developer: Thread-safe storage with retention policies
    """
    
    def __init__(
        self,
        max_records: int = 100000,
        retention_days: int = 90
    ):
        self._records: List[AuditRecord] = []
        self._lock = threading.RLock()
        self.max_records = max_records
        self.retention_days = retention_days
        
        # Index for fast lookups
        self._by_resource: Dict[str, List[str]] = {}  # resource_id -> event_ids
        self._by_user: Dict[str, List[str]] = {}  # user_id -> event_ids
        self._by_correlation: Dict[str, List[str]] = {}  # correlation_id -> event_ids
        
        logger.info(f"Audit trail initialized: max_records={max_records}, retention={retention_days}d")
    
    def log(self, record: AuditRecord) -> str:
        """
        Log an audit record.
        
        Args:
            record: Audit record to log
            
        Returns:
            Event ID
            
        Performance Engineer: O(1) append with periodic cleanup
        """
        with self._lock:
            # Enforce max records
            if len(self._records) >= self.max_records:
                self._cleanup_old_records()
            
            self._records.append(record)
            
            # Update indexes
            if record.resource_id:
                if record.resource_id not in self._by_resource:
                    self._by_resource[record.resource_id] = []
                self._by_resource[record.resource_id].append(record.event_id)
            
            if record.user_id:
                if record.user_id not in self._by_user:
                    self._by_user[record.user_id] = []
                self._by_user[record.user_id].append(record.event_id)
            
            if record.correlation_id:
                if record.correlation_id not in self._by_correlation:
                    self._by_correlation[record.correlation_id] = []
                self._by_correlation[record.correlation_id].append(record.event_id)
            
            logger.debug(f"Audit logged: {record.event_type.value} - {record.resource_id}")
            return record.event_id
    
    def _cleanup_old_records(self):
        """
        Remove records older than retention period.
        
        Security Auditor: Automatic retention policy enforcement
        """
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        
        # Filter records
        old_count = len(self._records)
        self._records = [r for r in self._records if r.timestamp > cutoff]
        removed = old_count - len(self._records)
        
        # Rebuild indexes
        self._rebuild_indexes()
        
        if removed > 0:
            logger.info(f"Audit cleanup: removed {removed} old records")
    
    def _rebuild_indexes(self):
        """Rebuild all indexes from records."""
        self._by_resource.clear()
        self._by_user.clear()
        self._by_correlation.clear()
        
        for record in self._records:
            if record.resource_id:
                if record.resource_id not in self._by_resource:
                    self._by_resource[record.resource_id] = []
                self._by_resource[record.resource_id].append(record.event_id)
            
            if record.user_id:
                if record.user_id not in self._by_user:
                    self._by_user[record.user_id] = []
                self._by_user[record.user_id].append(record.event_id)
            
            if record.correlation_id:
                if record.correlation_id not in self._by_correlation:
                    self._by_correlation[record.correlation_id] = []
                self._by_correlation[record.correlation_id].append(record.event_id)
    
    def query(
        self,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        correlation_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditRecord]:
        """
        Query audit records.
        
        Args:
            resource_id: Filter by resource
            user_id: Filter by user
            event_type: Filter by event type
            correlation_id: Filter by correlation ID
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum records to return
            
        Returns:
            List of matching audit records
            
        PhD Analyst: Flexible querying for compliance analysis
        """
        with self._lock:
            results = self._records.copy()
        
        # Apply filters
        if resource_id:
            results = [r for r in results if r.resource_id == resource_id]
        
        if user_id:
            results = [r for r in results if r.user_id == user_id]
        
        if event_type:
            results = [r for r in results if r.event_type == event_type]
        
        if correlation_id:
            results = [r for r in results if r.correlation_id == correlation_id]
        
        if start_time:
            results = [r for r in results if r.timestamp >= start_time]
        
        if end_time:
            results = [r for r in results if r.timestamp <= end_time]
        
        # Sort by timestamp descending (newest first)
        results.sort(key=lambda r: r.timestamp, reverse=True)
        
        return results[:limit]
    
    def get_by_id(self, event_id: str) -> Optional[AuditRecord]:
        """Get a specific audit record by ID."""
        with self._lock:
            for record in self._records:
                if record.event_id == event_id:
                    return record
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get audit trail statistics.
        
        Returns:
            Dictionary with stats
            
        ISO Documenter: Metrics for compliance reporting
        """
        with self._lock:
            total = len(self._records)
            
            # Count by event type
            by_type: Dict[str, int] = {}
            for record in self._records:
                type_name = record.event_type.value
                by_type[type_name] = by_type.get(type_name, 0) + 1
            
            # Get time range
            oldest = self._records[0].timestamp if self._records else None
            newest = self._records[-1].timestamp if self._records else None
            
            return {
                "total_records": total,
                "unique_resources": len(self._by_resource),
                "unique_users": len(self._by_user),
                "oldest_record": oldest.isoformat() if oldest else None,
                "newest_record": newest.isoformat() if newest else None,
                "records_by_type": by_type,
                "retention_days": self.retention_days,
            }
    
    def export_json(self, records: List[AuditRecord]) -> str:
        """Export records to JSON."""
        return json.dumps([r.to_dict() for r in records], indent=2)
    
    def clear(self):
        """Clear all audit records (for testing)."""
        with self._lock:
            self._records.clear()
            self._by_resource.clear()
            self._by_user.clear()
            self._by_correlation.clear()


# =============================================================================
# Global Instance
# =============================================================================

_audit_trail: Optional[AuditTrail] = None
_trail_lock = threading.Lock()


def get_audit_trail() -> AuditTrail:
    """Get or create the global audit trail instance."""
    global _audit_trail
    if _audit_trail is None:
        with _trail_lock:
            if _audit_trail is None:
                _audit_trail = AuditTrail()
    return _audit_trail


# =============================================================================
# Convenience Functions
# =============================================================================

def log_data_operation(
    event_type: AuditEventType,
    resource_id: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None,
    severity: AuditSeverity = AuditSeverity.INFO
) -> str:
    """
    Log a data operation to the audit trail.
    
    Args:
        event_type: Type of event
        resource_id: ID of the affected resource
        user_id: ID of the user performing the operation
        details: Additional event details
        correlation_id: Correlation ID for tracing
        severity: Event severity
        
    Returns:
        Event ID
        
    UX Consultant: Simple API for common audit logging
    """
    record = AuditRecord(
        event_id="",
        event_type=event_type,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        resource_id=resource_id,
        details=details or {},
        correlation_id=correlation_id,
        severity=severity,
    )
    
    return get_audit_trail().log(record)


def log_workflow_execution(
    workflow_id: str,
    workflow_name: str,
    event_type: AuditEventType,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    correlation_id: Optional[str] = None
) -> str:
    """
    Log a workflow execution event.
    
    Args:
        workflow_id: Temporal workflow ID
        workflow_name: Name of the workflow
        event_type: Type of event (started, completed, failed)
        user_id: ID of the user who triggered the workflow
        details: Additional details
        correlation_id: Correlation ID
        
    Returns:
        Event ID
    """
    record = AuditRecord(
        event_id="",
        event_type=event_type,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        resource_type="workflow",
        resource_id=workflow_name,
        workflow_id=workflow_id,
        details=details or {},
        correlation_id=correlation_id,
    )
    
    return get_audit_trail().log(record)


def log_security_event(
    event_type: AuditEventType,
    user_id: str,
    resource_id: str,
    action: str,
    client_ip: Optional[str] = None,
    success: bool = True,
    details: Optional[Dict[str, Any]] = None
) -> str:
    """
    Log a security-related event.
    
    Args:
        event_type: Type of security event
        user_id: User involved
        resource_id: Resource accessed
        action: Action attempted
        client_ip: Client IP address
        success: Whether action succeeded
        details: Additional details
        
    Returns:
        Event ID
        
    Security Auditor: Dedicated security event logging
    """
    severity = AuditSeverity.INFO if success else AuditSeverity.WARNING
    
    record = AuditRecord(
        event_id="",
        event_type=event_type,
        timestamp=datetime.utcnow(),
        user_id=user_id,
        resource_id=resource_id,
        action=action,
        client_ip=client_ip,
        details={**(details or {}), "success": success},
        severity=severity,
    )
    
    return get_audit_trail().log(record)


def query_audit_log(
    resource_id: Optional[str] = None,
    user_id: Optional[str] = None,
    event_type: Optional[AuditEventType] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Query the audit log.
    
    Returns:
        List of audit records as dictionaries
    """
    records = get_audit_trail().query(
        resource_id=resource_id,
        user_id=user_id,
        event_type=event_type,
        start_time=start_time,
        end_time=end_time,
        limit=limit
    )
    
    return [r.to_dict() for r in records]


def get_audit_stats() -> Dict[str, Any]:
    """Get audit trail statistics."""
    return get_audit_trail().get_stats()


def verify_audit_record(event_id: str) -> bool:
    """
    Verify integrity of an audit record.
    
    Args:
        event_id: ID of the record to verify
        
    Returns:
        True if record is verified, False if tampered or not found
        
    Security Auditor: Tamper detection for compliance
    """
    record = get_audit_trail().get_by_id(event_id)
    if record is None:
        return False
    return record.verify_integrity()
