"""
Ontology Engine — Service Layer.

Business logic for Object Types, Object Instances, Link Types,
and Link Instances. All methods accept explicit tenant_id to
enforce isolation at the service boundary.

ONT-F-006: Schema update with backward-compatibility checks
ONT-F-013: Batch operations
ONT-F-014: Upsert
ONT-F-017: Optimistic concurrency
ONT-F-023: Referential integrity
ONT-F-024: Cascading operations
ONT-F-025: Inverse link navigation
ONT-F-032: Multi-hop traversal
ONT-F-033: Filtered traversal
"""

from __future__ import annotations

import builtins
import logging
from typing import Any

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.core.events import publish_ontology_change
from apps.ontology.models import (
    Cardinality,
    Link,
    LinkType,
    Object,
    ObjectType,
    Property,
)
from apps.ontology.validators import ValidationError, validate_properties

logger = logging.getLogger(__name__)


# =========================================================================
# Object Type Service
# =========================================================================


class ObjectTypeService:
    """ONT-F-001 to ONT-F-008: Object type CRUD + schema versioning."""

    @staticmethod
    def list(tenant_id: str, *, include_deleted: bool = False) -> QuerySet[ObjectType]:
        qs = ObjectType.objects.filter(tenant_id=tenant_id)
        if not include_deleted:
            qs = qs.filter(deleted_at__isnull=True)
        return qs.order_by("name")

    @staticmethod
    def get(tenant_id: str, type_id: str) -> ObjectType:
        return ObjectType.objects.get(
            tenant_id=tenant_id,
            id=type_id,
            deleted_at__isnull=True,
        )

    @staticmethod
    @transaction.atomic
    def create(
        tenant_id: str,
        *,
        name: str,
        description: str = "",
        properties: builtins.list[dict[str, Any]],
        created_by: str = "",
    ) -> ObjectType:
        """ONT-F-001 + ONT-F-008: Create object type with properties.

        Args:
            created_by: Audit trail field for future use.
        """
        ot = ObjectType.objects.create(
            tenant_id=tenant_id,
            name=name,
            description=description,
            version=1,
        )
        for prop in properties:
            Property.objects.create(
                tenant_id=tenant_id,
                object_type=ot,
                name=prop["name"],
                property_type=prop["property_type"],
                required=prop.get("required", False),
                default_value=prop.get("default_value"),
                validation_rules=prop.get("validation_rules"),
                metadata=prop.get("metadata", {}),
            )
        logger.info("Created object type %s/%s", tenant_id, name)
        publish_ontology_change(
            tenant_id,
            "object_type.created",
            "ObjectType",
            str(ot.id),
            {"name": name},
        )
        return ot

    @staticmethod
    @transaction.atomic
    def update(
        tenant_id: str,
        type_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        properties: builtins.list[dict[str, Any]] | None = None,
    ) -> ObjectType:
        """ONT-F-006: Update with backward-compatibility checks + version bump."""
        ot = ObjectTypeService.get(tenant_id, type_id)

        if name is not None:
            ot.name = name
        if description is not None:
            ot.description = description

        if properties is not None:
            # Backward-compatibility: only allow additions and required changes,
            # not removals or type changes of existing required fields.
            existing = {p.name: p for p in ot.properties.all()}  # type: ignore[attr-defined]
            for prop in properties:
                if prop["name"] in existing:
                    old = existing[prop["name"]]
                    # Type change on a required field is forbidden
                    if old.required and old.property_type != prop.get(
                        "property_type", old.property_type
                    ):
                        raise ValidationError(
                            [
                                {
                                    "field": prop["name"],
                                    "code": "incompatible_change",
                                    "message": (
                                        f"Cannot change type of required property "
                                        f"'{prop['name']}' from {old.property_type} to "
                                        f"{prop.get('property_type')}"
                                    ),
                                }
                            ]
                        )
                    old.property_type = prop.get("property_type", old.property_type)
                    old.required = prop.get("required", old.required)
                    old.default_value = prop.get("default_value", old.default_value)
                    old.validation_rules = prop.get(
                        "validation_rules", old.validation_rules
                    )
                    old.metadata = prop.get("metadata", old.metadata)
                    old.save()
                else:
                    # New property — always allowed
                    Property.objects.create(
                        tenant_id=tenant_id,
                        object_type=ot,
                        name=prop["name"],
                        property_type=prop["property_type"],
                        required=prop.get("required", False),
                        default_value=prop.get("default_value"),
                        validation_rules=prop.get("validation_rules"),
                        metadata=prop.get("metadata", {}),
                    )

        ot.version += 1
        ot.save()
        logger.info("Updated object type %s/%s to v%d", tenant_id, ot.name, ot.version)
        publish_ontology_change(
            tenant_id,
            "object_type.updated",
            "ObjectType",
            str(ot.id),
            {"name": ot.name, "version": ot.version},
        )
        return ot

    @staticmethod
    def soft_delete(tenant_id: str, type_id: str) -> None:
        """ONT-F-007: Soft-delete."""
        ot = ObjectTypeService.get(tenant_id, type_id)
        # Refuse if instances exist
        if ot.instances.filter(deleted_at__isnull=True).exists():  # type: ignore[attr-defined]
            raise ValidationError(
                [
                    {
                        "field": "object_type",
                        "code": "has_instances",
                        "message": "Cannot delete object type with active instances",
                    }
                ]
            )
        ot.deleted_at = timezone.now()
        ot.save(update_fields=["deleted_at", "updated_at"])
        logger.info("Soft-deleted object type %s/%s", tenant_id, type_id)
        publish_ontology_change(
            tenant_id,
            "object_type.deleted",
            "ObjectType",
            type_id,
        )


