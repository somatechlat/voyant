"""Governance REST API endpoints."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from ninja import Field, Router, Schema
from ninja.errors import HttpError

from admin.common.messages import get_message
from apps.core.api_utils import auth_guard
from apps.core.config import get_settings
from apps.core.lib.tenant_quotas import (
    QuotaTier,
    ResourceType,
    get_quota_manager,
    get_usage_stats,
    set_tenant_tier,
)
from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)
settings = get_settings()
governance_router = Router(tags=["governance"], auth=require_permission("read:*"))


class GovernanceSearchResult(Schema):
    urn: str
    name: str
    type: str
    description: str | None = None
    platform: str | None = None
    tags: list[str] = Field(default_factory=list)


class SearchResponse(Schema):
    results: list[GovernanceSearchResult]
    total: int


class LineageNode(Schema):
    urn: str
    name: str
    type: str
    platform: str | None = None


class LineageEdge(Schema):
    source: str
    target: str
    type: str


class LineageResponse(Schema):
    nodes: list[LineageNode]
    edges: list[LineageEdge]


class SchemaField(Schema):
    name: str
    type: str
    nullable: bool = True
    description: str | None = None


class SchemaResponse(Schema):
    urn: str
    fields: list[SchemaField]


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


async def _datahub_graphql(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.datahub_gms_url}/api/graphql",
            json={"query": query, "variables": variables},
        )
        response.raise_for_status()
        data = response.json()

    if "errors" in data:
        logger.error("DataHub GraphQL errors: %s", data["errors"])
        raise HttpError(500, get_message("ERR_DATAHUB_QUERY_FAILED"))

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
async def search_metadata(
    request, query: str, types: str | None = None, limit: int = 10
):
    try:
        data = await _datahub_graphql(
            DATAHUB_SEARCH_QUERY,
            {"input": {"type": "DATASET", "query": query, "start": 0, "count": limit}},
        )
        search_data = data.get("search", {})
        results: list[GovernanceSearchResult] = []

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
        raise HttpError(500, get_message("ERR_SYSTEM", error=str(exc))) from exc


@governance_router.get("/lineage/{urn}", response=LineageResponse, auth=auth_guard)
async def get_lineage(request, urn: str, direction: str = "both", depth: int = 3):
    try:
        nodes = [
            LineageNode(
                urn=urn, name=urn.split(",")[1] if "," in urn else urn, type="dataset"
            )
        ]
        edges: list[LineageEdge] = []
        directions = (
            ["UPSTREAM", "DOWNSTREAM"] if direction == "both" else [direction.upper()]
        )

        for dir_enum in directions:
            data = await _datahub_graphql(
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

        unique_nodes: list[LineageNode] = []
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
        raise HttpError(500, get_message("ERR_SYSTEM", error=str(exc))) from exc


@governance_router.get("/schema/{urn}", response=SchemaResponse, auth=auth_guard)
async def get_schema(request, urn: str):
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{settings.datahub_gms_url}/aspects/{urn}?aspect=schemaMetadata"
            )
        if response.status_code == 404:
            raise HttpError(404, get_message("ERR_SCHEMA_NOT_FOUND"))
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
        raise HttpError(503, get_message("ERR_DATAHUB_UNAVAILABLE")) from exc


@governance_router.get("/quotas/tiers", response=list[QuotaTierInfo], auth=auth_guard)
def list_quota_tiers(request):
    manager = get_quota_manager()
    tiers: list[QuotaTierInfo] = []
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


@governance_router.post("/quotas/set-tier", response=dict[str, str], auth=auth_guard)
def update_quota_tier(request, payload: SetTierRequest):
    tenant_id = get_tenant_id(request)
    try:
        tier = QuotaTier(payload.tier)
    except ValueError as exc:
        raise HttpError(
            400, get_message("ERR_INVALID_TIER", tier=payload.tier)
        ) from exc
    set_tenant_tier(tenant_id, tier)
    return {"tenant_id": tenant_id, "tier": tier.value, "status": "updated"}


# ---------------------------------------------------------------------------
# Row-Level Security (GOV-F-003)
# ---------------------------------------------------------------------------


@governance_router.get("/row-security-policies", auth=auth_guard)
def list_row_security_policies(request):
    """List all row-level security policies."""
    from apps.governance.models import RowSecurityPolicy

    tenant_id = get_tenant_id(request)
    policies = RowSecurityPolicy.objects.filter(tenant_id=tenant_id, status="active")
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "table_name": p.table_name,
            "column_name": p.column_name,
            "filter_type": p.filter_type,
            "filter_config": p.filter_config,
            "applies_to_roles": p.applies_to_roles,
            "status": p.status,
        }
        for p in policies
    ]


@governance_router.post("/row-security-policies", auth=auth_guard)
def create_row_security_policy(request, payload: dict[str, Any]):
    """Create a new row-level security policy."""
    from apps.governance.models import RowSecurityPolicy

    tenant_id = get_tenant_id(request)
    policy = RowSecurityPolicy.objects.create(
        tenant_id=tenant_id,
        name=payload.get("name", ""),
        table_name=payload.get("table_name", ""),
        column_name=payload.get("column_name", ""),
        filter_type=payload.get("filter_type", "user_match"),
        filter_config=payload.get("filter_config", {}),
        applies_to_roles=payload.get("applies_to_roles", []),
    )
    return {"id": str(policy.id), "name": policy.name, "status": "created"}


# ---------------------------------------------------------------------------
# RLS Check & Policies (GOV-F-003)
# ---------------------------------------------------------------------------


class RLSCheckRequest(Schema):
    """Request body for the RLS query-check endpoint."""

    sql: str = Field(..., description="The SQL query to validate against RLS policies")
    user_id: str | None = Field(None, description="User ID to evaluate policies for")
    user_roles: list[str] = Field(
        default_factory=list, description="Roles of the requesting user"
    )


class RLSCheckResponse(Schema):
    """Response for the RLS query-check endpoint."""

    allowed: bool
    applied_policies: int = 0
    injected_filters: list[str] = Field(default_factory=list)
    modified_sql: str | None = None
    reason: str | None = None


class RLSPolicyItem(Schema):
    id: str
    name: str
    table_name: str
    column_name: str = ""
    filter_type: str
    filter_config: dict[str, Any] = Field(default_factory=dict)
    applies_to_roles: list[str] = Field(default_factory=list)
    status: str


@governance_router.post("/rls/check", response=RLSCheckResponse, auth=auth_guard)
def rls_check(request, payload: RLSCheckRequest):
    """Check if a query is allowed under current RLS policies.

    Evaluates active ``RowSecurityPolicy`` entries for the tenant and returns
    whether the query would be allowed and what filters would be injected.
    """
    from apps.core.lib.trino import TrinoClient
    from apps.governance.models import RowSecurityPolicy

    tenant_id = get_tenant_id(request)
    policies = list(
        RowSecurityPolicy.objects.filter(tenant_id=tenant_id, status="active")
    )

    if not policies:
        return RLSCheckResponse(allowed=True, applied_policies=0)

    # Check which policies would apply
    referenced_tables = TrinoClient._extract_table_references(payload.sql)
    applied = 0
    filters: list[str] = []
    for p in policies:
        if p.table_name not in referenced_tables:
            continue
        if not TrinoClient._policy_applies(p, payload.user_id, payload.user_roles):
            continue
        clause = TrinoClient._build_filter_clause(
            p,
            tenant_id,
            payload.user_id,
            payload.user_roles,
        )
        if clause:
            applied += 1
            filters.append(f"{p.name}: {clause}")

    # Build the modified SQL with RLS filters (dry-run)
    modified_sql = None
    if applied > 0:
        # Simulate filter injection via a temp instance
        temp_client = TrinoClient.__new__(TrinoClient)
        modified_sql = temp_client._inject_rls_filters(
            payload.sql,
            tenant_id,
            payload.user_id,
            payload.user_roles,
            RowSecurityPolicy,
        )

    return RLSCheckResponse(
        allowed=True,
        applied_policies=applied,
        injected_filters=filters,
        modified_sql=modified_sql,
        reason=(
            f"{applied} RLS filter(s) would be applied"
            if applied
            else "No RLS filters apply"
        ),
    )


@governance_router.get("/rls/policies", response=list[RLSPolicyItem], auth=auth_guard)
def list_rls_policies(request):
    """List all row-level security policies for the current tenant."""
    from apps.governance.models import RowSecurityPolicy

    tenant_id = get_tenant_id(request)
    policies = RowSecurityPolicy.objects.filter(tenant_id=tenant_id, status="active")
    return [
        RLSPolicyItem(
            id=str(p.id),
            name=p.name,
            table_name=p.table_name,
            column_name=p.column_name or "",
            filter_type=p.filter_type,
            filter_config=p.filter_config or {},
            applies_to_roles=p.applies_to_roles or [],
            status=p.status,
        )
        for p in policies
    ]


# ---------------------------------------------------------------------------
# Column Masking (GOV-F-004)
# ---------------------------------------------------------------------------


@governance_router.get("/column-masks", auth=auth_guard)
def list_column_masks(request):
    """List all column masking policies."""
    from apps.governance.models import ColumnMaskPolicy

    tenant_id = get_tenant_id(request)
    masks = ColumnMaskPolicy.objects.filter(tenant_id=tenant_id, status="active")
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "table_name": m.table_name,
            "column_name": m.column_name,
            "mask_type": m.mask_type,
            "mask_config": m.mask_config,
            "applies_to_roles": m.applies_to_roles,
            "exempt_roles": m.exempt_roles,
        }
        for m in masks
    ]


@governance_router.post("/column-masks", auth=auth_guard)
def create_column_mask(request, payload: dict[str, Any]):
    """Create a new column masking policy."""
    from apps.governance.models import ColumnMaskPolicy

    tenant_id = get_tenant_id(request)
    mask = ColumnMaskPolicy.objects.create(
        tenant_id=tenant_id,
        name=payload.get("name", ""),
        table_name=payload.get("table_name", ""),
        column_name=payload.get("column_name", ""),
        mask_type=payload.get("mask_type", "full"),
        mask_config=payload.get("mask_config", {}),
        applies_to_roles=payload.get("applies_to_roles", []),
        exempt_roles=payload.get("exempt_roles", []),
    )
    return {"id": str(mask.id), "name": mask.name, "status": "created"}


class ColumnMaskItem(Schema):
    id: str
    name: str
    table_name: str
    column_name: str
    mask_type: str
    mask_config: dict[str, Any] = Field(default_factory=dict)
    applies_to_roles: list[str] = Field(default_factory=list)
    exempt_roles: list[str] = Field(default_factory=list)
    status: str


@governance_router.get("/masks", response=list[ColumnMaskItem], auth=auth_guard)
def list_masks(request):
    """List all column masking policies for the current tenant."""
    from apps.governance.models import ColumnMaskPolicy

    tenant_id = get_tenant_id(request)
    masks = ColumnMaskPolicy.objects.filter(tenant_id=tenant_id, status="active")
    return [
        ColumnMaskItem(
            id=str(m.id),
            name=m.name,
            table_name=m.table_name,
            column_name=m.column_name,
            mask_type=m.mask_type,
            mask_config=m.mask_config or {},
            applies_to_roles=m.applies_to_roles or [],
            exempt_roles=m.exempt_roles or [],
            status=m.status,
        )
        for m in masks
    ]


# ---------------------------------------------------------------------------
# Data Classification (GOV-F-005)
# ---------------------------------------------------------------------------


@governance_router.get("/classifications", auth=auth_guard)
def list_classifications(request):
    """List all data classifications."""
    from apps.governance.models import DataClassification

    tenant_id = get_tenant_id(request)
    classifications = DataClassification.objects.filter(tenant_id=tenant_id)
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "level": c.level,
            "target_type": c.target_type,
            "target_name": c.target_name,
            "requires_encryption": c.requires_encryption,
            "requires_masking": c.requires_masking,
            "retention_days": c.retention_days,
        }
        for c in classifications
    ]


@governance_router.post("/classifications", auth=auth_guard)
def create_classification(request, payload: dict[str, Any]):
    """Create a new data classification tag."""
    from apps.governance.models import DataClassification

    tenant_id = get_tenant_id(request)
    classification = DataClassification.objects.create(
        tenant_id=tenant_id,
        name=payload.get("name", ""),
        level=payload.get("level", "internal"),
        target_type=payload.get("target_type", "table"),
        target_name=payload.get("target_name", ""),
        requires_encryption=payload.get("requires_encryption", False),
        requires_masking=payload.get("requires_masking", False),
        retention_days=payload.get("retention_days"),
    )
    return {
        "id": str(classification.id),
        "name": classification.name,
        "status": "created",
    }


# ---------------------------------------------------------------------------
# SecurityPolicy CRUD (GOV-F-006)
# ---------------------------------------------------------------------------


class SecurityPolicyItem(Schema):
    id: str
    name: str
    description: str = ""
    status: str
    table_name: str
    column_name: str = ""
    filter_expression: str
    roles: list[str] = Field(default_factory=list)


class SecurityPolicyCreateRequest(Schema):
    name: str
    description: str = ""
    table_name: str
    column_name: str = ""
    filter_expression: str
    roles: list[str] = Field(default_factory=list)
    status: str = "active"


class SecurityPolicyUpdateRequest(Schema):
    name: str | None = None
    description: str | None = None
    table_name: str | None = None
    column_name: str | None = None
    filter_expression: str | None = None
    roles: list[str] | None = None
    status: str | None = None


@governance_router.get(
    "/security-policies",
    response=list[SecurityPolicyItem],
    auth=auth_guard,
)
def list_security_policies(request):
    """List all SecurityPolicy entries for the current tenant."""
    from apps.governance.models import SecurityPolicy

    tenant_id = get_tenant_id(request)
    policies = SecurityPolicy.objects.filter(tenant_id=tenant_id)
    return [
        SecurityPolicyItem(
            id=str(p.id),
            name=p.name,
            description=p.description,
            status=p.status,
            table_name=p.table_name,
            column_name=p.column_name or "",
            filter_expression=p.filter_expression,
            roles=p.roles or [],
        )
        for p in policies
    ]


@governance_router.post(
    "/security-policies",
    response=SecurityPolicyItem,
    auth=auth_guard,
)
def create_security_policy(request, payload: SecurityPolicyCreateRequest):
    """Create a new SecurityPolicy."""
    from apps.governance.models import SecurityPolicy

    tenant_id = get_tenant_id(request)
    policy = SecurityPolicy.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        table_name=payload.table_name,
        column_name=payload.column_name,
        filter_expression=payload.filter_expression,
        roles=payload.roles,
        status=payload.status,
    )
    return SecurityPolicyItem(
        id=str(policy.id),
        name=policy.name,
        description=policy.description,
        status=policy.status,
        table_name=policy.table_name,
        column_name=policy.column_name or "",
        filter_expression=policy.filter_expression,
        roles=policy.roles or [],
    )


@governance_router.get(
    "/security-policies/{policy_id}",
    response=SecurityPolicyItem,
    auth=auth_guard,
)
def get_security_policy(request, policy_id: str):
    """Retrieve a single SecurityPolicy by ID."""
    from apps.governance.models import SecurityPolicy

    tenant_id = get_tenant_id(request)
    try:
        p = SecurityPolicy.objects.get(id=policy_id, tenant_id=tenant_id)
    except SecurityPolicy.DoesNotExist:
        raise HttpError(404, "Security policy not found")
    return SecurityPolicyItem(
        id=str(p.id),
        name=p.name,
        description=p.description,
        status=p.status,
        table_name=p.table_name,
        column_name=p.column_name or "",
        filter_expression=p.filter_expression,
        roles=p.roles or [],
    )


@governance_router.put(
    "/security-policies/{policy_id}",
    response=SecurityPolicyItem,
    auth=auth_guard,
)
def update_security_policy(
    request, policy_id: str, payload: SecurityPolicyUpdateRequest
):
    """Update a SecurityPolicy."""
    from apps.governance.models import SecurityPolicy

    tenant_id = get_tenant_id(request)
    try:
        policy = SecurityPolicy.objects.get(id=policy_id, tenant_id=tenant_id)
    except SecurityPolicy.DoesNotExist:
        raise HttpError(404, "Security policy not found")

    update_fields = payload.dict(exclude_unset=True)
    for field_name, value in update_fields.items():
        setattr(policy, field_name, value)
    policy.save()

    return SecurityPolicyItem(
        id=str(policy.id),
        name=policy.name,
        description=policy.description,
        status=policy.status,
        table_name=policy.table_name,
        column_name=policy.column_name or "",
        filter_expression=policy.filter_expression,
        roles=policy.roles or [],
    )


@governance_router.delete(
    "/security-policies/{policy_id}",
    response=dict[str, str],
    auth=auth_guard,
)
def delete_security_policy(request, policy_id: str):
    """Delete a SecurityPolicy."""
    from apps.governance.models import SecurityPolicy

    tenant_id = get_tenant_id(request)
    try:
        policy = SecurityPolicy.objects.get(id=policy_id, tenant_id=tenant_id)
    except SecurityPolicy.DoesNotExist:
        raise HttpError(404, "Security policy not found")
    policy.delete()
    return {"id": policy_id, "status": "deleted"}


# ---------------------------------------------------------------------------
# ColumnMask CRUD (GOV-F-007)
# ---------------------------------------------------------------------------


class ColumnMaskDefItem(Schema):
    id: str
    name: str
    description: str = ""
    status: str
    table_name: str
    column_name: str
    mask_type: str
    mask_config: dict[str, Any] = Field(default_factory=dict)
    roles: list[str] = Field(default_factory=list)
    exempt_roles: list[str] = Field(default_factory=list)


class ColumnMaskCreateRequest(Schema):
    name: str
    description: str = ""
    table_name: str
    column_name: str
    mask_type: str  # null / hash / partial / redact
    mask_config: dict[str, Any] = Field(default_factory=dict)
    roles: list[str] = Field(default_factory=list)
    exempt_roles: list[str] = Field(default_factory=list)
    status: str = "active"


class ColumnMaskUpdateRequest(Schema):
    name: str | None = None
    description: str | None = None
    table_name: str | None = None
    column_name: str | None = None
    mask_type: str | None = None
    mask_config: dict[str, Any] | None = None
    roles: list[str] | None = None
    exempt_roles: list[str] | None = None
    status: str | None = None


@governance_router.get(
    "/column-mask-defs",
    response=list[ColumnMaskDefItem],
    auth=auth_guard,
)
def list_column_mask_defs(request):
    """List all ColumnMask entries for the current tenant."""
    from apps.governance.models import ColumnMask

    tenant_id = get_tenant_id(request)
    masks = ColumnMask.objects.filter(tenant_id=tenant_id)
    return [
        ColumnMaskDefItem(
            id=str(m.id),
            name=m.name,
            description=m.description,
            status=m.status,
            table_name=m.table_name,
            column_name=m.column_name,
            mask_type=m.mask_type,
            mask_config=m.mask_config or {},
            roles=m.roles or [],
            exempt_roles=m.exempt_roles or [],
        )
        for m in masks
    ]


@governance_router.post(
    "/column-mask-defs",
    response=ColumnMaskDefItem,
    auth=auth_guard,
)
def create_column_mask_def(request, payload: ColumnMaskCreateRequest):
    """Create a new ColumnMask."""
    from apps.governance.models import ColumnMask

    tenant_id = get_tenant_id(request)
    mask = ColumnMask.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        table_name=payload.table_name,
        column_name=payload.column_name,
        mask_type=payload.mask_type,
        mask_config=payload.mask_config,
        roles=payload.roles,
        exempt_roles=payload.exempt_roles,
        status=payload.status,
    )
    return ColumnMaskDefItem(
        id=str(mask.id),
        name=mask.name,
        description=mask.description,
        status=mask.status,
        table_name=mask.table_name,
        column_name=mask.column_name,
        mask_type=mask.mask_type,
        mask_config=mask.mask_config or {},
        roles=mask.roles or [],
        exempt_roles=mask.exempt_roles or [],
    )


@governance_router.get(
    "/column-mask-defs/{mask_id}",
    response=ColumnMaskDefItem,
    auth=auth_guard,
)
def get_column_mask_def(request, mask_id: str):
    """Retrieve a single ColumnMask by ID."""
    from apps.governance.models import ColumnMask

    tenant_id = get_tenant_id(request)
    try:
        m = ColumnMask.objects.get(id=mask_id, tenant_id=tenant_id)
    except ColumnMask.DoesNotExist:
        raise HttpError(404, "Column mask not found")
    return ColumnMaskDefItem(
        id=str(m.id),
        name=m.name,
        description=m.description,
        status=m.status,
        table_name=m.table_name,
        column_name=m.column_name,
        mask_type=m.mask_type,
        mask_config=m.mask_config or {},
        roles=m.roles or [],
        exempt_roles=m.exempt_roles or [],
    )


@governance_router.put(
    "/column-mask-defs/{mask_id}",
    response=ColumnMaskDefItem,
    auth=auth_guard,
)
def update_column_mask_def(request, mask_id: str, payload: ColumnMaskUpdateRequest):
    """Update a ColumnMask."""
    from apps.governance.models import ColumnMask

    tenant_id = get_tenant_id(request)
    try:
        mask = ColumnMask.objects.get(id=mask_id, tenant_id=tenant_id)
    except ColumnMask.DoesNotExist:
        raise HttpError(404, "Column mask not found")

    update_fields = payload.dict(exclude_unset=True)
    for field_name, value in update_fields.items():
        setattr(mask, field_name, value)
    mask.save()

    return ColumnMaskDefItem(
        id=str(mask.id),
        name=mask.name,
        description=mask.description,
        status=mask.status,
        table_name=mask.table_name,
        column_name=mask.column_name,
        mask_type=mask.mask_type,
        mask_config=mask.mask_config or {},
        roles=mask.roles or [],
        exempt_roles=mask.exempt_roles or [],
    )


@governance_router.delete(
    "/column-mask-defs/{mask_id}",
    response=dict[str, str],
    auth=auth_guard,
)
def delete_column_mask_def(request, mask_id: str):
    """Delete a ColumnMask."""
    from apps.governance.models import ColumnMask

    tenant_id = get_tenant_id(request)
    try:
        mask = ColumnMask.objects.get(id=mask_id, tenant_id=tenant_id)
    except ColumnMask.DoesNotExist:
        raise HttpError(404, "Column mask not found")
    mask.delete()
    return {"id": mask_id, "status": "deleted"}


# ---------------------------------------------------------------------------
# Catalog Browser (GOV-F-008)
# ---------------------------------------------------------------------------


class CatalogColumnItem(Schema):
    name: str
    type: str
    nullable: bool = True
    description: str | None = None


class CatalogTableItem(Schema):
    name: str
    column_count: int = 0
    columns: list[CatalogColumnItem] = Field(default_factory=list)


class CatalogDatabaseItem(Schema):
    name: str
    table_count: int = 0
    tables: list[CatalogTableItem] = Field(default_factory=list)


class CatalogResponse(Schema):
    databases: list[CatalogDatabaseItem]


@governance_router.get("/catalog", response=CatalogResponse, auth=auth_guard)
def browse_catalog(request, schema: str | None = None, include_columns: bool = False):
    """Browse the data catalog: databases → tables → columns.

    Uses the Iceberg REST catalog when available, falling back to Trino
    metadata queries.
    """
    from apps.core.lib.trino import get_trino_client

    try:
        client = get_trino_client()
        databases: list[CatalogDatabaseItem] = []

        # Try Iceberg REST catalog namespaces first
        try:
            from apps.core.lib.iceberg import get_iceberg_client

            iceberg = get_iceberg_client()
            namespaces = iceberg.list_namespaces()
            for ns in namespaces:
                ns_name = (
                    ns
                    if isinstance(ns, str)
                    else ns[-1] if isinstance(ns, list) else str(ns)
                )
                tables_meta = iceberg.list_tables(ns_name)
                table_items: list[CatalogTableItem] = []
                for tbl in tables_meta:
                    tbl_name = tbl if isinstance(tbl, str) else str(tbl)
                    columns: list[CatalogColumnItem] = []
                    if include_columns:
                        try:
                            tbl_detail = iceberg.get_table(ns_name, tbl_name)
                            for sf in tbl_detail.schema_fields or []:
                                columns.append(
                                    CatalogColumnItem(
                                        name=sf.get("name", ""),
                                        type=sf.get("type", "unknown"),
                                        nullable=not sf.get("required", False),
                                    )
                                )
                        except Exception:
                            pass
                    table_items.append(
                        CatalogTableItem(
                            name=tbl_name,
                            column_count=len(columns),
                            columns=columns,
                        )
                    )
                databases.append(
                    CatalogDatabaseItem(
                        name=ns_name,
                        table_count=len(table_items),
                        tables=table_items,
                    )
                )
            if databases:
                return CatalogResponse(databases=databases)
        except Exception:
            pass  # Fall back to Trino

        # Trino fallback: list schemas via SHOW SCHEMAS
        result = client.execute("SHOW SCHEMAS")
        schemas = [row[0] for row in result.rows if row]

        target_schemas = [schema] if schema else schemas
        for sch in target_schemas:
            try:
                safe_schema = client._validate_identifier(sch)
                tables_result = client.execute(f"SHOW TABLES FROM {safe_schema}")
                table_items = []
                for row in tables_result.rows:
                    tbl_name = row[0] if row else ""
                    columns: list[CatalogColumnItem] = []
                    if include_columns:
                        try:
                            cols = client.get_columns(tbl_name, safe_schema)
                            columns = [
                                CatalogColumnItem(name=c["name"], type=c["type"])
                                for c in cols
                            ]
                        except Exception:
                            pass
                    table_items.append(
                        CatalogTableItem(
                            name=tbl_name,
                            column_count=len(columns),
                            columns=columns,
                        )
                    )
                databases.append(
                    CatalogDatabaseItem(
                        name=sch,
                        table_count=len(table_items),
                        tables=table_items,
                    )
                )
            except Exception:
                continue

        return CatalogResponse(databases=databases)

    except Exception as exc:
        logger.exception("Catalog browse failed")
        raise HttpError(500, get_message("ERR_SYSTEM", error=str(exc))) from exc


# ---------------------------------------------------------------------------
# Lineage Graph (GOV-F-009)
# ---------------------------------------------------------------------------


class LineageGraphNode(Schema):
    id: str
    type: str
    name: str


class LineageGraphEdge(Schema):
    source: str
    target: str
    type: str


class LineageGraphResponse(Schema):
    nodes: list[LineageGraphNode]
    edges: list[LineageGraphEdge]
    stats: dict[str, int]


@governance_router.get(
    "/lineage-graph",
    response=LineageGraphResponse,
    auth=auth_guard,
)
def get_lineage_graph(request, node_id: str | None = None, depth: int = 3):
    """Get the lineage graph, optionally centered on a specific node.

    Returns upstream/downstream relationships from the in-memory lineage
    graph for the current tenant.
    """
    from apps.governance.lib.lineage import get_lineage_graph

    tenant_id = get_tenant_id(request)
    graph = get_lineage_graph()

    if node_id:
        # Get upstream and downstream for the specific node
        upstream_ids = graph.get_upstream(node_id, depth=depth)
        downstream_ids = graph.get_downstream(node_id, depth=depth)
        relevant_ids = set(upstream_ids) | set(downstream_ids) | {node_id}

        nodes = []
        edges = []
        for nid in relevant_ids:
            n = graph.get_node(nid)
            if n:
                nodes.append(
                    LineageGraphNode(
                        id=n.node_id,
                        type=n.node_type.value,
                        name=n.name,
                    )
                )
            for e in graph.get_edges_for_node(nid):
                if e.source_id in relevant_ids and e.target_id in relevant_ids:
                    edges.append(
                        LineageGraphEdge(
                            source=e.source_id,
                            target=e.target_id,
                            type=e.edge_type.value,
                        )
                    )

        # Deduplicate edges
        seen = set()
        unique_edges = []
        for e in edges:
            key = (e.source, e.target, e.type)
            if key not in seen:
                seen.add(key)
                unique_edges.append(e)

        return LineageGraphResponse(
            nodes=nodes,
            edges=unique_edges,
            stats={"node_count": len(nodes), "edge_count": len(unique_edges)},
        )

    # Return full tenant graph
    data = graph.to_json(tenant_id=tenant_id, include_properties=False)
    return LineageGraphResponse(
        nodes=[
            LineageGraphNode(id=n["id"], type=n["type"], name=n["name"])
            for n in data["nodes"]
        ],
        edges=[
            LineageGraphEdge(source=e["source"], target=e["target"], type=e["type"])
            for e in data["edges"]
        ],
        stats=data.get("stats", {"node_count": 0, "edge_count": 0}),
    )


# ---------------------------------------------------------------------------
# GDPR Right-to-Deletion (GOV-F-010)
# ---------------------------------------------------------------------------


class GDPRDeleteRequest(Schema):
    """Request to trigger GDPR right-to-deletion."""

    user_id: str = Field(..., description="User ID whose data should be erased")


class GDPRDeleteResponse(Schema):
    """Response after triggering GDPR deletion workflow."""

    workflow_id: str
    tenant_id: str
    user_id: str
    status: str
    message: str


class GDPRStatusResponse(Schema):
    """Status of an in-progress GDPR deletion workflow."""

    workflow_id: str
    status: str
    result: dict[str, Any] | None = None
    error: str | None = None


@governance_router.post(
    "/gdpr/delete",
    response=GDPRDeleteResponse,
    auth=require_permission("write:governance"),
)
def gdpr_delete(request, payload: GDPRDeleteRequest):
    """Trigger GDPR Article 17 right-to-erasure for a user.

    Starts a Temporal workflow that deletes all user data across ontology,
    scraper, ML, and audit domains, then generates a deletion certificate.
    """
    import uuid as _uuid

    from apps.core.api_utils import run_async
    from apps.core.lib.temporal_client import get_temporal_client
    from apps.worker.workflows.gdpr_deletion import GDPRDeletionWorkflow

    tenant_id = get_tenant_id(request)
    workflow_id = f"gdpr-delete-{_uuid.uuid4().hex[:12]}"

    try:
        client = run_async(get_temporal_client)
        run_async(
            client.start_workflow,
            GDPRDeletionWorkflow.run,
            {"tenant_id": tenant_id, "user_id": payload.user_id},
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
    except Exception as exc:
        logger.error("Failed to start GDPR deletion workflow: %s", exc)
        raise HttpError(500, get_message("ERR_SYSTEM", error=str(exc))) from exc

    return GDPRDeleteResponse(
        workflow_id=workflow_id,
        tenant_id=tenant_id,
        user_id=payload.user_id,
        status="started",
        message="GDPR deletion workflow started. Use GET /v1/governance/gdpr/status/{workflow_id} to track progress.",
    )


@governance_router.get(
    "/gdpr/status/{workflow_id}",
    response=GDPRStatusResponse,
    auth=require_permission("read:governance"),
)
def gdpr_status(request, workflow_id: str):
    """Check the status of a GDPR deletion workflow.

    Returns the current status and, if complete, the deletion report
    including the certificate storage path.
    """
    from apps.core.api_utils import run_async
    from apps.core.lib.temporal_client import get_temporal_client

    try:
        client = run_async(get_temporal_client)
        handle = client.get_workflow_handle(workflow_id)

        try:
            result = run_async(handle.result)
            return GDPRStatusResponse(
                workflow_id=workflow_id,
                status="completed",
                result=result,
            )
        except Exception:
            # Workflow may still be running — try to describe it.
            try:
                desc = run_async(handle.describe)
                status_str = str(desc.status).split(".")[-1].lower()
                return GDPRStatusResponse(
                    workflow_id=workflow_id,
                    status=status_str,
                )
            except Exception as inner:
                return GDPRStatusResponse(
                    workflow_id=workflow_id,
                    status="unknown",
                    error=str(inner),
                )
    except Exception as exc:
        raise HttpError(404, f"Workflow {workflow_id} not found: {exc}") from exc


# ---------------------------------------------------------------------------
# Cell-Level Security (GOV-F-011)
# ---------------------------------------------------------------------------


class CellSecurityPolicyItem(Schema):
    id: str
    name: str
    description: str = ""
    status: str
    table_name: str
    column_name: str
    row_condition: dict[str, Any] = Field(default_factory=dict)
    viewer_condition: dict[str, Any] = Field(default_factory=dict)
    decision: str
    mask_value: str = "***"
    priority: int = 100


class CellSecurityPolicyCreateRequest(Schema):
    name: str
    description: str = ""
    table_name: str
    column_name: str
    row_condition: dict[str, Any] = Field(default_factory=dict)
    viewer_condition: dict[str, Any] = Field(default_factory=dict)
    decision: str = "mask"
    mask_value: str = "***"
    priority: int = 100
    status: str = "active"


class CellSecurityPolicyUpdateRequest(Schema):
    name: str | None = None
    description: str | None = None
    table_name: str | None = None
    column_name: str | None = None
    row_condition: dict[str, Any] | None = None
    viewer_condition: dict[str, Any] | None = None
    decision: str | None = None
    mask_value: str | None = None
    priority: int | None = None
    status: str | None = None


class CellAccessCheckRequest(Schema):
    """Request to evaluate cell-level access."""
    table_name: str = Field(..., description="Table name")
    column_name: str = Field(..., description="Column name")
    row_data: dict[str, Any] = Field(
        default_factory=dict, description="Row data for condition evaluation"
    )
    user_attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Viewer attributes (id, roles, department, etc.)",
    )


class CellAccessCheckResponse(Schema):
    """Response for cell-level access check."""
    decision: str
    policy_name: str | None = None
    table_name: str
    column_name: str


def _cell_policy_to_item(p) -> CellSecurityPolicyItem:
    return CellSecurityPolicyItem(
        id=str(p.id),
        name=p.name,
        description=p.description,
        status=p.status,
        table_name=p.table_name,
        column_name=p.column_name,
        row_condition=p.row_condition or {},
        viewer_condition=p.viewer_condition or {},
        decision=p.decision,
        mask_value=p.mask_value,
        priority=p.priority,
    )


@governance_router.get(
    "/cell-security-policies",
    response=list[CellSecurityPolicyItem],
    auth=auth_guard,
)
def list_cell_security_policies(request):
    """List all cell-level security policies for the current tenant."""
    from apps.governance.cell_security import CellSecurityPolicy

    tenant_id = get_tenant_id(request)
    policies = CellSecurityPolicy.objects.filter(tenant_id=tenant_id)
    return [_cell_policy_to_item(p) for p in policies]


@governance_router.post(
    "/cell-security-policies",
    response=CellSecurityPolicyItem,
    auth=auth_guard,
)
def create_cell_security_policy(request, payload: CellSecurityPolicyCreateRequest):
    """Create a new cell-level security policy."""
    from apps.governance.cell_security import CellSecurityPolicy

    tenant_id = get_tenant_id(request)
    policy = CellSecurityPolicy.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        table_name=payload.table_name,
        column_name=payload.column_name,
        row_condition=payload.row_condition,
        viewer_condition=payload.viewer_condition,
        decision=payload.decision,
        mask_value=payload.mask_value,
        priority=payload.priority,
        status=payload.status,
    )
    return _cell_policy_to_item(policy)


@governance_router.get(
    "/cell-security-policies/{policy_id}",
    response=CellSecurityPolicyItem,
    auth=auth_guard,
)
def get_cell_security_policy(request, policy_id: str):
    """Retrieve a single cell-level security policy by ID."""
    from apps.governance.cell_security import CellSecurityPolicy

    tenant_id = get_tenant_id(request)
    try:
        p = CellSecurityPolicy.objects.get(id=policy_id, tenant_id=tenant_id)
    except CellSecurityPolicy.DoesNotExist:
        raise HttpError(404, "Cell security policy not found")
    return _cell_policy_to_item(p)


@governance_router.put(
    "/cell-security-policies/{policy_id}",
    response=CellSecurityPolicyItem,
    auth=auth_guard,
)
def update_cell_security_policy(
    request, policy_id: str, payload: CellSecurityPolicyUpdateRequest
):
    """Update a cell-level security policy."""
    from apps.governance.cell_security import CellSecurityPolicy

    tenant_id = get_tenant_id(request)
    try:
        policy = CellSecurityPolicy.objects.get(id=policy_id, tenant_id=tenant_id)
    except CellSecurityPolicy.DoesNotExist:
        raise HttpError(404, "Cell security policy not found")

    for field_name, value in payload.dict(exclude_unset=True).items():
        setattr(policy, field_name, value)
    policy.save()
    return _cell_policy_to_item(policy)


@governance_router.delete(
    "/cell-security-policies/{policy_id}",
    response=dict[str, str],
    auth=auth_guard,
)
def delete_cell_security_policy(request, policy_id: str):
    """Delete a cell-level security policy."""
    from apps.governance.cell_security import CellSecurityPolicy

    tenant_id = get_tenant_id(request)
    try:
        policy = CellSecurityPolicy.objects.get(id=policy_id, tenant_id=tenant_id)
    except CellSecurityPolicy.DoesNotExist:
        raise HttpError(404, "Cell security policy not found")
    policy.delete()
    return {"id": policy_id, "status": "deleted"}


@governance_router.post(
    "/cell-security/check",
    response=CellAccessCheckResponse,
    auth=auth_guard,
)
def cell_access_check(request, payload: CellAccessCheckRequest):
    """Evaluate cell-level access for a specific table/column/row combination."""
    from apps.governance.cell_security import CellAccessDecision, CellSecurityEngine

    tenant_id = get_tenant_id(request)
    engine = CellSecurityEngine(tenant_id=tenant_id)
    decision = engine.evaluate_cell_access(
        user=payload.user_attributes,
        table=payload.table_name,
        column=payload.column_name,
        row_data=payload.row_data,
    )

    matching_policy = None
    if decision != CellAccessDecision.ALLOW:
        from apps.governance.cell_security import CellSecurityPolicy

        policy = CellSecurityPolicy.objects.filter(
            table_name=payload.table_name,
            column_name=payload.column_name,
            status="active",
            tenant_id=tenant_id,
        ).first()
        if policy:
            matching_policy = policy.name

    return CellAccessCheckResponse(
        decision=decision.value,
        policy_name=matching_policy,
        table_name=payload.table_name,
        column_name=payload.column_name,
    )


# ---------------------------------------------------------------------------
# ABAC Policies (GOV-F-012)
# ---------------------------------------------------------------------------


class ABACPolicyItem(Schema):
    id: str
    name: str
    description: str = ""
    status: str
    subject_attributes: dict[str, Any] = Field(default_factory=dict)
    resource_attributes: dict[str, Any] = Field(default_factory=dict)
    environment_attributes: dict[str, Any] = Field(default_factory=dict)
    decision: str
    priority: int = 100


class ABACPolicyCreateRequest(Schema):
    name: str
    description: str = ""
    subject_attributes: dict[str, Any] = Field(default_factory=dict)
    resource_attributes: dict[str, Any] = Field(default_factory=dict)
    environment_attributes: dict[str, Any] = Field(default_factory=dict)
    decision: str = "deny"
    priority: int = 100
    status: str = "active"


class ABACPolicyUpdateRequest(Schema):
    name: str | None = None
    description: str | None = None
    subject_attributes: dict[str, Any] | None = None
    resource_attributes: dict[str, Any] | None = None
    environment_attributes: dict[str, Any] | None = None
    decision: str | None = None
    priority: int | None = None
    status: str | None = None


class ABACEvaluateRequest(Schema):
    """Request to evaluate ABAC policies."""
    subject: dict[str, Any] = Field(
        default_factory=dict,
        description="Subject attributes (id, roles, department, etc.)",
    )
    resource: dict[str, Any] = Field(
        default_factory=dict,
        description="Resource attributes (type, classification, etc.)",
    )
    environment: dict[str, Any] = Field(
        default_factory=dict,
        description="Environment attributes (ip_address, time, etc.)",
    )


class ABACEvaluateResponse(Schema):
    """Response for ABAC evaluation."""
    decision: str
    subject: dict[str, Any] = Field(default_factory=dict)
    resource: dict[str, Any] = Field(default_factory=dict)


def _abac_policy_to_item(p) -> ABACPolicyItem:
    return ABACPolicyItem(
        id=str(p.id),
        name=p.name,
        description=p.description,
        status=p.status,
        subject_attributes=p.subject_attributes or {},
        resource_attributes=p.resource_attributes or {},
        environment_attributes=p.environment_attributes or {},
        decision=p.decision,
        priority=p.priority,
    )


@governance_router.get(
    "/abac-policies",
    response=list[ABACPolicyItem],
    auth=auth_guard,
)
def list_abac_policies(request):
    """List all ABAC policies for the current tenant."""
    from apps.governance.abac import ABACPolicy

    tenant_id = get_tenant_id(request)
    policies = ABACPolicy.objects.filter(tenant_id=tenant_id)
    return [_abac_policy_to_item(p) for p in policies]


@governance_router.post(
    "/abac-policies",
    response=ABACPolicyItem,
    auth=auth_guard,
)
def create_abac_policy(request, payload: ABACPolicyCreateRequest):
    """Create a new ABAC policy."""
    from apps.governance.abac import ABACPolicy

    tenant_id = get_tenant_id(request)
    policy = ABACPolicy.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        subject_attributes=payload.subject_attributes,
        resource_attributes=payload.resource_attributes,
        environment_attributes=payload.environment_attributes,
        decision=payload.decision,
        priority=payload.priority,
        status=payload.status,
    )
    return _abac_policy_to_item(policy)


@governance_router.get(
    "/abac-policies/{policy_id}",
    response=ABACPolicyItem,
    auth=auth_guard,
)
def get_abac_policy(request, policy_id: str):
    """Retrieve a single ABAC policy by ID."""
    from apps.governance.abac import ABACPolicy

    tenant_id = get_tenant_id(request)
    try:
        p = ABACPolicy.objects.get(id=policy_id, tenant_id=tenant_id)
    except ABACPolicy.DoesNotExist:
        raise HttpError(404, "ABAC policy not found")
    return _abac_policy_to_item(p)


@governance_router.put(
    "/abac-policies/{policy_id}",
    response=ABACPolicyItem,
    auth=auth_guard,
)
def update_abac_policy(request, policy_id: str, payload: ABACPolicyUpdateRequest):
    """Update an ABAC policy."""
    from apps.governance.abac import ABACPolicy

    tenant_id = get_tenant_id(request)
    try:
        policy = ABACPolicy.objects.get(id=policy_id, tenant_id=tenant_id)
    except ABACPolicy.DoesNotExist:
        raise HttpError(404, "ABAC policy not found")

    for field_name, value in payload.dict(exclude_unset=True).items():
        setattr(policy, field_name, value)
    policy.save()
    return _abac_policy_to_item(policy)


@governance_router.delete(
    "/abac-policies/{policy_id}",
    response=dict[str, str],
    auth=auth_guard,
)
def delete_abac_policy(request, policy_id: str):
    """Delete an ABAC policy."""
    from apps.governance.abac import ABACPolicy

    tenant_id = get_tenant_id(request)
    try:
        policy = ABACPolicy.objects.get(id=policy_id, tenant_id=tenant_id)
    except ABACPolicy.DoesNotExist:
        raise HttpError(404, "ABAC policy not found")
    policy.delete()
    return {"id": policy_id, "status": "deleted"}


@governance_router.post(
    "/abac/evaluate",
    response=ABACEvaluateResponse,
    auth=auth_guard,
)
def abac_evaluate(request, payload: ABACEvaluateRequest):
    """Evaluate ABAC policies against a request context.

    Uses deny-overrides combining algorithm: any matching DENY policy
    produces a final DENY, regardless of ALLOW policies.
    """
    from apps.governance.abac import evaluate_abac

    tenant_id = get_tenant_id(request)
    decision = evaluate_abac(
        tenant_id=tenant_id,
        subject=payload.subject,
        resource=payload.resource,
        environment=payload.environment,
    )
    return ABACEvaluateResponse(
        decision=decision.value,
        subject=payload.subject,
        resource=payload.resource,
    )
