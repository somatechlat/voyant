"""
Voyant Core Views.

Operational web views for health, readiness, status, and version probes.
Extracted from voyant_project/urls.py per Django architectural convention:
  - View functions belong in app views.py, NOT in url configs.

All probes check real infrastructure (DuckDB file, Temporal connectivity,
circuit breaker states). No mocks or stubs.
"""

from __future__ import annotations

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from asgiref.sync import async_to_sync
from django.http import JsonResponse

from apps.core.config import get_settings
from apps.core.lib.circuit_breaker import _circuit_breakers
from apps.core.middleware import get_version_info


def _run_with_timeout(func, timeout_seconds: float):
    """
    Execute a synchronous callable with a hard timeout.

    Args:
        func: Zero-argument callable to execute.
        timeout_seconds: Maximum wall-clock seconds to wait.

    Returns:
        The return value of func.

    Raises:
        concurrent.futures.TimeoutError: If func does not complete in time.
    """
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(func)
    try:
        return future.result(timeout=timeout_seconds)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)


def health(_request) -> JsonResponse:
    """
    Minimal liveness probe.

    Lightweight check suitable for Kubernetes liveness probes.
    Does NOT verify downstream dependency health — only confirms
    the Django process is alive and responding.

    Returns:
        200 JSON: {status, version, timestamp}
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
    Comprehensive readiness probe.

    Checks DuckDB file accessibility, R engine (if configured),
    Temporal cluster connectivity, and all circuit breaker states.
    Suitable for Kubernetes readiness probes.

    Returns:
        200 JSON: {status: "ready", checks: {...}}
        503 JSON: {status: "not_ready", checks: {...}} when any critical check fails.
    """
    checks: dict = {}
    overall_ready = True
    settings = get_settings()

    # DuckDB file check
    try:
        duckdb_path = settings.duckdb_path
        if not os.path.exists(duckdb_path):
            checks["duckdb"] = {
                "status": "skipped",
                "details": f"DuckDB file not initialized yet: {duckdb_path}",
            }
        elif not os.access(duckdb_path, os.R_OK | os.W_OK):
            raise PermissionError(
                f"DuckDB file is not readable/writable: {duckdb_path}"
            )
        if "duckdb" not in checks:
            checks["duckdb"] = {
                "status": "up",
                "details": f"File accessible at {duckdb_path}",
            }
    except Exception as exc:
        checks["duckdb"] = {"status": "down", "error": str(exc)}
        overall_ready = False

    # R engine check (optional — only when configured)
    if settings.r_engine_host:
        try:
            from apps.core.lib.r_bridge import REngine

            r_engine = REngine()
            if _run_with_timeout(r_engine.is_healthy, 2.0):
                checks["r_engine"] = {"status": "up", "details": "R engine responsive"}
            else:
                checks["r_engine"] = {
                    "status": "down",
                    "error": "R engine not responsive",
                }
                overall_ready = False
        except Exception as exc:
            checks["r_engine"] = {"status": "down", "error": str(exc)}
            overall_ready = False
    else:
        checks["r_engine"] = {
            "status": "skipped",
            "details": "VOYANT_R_ENGINE_HOST is not configured",
        }

    # Temporal connectivity check
    try:
        from apps.core.lib.temporal_client import get_temporal_client

        def _check_temporal() -> None:
            async_to_sync(asyncio.wait_for)(get_temporal_client(), timeout=2.0)

        _run_with_timeout(_check_temporal, 3.0)
        checks["temporal"] = {"status": "up", "details": "Client connected"}
    except Exception as exc:
        checks["temporal"] = {"status": "down", "error": str(exc)}
        overall_ready = False

    # Circuit breaker states
    try:
        cb_states = {}
        for name, cb in _circuit_breakers.items():
            cb_state = cb.get_state()
            cb_states[name] = cb_state.value
            if cb_state.value == "open" and name in ["rserve", "temporal"]:
                overall_ready = False
        checks["circuit_breakers"] = {"status": "monitored", "states": cb_states}
    except Exception:
        checks["circuit_breakers"] = {"status": "unknown"}

    http_status = 200 if overall_ready else 503
    return JsonResponse(
        {
            "status": "ready" if overall_ready else "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "checks": checks,
        },
        status=http_status,
    )


def status_view(_request) -> JsonResponse:
    """
    Detailed administrative status report.

    Aggregates version, environment, R engine metrics, and all circuit
    breaker states for debugging and monitoring dashboards.

    Returns:
        200 JSON: Full status payload with service health and circuit breaker metrics.
    """
    settings = get_settings()
    status_info: dict = {
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
        pass  # Avoid crashing the status view if metrics retrieval fails.

    return JsonResponse(status_info)


def version_view(_request) -> JsonResponse:
    """
    API version information endpoint.

    Delegates to the API versioning middleware for a consistent
    version response format across all Voyant clients.

    Returns:
        200 JSON: Versioning metadata from the API versioning middleware.
    """
    return JsonResponse(get_version_info())