# =========================================================================
# Object Instance Service
# =========================================================================


class ObjectService:
    """ONT-F-010 to ONT-F-017: Object instance CRUD + batch + upsert + versioning."""

    @staticmethod
    def list(tenant_id: str, object_type_id: str | None = None) -> QuerySet[Object]:
        qs = Object.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
        if object_type_id:
            qs = qs.filter(object_type_id=object_type_id)
        return qs.order_by("-created_at")

    @staticmethod
    def get(tenant_id: str, object_id: str) -> Object:
        return Object.objects.get(
            tenant_id=tenant_id,
            id=object_id,
            deleted_at__isnull=True,
        )

    @staticmethod
    @transaction.atomic
    def create(
        tenant_id: str,
        object_type_id: str,
        properties: dict[str, Any],
        *,
        created_by: str = "",
    ) -> Object:
        """ONT-F-010/011: Create with schema validation."""
        ot = ObjectTypeService.get(tenant_id, object_type_id)
        prop_defs = list(ot.properties.all())  # type: ignore[attr-defined]

        normalised, errors = validate_properties(properties, prop_defs)
        if errors:
            raise ValidationError(errors)

        obj = Object.objects.create(
            tenant_id=tenant_id,
            object_type=ot,
            properties=normalised,
            version=1,
        )
        logger.info("Created object %s in type %s", obj.id, ot.name)
        publish_ontology_change(
            tenant_id,
            "object.created",
            "Object",
            str(obj.id),
            {"object_type": ot.name},
        )
        return obj

    @staticmethod
    @transaction.atomic
    def update(
        tenant_id: str,
        object_id: str,
        properties: dict[str, Any],
        *,
        version: int | None = None,
    ) -> Object:
        """ONT-F-011/017: Update with validation + optimistic concurrency."""
        obj = ObjectService.get(tenant_id, object_id)

        if version is not None and obj.version != version:
            raise ValidationError(
                [
                    {
                        "field": "version",
                        "code": "conflict",
                        "message": f"Version mismatch: expected {version}, got {obj.version}",
                    }
                ]
            )

        ot = obj.object_type
        prop_defs = list(ot.properties.all())

        # Merge with existing properties for partial updates
        merged = {**obj.properties, **properties}
        normalised, errors = validate_properties(merged, prop_defs)
        if errors:
            raise ValidationError(errors)

        obj.properties = normalised
        obj.version += 1
        obj.save(update_fields=["properties", "version", "updated_at"])
        logger.info("Updated object %s to v%d", obj.id, obj.version)
        publish_ontology_change(
            tenant_id,
            "object.updated",
            "Object",
            str(obj.id),
            {"object_type": ot.name, "version": obj.version},
        )
        return obj

    @staticmethod
    def soft_delete(tenant_id: str, object_id: str) -> None:
        """ONT-F-016: Soft-delete with retention."""
        obj = ObjectService.get(tenant_id, object_id)
        # Check for active links
        active_links = Link.objects.filter(
            Q(source_object=obj) | Q(target_object=obj),
            deleted_at__isnull=True,
        )
        if active_links.exists():
            raise ValidationError(
                [
                    {
                        "field": "object",
                        "code": "has_links",
                        "message": "Cannot delete object with active links",
                    }
                ]
            )
        obj.deleted_at = timezone.now()
        obj.save(update_fields=["deleted_at", "updated_at"])
        publish_ontology_change(
            tenant_id,
            "object.deleted",
            "Object",
            object_id,
        )

    @staticmethod
    @transaction.atomic
    def batch_create(
        tenant_id: str,
        object_type_id: str,
        items: builtins.list[dict[str, Any]],
    ) -> builtins.list[Object]:
        """ONT-F-013: Batch create 1000+ objects."""
        ot = ObjectTypeService.get(tenant_id, object_type_id)
        prop_defs = list(ot.properties.all())  # type: ignore[attr-defined]
        created = []

        for item in items:
            normalised, errors = validate_properties(item, prop_defs)
            if errors:
                raise ValidationError(errors)
            obj = Object(
                tenant_id=tenant_id,
                object_type=ot,
                properties=normalised,
                version=1,
            )
            created.append(obj)

        return Object.objects.bulk_create(created)

    @staticmethod
    @transaction.atomic
    def upsert(
        tenant_id: str,
        object_type_id: str,
        key_property: str,
        items: builtins.list[dict[str, Any]],
    ) -> builtins.list[Object]:
        """ONT-F-014: Upsert by a unique key property."""
        results = []
        for item in items:
            key_val = item.get(key_property)
            if key_val is None:
                raise ValidationError(
                    [
                        {
                            "field": key_property,
                            "code": "required",
                            "message": f"Upsert key '{key_property}' is missing",
                        }
                    ]
                )
            existing = Object.objects.filter(
                tenant_id=tenant_id,
                object_type_id=object_type_id,
                properties__contains={key_property: key_val},
                deleted_at__isnull=True,
            ).first()
            if existing:
                obj = ObjectService.update(tenant_id, str(existing.id), item)
            else:
                obj = ObjectService.create(tenant_id, object_type_id, item)
            results.append(obj)
        return results


