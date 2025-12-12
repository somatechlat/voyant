"""
DataHub Client for Voyant

Lineage emission and metadata registration in DataHub.
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
    """DataHub dataset URN builder."""
    platform: str
    name: str
    env: str = "PROD"
    
    def __str__(self) -> str:
        return f"urn:li:dataset:(urn:li:dataPlatform:{self.platform},{self.name},{self.env})"


@dataclass
class LineageEdge:
    """Lineage relationship."""
    upstream: str
    downstream: str
    created: str


class DataHubClient:
    """DataHub REST and GraphQL client."""
    
    def __init__(self):
        self.gms_url = settings.datahub_gms_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
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
    # Lineage
    # =========================================================================
    
    async def emit_lineage(
        self,
        upstream_urns: List[str],
        downstream_urn: str,
    ) -> bool:
        """Emit lineage relationship to DataHub."""
        try:
            client = await self._get_client()
            
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
                                        "time": int(datetime.utcnow().timestamp() * 1000),
                                        "actor": "urn:li:corpuser:voyant",
                                    },
                                    "dataset": upstream,
                                    "type": "TRANSFORMED",
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
            
            logger.info(f"Emitted lineage: {upstream_urns} -> {downstream_urn}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to emit lineage: {e}")
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
        """Register or update dataset in DataHub."""
        try:
            client = await self._get_client()
            
            # Dataset properties
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
                            "registered_at": datetime.utcnow().isoformat(),
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
            
            # Schema if provided
            if schema_fields:
                schema_payload = {
                    "proposal": {
                        "entityType": "dataset",
                        "entityUrn": urn,
                        "aspectName": "schemaMetadata",
                        "aspect": {
                            "__type": "SchemaMetadata",
                            "schemaName": name,
                            "platform": "urn:li:dataPlatform:iceberg",
                            "version": 0,
                            "hash": "",
                            "platformSchema": {"__type": "OtherSchema", "rawSchema": ""},
                            "fields": [
                                {
                                    "fieldPath": f["name"],
                                    "type": {"type": {"__type": "StringType"}},
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
            
            logger.info(f"Registered dataset: {urn}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register dataset: {e}")
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
        """Search entities in DataHub."""
        try:
            client = await self._get_client()
            
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
                results.append({
                    "urn": entity.get("urn"),
                    "type": entity.get("type"),
                    "name": entity.get("name"),
                    "description": entity.get("description"),
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []


# Singleton client
_client: Optional[DataHubClient] = None

def get_datahub_client() -> DataHubClient:
    global _client
    if _client is None:
        _client = DataHubClient()
    return _client
