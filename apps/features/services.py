"""
Feature Store — Business logic services.

- FeatureComputeService: computes feature values from source_expression (SQL via Trino)
- FeatureServeService:  serves features online (Redis) and batch (SQL)
- FeatureStatsService:  computes statistics (mean, std, min, max, nulls_pct)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from django.db import models
from django.utils import timezone

from apps.features.models import Feature, FeatureGroup, FeatureValue, FeatureVersion

logger = logging.getLogger(__name__)


class FeatureComputeService:
    """
    Compute feature values from source expressions.

    Evaluates the SQL source_expression for each feature via Trino (or a
    compatible SQL engine) and persists results as FeatureValue rows.
    """

    @staticmethod
    def compute_feature(
        feature: Feature,
        entity_key_value: str | None = None,
        limit: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Compute a single feature's values.

        Args:
            feature: The Feature to compute.
            entity_key_value: Optional entity filter (e.g. a specific customer_id).
            limit: Max rows to compute.

        Returns:
            List of created FeatureValue dicts.
        """
        expression = feature.source_expression
        if not expression:
            logger.warning("Feature %s has no source_expression", feature.name)
            return []

        group = feature.feature_group
        entity_key = group.entity_key

        # Build SQL query from source_expression
        sql = expression
        if entity_key_value:
            # Inject entity filter — safe when source_expression is a column/table ref
            if "WHERE" not in sql.upper():
                sql = f"SELECT * FROM ({sql}) WHERE {entity_key} = :entity_key_value"
            else:
                sql = f"SELECT * FROM ({sql}) WHERE {entity_key} = :entity_key_value"

        logger.info(
            "Computing feature %s.%s (entity=%s)",
            group.name,
            feature.name,
            entity_key_value or "ALL",
        )

        try:
            # Execute via Trino — deferred import to avoid circular deps
            from apps.sql.services import execute_query  # type: ignore[import-untyped]

            params = {}
            if entity_key_value:
                params["entity_key_value"] = entity_key_value

            rows = execute_query(sql, params=params, limit=limit)
        except ImportError:
            # Fallback when SQL module is not yet wired — return empty
            logger.warning("SQL engine unavailable — skipping compute for %s", feature.name)
            return []
        except Exception as exc:
            logger.error("Compute failed for %s: %s", feature.name, exc)
            return []

        results: list[dict[str, Any]] = []
        now = timezone.now()
        tenant_id = feature.tenant_id

        for row in rows:
            raw_value = row.get(feature.name) if isinstance(row, dict) else None
            entity_val = (
                str(row.get(entity_key, ""))
                if isinstance(row, dict)
                else (entity_key_value or "")
            )

            fv, created = FeatureValue.objects.update_or_create(
                feature=feature,
                entity_key_value=entity_val,
                tenant_id=tenant_id,
                defaults={
                    "value": raw_value,
                    "computed_at": now,
                },
            )
            results.append(
                {
                    "id": str(fv.id),
                    "entity_key_value": entity_val,
                    "value": raw_value,
                    "created": created,
                }
            )

        logger.info(
            "Computed %d values for %s.%s", len(results), group.name, feature.name
        )
        return results

    @staticmethod
    def compute_group(
        feature_group: FeatureGroup,
        entity_key_value: str | None = None,
    ) -> dict[str, Any]:
        """Compute all features in a group."""
        features = feature_group.features.all()
        total_values = 0
        feature_results: dict[str, int] = {}

        for feat in features:
            values = FeatureComputeService.compute_feature(feat, entity_key_value)
            feature_results[feat.name] = len(values)
            total_values += len(values)

        return {
            "group_name": feature_group.name,
            "features_computed": len(feature_results),
            "total_values": total_values,
            "per_feature": feature_results,
        }


