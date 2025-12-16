"""
Error Catalog Module

Structured failure catalog with error codes and metadata.
Reference: docs/CANONICAL_ROADMAP.md - P2 Operability

Features:
- Canonical error codes (VYNT-XXXX format)
- Error categories (validation, auth, resource, system)
- Machine-readable error responses
- Internationalization-ready messages
- HTTP status code mapping

Personas Applied:
- PhD Developer: Proper exception hierarchy
- Analyst: Error categorization for monitoring
- QA: Comprehensive error coverage
- ISO Documenter: Complete error documentation
- Security: No sensitive data in errors
- Performance: Lightweight error creation
- UX: Clear, actionable error messages

Usage:
    from voyant.core.errors import (
        VoyantError, ValidationError, ResourceNotFoundError,
        error_response, get_error_catalog
    )
    
    # Raise typed error
    raise ValidationError("VYNT-1001", "Invalid column name")
    
    # Create error response for API
    return error_response("VYNT-2001", details={"resource": "job", "id": job_id})
"""
from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List, Type
from dataclasses import dataclass, field
from http import HTTPStatus

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    VALIDATION = "validation"            # Input validation failures
    AUTHENTICATION = "authentication"    # Auth failures
    AUTHORIZATION = "authorization"      # Permission failures
    RESOURCE = "resource"                # Resource not found/unavailable
    QUOTA = "quota"                      # Rate/quota limits
    SYSTEM = "system"                    # Internal system errors
    EXTERNAL = "external"                # External service failures
    DATA = "data"                        # Data quality/format issues


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    INFO = "info"           # Informational (e.g., deprecated)
    WARNING = "warning"     # Degraded but functional
    ERROR = "error"         # Operation failed
    CRITICAL = "critical"   # System-wide impact


@dataclass(frozen=True)
class ErrorDefinition:
    """Definition of an error in the catalog."""
    code: str                    # e.g., "VYNT-1001"
    message: str                 # Human-readable message template
    category: ErrorCategory
    severity: ErrorSeverity
    http_status: int
    description: str = ""        # Extended description
    resolution: str = ""         # How to fix
    retry_allowed: bool = False  # Can client retry?
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "http_status": self.http_status,
            "description": self.description,
            "resolution": self.resolution,
            "retry_allowed": self.retry_allowed,
        }


# =============================================================================
# Error Catalog (Canonical Error Definitions)
# =============================================================================

