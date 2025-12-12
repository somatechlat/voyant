"""
Governance API Routes

DataHub integration for search, lineage, and schema.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/governance")
settings = get_settings()


# =============================================================================
# Models
# =============================================================================

class SearchResult(BaseModel):
    urn: str
    name: str
    type: str
    description: Optional[str] = None
    platform: Optional[str] = None
    tags: List[str] = []


class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int


class LineageNode(BaseModel):
    urn: str
    name: str
    type: str
    platform: Optional[str] = None


class LineageEdge(BaseModel):
    source: str
    target: str
    type: str


class LineageResponse(BaseModel):
    nodes: List[LineageNode]
    edges: List[LineageEdge]


class SchemaField(BaseModel):
    name: str
    type: str
    nullable: bool = True
    description: Optional[str] = None


class SchemaResponse(BaseModel):
    urn: str
    fields: List[SchemaField]


# =============================================================================
# DataHub GraphQL Client
# =============================================================================

DATAHUB_SEARCH_QUERY = """
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
          platform {
            name
          }
          tags {
            tags {
              tag {
                name
              }
            }
          }
        }
      }
    }
  }
}
"""

DATAHUB_LINEAGE_QUERY = """
query lineage($urn: String!, $direction: LineageDirection!, $depth: Int!) {
  entity(urn: $urn) {
    urn
    ... on Dataset {
      name
    }
  }
  lineage(input: { urn: $urn, direction: $direction, depth: $depth }) {
    relationships {
      entity {
        urn
        type
        ... on Dataset {
          name
          platform { name }
        }
      }
      type
    }
  }
}
"""


async def _datahub_graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """Execute GraphQL query against DataHub."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.datahub_gms_url}/api/graphql",
            json={"query": query, "variables": variables},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            logger.error(f"DataHub GraphQL errors: {data['errors']}")
            raise HTTPException(status_code=500, detail="DataHub query failed")
        
        return data.get("data", {})


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/search", response_model=SearchResponse)
async def search_metadata(query: str, types: Optional[str] = None, limit: int = 10):
    """Search metadata in DataHub."""
    try:
        entity_types = types.split(",") if types else ["DATASET"]
        
        data = await _datahub_graphql(DATAHUB_SEARCH_QUERY, {
            "input": {
                "type": "DATASET",
                "query": query,
                "start": 0,
                "count": limit,
            }
        })
        
        results = []
        search_data = data.get("search", {})
        
        for item in search_data.get("searchResults", []):
            entity = item.get("entity", {})
            tags = []
            if entity.get("tags"):
                tags = [t["tag"]["name"] for t in entity["tags"].get("tags", [])]
            
            results.append(SearchResult(
                urn=entity.get("urn", ""),
                name=entity.get("name", ""),
                type=entity.get("type", "DATASET"),
                description=entity.get("description"),
                platform=entity.get("platform", {}).get("name") if entity.get("platform") else None,
                tags=tags,
            ))
        
        return SearchResponse(results=results, total=search_data.get("total", 0))
        
    except httpx.HTTPError as e:
        logger.error(f"DataHub request failed: {e}")
        raise HTTPException(status_code=503, detail="DataHub unavailable")
    except Exception as e:
        logger.exception("Search failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lineage/{urn:path}", response_model=LineageResponse)
async def get_lineage(urn: str, direction: str = "both", depth: int = 3):
    """Get data lineage from DataHub."""
    try:
        nodes = [LineageNode(urn=urn, name=urn.split(",")[1] if "," in urn else urn, type="dataset")]
        edges = []
        
        for dir_enum in (["UPSTREAM", "DOWNSTREAM"] if direction == "both" else [direction.upper()]):
            data = await _datahub_graphql(DATAHUB_LINEAGE_QUERY, {
                "urn": urn,
                "direction": dir_enum,
                "depth": min(depth, 10),
            })
            
            lineage = data.get("lineage", {})
            for rel in lineage.get("relationships", []):
                entity = rel.get("entity", {})
                node_urn = entity.get("urn", "")
                
                nodes.append(LineageNode(
                    urn=node_urn,
                    name=entity.get("name", node_urn),
                    type=entity.get("type", "dataset").lower(),
                    platform=entity.get("platform", {}).get("name") if entity.get("platform") else None,
                ))
                
                if dir_enum == "UPSTREAM":
                    edges.append(LineageEdge(source=node_urn, target=urn, type=rel.get("type", "PRODUCES")))
                else:
                    edges.append(LineageEdge(source=urn, target=node_urn, type=rel.get("type", "PRODUCES")))
        
        # Deduplicate nodes
        seen = set()
        unique_nodes = []
        for n in nodes:
            if n.urn not in seen:
                seen.add(n.urn)
                unique_nodes.append(n)
        
        return LineageResponse(nodes=unique_nodes, edges=edges)
        
    except httpx.HTTPError as e:
        logger.error(f"DataHub request failed: {e}")
        raise HTTPException(status_code=503, detail="DataHub unavailable")
    except Exception as e:
        logger.exception("Lineage failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schema/{urn:path}", response_model=SchemaResponse)
async def get_schema(urn: str):
    """Get schema from DataHub."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.datahub_gms_url}/aspects/{urn}?aspect=schemaMetadata",
                timeout=30.0,
            )
            
            if response.status_code == 404:
                raise HTTPException(status_code=404, detail="Schema not found")
            
            response.raise_for_status()
            data = response.json()
            
            fields = []
            schema_data = data.get("value", {}).get("schemaMetadata", {})
            
            for field in schema_data.get("fields", []):
                fields.append(SchemaField(
                    name=field.get("fieldPath", ""),
                    type=field.get("nativeDataType", "unknown"),
                    nullable=field.get("nullable", True),
                    description=field.get("description"),
                ))
            
            return SchemaResponse(urn=urn, fields=fields)
            
    except httpx.HTTPError as e:
        logger.error(f"DataHub request failed: {e}")
        raise HTTPException(status_code=503, detail="DataHub unavailable")