# =========================================================================
# Link Type Service
# =========================================================================


class LinkTypeService:
    """ONT-F-020 to ONT-F-025: Link type CRUD + referential integrity."""

    @staticmethod
    def list(tenant_id: str) -> QuerySet[LinkType]:
        return LinkType.objects.filter(
            tenant_id=tenant_id, deleted_at__isnull=True
        ).order_by("name")

    @staticmethod
    def get(tenant_id: str, lt_id: str) -> LinkType:
        return LinkType.objects.get(
            tenant_id=tenant_id, id=lt_id, deleted_at__isnull=True
        )

    @staticmethod
    @transaction.atomic
    def create(
        tenant_id: str,
        *,
        name: str,
        source_object_type_id: str,
        target_object_type_id: str,
        cardinality: str = Cardinality.ONE_TO_MANY,
        description: str = "",
        properties_schema: dict | None = None,
        inverse_name: str = "",
    ) -> LinkType:
        """ONT-F-020/021: Create link type with referential integrity."""
        # Validate source/target exist in same tenant
        ObjectTypeService.get(tenant_id, source_object_type_id)
        ObjectTypeService.get(tenant_id, target_object_type_id)

        lt = LinkType.objects.create(
            tenant_id=tenant_id,
            name=name,
            description=description,
            source_object_type_id=source_object_type_id,
            target_object_type_id=target_object_type_id,
            cardinality=cardinality,
            properties_schema=properties_schema,
            inverse_name=inverse_name,
        )
        logger.info("Created link type %s/%s", tenant_id, name)
        publish_ontology_change(
            tenant_id,
            "link_type.created",
            "LinkType",
            str(lt.id),
            {"name": name},
        )
        return lt

    @staticmethod
    def soft_delete(tenant_id: str, lt_id: str) -> None:
        lt = LinkTypeService.get(tenant_id, lt_id)
        if lt.instances.filter(deleted_at__isnull=True).exists():  # type: ignore[attr-defined]
            raise ValidationError(
                [
                    {
                        "field": "link_type",
                        "code": "has_instances",
                        "message": "Cannot delete link type with active instances",
                    }
                ]
            )
        lt.deleted_at = timezone.now()
        lt.save(update_fields=["deleted_at", "updated_at"])
        publish_ontology_change(
            tenant_id,
            "link_type.deleted",
            "LinkType",
            lt_id,
        )


# =========================================================================
# Link Instance Service
# =========================================================================


