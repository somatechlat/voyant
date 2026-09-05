"""Ontology API — Django Ninja REST endpoints for v4.0 ontology engine.

Covers: Object Types, Properties, Interfaces, StructTypes, SharedProperties,
ValueTypes, ActionTypes, Functions, Objects, Links, Traversal.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Field, Router, Schema
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.ontology.models import (
    ActionType,
    Function,
    Interface,
    Object,
    ObjectType,
    Property,
    SharedProperty,
    StructType,
    ValueType,
)

logger = logging.getLogger(__name__)

ontology_router = Router(tags=["ontology"], auth=require_permission("read:*"))

# ── Schemas ──────────────────────────────────────────────────────────────────


class ObjectTypeOut(Schema):
    id: str
    name: str
    description: str
    version: int
    property_count: int = 0
    instance_count: int = 0
    tenant_id: str
    created_at: str


class PropertyOut(Schema):
    id: str
    name: str
    property_type: str
    required: bool
    default_value: Any = None
    validation_rules: Any = None
    metadata: dict[str, Any] = {}


class InterfaceOut(Schema):
    id: str
    name: str
    description: str
    version: int
    required_properties: list[dict] = []
    optional_properties: list[dict] = []
    implementing_count: int = 0
    tenant_id: str


class StructTypeOut(Schema):
    id: str
    name: str
    description: str
    version: int
    fields: list[dict] = []
    tenant_id: str


class SharedPropertyOut(Schema):
    id: str
    name: str
    property_type: str
    description: str
    used_by_count: int = 0
    tenant_id: str


class ValueTypeOut(Schema):
    id: str
    name: str
    base_type: str
    version: int
    constraints: dict = {}
    is_system: bool = False
    tenant_id: str


class ActionTypeOut(Schema):
    id: str
    name: str
    description: str
    status: str
    version: int
    target_object_type: str | None = None
    parameters: list[dict] = []
    rules: list[dict] = []
    side_effects: list[dict] = []
    undoable: bool = False
    tenant_id: str


class FunctionOut(Schema):
    id: str
    name: str
    description: str
    status: str
    version: int
    language: str
    entry_point: str
    attached_to_type: str | None = None
    attached_to_action: str | None = None
    tenant_id: str


class ObjectOut(Schema):
    id: str
    object_type: str
    properties: dict[str, Any] = {}
    version: int
    tenant_id: str


class LinkOut(Schema):
    id: str
    link_type: str
    source_object: str
    target_object: str
    properties: dict[str, Any] = {}
    tenant_id: str


class CreateObjectTypeIn(Schema):
    name: str
    description: str = ""


class CreateInterfaceIn(Schema):
    name: str
    description: str = ""
    required_properties: list[dict] = []
    optional_properties: list[dict] = []


class CreateStructTypeIn(Schema):
    name: str
    description: str = ""
    fields: list[dict] = []


class CreateSharedPropertyIn(Schema):
    name: str
    property_type: str
    description: str = ""
    default_value: Any = None
    validation_rules: Any = None


class CreateValueTypeIn(Schema):
    name: str
    base_type: str
    description: str = ""
    constraints: dict = {}


class CreateActionTypeIn(Schema):
    name: str
    description: str = ""
    target_object_type_id: str | None = None
    parameters: list[dict] = []
    rules: list[dict] = []
    side_effects: list[dict] = []
    undoable: bool = False
    required_permission: str = ""


class CreateFunctionIn(Schema):
    name: str
    description: str = ""
    language: str = "python"
    source_code: str = ""
    entry_point: str = "handler"
    input_schema: dict = {}
    output_schema: dict = {}
    attached_to_type_id: str | None = None
    attached_to_action_id: str | None = None
    timeout_seconds: int = 30
    memory_limit_mb: int = 128


# ── Object Types ─────────────────────────────────────────────────────────────


@ontology_router.get("/types", response=list[ObjectTypeOut])
def list_object_types(request, include_deleted: bool = False):
    """List all object types for the current tenant."""
    from apps.ontology.services import ObjectTypeService

    tenant_id = get_tenant_id(request)
    types = ObjectTypeService.list(tenant_id, include_deleted=include_deleted)
    result = []
    for ot in types:
        prop_count = Property.objects.filter(object_type=ot).count()
        instance_count = Object.objects.filter(object_type=ot, deleted_at__isnull=True).count()
        result.append(ObjectTypeOut(
            id=str(ot.id),
            name=ot.name,
            description=ot.description,
            version=ot.version,
            property_count=prop_count,
            instance_count=instance_count,
            tenant_id=ot.tenant_id,
            created_at=ot.created_at.isoformat(),
        ))
    return result


@ontology_router.post("/types", response=ObjectTypeOut, auth=require_permission("write:ontology"))
def create_object_type(request, payload: CreateObjectTypeIn):
    """Create a new object type."""
    from apps.ontology.services import ObjectTypeService

    tenant_id = get_tenant_id(request)
    try:
        ot = ObjectTypeService.create(tenant_id, payload.name, payload.description)
        return ObjectTypeOut(
            id=str(ot.id),
            name=ot.name,
            description=ot.description,
            version=ot.version,
            property_count=0,
            instance_count=0,
            tenant_id=ot.tenant_id,
            created_at=ot.created_at.isoformat(),
        )
    except Exception as exc:
        raise HttpError(400, str(exc))


@ontology_router.get("/types/{type_id}")
def get_object_type(request, type_id: str):
    """Get object type with its properties."""
    from apps.ontology.services import ObjectTypeService

    tenant_id = get_tenant_id(request)
    try:
        ot = ObjectTypeService.get(tenant_id, type_id)
    except Exception:
        raise HttpError(404, "Object type not found")

    props = Property.objects.filter(object_type=ot)
    return {
        "id": str(ot.id),
        "name": ot.name,
        "description": ot.description,
        "version": ot.version,
        "tenant_id": ot.tenant_id,
        "properties": [
            {
                "id": str(p.id),
                "name": p.name,
                "property_type": p.property_type,
                "required": p.required,
                "default_value": p.default_value,
                "validation_rules": p.validation_rules,
            }
            for p in props
        ],
    }


# ── Interfaces ───────────────────────────────────────────────────────────────


@ontology_router.get("/interfaces", response=list[InterfaceOut])
def list_interfaces(request):
    """List all interfaces."""
    tenant_id = get_tenant_id(request)
    ifaces = Interface.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
    return [
        InterfaceOut(
            id=str(i.id),
            name=i.name,
            description=i.description,
            version=i.version,
            required_properties=i.required_properties,
            optional_properties=i.optional_properties,
            implementing_count=i.implementing_types.count(),
            tenant_id=i.tenant_id,
        )
        for i in ifaces
    ]


@ontology_router.post("/interfaces", response=InterfaceOut, auth=require_permission("write:ontology"))
def create_interface(request, payload: CreateInterfaceIn):
    """Create a new interface."""
    tenant_id = get_tenant_id(request)
    iface = Interface.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        required_properties=payload.required_properties,
        optional_properties=payload.optional_properties,
    )
    return InterfaceOut(
        id=str(iface.id),
        name=iface.name,
        description=iface.description,
        version=iface.version,
        required_properties=iface.required_properties,
        optional_properties=iface.optional_properties,
        tenant_id=iface.tenant_id,
    )


# ── Struct Types ─────────────────────────────────────────────────────────────


@ontology_router.get("/structs", response=list[StructTypeOut])
def list_struct_types(request):
    """List all struct types."""
    tenant_id = get_tenant_id(request)
    structs = StructType.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
    return [
        StructTypeOut(
            id=str(s.id),
            name=s.name,
            description=s.description,
            version=s.version,
            fields=s.fields,
            tenant_id=s.tenant_id,
        )
        for s in structs
    ]


@ontology_router.post("/structs", response=StructTypeOut, auth=require_permission("write:ontology"))
def create_struct_type(request, payload: CreateStructTypeIn):
    """Create a new struct type."""
    tenant_id = get_tenant_id(request)
    struct = StructType.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        fields=payload.fields,
    )
    return StructTypeOut(
        id=str(struct.id),
        name=struct.name,
        description=struct.description,
        version=struct.version,
        fields=struct.fields,
        tenant_id=struct.tenant_id,
    )


# ── Shared Properties ────────────────────────────────────────────────────────


@ontology_router.get("/shared-properties", response=list[SharedPropertyOut])
def list_shared_properties(request):
    """List all shared properties."""
    tenant_id = get_tenant_id(request)
    props = SharedProperty.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
    return [
        SharedPropertyOut(
            id=str(p.id),
            name=p.name,
            property_type=p.property_type,
            description=p.description,
            used_by_count=p.used_by_types.count(),
            tenant_id=p.tenant_id,
        )
        for p in props
    ]


@ontology_router.post("/shared-properties", response=SharedPropertyOut, auth=require_permission("write:ontology"))
def create_shared_property(request, payload: CreateSharedPropertyIn):
    """Create a new shared property."""
    tenant_id = get_tenant_id(request)
    prop = SharedProperty.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        property_type=payload.property_type,
        description=payload.description,
        default_value=payload.default_value,
        validation_rules=payload.validation_rules,
    )
    return SharedPropertyOut(
        id=str(prop.id),
        name=prop.name,
        property_type=prop.property_type,
        description=prop.description,
        tenant_id=prop.tenant_id,
    )


# ── Value Types ──────────────────────────────────────────────────────────────


@ontology_router.get("/value-types", response=list[ValueTypeOut])
def list_value_types(request):
    """List all value types."""
    tenant_id = get_tenant_id(request)
    vts = ValueType.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
    return [
        ValueTypeOut(
            id=str(v.id),
            name=v.name,
            base_type=v.base_type,
            version=v.version,
            constraints=v.constraints,
            is_system=v.is_system,
            tenant_id=v.tenant_id,
        )
        for v in vts
    ]


@ontology_router.post("/value-types", response=ValueTypeOut, auth=require_permission("write:ontology"))
def create_value_type(request, payload: CreateValueTypeIn):
    """Create a new value type."""
    tenant_id = get_tenant_id(request)
    vt = ValueType.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        base_type=payload.base_type,
        description=payload.description,
        constraints=payload.constraints,
    )
    return ValueTypeOut(
        id=str(vt.id),
        name=vt.name,
        base_type=vt.base_type,
        version=vt.version,
        constraints=vt.constraints,
        tenant_id=vt.tenant_id,
    )


# ── Action Types ─────────────────────────────────────────────────────────────


@ontology_router.get("/actions", response=list[ActionTypeOut])
def list_action_types(request, status: str | None = None):
    """List all action types."""
    tenant_id = get_tenant_id(request)
    qs = ActionType.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
    if status:
        qs = qs.filter(status=status)
    return [
        ActionTypeOut(
            id=str(a.id),
            name=a.name,
            description=a.description,
            status=a.status,
            version=a.version,
            target_object_type=str(a.target_object_type_id) if a.target_object_type_id else None,
            parameters=a.parameters,
            rules=a.rules,
            side_effects=a.side_effects,
            undoable=a.undoable,
            tenant_id=a.tenant_id,
        )
        for a in qs
    ]


@ontology_router.post("/actions", response=ActionTypeOut, auth=require_permission("write:ontology"))
def create_action_type(request, payload: CreateActionTypeIn):
    """Create a new action type."""
    tenant_id = get_tenant_id(request)
    target_ot = None
    if payload.target_object_type_id:
        target_ot = ObjectType.objects.filter(id=payload.target_object_type_id).first()
        if not target_ot:
            raise HttpError(404, "Target object type not found")

    action = ActionType.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        target_object_type=target_ot,
        parameters=payload.parameters,
        rules=payload.rules,
        side_effects=payload.side_effects,
        undoable=payload.undoable,
        required_permission=payload.required_permission,
    )
    return ActionTypeOut(
        id=str(action.id),
        name=action.name,
        description=action.description,
        status=action.status,
        version=action.version,
        target_object_type=str(action.target_object_type_id) if action.target_object_type_id else None,
        parameters=action.parameters,
        rules=action.rules,
        side_effects=action.side_effects,
        undoable=action.undoable,
        tenant_id=action.tenant_id,
    )


# ── Functions ────────────────────────────────────────────────────────────────


@ontology_router.get("/functions", response=list[FunctionOut])
def list_functions(request, status: str | None = None):
    """List all functions."""
    tenant_id = get_tenant_id(request)
    qs = Function.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
    if status:
        qs = qs.filter(status=status)
    return [
        FunctionOut(
            id=str(f.id),
            name=f.name,
            description=f.description,
            status=f.status,
            version=f.version,
            language=f.language,
            entry_point=f.entry_point,
            attached_to_type=str(f.attached_to_type_id) if f.attached_to_type_id else None,
            attached_to_action=str(f.attached_to_action_id) if f.attached_to_action_id else None,
            tenant_id=f.tenant_id,
        )
        for f in qs
    ]


@ontology_router.post("/functions", response=FunctionOut, auth=require_permission("write:ontology"))
def create_function(request, payload: CreateFunctionIn):
    """Create a new function."""
    tenant_id = get_tenant_id(request)
    func = Function.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        language=payload.language,
        source_code=payload.source_code,
        entry_point=payload.entry_point,
        input_schema=payload.input_schema,
        output_schema=payload.output_schema,
        attached_to_type_id=payload.attached_to_type_id,
        attached_to_action_id=payload.attached_to_action_id,
        timeout_seconds=payload.timeout_seconds,
        memory_limit_mb=payload.memory_limit_mb,
    )
    return FunctionOut(
        id=str(func.id),
        name=func.name,
        description=func.description,
        status=func.status,
        version=func.version,
        language=func.language,
        entry_point=func.entry_point,
        attached_to_type=str(func.attached_to_type_id) if func.attached_to_type_id else None,
        attached_to_action=str(func.attached_to_action_id) if func.attached_to_action_id else None,
        tenant_id=func.tenant_id,
    )
