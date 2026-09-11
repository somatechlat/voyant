"""
Apache Superset BI Integration Client (FR-26).

Provides integration with Apache Superset for business intelligence —
creating datasets, charts, and dashboards from Voyant's analytical results.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SupersetDataset:
    """Represents a Superset dataset (virtual or physical table)."""

    id: int | None = None
    database_id: int = 0
    schema: str = ""
    table_name: str = ""
    sql: str = ""
    columns: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class SupersetChart:
    """Represents a Superset chart/visualization."""

    id: int | None = None
    slice_name: str = ""
    viz_type: str = ""
    datasource_id: int = 0
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class SupersetDashboard:
    """Represents a Superset dashboard."""

    id: int | None = None
    title: str = ""
    slug: str = ""
    charts: list[int] = field(default_factory=list)


class SupersetClient:
    """
    Client for Apache Superset REST API.

    Provides dataset, chart, and dashboard management for embedding
    Voyant analytical results into Superset BI dashboards.
    """

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = base_url or getattr(settings, "superset_url", "")
        self._token: str | None = None
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=30.0,
            )
        return self._client

    def _get_token(self) -> str:
        if self._token:
            return self._token
        settings = get_settings()
        resp = self._get_client().post(
            "/api/v1/security/login",
            json={
                "username": getattr(settings, "superset_admin_user", "admin"),
                "password": getattr(settings, "superset_admin_password", ""),
                "provider": "db",
            },
        )
        resp.raise_for_status()
        self._token = resp.json().get("access_token", "")
        return self._token  # type: ignore[reportReturnType]

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._get_token()}"}

    def create_dataset(self, dataset: SupersetDataset) -> SupersetDataset:
        """Create a new dataset in Superset."""
        payload: dict[str, Any] = {
            "database": dataset.database_id,
            "schema": dataset.schema,
            "table_name": dataset.table_name,
        }
        if dataset.sql:
            payload["sql"] = dataset.sql
        resp = self._get_client().post(
            "/api/v1/dataset/",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        data = resp.json().get("id")
        dataset.id = data
        return dataset

    def create_chart(self, chart: SupersetChart) -> SupersetChart:
        """Create a new chart in Superset."""
        payload = {
            "slice_name": chart.slice_name,
            "viz_type": chart.viz_type,
            "datasource_id": chart.datasource_id,
            "params": str(chart.params),
        }
        resp = self._get_client().post(
            "/api/v1/chart/",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        chart.id = resp.json().get("id")
        return chart

    def create_dashboard(self, dashboard: SupersetDashboard) -> SupersetDashboard:
        """Create a new dashboard in Superset."""
        payload = {
            "dashboard_title": dashboard.title,
            "slug": dashboard.slug,
        }
        resp = self._get_client().post(
            "/api/v1/dashboard/",
            json=payload,
            headers=self._headers(),
        )
        resp.raise_for_status()
        dashboard.id = resp.json().get("id")
        return dashboard

    def list_databases(self) -> list[dict[str, Any]]:
        """List available database connections in Superset."""
        resp = self._get_client().get(
            "/api/v1/database/",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json().get("result", [])

    def is_available(self) -> bool:
        """Check if Superset is reachable."""
        try:
            resp = self._get_client().get("/health")
            return resp.status_code == 200
        except Exception:
            return False


def get_superset_client() -> SupersetClient:
    """Factory function for the singleton Superset client."""
    return SupersetClient()
