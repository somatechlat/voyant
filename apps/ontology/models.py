"""
Ontology Engine — Django ORM models.

Covers SRS §5.1–5.4: Object Types, Properties, Object Instances,
Link Types, and Link Instances.

All models inherit TenantModel for multi-tenancy and UUIDModel for
consistent primary keys, following the enterprise patterns established
in apps/core/models.py.
"""

from __future__ import annotations

from django.db import models

from apps.core.models import TenantModel, UUIDModel

# ---------------------------------------------------------------------------
# 5.1 Object Type Management
# ---------------------------------------------------------------------------


class ObjectType(TenantModel, UUIDModel):
    """
    Schema definition for a class of entities (e.g. Customer, Sensor).

    ONT-F-001: name + description + property definitions
    ONT-F-008: version field for automatic schema versioning
    """

    name = models.CharField(
        max_length=255,
        help_text="Unique name for this object type within the namespace",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Human-readable description",
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Auto-incrementing schema version",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Soft-deletion timestamp (null = active)",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_object_type"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_object_type_name_active",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "name"], name="idx_ot_tenant_name"),
        ]

    def __str__(self) -> str:
        return f"{self.name} (v{self.version})"


class PropertyType(models.TextChoices):
    """ONT-F-002: Supported property types."""

    STRING = "string", "String"
    INTEGER = "integer", "Integer"
    FLOAT = "float", "Float"
    BOOLEAN = "boolean", "Boolean"
    DATE = "date", "Date"
    TIMESTAMP = "timestamp", "Timestamp"
    ENUM = "enum", "Enum"
    ARRAY = "array", "Array"
    MAP = "map", "Map"
    STRUCT = "struct", "Struct"
    GEOPOINT = "geopoint", "Geopoint"


class Property(TenantModel, UUIDModel):
    """
    A named, typed attribute on an object type.

    ONT-F-002: property_type enum
    ONT-F-003: required flag
    ONT-F-004: default_value
    ONT-F-005: validation_rules (JSONB)
    """

    object_type = models.ForeignKey(
        ObjectType,
        on_delete=models.CASCADE,
        related_name="properties",
        help_text="Parent object type",
    )
    name = models.CharField(
        max_length=255,
        help_text="Property name (unique per object type)",
    )
    property_type = models.CharField(
        max_length=32,
        choices=PropertyType.choices,
        help_text="Data type of this property",
    )
    required = models.BooleanField(
        default=False,
        help_text="Whether this property is required on instances",
    )
    default_value = models.JSONField(
        null=True,
        blank=True,
        help_text="Default value (JSON-encoded)",
    )
    validation_rules = models.JSONField(
        null=True,
        blank=True,
        help_text="Validation rules: regex, min, max, enum_values, custom",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Arbitrary metadata (display_name, description, etc.)",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_property"
        constraints = [
            models.UniqueConstraint(
                fields=["object_type_id", "name"],
                name="uq_property_name_per_type",
            ),
        ]
        indexes = [
            models.Index(fields=["object_type_id"], name="idx_prop_object_type"),
        ]

    def __str__(self) -> str:
        return f"{self.object_type.name}.{self.name} ({self.property_type})"


# ---------------------------------------------------------------------------
# 5.2 Object Instance Management
# ---------------------------------------------------------------------------


class Object(TenantModel, UUIDModel):
    """
    A specific occurrence of an object type (e.g. Customer #4521).

    ONT-F-010 to ONT-F-017: CRUD, batch, upsert, timestamps, soft-delete,
    optimistic concurrency (version field).
    """

    object_type = models.ForeignKey(
        ObjectType,
        on_delete=models.PROTECT,
        related_name="instances",
        help_text="Schema this instance conforms to",
    )
    properties = models.JSONField(
        default=dict,
        help_text="Key-value properties conforming to the object type schema",
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="Optimistic concurrency version",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Soft-deletion timestamp (null = active)",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_object"
        indexes = [
            models.Index(fields=["object_type_id"], name="idx_obj_type"),
            models.Index(fields=["tenant_id", "object_type_id"], name="idx_obj_tenant_type"),
            models.Index(
                fields=["tenant_id", "-created_at"],
                name="idx_obj_tenant_created",
            ),
        ]

    def __str__(self) -> str:
        label = self.properties.get("name") or self.properties.get("title") or str(self.id)[:8]
        return f"{self.object_type.name}:{label}"


# ---------------------------------------------------------------------------
# 5.3 Link Type Management
# ---------------------------------------------------------------------------


class Cardinality(models.TextChoices):
    """ONT-F-021: Supported cardinality modes."""

    ONE_TO_ONE = "one_to_one", "One-to-One"
    ONE_TO_MANY = "one_to_many", "One-to-Many"
    MANY_TO_MANY = "many_to_many", "Many-to-Many"


class LinkType(TenantModel, UUIDModel):
    """
    Schema definition for a relationship between two object types.

    ONT-F-020: source_type + target_type
    ONT-F-021: cardinality
    ONT-F-022: properties (JSONB schema for link properties)
    """

    name = models.CharField(
        max_length=255,
        help_text="Unique link type name within the namespace",
    )
    description = models.TextField(
        blank=True,
        default="",
    )
    source_object_type = models.ForeignKey(
        ObjectType,
        on_delete=models.PROTECT,
        related_name="outgoing_link_types",
        help_text="Source object type",
    )
    target_object_type = models.ForeignKey(
        ObjectType,
        on_delete=models.PROTECT,
        related_name="incoming_link_types",
        help_text="Target object type",
    )
    cardinality = models.CharField(
        max_length=20,
        choices=Cardinality.choices,
        default=Cardinality.ONE_TO_MANY,
        help_text="Cardinality of the relationship",
    )
    properties_schema = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON schema for optional properties on link instances",
    )
    inverse_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional name for the inverse traversal direction",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Soft-deletion timestamp (null = active)",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_link_type"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_link_type_name_active",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "name"], name="idx_lt_tenant_name"),
            models.Index(fields=["source_object_type_id"], name="idx_lt_source"),
            models.Index(fields=["target_object_type_id"], name="idx_lt_target"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.source_object_type.name} → {self.target_object_type.name})"


# ---------------------------------------------------------------------------
# 5.4 Link Instance Management
# ---------------------------------------------------------------------------


class Link(TenantModel, UUIDModel):
    """
    A specific occurrence of a link type connecting two object instances.

    ONT-F-030: create link instances
    ONT-F-031/032: traversal supported via service layer
    """

    link_type = models.ForeignKey(
        LinkType,
        on_delete=models.PROTECT,
        related_name="instances",
        help_text="Schema this link conforms to",
    )
    source_object = models.ForeignKey(
        Object,
        on_delete=models.CASCADE,
        related_name="outgoing_links",
        help_text="Source object instance",
    )
    target_object = models.ForeignKey(
        Object,
        on_delete=models.CASCADE,
        related_name="incoming_links",
        help_text="Target object instance",
    )
    properties = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional properties on this link instance",
    )
    deleted_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Soft-deletion timestamp (null = active)",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_link"
        constraints = [
            models.UniqueConstraint(
                fields=["link_type_id", "source_object_id", "target_object_id"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_link_instance_active",
            ),
        ]
        indexes = [
            models.Index(fields=["link_type_id"], name="idx_link_type"),
            models.Index(fields=["source_object_id"], name="idx_link_source"),
            models.Index(fields=["target_object_id"], name="idx_link_target"),
            models.Index(
                fields=["tenant_id", "link_type_id"],
                name="idx_link_tenant_type",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.link_type.name}: {self.source_object_id} → {self.target_object_id}"  # type: ignore[attr-defined]
