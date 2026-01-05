"""
DataHub Client for Voyant Metadata Governance and Lineage.

This module provides a dedicated client for integrating with DataHub,
a universal metadata platform. It enables Voyant to:
-   Emit data lineage relationships (source -> job -> dataset).
-   Register and update dataset metadata, including schemas and properties.
-   Perform searches against the DataHub metadata catalog.

This integration is crucial for maintaining a comprehensive understanding of
data assets, their origins, transformations, and usage across the enterprise.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class DatasetUrn:
    """
    Helper for constructing DataHub Dataset URNs (Unique Resource Names).

    A URN uniquely identifies a data asset within DataHub.

    Attributes:
        platform (str): The name of the data platform (e.g., "iceberg", "postgresql").
        name (str): The logical name of the dataset (e.g., "customers", "orders_table").
        env (str, optional): The environment where the dataset resides (e.g., "PROD", "DEV"). Defaults to "PROD".
    """

    platform: str
    name: str
    env: str = "PROD"

    def __str__(self) -> str:
        """Returns the fully qualified DataHub Dataset URN string."""
        return f"urn:li:dataset:(urn:li:dataPlatform:{self.platform},{self.name},{self.env})"


@dataclass
class LineageEdge:
    """
    Represents a directed lineage relationship between two data entities in DataHub.

    Attributes:
        upstream (str): The URN of the upstream data asset.
        downstream (str): The URN of the downstream data asset.
        created (str): The ISO 8601 timestamp when this lineage relationship was created.
    """

    upstream: str
    downstream: str
    created: str


class DataHubClient:
    """
    Asynchronous client for interacting with the DataHub GMS (GraphQL Metadata Service).

    This client facilitates the registration of metadata, emission of lineage,
    and querying of the DataHub catalog.
    """

    def __init__(self):
        """
        Initializes the DataHubClient with the GMS URL from application settings.
        """
        self.gms_url = settings.datahub_gms_url
        self._client: Optional[httpx.AsyncClient] = None

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
                timeout=30.0,  # Set a default timeout for API requests.
            )
        return self._client

    async def close(self):
        """
        Closes the underlying HTTP client session.

        This should be called to gracefully release network resources.
        """
        if self._client:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Lineage Management
    # =========================================================================

    async def emit_lineage(
        self,
        upstream_urns: List[str],
        downstream_urn: str,
    ) -> bool:
        """
        Emits a lineage relationship to DataHub, linking upstream data assets to a downstream asset.

        Args:
            upstream_urns (List[str]): A list of URNs of the upstream data assets.
            downstream_urn (str): The URN of the downstream data asset.

        Returns:
            bool: True if the lineage relationship was successfully emitted, False otherwise.
        """
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
                                            datetime.utcnow().timestamp() * 1000
                                        ),
                                        "actor": "urn:li:corpuser:voyant",  # Identity of the actor emitting lineage.
                                    },
                                    "dataset": upstream,
                                    "type": "TRANSFORMED",  # Type of relationship (e.g., "TRANSFORMED", "COPY").
                                }
                            ],
                        },
                        "changeType": "UPSERT",  # Create or update the aspect.
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
        description: Optional[str] = None,
        schema_fields: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        Registers or updates a dataset's metadata in DataHub.

        This includes basic dataset properties and, optionally, its schema fields.

        Args:
            urn (str): The unique URN of the dataset to register.
            name (str): The human-readable name of the dataset.
            description (Optional[str]): A description of the dataset.
            schema_fields (Optional[List[Dict[str, Any]]]): A list of dictionaries,
                                                              each defining a schema field.
                                                              Example: `{"name": "col1", "type": "string"}`.
            tags (Optional[List[str]]): A list of tags to associate with the dataset.

        Returns:
            bool: True if the dataset was successfully registered/updated, False otherwise.
        """
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
                            "registered_at": datetime.utcnow().isoformat() + "Z",
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
                            "version": 0, # Schema version.
                            "hash": "", # A hash of the schema content for change detection.
                            "platformSchema": {
                                "__type": "OtherSchema",
                                "rawSchema": "", # Raw schema definition string.
                            },
                            "fields": [
                                {
                                    "fieldPath": f["name"],
                                    "type": {"type": {"__type": "StringType"}},  # Simplified type mapping.
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
            logger.error(f"Failed to register dataset '{name}' (URN: {urn}) in DataHub: {e}")
            return False

    # =========================================================================
    # Search
    # =========================================================================

    async def search(
        self,
        query: str,
        entity_type: str = "DATASET",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Searches for entities within the DataHub metadata catalog.

        Args:
            query (str): The search query string.
            entity_type (str, optional): The type of entity to search for (e.g., "DATASET", "DASHBOARD").
                                         Defaults to "DATASET".
            limit (int, optional): The maximum number of search results to return. Defaults to 10.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, each representing a search result
                                  with URN, type, name, and description.
        """
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
_client: Optional[DataHubClient] = None


def get_datahub_client() -> DataHubClient:
    """
    Retrieves the singleton instance of the DataHubClient.

    This factory function ensures that only one DataHubClient is instantiated
    per application process, promoting efficient use of network resources
    and persistent connections.

    Returns:
        DataHubClient: The singleton DataHubClient instance.
    """
    global _client
    if _client is None:
        _client = DataHubClient()
    return _client
