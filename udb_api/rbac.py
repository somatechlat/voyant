"""Simple RBAC utilities using X-UDB-Role header.

Roles hierarchy: viewer < analyst < admin
"""
from __future__ import annotations
from fastapi import Request, HTTPException
from functools import wraps
from typing import Callable, Any, Optional

ROLE_ORDER = {"viewer": 0, "analyst": 1, "admin": 2}
HEADER = "X-UDB-Role"

def get_role(request: Optional[Request]) -> str:
    if not request:
        return "viewer"
    # Primary header
    r = request.headers.get(HEADER)
    # Backward compatibility / legacy header alias
    if r is None:
        legacy = request.headers.get("X-Role")
        if legacy:
            r = legacy
    r = (r or "viewer").lower()
    return r if r in ROLE_ORDER else "viewer"

def require_role(min_role: str):
    min_level = ROLE_ORDER.get(min_role, 0)
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            request = kwargs.get("request")
            # attempt to find Request arg
            if request is None:
                for a in args:
                    if isinstance(a, Request):
                        request = a
                        break
            role = get_role(request)
            if ROLE_ORDER.get(role, 0) < min_level:
                raise HTTPException(status_code=403, detail="Insufficient role")
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def require_abac(**attr_equals: str):
    """Simple ABAC: enforce that specified headers (case-insensitive) equal expected values.

    Example:
        @require_abac(**{"x-udb-tenant": "acme"})
    """
    lowered = {k.lower(): v for k, v in attr_equals.items()}
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            request = kwargs.get("request")
            if request is None:
                for a in args:
                    if isinstance(a, Request):
                        request = a
                        break
            if request is None:
                raise HTTPException(status_code=400, detail="Request context missing")
            for hk, hv in lowered.items():
                if request.headers.get(hk) != hv:
                    raise HTTPException(status_code=403, detail=f"Attribute mismatch: {hk}")
            return await func(*args, **kwargs)
        return wrapper
    return decorator
