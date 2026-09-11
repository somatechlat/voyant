"""DataHub client for metadata governance and lineage."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class DatasetUrn:
    """
    Helper for constructing DataHub Dataset URNs.

    Attributes:
        platform: Data platform name (e.g., "iceberg", "postgresql").
        name: Logical dataset name.
        env: Environment (e.g., "PROD", "DEV"). Defaults to "PROD".
    """

    platform: str
    name: str
    env: str = "PROD"

    def __str__(self) -> str:
        return f"urn:li:dataset:(urn:li:dataPlatform:{self.platform},{self.name},{self.env})"


@dataclass
class LineageEdge:
    """
    Directed lineage relationship between two data entities.

    Attributes:
        upstream: URN of the upstream data asset.
        downstream: URN of the downstream data asset.
        created: ISO 8601 timestamp.
    """

    upstream: str
    downstream: str
    created: str


class DataHubClient:
    def __init__(self):
        self.gms_url = settings.datahub_gms_url
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Lazily gets or creates an asynchronous HTTP client instance for DataHub GMS API calls.

        The client is configured with the base URL and a timeout.

        Returns:
            httpx.AsyncClient: An asynchronous HTTP client instance.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.gms_url,
                timeout=30.0,
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Lineage Management
    # =========================================================================

    async def emit_lineage(
        self,
        upstream_urns: list[str],
        downstream_urn: str,
    ) -> bool:
        try:
            client = await self._get_client()

            # For each upstream, create a proposal to link it to the downstream dataset.
            for upstream in upstream_urns:
                payload = {
                    "proposal": {
                        "entityType": "dataset",
                        "entityUrn": downstream_urn,
                        "aspectName": "upstreamLineage",
                        "aspect": {
                            "__type": "UpstreamLineage",
                            "upstreams": [
                                {
                                    "auditStamp": {
                                        "time": int(
                                            datetime.now(UTC).timestamp() * 1000
                                        ),
                                        "actor": "urn:li:corpuser:voyant",  # Identity of the actor emitting lineage.
                                    },
                                    "dataset": upstream,
                                    "type": "TRANSFORMED",  # Type of relationship (e.g., "TRANSFORMED", "COPY").
                                }
                            ],
                        },
                        "changeType": "UPSERT",
                    }
                }

                response = await client.post(
                    "/aspects?action=ingestProposal",
                    json=payload,
                )
                response.raise_for_status()

            logger.info(f"Emitted lineage: {upstream_urns} -> {downstream_urn}.")
            return True

        except Exception as e:
            logger.error(f"Failed to emit lineage for {downstream_urn}: {e}")
            return False

    # =========================================================================
    # Dataset Registration
    # =========================================================================

    async def register_dataset(
        self,
        urn: str,
        name: str,
        description: str | None = None,
        schema_fields: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
    ) -> bool:
        try:
            client = await self._get_client()

            # 1. Ingest Dataset Properties.
            properties_payload = {
                "proposal": {
                    "entityType": "dataset",
                    "entityUrn": urn,
                    "aspectName": "datasetProperties",
                    "aspect": {
                        "__type": "DatasetProperties",
                        "name": name,
                        "description": description or "",
                        "customProperties": {
                            "registered_by": "voyant",
                            "registered_at": datetime.now(UTC).isoformat() + "Z",
                        },
                    },
                    "changeType": "UPSERT",
                }
            }

            response = await client.post(
                "/aspects?action=ingestProposal",
                json=properties_payload,
            )
            response.raise_for_status()

            # 2. Ingest Schema if provided.
            if schema_fields:
                schema_payload = {
                    "proposal": {
                        "entityType": "dataset",
                        "entityUrn": urn,
                        "aspectName": "schemaMetadata",
                        "aspect": {
                            "__type": "SchemaMetadata",
                            "schemaName": name,
                            "platform": "urn:li:dataPlatform:iceberg",  # Assume Iceberg as target platform.
                            "version": 0,  # Schema version.
                            "hash": "",  # A hash of the schema content for change detection.
                            "platformSchema": {
                                "__type": "OtherSchema",
                                "rawSchema": "",  # Raw schema definition string.
                            },
                            "fields": [
                                {
                                    "fieldPath": f["name"],
                                    "type": {
                                        "type": {"__type": "StringType"}
                                    },  # Simplified type mapping.
                                    "nativeDataType": f.get("type", "string"),
                                    "nullable": f.get("nullable", True),
                                    "description": f.get("description", ""),
                                }
                                for f in schema_fields
                            ],
                        },
                        "changeType": "UPSERT",
                    }
                }

                response = await client.post(
                    "/aspects?action=ingestProposal",
                    json=schema_payload,
                )
                response.raise_for_status()

            logger.info(f"Registered dataset '{name}' (URN: {urn}) in DataHub.")
            return True

        except Exception as e:
            logger.error(
                f"Failed to register dataset '{name}' (URN: {urn}) in DataHub: {e}"
            )
            return False

    # =========================================================================
    # Search
    # =========================================================================

    async def search(
        self,
        query: str,
        entity_type: str = "DATASET",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        try:
            client = await self._get_client()

            # GraphQL query for DataHub search functionality.
            graphql_query = """
            query search($input: SearchInput!) {
                search(input: $input) {
                    total
                    searchResults {
                        entity {
                            urn
                            type
                            ... on Dataset {
                                name
                                description
                            }
                        }
                    }
                }
            }
            """

            response = await client.post(
                "/api/graphql",
                json={
                    "query": graphql_query,
                    "variables": {
                        "input": {
                            "type": entity_type,
                            "query": query,
                            "start": 0,
                            "count": limit,
                        }
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("data", {}).get("search", {}).get("searchResults", []):
                entity = item.get("entity", {})
                results.append(
                    {
                        "urn": entity.get("urn"),
                        "type": entity.get("type"),
                        "name": entity.get("name"),
                        "description": entity.get("description"),
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Search in DataHub failed for query '{query}': {e}")
            return []


# Singleton client instance for application-wide use.
_client: DataHubClient | None = None


def get_datahub_client() -> DataHubClient:
    global _client
    if _client is None:
        _client = DataHubClient()
    return _client
