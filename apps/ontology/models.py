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


# ---------------------------------------------------------------------------
# 5.5 Interface Management (ONT-F-018)
# ---------------------------------------------------------------------------


class Interface(TenantModel, UUIDModel):
    """
    Polymorphic type abstraction. Describes the shape of object types.

    ONT-F-018: Interfaces provide object type polymorphism, allowing
    consistent modeling of object types that share a common shape.
    """

    name = models.CharField(
        max_length=255,
        help_text="Unique interface name within the namespace",
    )
    description = models.TextField(blank=True, default="")
    version = models.PositiveIntegerField(default=1)

    # Properties that implementing types must have
    required_properties = models.JSONField(
        default=list,
        blank=True,
        help_text='List of required property definitions: [{"name": "x", "type": "string"}, ...]',
    )
    optional_properties = models.JSONField(
        default=list,
        blank=True,
        help_text='List of optional property definitions: [{"name": "x", "type": "string"}, ...]',
    )

    # Which object types implement this interface
    implementing_types = models.ManyToManyField(
        ObjectType,
        blank=True,
        related_name="interfaces",
        help_text="Object types that implement this interface",
    )

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_interface"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_interface_name_active",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "name"], name="idx_iface_tenant_name"),
        ]

    def __str__(self) -> str:
        return f"Interface({self.name} v{self.version})"


# ---------------------------------------------------------------------------
# 5.6 Struct Type Management (ONT-F-020)
# ---------------------------------------------------------------------------


class StructType(TenantModel, UUIDModel):
    """
    Nested composite type for complex properties.

    ONT-F-020: Struct types allow properties to have nested structures
    (e.g. address with street, city, zip as sub-fields).
    """

    name = models.CharField(
        max_length=255,
        help_text="Unique struct type name",
    )
    description = models.TextField(blank=True, default="")
    version = models.PositiveIntegerField(default=1)

    fields = models.JSONField(
        default=list,
        help_text='List of fields: [{"name": "street", "type": "string", "required": true}, ...]',
    )

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_struct_type"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_struct_type_name_active",
            ),
        ]

    def __str__(self) -> str:
        return f"Struct({self.name} v{self.version})"


# ---------------------------------------------------------------------------
# 5.7 Shared Property Management (ONT-F-021)
# ---------------------------------------------------------------------------


class SharedProperty(TenantModel, UUIDModel):
    """
    Reusable property definition across multiple object types.

    ONT-F-021: Shared properties allow defining a property once and
    reusing it across multiple object types (e.g. "address", "created_by").
    """

    name = models.CharField(max_length=255, help_text="Unique shared property name")
    description = models.TextField(blank=True, default="")
    property_type = models.CharField(
        max_length=32,
        choices=PropertyType.choices,
        help_text="Data type",
    )
    default_value = models.JSONField(null=True, blank=True)
    validation_rules = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    # Which object types use this shared property
    used_by_types = models.ManyToManyField(
        ObjectType,
        blank=True,
        related_name="shared_properties",
        help_text="Object types that use this shared property",
    )

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_shared_property"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_shared_prop_name_active",
            ),
        ]

    def __str__(self) -> str:
        return f"SharedProp({self.name}: {self.property_type})"


# ---------------------------------------------------------------------------
# 5.8 Value Type Management (ONT-F-022)
# ---------------------------------------------------------------------------


class ValueType(TenantModel, UUIDModel):
    """
    Domain-specific value constraint with versioning.

    ONT-F-022: Value types define reusable domain constraints
    (e.g. "email" = string + regex, "percentage" = float + 0-100).
    """

    name = models.CharField(max_length=255, help_text="Unique value type name")
    description = models.TextField(blank=True, default="")
    base_type = models.CharField(
        max_length=32,
        choices=PropertyType.choices,
        help_text="Underlying property type",
    )
    version = models.PositiveIntegerField(default=1)

    constraints = models.JSONField(
        default=dict,
        help_text='Constraints: {"regex": "...", "min": 0, "max": 100, "enum_values": [...]}',
    )

    # Permissions
    created_by = models.CharField(max_length=256, blank=True)
    is_system = models.BooleanField(default=False, help_text="System value types cannot be deleted")

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_value_type"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_value_type_name_active",
            ),
        ]

    def __str__(self) -> str:
        return f"ValueType({self.name} v{self.version})"


# ---------------------------------------------------------------------------
# 5.9 Action Type Management (ONT-F-026)
# ---------------------------------------------------------------------------


