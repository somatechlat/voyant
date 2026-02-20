"""
URL Configuration for the Voyant Project.

This file is the primary URL router for the entire Django application. It defines
operational endpoints for health checks, readiness probes, and status monitoring,
and includes the main API router (`v1_api`) for all application functionality.

Note on 'Lazy' Imports:
Imports for optional dependencies (like temporal, duckdb, r_bridge) are intentionally
placed inside the view functions (`ready`, `status_view`). This is a deliberate
design choice to allow the web server to start and serve basic requests even if
heavy or optional services are unavailable or not installed, preventing a hard crash
on startup.
"""

from __future__ import annotations

from datetime import datetime, timezone

from asgiref.sync import async_to_sync
from django.http import JsonResponse
from django.urls import path

from apps.core.middleware import get_version_info
from apps.core.lib.circuit_breaker import _circuit_breakers
from apps.core.config import get_settings
from apps.core.api import api as v1_api


def health(_request) -> JsonResponse:
    """
    Perform a minimal health check.

    Returns a simple JSON response indicating the service is running. This check
    is lightweight and does not verify dependency health. It is suitable for
    basic "is the server up?" monitoring (e.g., a Kubernetes liveness probe).
    """
    return JsonResponse(
        {
            "status": "healthy",
            "version": "3.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
    )


def ready(_request) -> JsonResponse:
    """
    Perform a comprehensive readiness check of all critical dependencies.

    This probe checks the status of external services like DuckDB, the R engine,
    Temporal, and the state of all circuit breakers. It is suitable for determining
    if the application is ready to accept traffic (e.g., a Kubernetes readiness probe).

    Returns:
        A JSON response with an overall status ('ready' or 'not_ready') and a
        detailed breakdown of each dependency check. Returns HTTP 503 if not ready.
    """
    checks = {}
    overall_ready = True

    try:
        from apps.core.lib.duckdb_pool import get_pool

        # Readiness must fail fast: do not block for long waits on a pooled connection
        # and do not create new connections (which can block on file locks).
        pool = get_pool()
        conn = pool.get_connection(timeout=0.5, allow_create=False)
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            pool.return_connection(conn)
        checks["duckdb"] = {"status": "up", "details": "Connection successful"}
    except Exception as exc:
        checks["duckdb"] = {"status": "down", "error": str(exc)}
        overall_ready = False

    try:
        from apps.core.lib.r_bridge import REngine

        r_engine = REngine()
        if r_engine.is_healthy():
            checks["r_engine"] = {"status": "up", "details": "R engine responsive"}
        else:
            checks["r_engine"] = {"status": "down", "error": "R engine not responsive"}
            overall_ready = False
    except Exception as exc:
        checks["r_engine"] = {"status": "down", "error": str(exc)}
        overall_ready = False

    try:
        from apps.core.lib.temporal_client import get_temporal_client

        async_to_sync(get_temporal_client)()
        checks["temporal"] = {"status": "up", "details": "Client connected"}
    except Exception as exc:
        checks["temporal"] = {"status": "down", "error": str(exc)}
        overall_ready = False

    try:
        cb_states = {}
        for name, cb in _circuit_breakers.items():
            cb_state = cb.get_state()
            cb_states[name] = cb_state.value
            # Critical services that must not have an open circuit breaker
            if cb_state.value == "open" and name in ["rserve", "temporal"]:
                overall_ready = False
        checks["circuit_breakers"] = {"status": "monitored", "states": cb_states}
    except Exception:
        checks["circuit_breakers"] = {"status": "unknown"}

    status = 200 if overall_ready else 503
    return JsonResponse(
        {
            "status": "ready" if overall_ready else "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "checks": checks,
        },
        status=status,
    )


def status_view(_request) -> JsonResponse:
    """
    Provide a detailed status report for administrative purposes.

    This view aggregates high-level status information, including application version,
    environment, and detailed metrics from services like the R engine and all
    registered circuit breakers.
    """
    settings = get_settings()
    status_info = {
        "version": "3.0.0",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "environment": settings.env,
        "services": {},
        "circuit_breakers": {},
    }

    try:
        from apps.core.lib.r_bridge import REngine

        r_engine = REngine()
        status_info["services"]["r_engine"] = {
            "healthy": r_engine.is_healthy(),
            "host": r_engine.host,
            "port": r_engine.port,
        }
    except Exception as exc:
        status_info["services"]["r_engine"] = {"healthy": False, "error": str(exc)}

    try:
        for name, cb in _circuit_breakers.items():
            status_info["circuit_breakers"][name] = cb.get_metrics()
    except Exception:
        pass  # Avoid crashing status view if metrics retrieval fails

    return JsonResponse(status_info)


def version_view(_request) -> JsonResponse:
    """
    Return detailed API version information.

    Delegates to the API versioning middleware to provide a consistent
    response format for version details.
    """
    return JsonResponse(get_version_info())


# ==============================================================================
# URL Patterns
# ==============================================================================
# SECURITY WARNING: The operational endpoints (health, ready, status, version)
# expose detailed internal state. In a production environment, access to these
# endpoints should be restricted at the network or ingress level.
urlpatterns = [
    # Basic liveness probe to confirm the service is running.
    path("health", health),
    # Comprehensive readiness probe to check if the service is ready for traffic.
    path("ready", ready),
    # Common aliases for Kubernetes liveness and readiness probes.
    path("healthz", health),
    path("readyz", ready),
    # Detailed status endpoint for administrative and debugging purposes.
    path("status", status_view),
    # Endpoint to retrieve detailed API version information.
    path("version", version_view),
    # Includes all v1 application API routes from the NinjaAPI instance.
    path("v1/", v1_api.urls),
]
