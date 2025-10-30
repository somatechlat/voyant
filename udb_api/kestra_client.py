"""Kestra client integration for optional orchestration triggers.

Provides minimal wrapper to trigger and monitor flows if Kestra feature flag is enabled.
"""
from __future__ import annotations

import asyncio
import random
import os
from typing import Any, Dict, Optional

import httpx  # third-party
from .metrics import kestra_retries

class KestraClient:
    def __init__(self, base_url: str, api_token: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token or os.getenv("KESTRA_API_TOKEN")
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_token:
            h["Authorization"] = f"Bearer {self.api_token}"
        return h

    async def trigger_flow(
        self,
        namespace: str,
        flow_id: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/executions/{namespace}/{flow_id}"
        attempts = 0
        backoff = 0.5
        last_exc: Exception | None = None
        while attempts < 5:
            try:
                resp = await self._client.post(url, headers=self._headers(), json={"inputs": inputs or {}})
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:  # noqa: BLE001
                last_exc = e
                attempts += 1
                kestra_retries.inc()
                await asyncio.sleep(backoff + random.uniform(0, backoff)/2)
                backoff = min(backoff * 2, 5)
        assert last_exc is not None
        raise last_exc

    async def get_execution(self, execution_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v1/executions/{execution_id}"
        attempts = 0
        backoff = 0.5
        last_exc: Exception | None = None
        while attempts < 5:
            try:
                resp = await self._client.get(url, headers=self._headers())
                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError("server error", request=resp.request, response=resp)
                resp.raise_for_status()
                return resp.json()
            except Exception as e:  # noqa: BLE001
                last_exc = e
                attempts += 1
                kestra_retries.inc()
                await asyncio.sleep(backoff + random.uniform(0, backoff)/2)
                backoff = min(backoff * 2, 5)
        assert last_exc is not None
        raise last_exc

_kestra_client: KestraClient | None = None

def get_kestra_client() -> KestraClient:
    base = os.getenv("KESTRA_BASE_URL", "http://kestra:8080")
    global _kestra_client
    if _kestra_client is None:
        _kestra_client = KestraClient(base_url=base)
    return _kestra_client
