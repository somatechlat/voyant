"""
API Middleware

Request ID, Tenant, and API Version middleware.
"""
from __future__ import annotations

import re
import uuid
import logging
from contextvars import ContextVar
from typing import Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# Context variables for request-scoped data
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="default")
api_version_var: ContextVar[str] = ContextVar("api_version", default="v1")

# Supported API versions
SUPPORTED_VERSIONS = ["v1"]
DEFAULT_VERSION = "v1"
CURRENT_VERSION = "v1"

# Version pattern: application/vnd.voyant.v1+json
VERSION_PATTERN = re.compile(r"application/vnd\.voyant\.v(\d+)\+json")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Add request ID to each request for tracing."""
    
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_var.set(request_id)
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class TenantMiddleware(BaseHTTPMiddleware):
    """Extract tenant from request for multi-tenancy."""
    
    async def dispatch(self, request: Request, call_next):
        # Get tenant from header, JWT claim, or default
        tenant_id = request.headers.get("X-Tenant-ID", "default")
        tenant_id_var.set(tenant_id)
        
        response = await call_next(request)
        return response


class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    API Version negotiation via Accept header.
    
    Supports:
    - Accept: application/vnd.voyant.v1+json (explicit version)
    - Accept: application/json (use default version)
    - X-API-Version: v1 (header override)
    
    Sets X-API-Version response header with negotiated version.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip version negotiation for health endpoints
        if request.url.path in ("/health", "/ready", "/healthz", "/readyz"):
            return await call_next(request)
        
        # Try to extract version from headers
        version = self._extract_version(request)
        
        # Validate version
        if version and f"v{version}" not in SUPPORTED_VERSIONS:
            return JSONResponse(
                status_code=406,
                content={
                    "error": "Not Acceptable",
                    "message": f"API version v{version} is not supported",
                    "supported_versions": SUPPORTED_VERSIONS,
                    "current_version": CURRENT_VERSION,
                },
                headers={"X-API-Version": CURRENT_VERSION},
            )
        
        # Set context variable
        api_version = f"v{version}" if version else DEFAULT_VERSION
        api_version_var.set(api_version)
        
        # Continue request processing
        response = await call_next(request)
        
        # Add version header to response
        response.headers["X-API-Version"] = api_version
        return response
    
    def _extract_version(self, request: Request) -> Optional[str]:
        """Extract API version from request headers."""
        # Priority 1: X-API-Version header (explicit override)
        if header_version := request.headers.get("X-API-Version"):
            return header_version.lstrip("v")
        
        # Priority 2: Accept header with vendor format
        accept = request.headers.get("Accept", "")
        if match := VERSION_PATTERN.search(accept):
            return match.group(1)
        
        # Default: None (use default version)
        return None


def get_request_id() -> str:
    """Get current request ID."""
    return request_id_var.get()


def get_tenant_id() -> str:
    """Get current tenant ID."""
    return tenant_id_var.get()


def get_api_version() -> str:
    """Get negotiated API version."""
    return api_version_var.get()


def get_version_info() -> dict:
    """Get API version information."""
    return {
        "current_version": CURRENT_VERSION,
        "supported_versions": SUPPORTED_VERSIONS,
        "default_version": DEFAULT_VERSION,
        "accept_format": "application/vnd.voyant.{version}+json",
    }