class FeatureServeService:
    """
    Serve features for model inference.

    - Online: low-latency Redis lookup for a single entity.
    - Batch:  SQL-based retrieval for many entities.
    """

    @staticmethod
    def serve_online(
        tenant_id: str,
        entity_key_value: str,
        feature_group: FeatureGroup | None = None,
    ) -> dict[str, Any]:
        """
        Low-latency online serving via Redis cache.

        Returns the latest feature values for an entity, checking Redis first
        and falling back to the database.
        """
        cache_key = f"features:{tenant_id}:{entity_key_value}"
        if feature_group:
            cache_key += f":{feature_group.name}"

        # Attempt Redis lookup
        try:
            from django.core.cache import cache  # type: ignore[import-untyped]

            cached = cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit for %s", cache_key)
                return json.loads(cached) if isinstance(cached, str) else cached
        except Exception as exc:
            logger.debug("Redis lookup failed, falling back to DB: %s", exc)

        # Fallback to DB — get latest value per feature
        qs = FeatureValue.objects.filter(
            tenant_id=tenant_id,
            entity_key_value=entity_key_value,
        ).select_related("feature", "feature__feature_group")

        if feature_group:
            qs = qs.filter(feature__feature_group=feature_group)

        # Get the most recent value per feature
        values: dict[str, Any] = {}
        seen_features: set[str] = set()

        for fv in qs.order_by("feature_id", "-computed_at"):
            fid = str(fv.feature_id)
            if fid in seen_features:
                continue
            seen_features.add(fid)
            values[fv.feature.name] = {
                "value": fv.value,
                "computed_at": fv.computed_at.isoformat(),
                "feature_group": fv.feature.feature_group.name,
                "data_type": fv.feature.data_type,
            }

        result: dict[str, Any] = {
            "entity_key_value": entity_key_value,
            "features": values,
            "source": "database",
        }

        # Cache for future lookups (60-second TTL)
        try:
            from django.core.cache import cache

            cache.set(cache_key, json.dumps(result, default=str), timeout=60)
        except Exception:
            pass

        return result

    @staticmethod
    def serve_batch(
        tenant_id: str,
        feature_group: FeatureGroup,
        entity_key_values: list[str] | None = None,
        limit: int = 10000,
    ) -> dict[str, Any]:
        """
        Batch serving via SQL query.

        Retrieves feature values for many entities at once.
        """
        qs = FeatureValue.objects.filter(
            tenant_id=tenant_id,
            feature__feature_group=feature_group,
        ).select_related("feature")

        if entity_key_values:
            qs = qs.filter(entity_key_value__in=entity_key_values)

        # Get latest per (feature, entity)
        values_by_entity: dict[str, dict[str, Any]] = {}
        for fv in qs.order_by("entity_key_value", "feature_id", "-computed_at")[:limit]:
            ent = fv.entity_key_value
            if ent not in values_by_entity:
                values_by_entity[ent] = {}
            fname = fv.feature.name
            if fname not in values_by_entity[ent]:
                values_by_entity[ent][fname] = fv.value

        return {
            "feature_group": feature_group.name,
            "entity_key": feature_group.entity_key,
            "entity_count": len(values_by_entity),
            "features": list(
                feature_group.features.values_list("name", flat=True)
            ),
            "data": values_by_entity,
            "source": "batch_sql",
        }

    @staticmethod
    def serve_point_in_time(
        tenant_id: str,
        entity_key_value: str,
        point_in_time: datetime,
        feature_group: FeatureGroup | None = None,
    ) -> dict[str, Any]:
        """
        Point-in-time correct retrieval (FR-6.4.5.3).

        Returns feature values as they were at the specified timestamp,
        preventing data leakage in ML training pipelines.
        """
        qs = FeatureValue.objects.filter(
            tenant_id=tenant_id,
            entity_key_value=entity_key_value,
            computed_at__lte=point_in_time,
        ).select_related("feature", "feature__feature_group")

        if feature_group:
            qs = qs.filter(feature__feature_group=feature_group)

        values: dict[str, Any] = {}
        seen: set[str] = set()
        for fv in qs.order_by("feature_id", "-computed_at"):
            fid = str(fv.feature_id)
            if fid in seen:
                continue
            seen.add(fid)
            values[fv.feature.name] = {
                "value": fv.value,
                "computed_at": fv.computed_at.isoformat(),
                "feature_group": fv.feature.feature_group.name,
            }

        return {
            "entity_key_value": entity_key_value,
            "point_in_time": point_in_time.isoformat(),
            "features": values,
        }


class FeatureStatsService:
    """
    Compute and update statistics for features (FR-6.4.5.6).

    Calculates mean, std, min, max, and nulls_pct from stored FeatureValues.
    """

    @staticmethod
    def compute_statistics(feature: Feature) -> dict[str, Any]:
        """
        Compute statistics for a single feature from its stored values.

        Uses database aggregation for efficiency, with Python-side std calculation.
        """

        qs = FeatureValue.objects.filter(feature=feature)
        total = qs.count()
        if total == 0:
            stats: dict[str, Any] = {
                "mean": None,
                "std": None,
                "min": None,
                "max": None,
                "nulls_pct": 0.0,
                "count": 0,
            }
            feature.statistics = stats
            feature.save(update_fields=["statistics"])
            return stats

        # Count nulls — values stored as None or JSON null
        null_count = qs.filter(
            models.Q(value__isnull=True) | models.Q(value=None)
        ).count()

        # Numeric aggregation on values that are numeric
        # FeatureValue.value is JSON, so we filter for numeric-ish values
        numeric_values: list[float] = []
        for fv in qs.iterator(chunk_size=2000):
            v = fv.value
            if v is None:
                continue
            try:
                numeric_values.append(float(v))
            except (TypeError, ValueError):
                continue

        if numeric_values:
            import statistics

            mean_val = statistics.mean(numeric_values)
            std_val = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0
            min_val = min(numeric_values)
            max_val = max(numeric_values)
        else:
            mean_val = None
            std_val = None
            min_val = None
            max_val = None

        stats = {
            "mean": round(mean_val, 6) if mean_val is not None else None,
            "std": round(std_val, 6) if std_val is not None else None,
            "min": min_val,
            "max": max_val,
            "nulls_pct": round((null_count / total) * 100, 2) if total else 0.0,
            "count": total,
        }

        feature.statistics = stats
        feature.save(update_fields=["statistics"])
        logger.info("Stats for %s.%s: %s", feature.feature_group.name, feature.name, stats)
        return stats

    @staticmethod
    def compute_group_statistics(feature_group: FeatureGroup) -> dict[str, Any]:
        """Compute statistics for all features in a group."""
        results: dict[str, Any] = {}
        for feature in feature_group.features.all():
            results[feature.name] = FeatureStatsService.compute_statistics(feature)
        return {
            "feature_group": feature_group.name,
            "feature_count": len(results),
            "statistics": results,
        }

    @staticmethod
    def create_version_snapshot(feature: Feature) -> FeatureVersion:
        """Create a versioned snapshot of a feature's current schema (FR-6.4.5.4)."""
        last_version = feature.versions.order_by("-version_number").first()
        new_version_number = (last_version.version_number + 1) if last_version else 1

        schema_snapshot = {
            "name": feature.name,
            "data_type": feature.data_type,
            "description": feature.description,
            "source_expression": feature.source_expression,
            "statistics": feature.statistics,
            "ordinal_position": feature.ordinal_position,
        }

        return FeatureVersion.objects.create(
            feature=feature,
            version_number=new_version_number,
            schema_snapshot=schema_snapshot,
        )
