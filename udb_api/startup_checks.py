"""Dependency startup self-checks.

Performs lightweight connectivity / readiness probes for enabled integrations.
Exposes an in-memory snapshot and functions to run checks.
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import time
from typing import Any, Dict

import duckdb
import httpx

from .config import get_settings
from .metrics import dependency_check_failures, dependency_up

_LATEST: Dict[str, Dict[str, Any]] = {}
_LAST_RUN_TS: float | None = None


async def _check_duckdb(res: Dict[str, Any]):
    try:
        path = get_settings().duckdb_path
        con = duckdb.connect(path)
        con.execute("SELECT 1")
        res["duckdb"] = {"status": "ok"}
    except Exception as e:  # noqa: BLE001
        res["duckdb"] = {"status": "error", "detail": str(e)[:200]}


async def _check_redis(res: Dict[str, Any]):
    import redis  # type: ignore

    url = get_settings().redis_url
    if not url:
        return
    try:
        r = redis.Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2)
        pong = r.ping()
        res["redis"] = {"status": "ok", "pong": pong}
    except Exception as e:  # noqa: BLE001
        res["redis"] = {"status": "error", "detail": str(e)[:200]}


async def _check_kafka(res: Dict[str, Any]):
    brokers = get_settings().kafka_brokers
    if not brokers:
        return
    # Simple TCP connect to first broker
    broker = brokers.split(",")[0]
    host, port = broker.split(":") if ":" in broker else (broker, "9092")
    try:
        with socket.create_connection((host, int(port)), timeout=2):
            res["kafka"] = {"status": "ok"}
    except Exception as e:  # noqa: BLE001
        res["kafka"] = {"status": "error", "detail": str(e)[:200]}


async def _check_airbyte(res: Dict[str, Any]):
    base = str(get_settings().airbyte_url)
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            # Hitting /health is preferable; fallback to root
            r = await client.get(f"{base}/health")
            if r.status_code == 200:
                res["airbyte"] = {"status": "ok"}
            else:
                res["airbyte"] = {"status": "error", "code": r.status_code}
    except Exception as e:  # noqa: BLE001
        res["airbyte"] = {"status": "error", "detail": str(e)[:160]}


async def _check_kestra(res: Dict[str, Any]):
    s = get_settings()
    if not s.enable_kestra:
        return
    base = os.getenv("KESTRA_BASE_URL", s.kestra_base_url or "http://kestra:8080")
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{base}/api/v1/executions?limit=1")
            if r.status_code < 300:
                res["kestra"] = {"status": "ok"}
            else:
                res["kestra"] = {"status": "error", "code": r.status_code}
    except Exception as e:  # noqa: BLE001
        res["kestra"] = {"status": "error", "detail": str(e)[:160]}


async def run_checks() -> Dict[str, Any]:
    global _LATEST, _LAST_RUN_TS
    res: Dict[str, Any] = {}
    await asyncio.gather(
        _check_duckdb(res),
        _check_redis(res),
        _check_kafka(res),
        _check_airbyte(res),
        _check_kestra(res),
    )
    # Update metrics
    for component, data in res.items():
        dependency_up.labels(component).set(1 if data.get("status") == "ok" else 0)
        if data.get("status") != "ok":
            dependency_check_failures.inc()
    _LAST_RUN_TS = time.time()
    _LATEST = res
    return res


def latest() -> Dict[str, Any]:
    return {
        "lastRun": _LAST_RUN_TS,
        "checks": _LATEST,
        "summary": {
            "ok": [k for k, v in _LATEST.items() if v.get("status") == "ok"],
            "error": {k: v for k, v in _LATEST.items() if v.get("status") == "error"},
        },
    }


async def ensure_startup(strict: bool = False):
    res = await run_checks()
    if strict:
        failing = [k for k, v in res.items() if v.get("status") != "ok"]
        if failing:
            # Emit JSON for operator clarity then raise
            raise RuntimeError(f"Startup dependency failures: {json.dumps({k: res[k] for k in failing})}")
