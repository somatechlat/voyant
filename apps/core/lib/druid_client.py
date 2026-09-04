"""
Apache Druid/Pinot OLAP Support (FR-27).

Provides a client for querying Apache Druid (and Apache Pinot) for real-time
OLAP analytics on high-cardinality, time-series data.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class OLAPQueryResult:
    """Result from an OLAP query (Druid or Pinot)."""

    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    query_duration_ms: int = 0
    engine: str = "druid"


@dataclass
class OLAPDataSource:
    """Represents an OLAP data source (Druid datasource / Pinot table)."""

    name: str
    dimensions: list[str] = field(default_factory=list)
    metrics: list[str] = field(default_factory=list)
    intervals: list[str] = field(default_factory=list)
    row_count: int = 0
    engine: str = "druid"


class DruidClient:
    """
    Client for Apache Druid native query API.

    Supports SQL and native Druid queries for real-time OLAP analytics.
    Also compatible with Apache Pinot's SQL endpoint.
    """

    def __init__(self, base_url: str | None = None, engine: str = "druid"):
        settings = get_settings()
        self.base_url = base_url or getattr(settings, "druid_url", "")
        self.engine = engine
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=60.0,
                headers={"Content-Type": "application/json"},
            )
        return self._client

    def execute_sql(self, sql: str, limit: int = 10000) -> OLAPQueryResult:
        """Execute a SQL query against Druid/Pinot."""
        if self.engine == "pinot":
            return self._execute_pinot_sql(sql, limit)

        resp = self._get_client().post(
            "/druid/v2/sql",
            json={"query": sql, "resultFormat": "array", "limit": limit},
        )
        resp.raise_for_status()
        data = resp.json()
        columns = [c.get("name", "") for c in data.get("header", [])]
        rows = data.get("rows", [])
        return OLAPQueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            engine="druid",
        )

    def _execute_pinot_sql(self, sql: str, limit: int) -> OLAPQueryResult:
        """Execute SQL against Pinot's SQL endpoint."""
        resp = self._get_client().post(
            "/query/sql",
            json={"sql": sql},
        )
        resp.raise_for_status()
        data = resp.json()
        result_table = data.get("resultTable", {})
        columns = result_table.get("columnNames", [])
        rows = result_table.get("rows", [])
        return OLAPQueryResult(
            columns=columns,
            rows=rows[:limit],
            row_count=len(rows),
            engine="pinot",
        )

    def list_datasources(self) -> list[OLAPDataSource]:
        """List available datasources/tables."""
        if self.engine == "pinot":
            return self._list_pinot_tables()

        resp = self._get_client().get("/druid/v2/datasources")
        resp.raise_for_status()
        names = resp.json()
        datasources = []
        for name in names:
            try:
                resp2 = self._get_client().get(f"/druid/v2/datasources/{name}")
                resp2.raise_for_status()
                meta = resp2.json()
                datasources.append(
                    OLAPDataSource(
                        name=name,
                        dimensions=meta.get("dimensions", []),
                        metrics=meta.get("metrics", []),
                        intervals=meta.get("intervals", []),
                        engine="druid",
                    )
                )
            except Exception:
                datasources.append(OLAPDataSource(name=name, engine="druid"))
        return datasources

    def _list_pinot_tables(self) -> list[OLAPDataSource]:
        """List Pinot tables."""
        resp = self._get_client().get("/tables")
        resp.raise_for_status()
        tables = resp.json().get("tables", [])
        return [OLAPDataSource(name=t, engine="pinot") for t in tables]

    def is_available(self) -> bool:
        """Check if Druid/Pinot is reachable."""
        try:
            if self.engine == "pinot":
                resp = self._get_client().get("/health")
            else:
                resp = self._get_client().get("/status")
            return resp.status_code == 200
        except Exception:
            return False


def get_druid_client() -> DruidClient:
    """Factory function for the singleton Druid client."""
    return DruidClient()


def get_pinot_client() -> DruidClient:
    """Factory function for the singleton Pinot client."""
    return DruidClient(engine="pinot")