class LinkService:
    """ONT-F-030 to ONT-F-034: Link instance CRUD + traversal."""

    @staticmethod
    @transaction.atomic
    def create(
        tenant_id: str,
        link_type_id: str,
        source_object_id: str,
        target_object_id: str,
        properties: dict[str, Any] | None = None,
    ) -> Link:
        """ONT-F-030/023: Create with referential integrity check."""
        lt = LinkTypeService.get(tenant_id, link_type_id)
        src = ObjectService.get(tenant_id, source_object_id)
        tgt = ObjectService.get(tenant_id, target_object_id)

        # Verify types match
        if str(src.object_type_id) != str(lt.source_object_type_id):  # type: ignore[attr-defined]
            raise ValidationError(
                [
                    {
                        "field": "source_object",
                        "code": "type_mismatch",
                        "message": (
                            f"Source object type {src.object_type.name} != expected {lt.source_object_type.name}"
                        ),
                    }
                ]
            )
        if str(tgt.object_type_id) != str(lt.target_object_type_id):  # type: ignore[attr-defined]
            raise ValidationError(
                [
                    {
                        "field": "target_object",
                        "code": "type_mismatch",
                        "message": (
                            f"Target object type {tgt.object_type.name} != expected {lt.target_object_type.name}"
                        ),
                    }
                ]
            )

        # One-to-one uniqueness
        if lt.cardinality == Cardinality.ONE_TO_ONE:
            if Link.objects.filter(
                link_type=lt,
                source_object=src,
                deleted_at__isnull=True,
            ).exists():
                raise ValidationError(
                    [
                        {
                            "field": "link",
                            "code": "duplicate",
                            "message": "One-to-one link already exists from this source",
                        }
                    ]
                )

        link = Link.objects.create(
            tenant_id=tenant_id,
            link_type=lt,
            source_object=src,
            target_object=tgt,
            properties=properties or {},
        )
        logger.info("Created link %s", link.id)
        publish_ontology_change(
            tenant_id,
            "link.created",
            "Link",
            str(link.id),
            {
                "link_type": lt.name,
                "source_object_id": source_object_id,
                "target_object_id": target_object_id,
            },
        )
        return link

    @staticmethod
    @transaction.atomic
    def delete(tenant_id: str, link_id: str) -> None:
        link = Link.objects.get(
            tenant_id=tenant_id, id=link_id, deleted_at__isnull=True
        )
        link.deleted_at = timezone.now()
        link.save(update_fields=["deleted_at", "updated_at"])
        publish_ontology_change(
            tenant_id,
            "link.deleted",
            "Link",
            link_id,
        )

    @staticmethod
    def traverse(
        tenant_id: str,
        object_id: str,
        *,
        link_type_name: str | None = None,
        direction: str = "outgoing",
        max_depth: int = 1,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        ONT-F-031/032/033: Traverse links from a starting object.

        direction: 'outgoing', 'incoming', or 'both'
        max_depth: how many hops to follow (default 1 = direct links only)
        filters: reserved for future property-based filtering on intermediate objects
        """
        visited = set()
        results: list[dict[str, Any]] = []

        def _traverse(obj_id: str, depth: int):
            if depth > max_depth or obj_id in visited:
                return
            visited.add(obj_id)

            qs_out = Link.objects.filter(
                tenant_id=tenant_id,
                source_object_id=obj_id,
                deleted_at__isnull=True,
            )
            qs_in = Link.objects.filter(
                tenant_id=tenant_id,
                target_object_id=obj_id,
                deleted_at__isnull=True,
            )

            if link_type_name:
                qs_out = qs_out.filter(link_type__name=link_type_name)
                qs_in = qs_in.filter(link_type__name=link_type_name)

            if direction in ("outgoing", "both"):
                for link in qs_out.select_related("target_object", "link_type"):
                    target = link.target_object
                    results.append(
                        {
                            "link_id": str(link.id),
                            "link_type": link.link_type.name,
                            "direction": "outgoing",
                            "object_id": str(target.id),
                            "object_type": target.object_type.name,
                            "properties": target.properties,
                            "link_properties": link.properties,
                            "depth": depth,
                        }
                    )
                    _traverse(str(target.id), depth + 1)

            if direction in ("incoming", "both"):
                for link in qs_in.select_related("source_object", "link_type"):
                    source = link.source_object
                    results.append(
                        {
                            "link_id": str(link.id),
                            "link_type": link.link_type.name,
                            "direction": "incoming",
                            "object_id": str(source.id),
                            "object_type": source.object_type.name,
                            "properties": source.properties,
                            "link_properties": link.properties,
                            "depth": depth,
                        }
                    )
                    _traverse(str(source.id), depth + 1)

        _traverse(object_id, 1)
        return results