class ActionType(TenantModel, UUIDModel):
    """
    Operation definition with parameters, rules, side effects, and undo.

    ONT-F-026: Action types define operations that can be performed on
    objects (e.g. "Approve Order", "Assign Driver", "Close Ticket").
    They include parameter schemas, validation rules, side effects,
    and undo logic.
    """

    STATUS_DRAFT = "draft"
    STATUS_ACTIVE = "active"
    STATUS_DEPRECATED = "deprecated"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_DEPRECATED, "Deprecated"),
    ]

    name = models.CharField(max_length=255, help_text="Unique action type name")
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    version = models.PositiveIntegerField(default=1)

    # Target object type (the object this action operates on)
    target_object_type = models.ForeignKey(
        ObjectType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="action_types",
        help_text="Object type this action operates on",
    )

    # Parameter schema
    parameters = models.JSONField(
        default=list,
        blank=True,
        help_text='Parameter definitions: [{"name": "reason", "type": "string", "required": true}, ...]',
    )

    # Validation rules (pre-conditions)
    rules = models.JSONField(
        default=list,
        blank=True,
        help_text='Pre-condition rules: [{"type": "status_check", "value": "open"}, ...]',
    )

    # Side effects (post-execution)
    side_effects = models.JSONField(
        default=list,
        blank=True,
        help_text='Side effects: [{"type": "notification", "channel": "email"}, {"type": "webhook", "url": "..."}]',
    )

    # Undo support
    undoable = models.BooleanField(default=False, help_text="Whether this action supports undo")
    undo_rules = models.JSONField(
        default=list,
        blank=True,
        help_text='Undo rules: [{"type": "status_revert"}, ...]',
    )

    # Permissions
    required_permission = models.CharField(
        max_length=256,
        blank=True,
        help_text="Permission required to execute this action",
    )

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_action_type"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_action_type_name_active",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="idx_action_tenant_status"),
            models.Index(fields=["target_object_type_id"], name="idx_action_target_type"),
        ]

    def __str__(self) -> str:
        return f"Action({self.name} v{self.version})"


# ---------------------------------------------------------------------------
# 5.10 Function Management (ONT-F-029)
# ---------------------------------------------------------------------------


class Function(TenantModel, UUIDModel):
    """
    Business logic attached to objects/actions.

    ONT-F-029: Functions provide a way to author and evolve business
    logic with arbitrary complexity. They can be attached to object
    types (computed properties, aggregations) or action types
    (validation, side effects).
    """

    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"
    STATUS_DEPRECATED = "deprecated"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
        (STATUS_DEPRECATED, "Deprecated"),
    ]

    LANGUAGE_PYTHON = "python"
    LANGUAGE_TYPESCRIPT = "typescript"
    LANGUAGE_CHOICES = [
        (LANGUAGE_PYTHON, "Python"),
        (LANGUAGE_TYPESCRIPT, "TypeScript"),
    ]

    name = models.CharField(max_length=255, help_text="Unique function name")
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        db_index=True,
    )
    version = models.PositiveIntegerField(default=1)
    language = models.CharField(
        max_length=20,
        choices=LANGUAGE_CHOICES,
        default=LANGUAGE_PYTHON,
    )

    # Source code
    source_code = models.TextField(help_text="Function source code")
    entry_point = models.CharField(
        max_length=255,
        default="handler",
        help_text="Entry point function name",
    )

    # Input/output schema
    input_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text='Input parameter schema: {"params": [{"name": "x", "type": "integer"}]}',
    )
    output_schema = models.JSONField(
        default=dict,
        blank=True,
        help_text='Output schema: {"type": "object", "properties": {...}}',
    )

    # Attachment
    attached_to_type = models.ForeignKey(
        ObjectType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="functions",
        help_text="Object type this function is attached to",
    )
    attached_to_action = models.ForeignKey(
        ActionType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="functions",
        help_text="Action type this function is attached to",
    )

    # Execution config
    timeout_seconds = models.IntegerField(default=30, help_text="Max execution time")
    memory_limit_mb = models.IntegerField(default=128, help_text="Max memory usage")

    # Permissions
    created_by = models.CharField(max_length=256, blank=True)

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "ontology_function"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant_id", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="uq_function_name_active",
            ),
        ]
        indexes = [
            models.Index(fields=["tenant_id", "status"], name="idx_func_tenant_status"),
            models.Index(fields=["attached_to_type_id"], name="idx_func_attached_type"),
            models.Index(fields=["attached_to_action_id"], name="idx_func_attached_action"),
        ]

    def __str__(self) -> str:
        return f"Function({self.name} v{self.version} [{self.language}])"


# Re-export ActionExecution so Django's migration framework discovers it.
from apps.ontology.action_executor import ActionExecution  # noqa: E402, F401
