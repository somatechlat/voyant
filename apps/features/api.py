"""Feature Store API — REST endpoints for features, groups, and serving."""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.features.models import Feature, FeatureGroup, FeatureValue
from apps.features.services import (
    FeatureComputeService,
    FeatureServeService,
    FeatureStatsService,
)

logger = logging.getLogger(__name__)

features_router = Router(tags=["features"], auth=require_permission("read:*"))


# ── Feature Groups CRUD ──────────────────────────────────────────────────────


@features_router.get("/groups")
def list_feature_groups(request):
    """List all feature groups for the current tenant."""
    tenant_id = get_tenant_id(request)
    groups = FeatureGroup.objects.filter(tenant_id=tenant_id).order_by("-created_at")
    return [
        {
            "id": str(g.id),
            "name": g.name,
            "description": g.description,
            "entity_key": g.entity_key,
            "online_enabled": g.online_enabled,
            "batch_enabled": g.batch_enabled,
            "schedule": g.schedule,
            "tags": g.tags,
            "feature_count": g.features.count(),  # type: ignore[attr-defined]
            "created_by": g.created_by,
            "created_at": g.created_at.isoformat(),
            "updated_at": g.updated_at.isoformat(),
        }
        for g in groups
    ]


@features_router.post("/groups", auth=require_permission("write:features"))
def create_feature_group(request, payload: dict[str, Any]):
    """Create a new feature group."""
    tenant_id = get_tenant_id(request)
    name = payload.get("name", "").strip()
    if not name:
        raise HttpError(400, "name is required")
    if FeatureGroup.objects.filter(name=name).exists():
        raise HttpError(409, f"Feature group '{name}' already exists")

    group = FeatureGroup.objects.create(
        tenant_id=tenant_id,
        name=name,
        description=payload.get("description", ""),
        entity_key=payload.get("entity_key", "entity_id"),
        online_enabled=payload.get("online_enabled", False),
        batch_enabled=payload.get("batch_enabled", True),
        schedule=payload.get("schedule", ""),
        tags=payload.get("tags", {}),
        created_by=payload.get("created_by", ""),
    )
    return {"id": str(group.id), "name": group.name, "status": "created"}


@features_router.get("/groups/{group_id}")
def get_feature_group(request, group_id: str):
    """Get a feature group with its features."""
    tenant_id = get_tenant_id(request)
    group = FeatureGroup.objects.filter(id=group_id, tenant_id=tenant_id).first()
    if not group:
        raise HttpError(404, "Feature group not found")

    features = group.features.all().order_by("ordinal_position", "name")
    return {
        "id": str(group.id),
        "name": group.name,
        "description": group.description,
        "entity_key": group.entity_key,
        "online_enabled": group.online_enabled,
        "batch_enabled": group.batch_enabled,
        "schedule": group.schedule,
        "tags": group.tags,
        "created_by": group.created_by,
        "created_at": group.created_at.isoformat(),
        "updated_at": group.updated_at.isoformat(),
        "features": [
            {
                "id": str(f.id),
                "name": f.name,
                "data_type": f.data_type,
                "description": f.description,
                "source_expression": f.source_expression,
                "statistics": f.statistics,
                "ordinal_position": f.ordinal_position,
            }
            for f in features
        ],
    }


@features_router.put("/groups/{group_id}", auth=require_permission("write:features"))
def update_feature_group(request, group_id: str, payload: dict[str, Any]):
    """Update a feature group."""
    tenant_id = get_tenant_id(request)
    group = FeatureGroup.objects.filter(id=group_id, tenant_id=tenant_id).first()
    if not group:
        raise HttpError(404, "Feature group not found")

    for field in [
        "name",
        "description",
        "entity_key",
        "online_enabled",
        "batch_enabled",
        "schedule",
        "tags",
    ]:
        if field in payload:
            setattr(group, field, payload[field])
    group.save()
    return {"id": str(group.id), "name": group.name, "status": "updated"}


@features_router.delete(
    "/groups/{group_id}", auth=require_permission("write:features")
)
def delete_feature_group(request, group_id: str):
    """Delete a feature group and all its features."""
    tenant_id = get_tenant_id(request)
    deleted, _ = FeatureGroup.objects.filter(id=group_id, tenant_id=tenant_id).delete()
    if not deleted:
        raise HttpError(404, "Feature group not found")
    return {"status": "deleted"}


# ── Features CRUD ─────────────────────────────────────────────────────────────


@features_router.get("")
def list_features(request, group_id: str | None = None):
    """List features, optionally filtered by group."""
    tenant_id = get_tenant_id(request)
    qs = Feature.objects.filter(tenant_id=tenant_id).select_related("feature_group")
    if group_id:
        qs = qs.filter(feature_group_id=group_id)

    return [
        {
            "id": str(f.id),
            "feature_group_id": str(f.feature_group_id),
            "feature_group_name": f.feature_group.name,
            "name": f.name,
            "data_type": f.data_type,
            "description": f.description,
            "source_expression": f.source_expression,
            "statistics": f.statistics,
            "ordinal_position": f.ordinal_position,
            "created_at": f.created_at.isoformat(),
        }
        for f in qs.order_by("ordinal_position", "name")
    ]


