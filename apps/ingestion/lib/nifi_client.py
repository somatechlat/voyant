"""
Apache NiFi Dataflow Integration Client (FR-25).

Provides integration with Apache NiFi for dataflow management — creating,
monitoring, and controlling data pipelines that feed into Voyant's ingestion layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class NiFiProcessGroup:
    """Represents a NiFi process group (dataflow)."""

    id: str
    name: str
    running_count: int = 0
    stopped_count: int = 0
    invalid_count: int = 0
    disabled_count: int = 0


@dataclass
class NiFiProcessor:
    """Represents a NiFi processor (single processing step)."""

    id: str
    name: str
    type: str = ""
    state: str = "STOPPED"
    properties: dict[str, str] = field(default_factory=dict)


class NiFiClient:
    """
    Client for Apache NiFi REST API.

    Provides dataflow lifecycle management — create, start, stop, and monitor
    NiFi data pipelines that feed data into Voyant's ingestion layer.
    """

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = base_url or getattr(settings, "nifi_url", "")
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=30.0,
            )
        return self._client

    def get_root_process_group(self) -> NiFiProcessGroup:
        """Get the root process group."""
        resp = self._get_client().get("/nifi-api/flow/process-groups/root")
        resp.raise_for_status()
        pg = resp.json().get("processGroupFlow", {}).get("breadcrumb", {}).get(
            "breadcrumb", {}
        )
        status = resp.json().get("processGroupFlow", {}).get("status", {})
        return NiFiProcessGroup(
            id=pg.get("id", "root"),
            name=pg.get("name", "root"),
            running_count=status.get("aggregateSnapshot", {}).get(
                "activeThreadCount", 0
            ),
        )

    def list_processors(self, process_group_id: str = "root") -> list[NiFiProcessor]:
        """List all processors in a process group."""
        resp = self._get_client().get(
            f"/nifi-api/flow/process-groups/{process_group_id}/processors"
        )
        resp.raise_for_status()
        processors = resp.json().get("processors", [])
        return [
            NiFiProcessor(
                id=p.get("id", ""),
                name=p.get("component", {}).get("name", ""),
                type=p.get("component", {}).get("type", ""),
                state=p.get("component", {}).get("state", "STOPPED"),
                properties=p.get("component", {}).get("properties", {}),
            )
            for p in processors
        ]

    def start_processor(self, processor_id: str) -> None:
        """Start a NiFi processor."""
        resp = self._get_client().put(
            f"/nifi-api/processors/{processor_id}/run-status",
            json={"state": "RUNNING", "revision": {"version": 0}},
        )
        resp.raise_for_status()

    def stop_processor(self, processor_id: str) -> None:
        """Stop a NiFi processor."""
        resp = self._get_client().put(
            f"/nifi-api/processors/{processor_id}/run-status",
            json={"state": "STOPPED", "revision": {"version": 0}},
        )
        resp.raise_for_status()

    def get_flow_status(self) -> dict[str, Any]:
        """Get the overall NiFi flow status."""
        resp = self._get_client().get("/nifi-api/flow/status")
        resp.raise_for_status()
        return resp.json().get("controllerStatus", {})

    def is_available(self) -> bool:
        """Check if NiFi is reachable."""
        try:
            resp = self._get_client().get("/nifi-api/flow/status")
            return resp.status_code == 200
        except Exception:
            return False


def get_nifi_client() -> NiFiClient:
    """Factory function for the singleton NiFi client."""
    return NiFiClient()
