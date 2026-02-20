
import logging
import httpx
from typing import Any, Dict, List, Optional
from ninja import Router, Schema, Field
from ninja.errors import HttpError
from apps.core.api_utils import auth_guard
from apps.core.config import get_settings
from apps.core.middleware import get_tenant_id

logger = logging.getLogger(__name__)
settings = get_settings()
governance_router = Router(tags=["governance"])

class GovernanceSearchResult(Schema):
    urn: str
    name: str
    type: str
    description: Optional[str] = None
    platform: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class SearchResponse(Schema):
    results: List[GovernanceSearchResult]
    total: int


class LineageNode(Schema):
    urn: str
    name: str
    type: str
    platform: Optional[str] = None


class LineageEdge(Schema):
    source: str
    target: str
    type: str


class LineageResponse(Schema):
    nodes: List[LineageNode]
    edges: List[LineageEdge]


class SchemaField(Schema):
    name: str
    type: str
    nullable: bool = True
    description: Optional[str] = None


class SchemaResponse(Schema):
    urn: str
    fields: List[SchemaField]


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


def _datahub_graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{settings.datahub_gms_url}/api/graphql",
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()

    if "errors" in data:
        logger.error("DataHub GraphQL errors: %s", data["errors"])
        raise HttpError(500, "DataHub query failed")

    return data.get("data", {})


@governance_router.get("/search", response=SearchResponse, auth=auth_guard)
def search_metadata(request, query: str, types: Optional[str] = None, limit: int = 10):
    try:
        data = _datahub_graphql(
            DATAHUB_SEARCH_QUERY,
            {
                "input": {
                    "type": "DATASET",
                    "query": query,
                    "start": 0,
                    "count": limit,
                }
            },
        )

        results = []
        search_data = data.get("search", {})

        for item in search_data.get("searchResults", []):
            entity = item.get("entity", {})
            tags = []
            if entity.get("tags"):
                tags = [t["tag"]["name"] for t in entity["tags"].get("tags", [])]

            results.append(
                GovernanceSearchResult(
                    urn=entity.get("urn", ""),
                    name=entity.get("name", ""),
                    type=entity.get("type", "DATASET"),
                    description=entity.get("description"),
                    platform=(
                        entity.get("platform", {}).get("name")
                        if entity.get("platform")
                        else None
                    ),
                    tags=tags,
                )
            )

        return SearchResponse(results=results, total=search_data.get("total", 0))
    except HttpError:
        raise
    except Exception as exc:
        logger.exception("Search failed")
        raise HttpError(500, str(exc)) from exc


@governance_router.get("/lineage/{urn}", response=LineageResponse, auth=auth_guard)
def get_lineage(request, urn: str, direction: str = "both", depth: int = 3):
    try:
        nodes = [
            LineageNode(
                urn=urn, name=urn.split(",")[1] if "," in urn else urn, type="dataset"
            )
        ]
        edges = []

        directions = (
            ["UPSTREAM", "DOWNSTREAM"] if direction == "both" else [direction.upper()]
        )
        for dir_enum in directions:
            data = _datahub_graphql(
                DATAHUB_LINEAGE_QUERY,
                {"urn": urn, "direction": dir_enum, "depth": min(depth, 10)},
            )
            lineage = data.get("lineage", {})
            for rel in lineage.get("relationships", []):
                entity = rel.get("entity", {})
                node_urn = entity.get("urn", "")
                nodes.append(
                    LineageNode(
                        urn=node_urn,
                        name=entity.get("name", node_urn),
                        type=entity.get("type", "dataset").lower(),
                        platform=(
                            entity.get("platform", {}).get("name")
                            if entity.get("platform")
                            else None
                        ),
                    )
                )
                if dir_enum == "UPSTREAM":
                    edges.append(
                        LineageEdge(
                            source=node_urn,
                            target=urn,
                            type=rel.get("type", "PRODUCES"),
                        )
                    )
                else:
                    edges.append(
                        LineageEdge(
                            source=urn,
                            target=node_urn,
                            type=rel.get("type", "PRODUCES"),
                        )
                    )

        seen = set()
        unique_nodes = []
        for node in nodes:
            if node.urn not in seen:
                seen.add(node.urn)
                unique_nodes.append(node)

        return LineageResponse(nodes=unique_nodes, edges=edges)
    except HttpError:
        raise
    except Exception as exc:
        logger.exception("Lineage failed")
        raise HttpError(500, str(exc)) from exc


@governance_router.get("/schema/{urn}", response=SchemaResponse, auth=auth_guard)
def get_schema(request, urn: str):
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{settings.datahub_gms_url}/aspects/{urn}?aspect=schemaMetadata",
            )
        if response.status_code == 404:
            raise HttpError(404, "Schema not found")
        response.raise_for_status()
        data = response.json()

        fields = []
        schema_data = data.get("value", {}).get("schemaMetadata", {})
        for field in schema_data.get("fields", []):
            fields.append(
                SchemaField(
                    name=field.get("fieldPath", ""),
                    type=field.get("nativeDataType", "unknown"),
                    nullable=field.get("nullable", True),
                    description=field.get("description"),
                )
            )
        return SchemaResponse(urn=urn, fields=fields)
    except HttpError:
        raise
    except httpx.HTTPError as exc:
        logger.error("DataHub request failed: %s", exc)
        raise HttpError(503, "DataHub unavailable") from exc

class QuotaTierInfo(Schema):
    tier_id: str
    name: str
    max_jobs_per_day: int
    max_artifacts_gb: float
    max_sources: int
    max_concurrent_jobs: int


class QuotaUsageStatus(Schema):
    tenant_id: str
    tier: str
    jobs_today: int
    jobs_limit: int
    jobs_remaining: int
    artifacts_gb: float
    artifacts_limit_gb: float
    sources_count: int
    sources_limit: int
    concurrent_jobs: int
    concurrent_limit: int


class SetTierRequest(Schema):
    tier: str


# Assuming _list_tiers, _get_usage_status etc are imported or defined.
# They seemed to be missing from the viewed file chunk or I missed them?
# Ah, I see them used in the previous view (`_list_tiers` etc).
# I need to implement them or import them.
# They are likely defined later in the file or imported.
# Let's stub them for now or verify where they come from.
# Actually, I'll need to check the rest of the file to see if they were helpers defined after.
