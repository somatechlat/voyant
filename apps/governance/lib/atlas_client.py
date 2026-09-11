"""
Apache Atlas Metadata Governance Client (FR-23).

Provides integration with Apache Atlas for metadata management, entity
registration, lineage tracking, and type system access.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AtlasEntity:
    """Represents an Atlas metadata entity."""

    guid: str = ""
    type_name: str = ""
    qualified_name: str = ""
    name: str = ""
    attributes: dict[str, Any] = field(default_factory=dict)
    classifications: list[str] = field(default_factory=list)
    status: str = "ACTIVE"


@dataclass
class AtlasLineage:
    """Represents lineage graph for an entity."""

    guid: str
    upstream: list[AtlasEntity] = field(default_factory=list)
    downstream: list[AtlasEntity] = field(default_factory=list)


class AtlasClient:
    """
    Client for Apache Atlas REST API.

    Provides entity CRUD, lineage retrieval, type system access, and
    search capabilities for centralized metadata governance.
    """

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = base_url or getattr(settings, "atlas_url", "")
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=30.0,
                auth=(
                    getattr(get_settings(), "atlas_admin_user", "admin"),
                    getattr(get_settings(), "atlas_admin_password", ""),
                ),
            )
        return self._client

    def get_entity(self, guid: str) -> AtlasEntity:
        """Get an entity by GUID."""
        resp = self._get_client().get(f"/api/atlas/v2/entity/guid/{guid}")
        resp.raise_for_status()
        entity_data = resp.json().get("entity", {})
        attrs = entity_data.get("attributes", {})
        return AtlasEntity(
            guid=entity_data.get("guid", guid),
            type_name=entity_data.get("typeName", ""),
            qualified_name=attrs.get("qualifiedName", ""),
            name=attrs.get("name", ""),
            attributes=attrs,
            classifications=[
                c.get("typeName", "") for c in entity_data.get("classifications", [])
            ],
            status=entity_data.get("status", "ACTIVE"),
        )

    def search_entities(
        self, query: str, type_name: str | None = None, limit: int = 50
    ) -> list[AtlasEntity]:
        """Search for entities using Atlas DSL or full-text search."""
        params: dict[str, Any] = {"query": query, "limit": limit}
        if type_name:
            params["typeName"] = type_name
        resp = self._get_client().get("/api/atlas/v2/search/dsl", params=params)
        resp.raise_for_status()
        results = resp.json().get("results", [])
        entities = []
        for r in results:
            attrs = r.get("attributes", {})
            entities.append(
                AtlasEntity(
                    guid=r.get("guid", ""),
                    type_name=r.get("typeName", ""),
                    qualified_name=attrs.get("qualifiedName", ""),
                    name=attrs.get("name", ""),
                    attributes=attrs,
                )
            )
        return entities

    def create_entity(self, entity: dict[str, Any]) -> AtlasEntity:
        """Create a new entity in Atlas."""
        resp = self._get_client().post(
            "/api/atlas/v2/entity",
            json={"entity": entity},
        )
        resp.raise_for_status()
        data = resp.json()
        guid = data.get("mutatedEntities", {}).get("CREATE", [{}])[0].get("guid", "")
        return AtlasEntity(guid=guid)

    def get_lineage(self, guid: str, depth: int = 3) -> AtlasLineage:
        """Get upstream and downstream lineage for an entity."""
        resp = self._get_client().get(
            f"/api/atlas/v2/lineage/guid/{guid}",
            params={"depth": min(depth, 10)},
        )
        resp.raise_for_status()
        data = resp.json()

        def _parse_entities(nodes: list) -> list[AtlasEntity]:
            entities = []
            for node in nodes:
                attrs = node.get("attributes", {})
                entities.append(
                    AtlasEntity(
                        guid=node.get("guid", ""),
                        type_name=node.get("typeName", ""),
                        qualified_name=attrs.get("qualifiedName", ""),
                        name=attrs.get("name", ""),
                    )
                )
            return entities

        return AtlasLineage(
            guid=guid,
            upstream=_parse_entities(data.get("upstream", {}).get("nodes", [])),
            downstream=_parse_entities(data.get("downstream", {}).get("nodes", [])),
        )

    def add_classification(self, guid: str, classification_type: str) -> None:
        """Add a classification (tag) to an entity."""
        resp = self._get_client().post(
            f"/api/atlas/v2/entity/guid/{guid}/classifications",
            json=[{"typeName": classification_type}],
        )
        resp.raise_for_status()

    def is_available(self) -> bool:
        """Check if Atlas is reachable."""
        try:
            resp = self._get_client().get("/api/atlas/v2/admin/status")
            return resp.status_code == 200
        except Exception:
            return False


def get_atlas_client() -> AtlasClient:
    """Factory function for the singleton Atlas client."""
    return AtlasClient()
