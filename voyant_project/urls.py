"""URL configuration for Voyant."""
from __future__ import annotations

from datetime import datetime

from django.http import JsonResponse
from django.urls import path
from asgiref.sync import async_to_sync

from voyant.api.middleware import get_version_info
from voyant.core.circuit_breaker import _circuit_breakers
from voyant.core.config import get_settings
from voyant_app.api import api as v1_api


def health(_request):
    return JsonResponse(
        {
            "status": "healthy",
            "version": "3.0.0",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


def ready(_request):
    checks = {}
    overall_ready = True

    try:
        from voyant.core.duckdb_pool import get_connection

        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        checks["duckdb"] = {"status": "up", "details": "Connection successful"}
    except Exception as exc:
        checks["duckdb"] = {"status": "down", "error": str(exc)}
        overall_ready = False

    try:
        from voyant.core.r_bridge import REngine

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
        from voyant.core.temporal_client import get_temporal_client

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
            if cb_state.value == "open" and name in ["rserve", "temporal"]:
                overall_ready = False
        checks["circuit_breakers"] = {"status": "monitored", "states": cb_states}
    except Exception:
        checks["circuit_breakers"] = {"status": "unknown"}

    status = 200 if overall_ready else 503
    return JsonResponse(
        {
            "status": "ready" if overall_ready else "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": checks,
        },
        status=status,
    )


def status_view(_request):
    settings = get_settings()
    status_info = {
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.env,
        "services": {},
        "circuit_breakers": {},
    }

    try:
        from voyant.core.r_bridge import REngine

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
        pass

    return JsonResponse(status_info)


def version_view(_request):
    return JsonResponse(get_version_info())


urlpatterns = [
    path("health", health),
    path("ready", ready),
    path("healthz", health),
    path("readyz", ready),
    path("status", status_view),
    path("version", version_view),
    path("v1/", v1_api.urls),
]
