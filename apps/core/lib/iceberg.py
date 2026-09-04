"""
Apache Iceberg Integration Module (FR-20).

Provides a client for interacting with Iceberg tables via the REST catalog API.
Supports table discovery, schema inspection, snapshot management, and data reads
through Trino as the query engine.

Iceberg tables are accessed through Trino's Iceberg catalog connector, which
provides full SQL access to Iceberg's time-travel, schema evolution, and
partition evolution features.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class IcebergTable:
    """Represents an Iceberg table with its metadata."""

    namespace: str
    table_name: str
    location: str = ""
    current_snapshot_id: int | None = None
    schema_fields: list[dict[str, Any]] = field(default_factory=list)
    partition_spec: list[dict[str, Any]] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    snapshot_count: int = 0


@dataclass
class IcebergSnapshot:
    """Represents an Iceberg table snapshot (point-in-time version)."""

    snapshot_id: int
    timestamp_ms: int
    operation: str = ""
    summary: dict[str, str] = field(default_factory=dict)
    manifest_list: str = ""


class IcebergClient:
    """
    Client for Apache Iceberg REST catalog operations.

    Provides table discovery, schema inspection, and snapshot management
    through the Iceberg REST catalog API. Data reads are delegated to Trino
    via the existing TrinoClient.
    """

    def __init__(self, catalog_url: str | None = None):
        settings = get_settings()
        self.catalog_url = catalog_url or getattr(settings, "iceberg_catalog_url", "")
        self.warehouse = getattr(settings, "iceberg_warehouse", "voyant-warehouse")
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.catalog_url,
                timeout=30.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def list_namespaces(self) -> list[str]:
        """List all namespaces in the Iceberg catalog."""
        resp = self._get_client().get("/v1/namespaces")
        resp.raise_for_status()
        data = resp.json()
        return [".".join(ns) for ns in data.get("namespaces", [])]

    def list_tables(self, namespace: str) -> list[str]:
        """List all tables in a namespace."""
        resp = self._get_client().get(f"/v1/namespaces/{namespace}/tables")
        resp.raise_for_status()
        data = resp.json()
        return [t.get("name", "") for t in data.get("identifiers", [])]

    def get_table(self, namespace: str, table_name: str) -> IcebergTable:
        """Get full table metadata including schema, partitions, and snapshots."""
        resp = self._get_client().get(f"/v1/namespaces/{namespace}/tables/{table_name}")
        resp.raise_for_status()
        data = resp.json()

        metadata = data.get("metadata", {})
        current_schema_id = metadata.get("current-schema-id", 0)
        schemas = metadata.get("schemas", [])
        fields = []
        for schema in schemas:
            if schema.get("schema-id") == current_schema_id:
                fields = schema.get("fields", [])
                break

        partition_spec_id = metadata.get("default-spec-id", 0)
        specs = metadata.get("partition-specs", [])
        partitions = []
        for spec in specs:
            if spec.get("spec-id") == partition_spec_id:
                partitions = spec.get("fields", [])
                break

        snapshots = metadata.get("snapshots", [])
        current_snapshot = metadata.get("current-snapshot-id")

        return IcebergTable(
            namespace=namespace,
            table_name=table_name,
            location=metadata.get("location", ""),
            current_snapshot_id=current_snapshot,
            schema_fields=[
                {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "type": f.get("type"),
                    "required": f.get("required", False),
                }
                for f in fields
            ],
            partition_spec=[
                {
                    "source-id": p.get("source-id"),
                    "field-id": p.get("field-id"),
                    "transform": p.get("transform"),
                    "name": p.get("name"),
                }
                for p in partitions
            ],
            properties=metadata.get("properties", {}),
            snapshot_count=len(snapshots),
        )

    def get_snapshots(self, namespace: str, table_name: str) -> list[IcebergSnapshot]:
        """Get all snapshots for a table."""
        resp = self._get_client().get(f"/v1/namespaces/{namespace}/tables/{table_name}")
        resp.raise_for_status()
        metadata = resp.json().get("metadata", {})

        snapshots = []
        for snap in metadata.get("snapshots", []):
            summary = snap.get("summary", {})
            snapshots.append(
                IcebergSnapshot(
                    snapshot_id=snap.get("snapshot-id", 0),
                    timestamp_ms=snap.get("timestamp-ms", 0),
                    operation=summary.get("operation", ""),
                    summary=summary,
                    manifest_list=snap.get("manifest-list", ""),
                )
            )
        return snapshots

    def create_namespace(self, namespace: str) -> dict:
        """Create a new namespace in the catalog."""
        resp = self._get_client().post(
            "/v1/namespaces",
            json={"namespace": [namespace]},
        )
        resp.raise_for_status()
        return resp.json()

    def drop_table(self, namespace: str, table_name: str, purge: bool = False) -> None:
        """Drop an Iceberg table. If purge=True, delete all data files."""
        url = f"/v1/namespaces/{namespace}/tables/{table_name}"
        if purge:
            url += "?purge=true"
        resp = self._get_client().delete(url)
        resp.raise_for_status()

    def is_available(self) -> bool:
        """Check if the Iceberg catalog is reachable."""
        try:
            resp = self._get_client().get("/v1/config")
            return resp.status_code == 200
        except Exception:
            return False


def get_iceberg_client() -> IcebergClient:
    """Factory function for the singleton Iceberg client."""
    return IcebergClient()
