"""Governance REST API endpoints."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from ninja import Field, Router, Schema
from ninja.errors import HttpError

from apps.core.api_utils import auth_guard
from apps.core.lib.tenant_quotas import (
    QuotaTier,
    ResourceType,
    get_quota_manager,
    get_usage_stats,
    set_tenant_tier,
)
from apps.core.middleware import get_tenant_id
from apps.core.config import get_settings

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
          platform { name }
          tags { tags { tag { name } } }
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
    ... on Dataset { name }
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


def _quota_usage_for_tenant(tenant_id: str) -> QuotaUsageStatus:
    manager = get_quota_manager()
    tier = manager.get_tenant_tier(tenant_id)
    policy = manager.get_policy(tenant_id)
    usage_map = {s.resource.value: s for s in get_usage_stats(tenant_id)}

    jobs_limit = policy.get_limit(ResourceType.JOBS_PER_DAY)
    artifacts_limit = policy.get_limit(ResourceType.TOTAL_STORAGE_MB)
    sources_limit = policy.get_limit(ResourceType.WORKFLOWS_PER_DAY)
    concurrent_limit = policy.get_limit(ResourceType.JOBS_CONCURRENT)

    jobs_usage = usage_map.get(ResourceType.JOBS_PER_DAY.value)
    artifacts_usage = usage_map.get(ResourceType.TOTAL_STORAGE_MB.value)
    sources_usage = usage_map.get(ResourceType.WORKFLOWS_PER_DAY.value)
    concurrent_usage = usage_map.get(ResourceType.JOBS_CONCURRENT.value)

    jobs_cap = int(jobs_limit.limit) if jobs_limit else 0
    jobs_now = int(jobs_usage.current_usage) if jobs_usage else 0
    artifacts_cap_mb = float(artifacts_limit.limit) if artifacts_limit else 0.0
    artifacts_now_mb = float(artifacts_usage.current_usage) if artifacts_usage else 0.0
    sources_cap = int(sources_limit.limit) if sources_limit else 0
    sources_now = int(sources_usage.current_usage) if sources_usage else 0
    concurrent_cap = int(concurrent_limit.limit) if concurrent_limit else 0
    concurrent_now = int(concurrent_usage.current_usage) if concurrent_usage else 0

    return QuotaUsageStatus(
        tenant_id=tenant_id,
        tier=tier.value,
        jobs_today=jobs_now,
        jobs_limit=jobs_cap,
        jobs_remaining=max(0, jobs_cap - jobs_now),
        artifacts_gb=round(artifacts_now_mb / 1024.0, 3),
        artifacts_limit_gb=round(artifacts_cap_mb / 1024.0, 3),
        sources_count=sources_now,
        sources_limit=sources_cap,
        concurrent_jobs=concurrent_now,
        concurrent_limit=concurrent_cap,
    )


def _policy_limit(policy, resource: ResourceType) -> float:
    limit_cfg = policy.get_limit(resource)
    if not limit_cfg:
        return 0.0
    return float(limit_cfg.limit)


@governance_router.get("/search", response=SearchResponse, auth=auth_guard)
def search_metadata(request, query: str, types: Optional[str] = None, limit: int = 10):
    try:
        data = _datahub_graphql(
            DATAHUB_SEARCH_QUERY,
            {"input": {"type": "DATASET", "query": query, "start": 0, "count": limit}},
        )
        search_data = data.get("search", {})
        results: List[GovernanceSearchResult] = []

        for item in search_data.get("searchResults", []):
            entity = item.get("entity", {})
            tags = [t["tag"]["name"] for t in entity.get("tags", {}).get("tags", [])]
            results.append(
                GovernanceSearchResult(
                    urn=entity.get("urn", ""),
                    name=entity.get("name", ""),
                    type=entity.get("type", "DATASET"),
                    description=entity.get("description"),
                    platform=(entity.get("platform") or {}).get("name"),
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
        nodes = [LineageNode(urn=urn, name=urn.split(",")[1] if "," in urn else urn, type="dataset")]
        edges: List[LineageEdge] = []
        directions = ["UPSTREAM", "DOWNSTREAM"] if direction == "both" else [direction.upper()]

        for dir_enum in directions:
            data = _datahub_graphql(
                DATAHUB_LINEAGE_QUERY,
                {"urn": urn, "direction": dir_enum, "depth": min(depth, 10)},
            )
            for rel in data.get("lineage", {}).get("relationships", []):
                entity = rel.get("entity", {})
                node_urn = entity.get("urn", "")
                nodes.append(
                    LineageNode(
                        urn=node_urn,
                        name=entity.get("name", node_urn),
                        type=entity.get("type", "dataset").lower(),
                        platform=(entity.get("platform") or {}).get("name"),
                    )
                )
                if dir_enum == "UPSTREAM":
                    edges.append(LineageEdge(source=node_urn, target=urn, type=rel.get("type", "PRODUCES")))
                else:
                    edges.append(LineageEdge(source=urn, target=node_urn, type=rel.get("type", "PRODUCES")))

        unique_nodes: List[LineageNode] = []
        seen = set()
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
            response = client.get(f"{settings.datahub_gms_url}/aspects/{urn}?aspect=schemaMetadata")
        if response.status_code == 404:
            raise HttpError(404, "Schema not found")
        response.raise_for_status()

        schema_data = response.json().get("value", {}).get("schemaMetadata", {})
        fields = [
            SchemaField(
                name=field.get("fieldPath", ""),
                type=field.get("nativeDataType", "unknown"),
                nullable=field.get("nullable", True),
                description=field.get("description"),
            )
            for field in schema_data.get("fields", [])
        ]
        return SchemaResponse(urn=urn, fields=fields)
    except HttpError:
        raise
    except httpx.HTTPError as exc:
        logger.error("DataHub request failed: %s", exc)
        raise HttpError(503, "DataHub unavailable") from exc


@governance_router.get("/quotas/tiers", response=List[QuotaTierInfo], auth=auth_guard)
def list_quota_tiers(request):
    manager = get_quota_manager()
    tiers: List[QuotaTierInfo] = []
    for tier in QuotaTier:
        policy = manager.policies.get(tier)
        if not policy:
            continue
        tiers.append(
            QuotaTierInfo(
                tier_id=tier.value,
                name=tier.value,
                max_jobs_per_day=int(_policy_limit(policy, ResourceType.JOBS_PER_DAY)),
                max_artifacts_gb=round(
                    _policy_limit(policy, ResourceType.TOTAL_STORAGE_MB) / 1024.0, 3
                ),
                max_sources=int(_policy_limit(policy, ResourceType.WORKFLOWS_PER_DAY)),
                max_concurrent_jobs=int(
                    _policy_limit(policy, ResourceType.JOBS_CONCURRENT)
                ),
            )
        )
    return tiers


@governance_router.get("/quotas/usage", response=QuotaUsageStatus, auth=auth_guard)
def get_quota_usage(request):
    return _quota_usage_for_tenant(get_tenant_id(request))


@governance_router.get("/quotas/limits", response=QuotaUsageStatus, auth=auth_guard)
def get_quota_limits(request):
    return _quota_usage_for_tenant(get_tenant_id(request))


@governance_router.post("/quotas/set-tier", response=Dict[str, str], auth=auth_guard)
def update_quota_tier(request, payload: SetTierRequest):
    tenant_id = get_tenant_id(request)
    try:
        tier = QuotaTier(payload.tier)
    except ValueError as exc:
        raise HttpError(400, f"Invalid tier: {payload.tier}") from exc
    set_tenant_tier(tenant_id, tier)
    return {"tenant_id": tenant_id, "tier": tier.value, "status": "updated"}
