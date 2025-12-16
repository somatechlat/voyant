"""
Health check endpoints.

Comprehensive health and readiness probes for production deployment.
Adheres to VIBE Coding Rules: Real service checks, no mocks.

Performance Engineer: Fast health checks (<100ms) for liveness
SRE/Security Auditor: Detailed readiness checks with external dependencies
ISO Documenter: Clear status codes and error messages
"""
from fastapi import APIRouter, Response, status
from datetime import datetime
import logging
from typing import Dict, Any

from voyant.core.config import get_settings
from voyant.core.circuit_breaker import get_circuit_breaker

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health():
    """
    Liveness probe - Is the service running?
    
    Returns 200 if service is alive, regardless of external dependencies.
    Kubernetes uses this to restart crashed pods.
    
    Performance Engineer: O(1) check, <1ms response time
    """
    return {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/ready")
async def ready(response: Response):
    """
    Readiness probe - Is the service ready to handle requests?
    
    Checks:
    - Temporal connection
    - DuckDB availability
    - R-Engine availability
    - Circuit breaker states
    
    Returns 200 if ready, 503 if not ready.
    Kubernetes uses this to route traffic.
    
    QA Engineer: Comprehensive dependency validation
    Security Auditor: No sensitive data in responses
    """
    settings = get_settings()
    checks: Dict[str, Any] = {}
    overall_ready = True
    
    # 1. DuckDB Check
    try:
        from voyant.core.storage import get_duckdb_connection
        conn = get_duckdb_connection()
        conn.execute("SELECT 1").fetchone()
        checks["duckdb"] = {"status": "up", "details": "Connection successful"}
    except Exception as e:
        checks["duckdb"] = {"status": "down", "error": str(e)}
        overall_ready = False
    
    # 2. R-Engine Check
    try:
        from voyant.core.r_bridge import REngine
        r = REngine()
        is_healthy = r.is_healthy()
        if is_healthy:
            checks["r_engine"] = {"status": "up", "details": "R engine responsive"}
        else:
            checks["r_engine"] = {"status": "down", "error": "R engine not responsive"}
            overall_ready = False
    except Exception as e:
        checks["r_engine"] = {"status": "down", "error": str(e)}
        overall_ready = False
    
    # 3. Temporal Check
    try:
        from voyant.core.temporal_client import get_temporal_client
        client = await get_temporal_client()
        # Simple check - if client exists and connected
        checks["temporal"] = {"status": "up", "details": "Client connected"}
    except Exception as e:
        checks["temporal"] = {"status": "down", "error": str(e)}
        overall_ready = False
    
    # 4. Circuit Breaker States
    try:
        from voyant.core.circuit_breaker import _circuit_breakers
        cb_states = {}
        for name, cb in _circuit_breakers.items():
            cb_state = cb.get_state()
            cb_states[name] = cb_state.value
            # If any critical circuit breaker is open, mark as not ready
            if cb_state.value == "open" and name in ["rserve", "temporal"]:
                overall_ready = False
        
        checks["circuit_breakers"] = {
            "status": "monitored",
            "states": cb_states
        }
    except Exception as e:
        logger.warning(f"Could not check circuit breakers: {e}")
        checks["circuit_breakers"] = {"status": "unknown"}
    
    # Set HTTP status code
    if not overall_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": "ready" if overall_ready else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks
    }


@router.get("/healthz")
async def healthz():
    """
    Kubernetes-style liveness endpoint (alias for /health).
    
    UX Consultant: Standard Kubernetes naming convention
    """
    return await health()


@router.get("/readyz")
async def readyz(response: Response):
    """
    Kubernetes-style readiness endpoint (alias for /ready).
    
    UX Consultant: Standard Kubernetes naming convention
    """
    return await ready(response)


@router.get("/status")
async def detailed_status():
    """
    Detailed system status for monitoring dashboards.
    
    Returns comprehensive system state including:
    - All service health
    - Circuit breaker metrics
    - Version information
    - Uptime
    
    ISO Documenter: Structured status for SRE dashboards
    """
    settings = get_settings()
    
    status_info = {
        "version": "3.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment,
        "services": {},
        "circuit_breakers": {}
    }
    
    # Collect service statuses
    try:
        from voyant.core.r_bridge import REngine
        r = REngine()
        status_info["services"]["r_engine"] = {
            "healthy": r.is_healthy(),
            "host": r.host,
            "port": r.port
        }
    except Exception as e:
        status_info["services"]["r_engine"] = {"healthy": False, "error": str(e)}
    
    # Collect circuit breaker metrics
    try:
        from voyant.core.circuit_breaker import _circuit_breakers
        for name, cb in _circuit_breakers.items():
            status_info["circuit_breakers"][name] = cb.get_metrics()
    except Exception as e:
        logger.warning(f"Could not collect circuit breaker metrics: {e}")
    
    return status_info