ERROR_CATALOG: Dict[str, ErrorDefinition] = {
    # =========================================================================
    # 1000-1999: Validation Errors
    # =========================================================================
    "VYNT-1001": ErrorDefinition(
        code="VYNT-1001",
        message="Invalid request body",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.ERROR,
        http_status=400,
        description="The request body does not conform to the expected schema",
        resolution="Check the API documentation and ensure all required fields are present",
    ),
    "VYNT-1002": ErrorDefinition(
        code="VYNT-1002",
        message="Invalid column name: {column}",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.ERROR,
        http_status=400,
        description="The specified column does not exist in the dataset",
        resolution="Verify column names using the /profile endpoint",
    ),
    "VYNT-1003": ErrorDefinition(
        code="VYNT-1003",
        message="Invalid date format: {value}",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.ERROR,
        http_status=400,
        description="Date must be in ISO 8601 format (YYYY-MM-DD)",
        resolution="Use format: 2024-01-15",
    ),
    "VYNT-1004": ErrorDefinition(
        code="VYNT-1004",
        message="Missing required parameter: {param}",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.ERROR,
        http_status=400,
        resolution="Include the required parameter in your request",
    ),
    "VYNT-1005": ErrorDefinition(
        code="VYNT-1005",
        message="Invalid SQL template: {reason}",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.ERROR,
        http_status=400,
        description="The KPI SQL template failed validation",
        resolution="Check SQL syntax and placeholder usage",
    ),
    
    # =========================================================================
    # 2000-2999: Resource Errors
    # =========================================================================
    "VYNT-2001": ErrorDefinition(
        code="VYNT-2001",
        message="Job not found: {job_id}",
        category=ErrorCategory.RESOURCE,
        severity=ErrorSeverity.ERROR,
        http_status=404,
        description="The requested job does not exist or has been pruned",
        resolution="Use /jobs to list available jobs",
    ),
    "VYNT-2002": ErrorDefinition(
        code="VYNT-2002",
        message="Artifact not found: {artifact_key}",
        category=ErrorCategory.RESOURCE,
        severity=ErrorSeverity.ERROR,
        http_status=404,
        description="The requested artifact does not exist",
        resolution="Check artifact key using /artifacts/{job_id}",
    ),
    "VYNT-2003": ErrorDefinition(
        code="VYNT-2003",
        message="Source not found: {source_id}",
        category=ErrorCategory.RESOURCE,
        severity=ErrorSeverity.ERROR,
        http_status=404,
        description="The data source does not exist in DuckDB",
        resolution="Ingest data first using /ingest",
    ),
    "VYNT-2004": ErrorDefinition(
        code="VYNT-2004",
        message="Baseline not found: {baseline_id}",
        category=ErrorCategory.RESOURCE,
        severity=ErrorSeverity.ERROR,
        http_status=404,
        description="No baseline exists for comparison",
        resolution="Create a baseline using /quality with create_baseline=true",
    ),
    "VYNT-2005": ErrorDefinition(
        code="VYNT-2005",
        message="Contract not found: {contract_name}",
        category=ErrorCategory.RESOURCE,
        severity=ErrorSeverity.ERROR,
        http_status=404,
        resolution="Register the contract using /governance/contracts",
    ),
    
    # =========================================================================
    # 3000-3999: Authentication/Authorization Errors
    # =========================================================================
    "VYNT-3001": ErrorDefinition(
        code="VYNT-3001",
        message="Authentication required",
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.ERROR,
        http_status=401,
        description="No valid authentication token provided",
        resolution="Include a valid Bearer token in the Authorization header",
    ),
    "VYNT-3002": ErrorDefinition(
        code="VYNT-3002",
        message="Token expired",
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.ERROR,
        http_status=401,
        description="The authentication token has expired",
        resolution="Obtain a new token from the authentication endpoint",
        retry_allowed=True,
    ),
    "VYNT-3003": ErrorDefinition(
        code="VYNT-3003",
        message="Insufficient permissions for {action}",
        category=ErrorCategory.AUTHORIZATION,
        severity=ErrorSeverity.ERROR,
        http_status=403,
        description="Your role does not have permission for this action",
        resolution="Contact your administrator for access",
    ),
    "VYNT-3004": ErrorDefinition(
        code="VYNT-3004",
        message="Tenant access denied: {tenant_id}",
        category=ErrorCategory.AUTHORIZATION,
        severity=ErrorSeverity.ERROR,
        http_status=403,
        description="You do not have access to this tenant's resources",
    ),
    
    # =========================================================================
    # 4000-4999: Quota/Limit Errors
    # =========================================================================
    "VYNT-4001": ErrorDefinition(
        code="VYNT-4001",
        message="Daily job quota exceeded",
        category=ErrorCategory.QUOTA,
        severity=ErrorSeverity.WARNING,
        http_status=429,
        description="You have reached your daily job limit",
        resolution="Wait until tomorrow or upgrade your plan",
        retry_allowed=True,
    ),
    "VYNT-4002": ErrorDefinition(
        code="VYNT-4002",
        message="Concurrent job limit reached: {count}/{limit}",
        category=ErrorCategory.QUOTA,
        severity=ErrorSeverity.WARNING,
        http_status=429,
        description="Maximum concurrent jobs are already running",
        resolution="Wait for existing jobs to complete",
        retry_allowed=True,
    ),
    "VYNT-4003": ErrorDefinition(
        code="VYNT-4003",
        message="Artifact storage limit exceeded: {used_gb}/{limit_gb} GB",
        category=ErrorCategory.QUOTA,
        severity=ErrorSeverity.ERROR,
        http_status=507,
        description="Your artifact storage quota is full",
        resolution="Delete old artifacts or upgrade your plan",
    ),
    "VYNT-4004": ErrorDefinition(
        code="VYNT-4004",
        message="Rate limit exceeded",
        category=ErrorCategory.QUOTA,
        severity=ErrorSeverity.WARNING,
        http_status=429,
        description="Too many requests in a short period",
        resolution="Wait and retry with exponential backoff",
        retry_allowed=True,
    ),
    
    # =========================================================================
    # 5000-5999: System Errors
    # =========================================================================
    "VYNT-5001": ErrorDefinition(
        code="VYNT-5001",
        message="Internal server error",
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.CRITICAL,
        http_status=500,
        description="An unexpected error occurred",
        resolution="Contact support with the request ID",
        retry_allowed=True,
    ),
    "VYNT-5002": ErrorDefinition(
        code="VYNT-5002",
        message="Database connection failed",
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.CRITICAL,
        http_status=503,
        description="Unable to connect to the database",
        resolution="Check database connectivity and retry",
        retry_allowed=True,
    ),
    "VYNT-5003": ErrorDefinition(
        code="VYNT-5003",
        message="Job execution timeout after {seconds} seconds",
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.ERROR,
        http_status=504,
        description="The job took too long to complete",
        resolution="Try a smaller dataset or simpler analysis",
        retry_allowed=True,
    ),
    
    # =========================================================================
    # 6000-6999: External Service Errors
    # =========================================================================
    "VYNT-6001": ErrorDefinition(
        code="VYNT-6001",
        message="Airbyte connection failed: {reason}",
        category=ErrorCategory.EXTERNAL,
        severity=ErrorSeverity.ERROR,
        http_status=502,
        description="Could not connect to Airbyte for data sync",
        resolution="Check Airbyte status and configuration",
        retry_allowed=True,
    ),
    "VYNT-6002": ErrorDefinition(
        code="VYNT-6002",
        message="DataHub unavailable",
        category=ErrorCategory.EXTERNAL,
        severity=ErrorSeverity.WARNING,
        http_status=503,
        description="DataHub service is not responding",
        resolution="Lineage features temporarily unavailable",
        retry_allowed=True,
    ),
    
    # =========================================================================
    # 7000-7999: Data Quality Errors
    # =========================================================================
    "VYNT-7001": ErrorDefinition(
        code="VYNT-7001",
        message="Data contract violation: {violations} violations",
        category=ErrorCategory.DATA,
        severity=ErrorSeverity.ERROR,
        http_status=422,
        description="Data does not conform to the contract schema",
        resolution="Review the violations in the response details",
    ),
    "VYNT-7002": ErrorDefinition(
        code="VYNT-7002",
        message="Insufficient data for analysis: {rows} rows (minimum: {min_rows})",
        category=ErrorCategory.DATA,
        severity=ErrorSeverity.WARNING,
        http_status=422,
        description="Not enough data points for meaningful analysis",
        resolution="Provide more data or lower the minimum threshold",
    ),
    "VYNT-7003": ErrorDefinition(
        code="VYNT-7003",
        message="Significant drift detected: {drift_score}",
        category=ErrorCategory.DATA,
        severity=ErrorSeverity.WARNING,
        http_status=200,  # Warning, not failure
        description="Data has drifted significantly from baseline",
        resolution="Review drift report and update baseline if appropriate",
    ),
}