@features_router.post("", auth=require_permission("write:features"))
def create_feature(request, payload: dict[str, Any]):
    """Create a new feature within a group."""
    tenant_id = get_tenant_id(request)
    group_id = payload.get("feature_group_id")
    if not group_id:
        raise HttpError(400, "feature_group_id is required")

    group = FeatureGroup.objects.filter(id=group_id, tenant_id=tenant_id).first()
    if not group:
        raise HttpError(404, "Feature group not found")

    name = payload.get("name", "").strip()
    if not name:
        raise HttpError(400, "name is required")

    if Feature.objects.filter(feature_group=group, name=name).exists():
        raise HttpError(409, f"Feature '{name}' already exists in group '{group.name}'")

    feature = Feature.objects.create(
        tenant_id=tenant_id,
        feature_group=group,
        name=name,
        data_type=payload.get("data_type", Feature.DataType.FLOAT),
        description=payload.get("description", ""),
        source_expression=payload.get("source_expression", ""),
        ordinal_position=payload.get("ordinal_position", 0),
    )

    # Create initial version snapshot
    FeatureStatsService.create_version_snapshot(feature)

    return {"id": str(feature.id), "name": feature.name, "status": "created"}


@features_router.get("/{feature_id}")
def get_feature(request, feature_id: str):
    """Get a single feature with its metadata."""
    tenant_id = get_tenant_id(request)
    feature = Feature.objects.filter(id=feature_id, tenant_id=tenant_id).select_related(
        "feature_group"
    ).first()
    if not feature:
        raise HttpError(404, "Feature not found")

    return {
        "id": str(feature.id),
        "feature_group_id": str(feature.feature_group_id),
        "feature_group_name": feature.feature_group.name,
        "name": feature.name,
        "data_type": feature.data_type,
        "description": feature.description,
        "source_expression": feature.source_expression,
        "statistics": feature.statistics,
        "ordinal_position": feature.ordinal_position,
        "created_at": feature.created_at.isoformat(),
        "updated_at": feature.updated_at.isoformat(),
    }


@features_router.put("/{feature_id}", auth=require_permission("write:features"))
def update_feature(request, feature_id: str, payload: dict[str, Any]):
    """Update a feature."""
    tenant_id = get_tenant_id(request)
    feature = Feature.objects.filter(id=feature_id, tenant_id=tenant_id).first()
    if not feature:
        raise HttpError(404, "Feature not found")

    changed = False
    for field in [
        "name",
        "data_type",
        "description",
        "source_expression",
        "ordinal_position",
    ]:
        if field in payload:
            setattr(feature, field, payload[field])
            changed = True
    feature.save()

    # Create a version snapshot if schema changed
    if changed:
        FeatureStatsService.create_version_snapshot(feature)

    return {"id": str(feature.id), "name": feature.name, "status": "updated"}


@features_router.delete("/{feature_id}", auth=require_permission("write:features"))
def delete_feature(request, feature_id: str):
    """Delete a feature and its values."""
    tenant_id = get_tenant_id(request)
    deleted, _ = Feature.objects.filter(id=feature_id, tenant_id=tenant_id).delete()
    if not deleted:
        raise HttpError(404, "Feature not found")
    return {"status": "deleted"}


# ── Feature Query & Compute ───────────────────────────────────────────────────


@features_router.get("/query")
def query_feature_values(
    request,
    entity_key_value: str | None = None,
    group_id: str | None = None,
    limit: int = 100,
):
    """Query feature values by entity key."""
    tenant_id = get_tenant_id(request)
    qs = FeatureValue.objects.filter(tenant_id=tenant_id).select_related(
        "feature", "feature__feature_group"
    )

    if entity_key_value:
        qs = qs.filter(entity_key_value=entity_key_value)
    if group_id:
        qs = qs.filter(feature__feature_group_id=group_id)

    values = qs.order_by("-computed_at")[:limit]
    return [
        {
            "id": str(v.id),
            "feature_name": v.feature.name,
            "feature_group": v.feature.feature_group.name,
            "entity_key_value": v.entity_key_value,
            "value": v.value,
            "computed_at": v.computed_at.isoformat(),
        }
        for v in values
    ]


@features_router.post("/compute", auth=require_permission("write:features"))
def trigger_compute(request, payload: dict[str, Any]):
    """Trigger feature computation for a group or individual feature."""
    tenant_id = get_tenant_id(request)

    group_id = payload.get("feature_group_id")
    feature_id = payload.get("feature_id")
    entity_key_value = payload.get("entity_key_value")

    if feature_id:
        feature = Feature.objects.filter(id=feature_id, tenant_id=tenant_id).first()
        if not feature:
            raise HttpError(404, "Feature not found")
        results = FeatureComputeService.compute_feature(feature, entity_key_value)
        return {
            "feature": feature.name,
            "values_computed": len(results),
            "results": results,
        }
    elif group_id:
        group = FeatureGroup.objects.filter(id=group_id, tenant_id=tenant_id).first()
        if not group:
            raise HttpError(404, "Feature group not found")
        results = FeatureComputeService.compute_group(group, entity_key_value)
        return results
    else:
        raise HttpError(400, "feature_group_id or feature_id is required")


# ── Statistics ────────────────────────────────────────────────────────────────


@features_router.get("/groups/{group_id}/statistics")
def get_group_statistics(request, group_id: str):
    """Get statistics for all features in a group."""
    tenant_id = get_tenant_id(request)
    group = FeatureGroup.objects.filter(id=group_id, tenant_id=tenant_id).first()
    if not group:
        raise HttpError(404, "Feature group not found")

    stats = FeatureStatsService.compute_group_statistics(group)
    return stats


# ── Online Serving ────────────────────────────────────────────────────────────


@features_router.get("/online/{entity_key_value}")
def serve_online(request, entity_key_value: str, group_id: str | None = None):
    """
    Low-latency online feature serving.

    Returns the latest feature values for a single entity, using Redis
    cache when available (FR-6.4.5.2).
    """
    tenant_id = get_tenant_id(request)

    group = None
    if group_id:
        group = FeatureGroup.objects.filter(id=group_id, tenant_id=tenant_id).first()
        if not group:
            raise HttpError(404, "Feature group not found")

    result = FeatureServeService.serve_online(tenant_id, entity_key_value, group)
    return result
