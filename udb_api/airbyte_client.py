"""Thin async wrapper around Airbyte OSS API.

Implements a subset of the Airbyte public API:
 - POST /api/v1/source_definitions/list
 - POST /api/v1/sources/create
 - POST /api/v1/destinations/create
 - POST /api/v1/connections/create
 - POST /api/v1/connections/sync
 - POST /api/v1/jobs/get
 - POST /api/v1/workspaces/list (to derive workspace if ID not provided)

All operations require a workspace ID; if not supplied explicitly in settings, the
first active workspace is used (deterministic but discouraged for multi-tenant prod).
"""
from __future__ import annotations

import asyncio
import random
import logging
from typing import Any, Dict, Optional

import httpx

from .config import get_settings
from .metrics import airbyte_retries

logger = logging.getLogger("udb.airbyte")

class AirbyteClient:
    def __init__(self, base_url: Optional[str] = None):
        self.settings = get_settings()
        self.base_url = base_url or self.settings.airbyte_url
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=30)

    async def close(self):  # pragma: no cover
        await self._client.aclose()

    async def health(self) -> bool:
        try:
            r = await self._client.get("/health")
            return r.status_code == 200
        except Exception:  # pragma: no cover
            return False

    async def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        attempts = 0
        backoff = 0.5
        last_exc: Exception | None = None
        while attempts < 5:
            try:
                r = await self._client.post(path, json=payload)
                if r.status_code >= 500:
                    raise httpx.HTTPStatusError("server error", request=r.request, response=r)
                r.raise_for_status()
                return r.json()
            except Exception as e:  # noqa: BLE001
                last_exc = e
                attempts += 1
                airbyte_retries.inc()
                logger.warning({"event": "airbyte_retry", "path": path, "attempt": attempts, "error": str(e)})
                jitter = random.uniform(0, backoff)
                await asyncio.sleep(backoff + jitter / 2)
                backoff = min(backoff * 2, 5)
        assert last_exc is not None
        raise last_exc

    async def get_workspace_id(self) -> str:
        if self.settings.airbyte_workspace_id:
            return self.settings.airbyte_workspace_id
        data = await self._post("/api/v1/workspaces/list", {"pagination": {"page_size": 20}})
        workspaces = data.get("workspaces", [])
        if not workspaces:
            raise RuntimeError("No Airbyte workspace found; set AIRBYTE_WORKSPACE_ID")
        wid = workspaces[0]["workspaceId"]
        logger.warning("Using first workspaceId=%s (configure AIRBYTE_WORKSPACE_ID)", wid)
        return wid

    async def create_source(self, name: str, source_def_id: str, config: dict) -> str:
        workspace_id = await self.get_workspace_id()
        payload = {
            "workspaceId": workspace_id,
            "name": name,
            "sourceDefinitionId": source_def_id,
            "connectionConfiguration": config,
        }
        data = await self._post("/api/v1/sources/create", payload)
        source_id = data.get("sourceId")
        logger.info({"event": "airbyte_source_created", "sourceId": source_id})
        return source_id

    async def ensure_destination(self, name: str, destination_def_id: str, config: dict) -> str:
        workspace_id = await self.get_workspace_id()
        payload = {
            "workspaceId": workspace_id,
            "name": name,
            "destinationDefinitionId": destination_def_id,
            "connectionConfiguration": config,
        }
        data = await self._post("/api/v1/destinations/create", payload)
        destination_id = data.get("destinationId")
        logger.info({"event": "airbyte_destination_created", "destinationId": destination_id})
        return destination_id

    async def create_connection(self, source_id: str, destination_id: str, stream_config: Optional[dict] = None) -> str:
        # NOTE: For simplicity we enable all streams with full refresh overwrite initially.
        payload = {
            "name": f"conn_{source_id[:5]}_{destination_id[:5]}",
            "sourceId": source_id,
            "destinationId": destination_id,
            "namespaceDefinition": "source",
            "namespaceFormat": "${SOURCE_NAMESPACE}",
            "prefix": "",
            "syncCatalog": stream_config or {"streams": []},
            "scheduleType": "manual",
            "status": "active",
        }
        data = await self._post("/api/v1/connections/create", payload)
        connection_id = data.get("connectionId")
        logger.info({"event": "airbyte_connection_created", "connectionId": connection_id})
        return connection_id

    async def discover_schema(self, source_id: str) -> dict:
        payload = {"sourceId": source_id}
        data = await self._post("/api/v1/sources/discover_schema", payload)
        return data.get("catalog", {})

    async def trigger_sync(self, connection_id: str) -> str:
        data = await self._post("/api/v1/connections/sync", {"connectionId": connection_id})
        job_id = data.get("job", {}).get("id") or data.get("jobId")
        logger.info({"event": "airbyte_sync_triggered", "connectionId": connection_id, "jobId": job_id})
        return str(job_id)

    async def job_status(self, job_id: str) -> dict:
        data = await self._post("/api/v1/jobs/get", {"id": int(job_id)})
        job = data.get("job", {})
        state = job.get("status", "unknown")
        return {"jobId": job_id, "state": state, "raw": job}

# Singleton accessor (simple)
_airbyte_client: Optional[AirbyteClient] = None

def get_airbyte_client() -> AirbyteClient:
    global _airbyte_client
    if _airbyte_client is None:
        _airbyte_client = AirbyteClient()
    return _airbyte_client