# =============================================================================
# Exception Classes
# =============================================================================

class VoyantError(Exception):
    """Base exception for Voyant errors."""
    
    def __init__(
        self,
        code: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        **format_args,
    ):
        self.code = code
        self.details = details or {}
        
        # Get definition from catalog
        self.definition = ERROR_CATALOG.get(code)
        
        if self.definition:
            # Format message with provided args
            if message:
                self.message = message
            else:
                try:
                    self.message = self.definition.message.format(**format_args)
                except KeyError:
                    self.message = self.definition.message
            self.http_status = self.definition.http_status
            self.category = self.definition.category
        else:
            self.message = message or f"Unknown error: {code}"
            self.http_status = 500
            self.category = ErrorCategory.SYSTEM
        
        super().__init__(self.message)
    
    def to_response(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        """Convert to API error response."""
        response = {
            "error": {
                "code": self.code,
                "message": self.message,
                "category": self.category.value if isinstance(self.category, ErrorCategory) else self.category,
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        
        if self.details:
            # Security: Filter sensitive data
            safe_details = {k: v for k, v in self.details.items() 
                          if k not in ("password", "token", "secret", "key")}
            response["error"]["details"] = safe_details
        
        if request_id:
            response["request_id"] = request_id
        
        if self.definition:
            response["error"]["retry_allowed"] = self.definition.retry_allowed
            if self.definition.resolution:
                response["error"]["resolution"] = self.definition.resolution
        
        return response


class ValidationError(VoyantError):
    """Validation errors (1000 series)."""
    pass


class ResourceNotFoundError(VoyantError):
    """Resource not found errors (2000 series)."""
    pass


class AuthenticationError(VoyantError):
    """Authentication errors (3000 series)."""
    pass


class AuthorizationError(VoyantError):
    """Authorization errors (3000 series)."""
    pass


class QuotaExceededError(VoyantError):
    """Quota/limit errors (4000 series)."""
    pass


class SystemError(VoyantError):
    """System errors (5000 series)."""
    pass


class ExternalServiceError(VoyantError):
    """Raised when an external service (API, DB, etc.) fails."""
    pass

class ServiceUnavailableError(VoyantError):
    """
    Raised when a service is temporarily unavailable (circuit breaker open).
    
    Security Auditor: Generic message, no internal details leaked.
    """
    def __init__(self, service_name: str, code: str = "VYNT-9000"):
        super().__init__(
            code=code,
            message=f"{service_name} is temporarily unavailable. Circuit breaker is open.",
            severity="warning",
            resolution="Wait for service recovery or contact support"
        )
        self.service_name = service_name


class AnalysisError(VoyantError):
    """
    Analysis/ML-related errors.
    
    Used for failures in statistical analysis, ML model training, forecasting, etc.
    PhD-level Developer: Dedicated exception for analysis domain errors.
    """
    pass


class DataQualityError(VoyantError):
    """Data quality errors (7000 series)."""
    pass



# =============================================================================
# Helper Functions
# =============================================================================

def error_response(
    code: str,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    **format_args,
) -> Dict[str, Any]:
    """Create a standard error response without raising."""
    error = VoyantError(code, message, details, **format_args)
    return error.to_response(request_id)


def get_error_catalog() -> Dict[str, Dict[str, Any]]:
    """Get the full error catalog as JSON-serializable dict."""
    return {code: defn.to_dict() for code, defn in ERROR_CATALOG.items()}


def get_errors_by_category(category: ErrorCategory) -> List[Dict[str, Any]]:
    """Get all errors in a category."""
    return [
        defn.to_dict() for defn in ERROR_CATALOG.values()
        if defn.category == category
    ]


def list_error_codes() -> List[str]:
    """List all error codes."""
    return sorted(ERROR_CATALOG.keys())
