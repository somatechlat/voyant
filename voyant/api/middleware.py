"""
API Middleware

Request ID and Tenant middleware for multi-tenancy.
"""
from __future__ import annotations

import uuid
import logging
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

# Context variables for request-scoped data
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="default")


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


def get_request_id() -> str:
    """Get current request ID."""
    return request_id_var.get()


def get_tenant_id() -> str:
    """Get current tenant ID."""
    return tenant_id_var.get()
