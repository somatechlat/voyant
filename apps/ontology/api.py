"""Ontology API — Django Ninja REST endpoints for v4.0 ontology engine.

Covers: Object Types, Properties, Interfaces, StructTypes, SharedProperties,
ValueTypes, ActionTypes, Functions, Objects, Links, Traversal.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.ontology.models import (
    ActionType,
    Function,
    Interface,
    Link,
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
    properties: list[dict[str, Any]] = []


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


# ── Object Types: GET / PUT / DELETE ─────────────────────────────────────────


class UpdateObjectTypeIn(Schema):
    name: str | None = None
    description: str | None = None
    properties: list[dict[str, Any]] | None = None


@ontology_router.put("/types/{type_id}", auth=require_permission("write:ontology"))
def update_object_type(request, type_id: str, payload: UpdateObjectTypeIn):
    """Update an existing object type."""
    from apps.ontology.services import ObjectTypeService

    tenant_id = get_tenant_id(request)
    try:
        ot = ObjectTypeService.update(
            tenant_id,
            type_id,
            name=payload.name,
            description=payload.description,
            properties=payload.properties,
        )
        return {
            "id": str(ot.id),
            "name": ot.name,
            "description": ot.description,
            "version": ot.version,
            "tenant_id": ot.tenant_id,
        }
    except Exception as exc:
        raise HttpError(400, str(exc))


@ontology_router.delete("/types/{type_id}", auth=require_permission("write:ontology"))
def delete_object_type(request, type_id: str):
    """Soft-delete an object type."""
    from apps.ontology.services import ObjectTypeService

    tenant_id = get_tenant_id(request)
    try:
        ObjectTypeService.soft_delete(tenant_id, type_id)
        return {"status": "deleted", "id": type_id}
    except Exception as exc:
        raise HttpError(400, str(exc))


# ── Interfaces: GET(id) / PUT / DELETE ───────────────────────────────────────


class UpdateInterfaceIn(Schema):
    name: str | None = None
    description: str | None = None
    required_properties: list[dict] | None = None
    optional_properties: list[dict] | None = None


@ontology_router.get("/interfaces/{iface_id}")
def get_interface(request, iface_id: str):
    """Get a single interface by ID."""
    tenant_id = get_tenant_id(request)
    iface = Interface.objects.filter(
        tenant_id=tenant_id, id=iface_id, deleted_at__isnull=True
    ).first()
    if not iface:
        raise HttpError(404, "Interface not found")
    return {
        "id": str(iface.id),
        "name": iface.name,
        "description": iface.description,
        "version": iface.version,
        "required_properties": iface.required_properties,
        "optional_properties": iface.optional_properties,
        "implementing_types": [
            str(t.id) for t in iface.implementing_types.all()
        ],
        "tenant_id": iface.tenant_id,
        "created_at": iface.created_at.isoformat(),
    }


@ontology_router.put("/interfaces/{iface_id}", auth=require_permission("write:ontology"))
def update_interface(request, iface_id: str, payload: UpdateInterfaceIn):
    """Update an existing interface."""
    tenant_id = get_tenant_id(request)
    iface = Interface.objects.filter(
        tenant_id=tenant_id, id=iface_id, deleted_at__isnull=True
    ).first()
    if not iface:
        raise HttpError(404, "Interface not found")
    if payload.name is not None:
        iface.name = payload.name
    if payload.description is not None:
        iface.description = payload.description
    if payload.required_properties is not None:
        iface.required_properties = payload.required_properties
    if payload.optional_properties is not None:
        iface.optional_properties = payload.optional_properties
    iface.version += 1
    iface.save()
    return {
        "id": str(iface.id),
        "name": iface.name,
        "description": iface.description,
        "version": iface.version,
        "tenant_id": iface.tenant_id,
    }


@ontology_router.delete("/interfaces/{iface_id}", auth=require_permission("write:ontology"))
def delete_interface(request, iface_id: str):
    """Soft-delete an interface."""
    tenant_id = get_tenant_id(request)
    iface = Interface.objects.filter(
        tenant_id=tenant_id, id=iface_id, deleted_at__isnull=True
    ).first()
    if not iface:
        raise HttpError(404, "Interface not found")
    from django.utils import timezone
    iface.deleted_at = timezone.now()
    iface.save(update_fields=["deleted_at", "updated_at"])
    return {"status": "deleted", "id": iface_id}


# ── Struct Types: GET(id) / PUT / DELETE ─────────────────────────────────────


class UpdateStructTypeIn(Schema):
    name: str | None = None
    description: str | None = None
    fields: list[dict] | None = None


@ontology_router.get("/structs/{struct_id}")
def get_struct_type(request, struct_id: str):
    """Get a single struct type by ID."""
    tenant_id = get_tenant_id(request)
    st = StructType.objects.filter(
        tenant_id=tenant_id, id=struct_id, deleted_at__isnull=True
    ).first()
    if not st:
        raise HttpError(404, "Struct type not found")
    return {
        "id": str(st.id),
        "name": st.name,
        "description": st.description,
        "version": st.version,
        "fields": st.fields,
        "tenant_id": st.tenant_id,
        "created_at": st.created_at.isoformat(),
    }


@ontology_router.put("/structs/{struct_id}", auth=require_permission("write:ontology"))
def update_struct_type(request, struct_id: str, payload: UpdateStructTypeIn):
    """Update an existing struct type."""
    tenant_id = get_tenant_id(request)
    st = StructType.objects.filter(
        tenant_id=tenant_id, id=struct_id, deleted_at__isnull=True
    ).first()
    if not st:
        raise HttpError(404, "Struct type not found")
    if payload.name is not None:
        st.name = payload.name
    if payload.description is not None:
        st.description = payload.description
    if payload.fields is not None:
        st.fields = payload.fields
    st.version += 1
    st.save()
    return {
        "id": str(st.id),
        "name": st.name,
        "description": st.description,
        "version": st.version,
        "fields": st.fields,
        "tenant_id": st.tenant_id,
    }


@ontology_router.delete("/structs/{struct_id}", auth=require_permission("write:ontology"))
def delete_struct_type(request, struct_id: str):
    """Soft-delete a struct type."""
    tenant_id = get_tenant_id(request)
    st = StructType.objects.filter(
        tenant_id=tenant_id, id=struct_id, deleted_at__isnull=True
    ).first()
    if not st:
        raise HttpError(404, "Struct type not found")
    from django.utils import timezone
    st.deleted_at = timezone.now()
    st.save(update_fields=["deleted_at", "updated_at"])
    return {"status": "deleted", "id": struct_id}


# ── Shared Properties: GET(id) / PUT / DELETE ────────────────────────────────


class UpdateSharedPropertyIn(Schema):
    name: str | None = None
    property_type: str | None = None
    description: str | None = None
    default_value: Any = None
    validation_rules: Any = None


@ontology_router.get("/shared-properties/{prop_id}")
def get_shared_property(request, prop_id: str):
    """Get a single shared property by ID."""
    tenant_id = get_tenant_id(request)
    sp = SharedProperty.objects.filter(
        tenant_id=tenant_id, id=prop_id, deleted_at__isnull=True
    ).first()
    if not sp:
        raise HttpError(404, "Shared property not found")
    return {
        "id": str(sp.id),
        "name": sp.name,
        "property_type": sp.property_type,
        "description": sp.description,
        "default_value": sp.default_value,
        "validation_rules": sp.validation_rules,
        "used_by_types": [str(t.id) for t in sp.used_by_types.all()],
        "tenant_id": sp.tenant_id,
        "created_at": sp.created_at.isoformat(),
    }


@ontology_router.put("/shared-properties/{prop_id}", auth=require_permission("write:ontology"))
def update_shared_property(request, prop_id: str, payload: UpdateSharedPropertyIn):
    """Update an existing shared property."""
    tenant_id = get_tenant_id(request)
    sp = SharedProperty.objects.filter(
        tenant_id=tenant_id, id=prop_id, deleted_at__isnull=True
    ).first()
    if not sp:
        raise HttpError(404, "Shared property not found")
    if payload.name is not None:
        sp.name = payload.name
    if payload.property_type is not None:
        sp.property_type = payload.property_type
    if payload.description is not None:
        sp.description = payload.description
    if payload.default_value is not None:
        sp.default_value = payload.default_value
    if payload.validation_rules is not None:
        sp.validation_rules = payload.validation_rules
    sp.save()
    return {
        "id": str(sp.id),
        "name": sp.name,
        "property_type": sp.property_type,
        "description": sp.description,
        "tenant_id": sp.tenant_id,
    }


@ontology_router.delete("/shared-properties/{prop_id}", auth=require_permission("write:ontology"))
def delete_shared_property(request, prop_id: str):
    """Soft-delete a shared property."""
    tenant_id = get_tenant_id(request)
    sp = SharedProperty.objects.filter(
        tenant_id=tenant_id, id=prop_id, deleted_at__isnull=True
    ).first()
    if not sp:
        raise HttpError(404, "Shared property not found")
    from django.utils import timezone
    sp.deleted_at = timezone.now()
    sp.save(update_fields=["deleted_at", "updated_at"])
    return {"status": "deleted", "id": prop_id}


# ── Value Types: GET(id) / PUT / DELETE ──────────────────────────────────────


class UpdateValueTypeIn(Schema):
    name: str | None = None
    description: str | None = None
    base_type: str | None = None
    constraints: dict | None = None


@ontology_router.get("/value-types/{vt_id}")
def get_value_type(request, vt_id: str):
    """Get a single value type by ID."""
    tenant_id = get_tenant_id(request)
    vt = ValueType.objects.filter(
        tenant_id=tenant_id, id=vt_id, deleted_at__isnull=True
    ).first()
    if not vt:
        raise HttpError(404, "Value type not found")
    return {
        "id": str(vt.id),
        "name": vt.name,
        "base_type": vt.base_type,
        "version": vt.version,
        "constraints": vt.constraints,
        "is_system": vt.is_system,
        "tenant_id": vt.tenant_id,
        "created_at": vt.created_at.isoformat(),
    }


@ontology_router.put("/value-types/{vt_id}", auth=require_permission("write:ontology"))
def update_value_type(request, vt_id: str, payload: UpdateValueTypeIn):
    """Update an existing value type."""
    tenant_id = get_tenant_id(request)
    vt = ValueType.objects.filter(
        tenant_id=tenant_id, id=vt_id, deleted_at__isnull=True
    ).first()
    if not vt:
        raise HttpError(404, "Value type not found")
    if vt.is_system:
        raise HttpError(400, "Cannot modify system value types")
    if payload.name is not None:
        vt.name = payload.name
    if payload.description is not None:
        vt.description = payload.description
    if payload.base_type is not None:
        vt.base_type = payload.base_type
    if payload.constraints is not None:
        vt.constraints = payload.constraints
    vt.version += 1
    vt.save()
    return {
        "id": str(vt.id),
        "name": vt.name,
        "base_type": vt.base_type,
        "version": vt.version,
        "constraints": vt.constraints,
        "tenant_id": vt.tenant_id,
    }


@ontology_router.delete("/value-types/{vt_id}", auth=require_permission("write:ontology"))
def delete_value_type(request, vt_id: str):
    """Soft-delete a value type."""
    tenant_id = get_tenant_id(request)
    vt = ValueType.objects.filter(
        tenant_id=tenant_id, id=vt_id, deleted_at__isnull=True
    ).first()
    if not vt:
        raise HttpError(404, "Value type not found")
    if vt.is_system:
        raise HttpError(400, "Cannot delete system value types")
    from django.utils import timezone
    vt.deleted_at = timezone.now()
    vt.save(update_fields=["deleted_at", "updated_at"])
    return {"status": "deleted", "id": vt_id}


# ── Action Types: GET(id) / PUT / DELETE ─────────────────────────────────────


class UpdateActionTypeIn(Schema):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    target_object_type_id: str | None = None
    parameters: list[dict] | None = None
    rules: list[dict] | None = None
    side_effects: list[dict] | None = None
    undoable: bool | None = None
    required_permission: str | None = None


@ontology_router.get("/actions/{action_id}")
def get_action_type(request, action_id: str):
    """Get a single action type by ID."""
    tenant_id = get_tenant_id(request)
    at = ActionType.objects.filter(
        tenant_id=tenant_id, id=action_id, deleted_at__isnull=True
    ).first()
    if not at:
        raise HttpError(404, "Action type not found")
    return {
        "id": str(at.id),
        "name": at.name,
        "description": at.description,
        "status": at.status,
        "version": at.version,
        "target_object_type": str(at.target_object_type_id) if at.target_object_type_id else None,
        "parameters": at.parameters,
        "rules": at.rules,
        "side_effects": at.side_effects,
        "undoable": at.undoable,
        "undo_rules": at.undo_rules,
        "required_permission": at.required_permission,
        "tenant_id": at.tenant_id,
        "created_at": at.created_at.isoformat(),
    }


@ontology_router.put("/actions/{action_id}", auth=require_permission("write:ontology"))
def update_action_type(request, action_id: str, payload: UpdateActionTypeIn):
    """Update an existing action type."""
    tenant_id = get_tenant_id(request)
    at = ActionType.objects.filter(
        tenant_id=tenant_id, id=action_id, deleted_at__isnull=True
    ).first()
    if not at:
        raise HttpError(404, "Action type not found")
    if payload.name is not None:
        at.name = payload.name
    if payload.description is not None:
        at.description = payload.description
    if payload.status is not None:
        at.status = payload.status
    if payload.target_object_type_id is not None:
        ot = ObjectType.objects.filter(id=payload.target_object_type_id).first()
        if not ot:
            raise HttpError(404, "Target object type not found")
        at.target_object_type = ot
    if payload.parameters is not None:
        at.parameters = payload.parameters
    if payload.rules is not None:
        at.rules = payload.rules
    if payload.side_effects is not None:
        at.side_effects = payload.side_effects
    if payload.undoable is not None:
        at.undoable = payload.undoable
    if payload.required_permission is not None:
        at.required_permission = payload.required_permission
    at.version += 1
    at.save()
    return {
        "id": str(at.id),
        "name": at.name,
        "description": at.description,
        "status": at.status,
        "version": at.version,
        "tenant_id": at.tenant_id,
    }


@ontology_router.delete("/actions/{action_id}", auth=require_permission("write:ontology"))
def delete_action_type(request, action_id: str):
    """Soft-delete an action type."""
    tenant_id = get_tenant_id(request)
    at = ActionType.objects.filter(
        tenant_id=tenant_id, id=action_id, deleted_at__isnull=True
    ).first()
    if not at:
        raise HttpError(404, "Action type not found")
    from django.utils import timezone
    at.deleted_at = timezone.now()
    at.save(update_fields=["deleted_at", "updated_at"])
    return {"status": "deleted", "id": action_id}


# ── Functions: GET(id) / PUT / DELETE ────────────────────────────────────────


class UpdateFunctionIn(Schema):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    language: str | None = None
    source_code: str | None = None
    entry_point: str | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None
    attached_to_type_id: str | None = None
    attached_to_action_id: str | None = None
    timeout_seconds: int | None = None
    memory_limit_mb: int | None = None


@ontology_router.get("/functions/{func_id}")
def get_function(request, func_id: str):
    """Get a single function by ID."""
    tenant_id = get_tenant_id(request)
    fn = Function.objects.filter(
        tenant_id=tenant_id, id=func_id, deleted_at__isnull=True
    ).first()
    if not fn:
        raise HttpError(404, "Function not found")
    return {
        "id": str(fn.id),
        "name": fn.name,
        "description": fn.description,
        "status": fn.status,
        "version": fn.version,
        "language": fn.language,
        "source_code": fn.source_code,
        "entry_point": fn.entry_point,
        "input_schema": fn.input_schema,
        "output_schema": fn.output_schema,
        "attached_to_type": str(fn.attached_to_type_id) if fn.attached_to_type_id else None,
        "attached_to_action": str(fn.attached_to_action_id) if fn.attached_to_action_id else None,
        "timeout_seconds": fn.timeout_seconds,
        "memory_limit_mb": fn.memory_limit_mb,
        "tenant_id": fn.tenant_id,
        "created_at": fn.created_at.isoformat(),
    }


@ontology_router.put("/functions/{func_id}", auth=require_permission("write:ontology"))
def update_function(request, func_id: str, payload: UpdateFunctionIn):
    """Update an existing function."""
    tenant_id = get_tenant_id(request)
    fn = Function.objects.filter(
        tenant_id=tenant_id, id=func_id, deleted_at__isnull=True
    ).first()
    if not fn:
        raise HttpError(404, "Function not found")
    if payload.name is not None:
        fn.name = payload.name
    if payload.description is not None:
        fn.description = payload.description
    if payload.status is not None:
        fn.status = payload.status
    if payload.language is not None:
        fn.language = payload.language
    if payload.source_code is not None:
        fn.source_code = payload.source_code
    if payload.entry_point is not None:
        fn.entry_point = payload.entry_point
    if payload.input_schema is not None:
        fn.input_schema = payload.input_schema
    if payload.output_schema is not None:
        fn.output_schema = payload.output_schema
    if payload.attached_to_type_id is not None:
        fn.attached_to_type_id = payload.attached_to_type_id or None
    if payload.attached_to_action_id is not None:
        fn.attached_to_action_id = payload.attached_to_action_id or None
    if payload.timeout_seconds is not None:
        fn.timeout_seconds = payload.timeout_seconds
    if payload.memory_limit_mb is not None:
        fn.memory_limit_mb = payload.memory_limit_mb
    fn.version += 1
    fn.save()
    return {
        "id": str(fn.id),
        "name": fn.name,
        "description": fn.description,
        "status": fn.status,
        "version": fn.version,
        "language": fn.language,
        "tenant_id": fn.tenant_id,
    }


@ontology_router.delete("/functions/{func_id}", auth=require_permission("write:ontology"))
def delete_function(request, func_id: str):
    """Soft-delete a function."""
    tenant_id = get_tenant_id(request)
    fn = Function.objects.filter(
        tenant_id=tenant_id, id=func_id, deleted_at__isnull=True
    ).first()
    if not fn:
        raise HttpError(404, "Function not found")
    from django.utils import timezone
    fn.deleted_at = timezone.now()
    fn.save(update_fields=["deleted_at", "updated_at"])
    return {"status": "deleted", "id": func_id}


# ── Objects: CRUD + Batch + Upsert ───────────────────────────────────────────


class CreateObjectIn(Schema):
    object_type_id: str
    properties: dict[str, Any] = {}


class UpdateObjectIn(Schema):
    properties: dict[str, Any]
    version: int | None = None


class BatchCreateIn(Schema):
    object_type_id: str
    items: list[dict[str, Any]]


class UpsertIn(Schema):
    object_type_id: str
    key_property: str
    items: list[dict[str, Any]]


@ontology_router.get("/objects")
def list_objects(request, object_type_id: str | None = None, limit: int = 100):
    """List objects, optionally filtered by type."""
    from apps.ontology.services import ObjectService

    tenant_id = get_tenant_id(request)
    qs = ObjectService.list(tenant_id, object_type_id=object_type_id)[:limit]
    return [
        {
            "id": str(o.id),
            "object_type": str(o.object_type_id),
            "object_type_name": o.object_type.name,
            "properties": o.properties,
            "version": o.version,
            "tenant_id": o.tenant_id,
            "created_at": o.created_at.isoformat(),
        }
        for o in qs
    ]


@ontology_router.get("/objects/{object_id}")
def get_object(request, object_id: str):
    """Get a single object by ID."""
    from apps.ontology.services import ObjectService

    tenant_id = get_tenant_id(request)
    try:
        obj = ObjectService.get(tenant_id, object_id)
    except Exception:
        raise HttpError(404, "Object not found")
    return {
        "id": str(obj.id),
        "object_type": str(obj.object_type_id),
        "object_type_name": obj.object_type.name,
        "properties": obj.properties,
        "version": obj.version,
        "tenant_id": obj.tenant_id,
        "created_at": obj.created_at.isoformat(),
    }


@ontology_router.post("/objects", auth=require_permission("write:ontology"))
def create_object(request, payload: CreateObjectIn):
    """Create a new object instance."""
    from apps.ontology.services import ObjectService

    tenant_id = get_tenant_id(request)
    try:
        obj = ObjectService.create(tenant_id, payload.object_type_id, payload.properties)
        return {
            "id": str(obj.id),
            "object_type": str(obj.object_type_id),
            "properties": obj.properties,
            "version": obj.version,
            "tenant_id": obj.tenant_id,
        }
    except Exception as exc:
        raise HttpError(400, str(exc))


@ontology_router.put("/objects/{object_id}", auth=require_permission("write:ontology"))
def update_object(request, object_id: str, payload: UpdateObjectIn):
    """Update an existing object."""
    from apps.ontology.services import ObjectService

    tenant_id = get_tenant_id(request)
    try:
        obj = ObjectService.update(
            tenant_id, object_id, payload.properties, version=payload.version
        )
        return {
            "id": str(obj.id),
            "object_type": str(obj.object_type_id),
            "properties": obj.properties,
            "version": obj.version,
            "tenant_id": obj.tenant_id,
        }
    except Exception as exc:
        raise HttpError(400, str(exc))


@ontology_router.delete("/objects/{object_id}", auth=require_permission("write:ontology"))
def delete_object(request, object_id: str):
    """Soft-delete an object."""
    from apps.ontology.services import ObjectService

    tenant_id = get_tenant_id(request)
    try:
        ObjectService.soft_delete(tenant_id, object_id)
        return {"status": "deleted", "id": object_id}
    except Exception as exc:
        raise HttpError(400, str(exc))


@ontology_router.post("/objects/batch", auth=require_permission("write:ontology"))
def batch_create_objects(request, payload: BatchCreateIn):
    """Batch create 1000+ objects."""
    from apps.ontology.services import ObjectService

    tenant_id = get_tenant_id(request)
    try:
        objects = ObjectService.batch_create(tenant_id, payload.object_type_id, payload.items)
        return {
            "created": len(objects),
            "ids": [str(o.id) for o in objects],
        }
    except Exception as exc:
        raise HttpError(400, str(exc))


@ontology_router.post("/objects/upsert", auth=require_permission("write:ontology"))
def upsert_objects(request, payload: UpsertIn):
    """Upsert objects by unique key property."""
    from apps.ontology.services import ObjectService

    tenant_id = get_tenant_id(request)
    try:
        objects = ObjectService.upsert(
            tenant_id, payload.object_type_id, payload.key_property, payload.items
        )
        return {
            "processed": len(objects),
            "ids": [str(o.id) for o in objects],
        }
    except Exception as exc:
        raise HttpError(400, str(exc))


# ── Link Types: CRUD ─────────────────────────────────────────────────────────


class CreateLinkTypeIn(Schema):
    name: str
    source_object_type_id: str
    target_object_type_id: str
    cardinality: str = "one_to_many"
    description: str = ""
    properties_schema: dict | None = None
    inverse_name: str = ""


class UpdateLinkTypeIn(Schema):
    name: str | None = None
    description: str | None = None
    properties_schema: dict | None = None
    inverse_name: str | None = None


@ontology_router.get("/link-types")
def list_link_types(request):
    """List all link types."""
    from apps.ontology.services import LinkTypeService

    tenant_id = get_tenant_id(request)
    lts = LinkTypeService.list(tenant_id)
    return [
        {
            "id": str(lt.id),
            "name": lt.name,
            "description": lt.description,
            "source_object_type": str(lt.source_object_type_id),
            "source_object_type_name": lt.source_object_type.name,
            "target_object_type": str(lt.target_object_type_id),
            "target_object_type_name": lt.target_object_type.name,
            "cardinality": lt.cardinality,
            "properties_schema": lt.properties_schema,
            "inverse_name": lt.inverse_name,
            "instance_count": lt.instances.filter(deleted_at__isnull=True).count(),
            "tenant_id": lt.tenant_id,
        }
        for lt in lts
    ]


@ontology_router.get("/link-types/{lt_id}")
def get_link_type(request, lt_id: str):
    """Get a single link type by ID."""
    from apps.ontology.services import LinkTypeService

    tenant_id = get_tenant_id(request)
    try:
        lt = LinkTypeService.get(tenant_id, lt_id)
    except Exception:
        raise HttpError(404, "Link type not found")
    return {
        "id": str(lt.id),
        "name": lt.name,
        "description": lt.description,
        "source_object_type": str(lt.source_object_type_id),
        "target_object_type": str(lt.target_object_type_id),
        "cardinality": lt.cardinality,
        "properties_schema": lt.properties_schema,
        "inverse_name": lt.inverse_name,
        "tenant_id": lt.tenant_id,
        "created_at": lt.created_at.isoformat(),
    }


@ontology_router.post("/link-types", auth=require_permission("write:ontology"))
def create_link_type(request, payload: CreateLinkTypeIn):
    """Create a new link type."""
    from apps.ontology.services import LinkTypeService

    tenant_id = get_tenant_id(request)
    try:
        lt = LinkTypeService.create(
            tenant_id,
            name=payload.name,
            source_object_type_id=payload.source_object_type_id,
            target_object_type_id=payload.target_object_type_id,
            cardinality=payload.cardinality,
            description=payload.description,
            properties_schema=payload.properties_schema,
            inverse_name=payload.inverse_name,
        )
        return {
            "id": str(lt.id),
            "name": lt.name,
            "description": lt.description,
            "cardinality": lt.cardinality,
            "tenant_id": lt.tenant_id,
        }
    except Exception as exc:
        raise HttpError(400, str(exc))


@ontology_router.put("/link-types/{lt_id}", auth=require_permission("write:ontology"))
def update_link_type(request, lt_id: str, payload: UpdateLinkTypeIn):
    """Update an existing link type."""
    from apps.ontology.services import LinkTypeService

    tenant_id = get_tenant_id(request)
    try:
        lt = LinkTypeService.get(tenant_id, lt_id)
    except Exception:
        raise HttpError(404, "Link type not found")
    if payload.name is not None:
        lt.name = payload.name
    if payload.description is not None:
        lt.description = payload.description
    if payload.properties_schema is not None:
        lt.properties_schema = payload.properties_schema
    if payload.inverse_name is not None:
        lt.inverse_name = payload.inverse_name
    lt.save()
    return {
        "id": str(lt.id),
        "name": lt.name,
        "description": lt.description,
        "cardinality": lt.cardinality,
        "tenant_id": lt.tenant_id,
    }


@ontology_router.delete("/link-types/{lt_id}", auth=require_permission("write:ontology"))
def delete_link_type(request, lt_id: str):
    """Soft-delete a link type."""
    from apps.ontology.services import LinkTypeService

    tenant_id = get_tenant_id(request)
    try:
        LinkTypeService.soft_delete(tenant_id, lt_id)
        return {"status": "deleted", "id": lt_id}
    except Exception as exc:
        raise HttpError(400, str(exc))


# ── Links: Create / List / Delete / Traverse ─────────────────────────────────


class CreateLinkIn(Schema):
    link_type_id: str
    source_object_id: str
    target_object_id: str
    properties: dict[str, Any] = {}


class TraverseIn(Schema):
    link_type_name: str | None = None
    direction: str = "outgoing"
    max_depth: int = 1


@ontology_router.get("/links")
def list_links(request, link_type_id: str | None = None, limit: int = 100):
    """List link instances."""
    tenant_id = get_tenant_id(request)
    qs = Link.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
    if link_type_id:
        qs = qs.filter(link_type_id=link_type_id)
    qs = qs.select_related("link_type", "source_object", "target_object")[:limit]
    return [
        {
            "id": str(lk.id),
            "link_type": str(lk.link_type_id),
            "link_type_name": lk.link_type.name,
            "source_object": str(lk.source_object_id),
            "target_object": str(lk.target_object_id),
            "properties": lk.properties,
            "tenant_id": lk.tenant_id,
        }
        for lk in qs
    ]


@ontology_router.post("/links", auth=require_permission("write:ontology"))
def create_link(request, payload: CreateLinkIn):
    """Create a new link instance."""
    from apps.ontology.services import LinkService

    tenant_id = get_tenant_id(request)
    try:
        link = LinkService.create(
            tenant_id,
            link_type_id=payload.link_type_id,
            source_object_id=payload.source_object_id,
            target_object_id=payload.target_object_id,
            properties=payload.properties,
        )
        return {
            "id": str(link.id),
            "link_type": str(link.link_type_id),
            "source_object": str(link.source_object_id),
            "target_object": str(link.target_object_id),
            "properties": link.properties,
            "tenant_id": link.tenant_id,
        }
    except Exception as exc:
        raise HttpError(400, str(exc))


@ontology_router.delete("/links/{link_id}", auth=require_permission("write:ontology"))
def delete_link(request, link_id: str):
    """Soft-delete a link."""
    from apps.ontology.services import LinkService

    tenant_id = get_tenant_id(request)
    try:
        LinkService.delete(tenant_id, link_id)
        return {"status": "deleted", "id": link_id}
    except Exception as exc:
        raise HttpError(400, str(exc))


# ── Traversal ────────────────────────────────────────────────────────────────


@ontology_router.post("/objects/{object_id}/traverse")
def traverse_object(request, object_id: str, payload: TraverseIn):
    """Traverse links from an object (multi-hop)."""
    from apps.ontology.services import LinkService

    tenant_id = get_tenant_id(request)
    try:
        results = LinkService.traverse(
            tenant_id,
            object_id,
            link_type_name=payload.link_type_name,
            direction=payload.direction,
            max_depth=min(payload.max_depth, 10),
        )
        return {"object_id": object_id, "results": results, "count": len(results)}
    except Exception as exc:
        raise HttpError(400, str(exc))
