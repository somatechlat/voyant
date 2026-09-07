"""
Voyant MCP — ontology engine tools (15 tools).

Covers: Object Types, Interfaces, StructTypes, SharedProperties,
ValueTypes, ActionTypes, Functions, Objects, Links, Traversal.
"""

import logging

from django_mcp import mcp_app

from apps.core.config import get_settings
from apps.mcp.tools_core import _tenant
from apps.ontology.models import (
    Interface,
    ObjectType,
    Property,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Object Types ─────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.types.list")
def tool_ontology_types_list(tenant_id=None):
    """List all object types with property and instance counts."""
    tid = _tenant(tenant_id)
    types = ObjectType.objects.filter(tenant_id=tid, deleted_at__isnull=True).order_by("name")
    return [
        {
            "id": str(ot.id),
            "name": ot.name,
            "description": ot.description,
            "version": ot.version,
            "property_count": ot.properties.count(),
            "instance_count": ot.instances.filter(deleted_at__isnull=True).count(),
        }
        for ot in types
    ]


@mcp_app.tool(name="voyant.ontology.types.get")
def tool_ontology_types_get(type_id: str, tenant_id=None):
    """Get an object type with its full property definitions."""
    tid = _tenant(tenant_id)
    ot = ObjectType.objects.filter(
        tenant_id=tid, id=type_id, deleted_at__isnull=True
    ).first()
    if not ot:
        return {"error": "Object type not found"}
    props = Property.objects.filter(object_type=ot)
    return {
        "id": str(ot.id),
        "name": ot.name,
        "description": ot.description,
        "version": ot.version,
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


@mcp_app.tool(name="voyant.ontology.types.create")
def tool_ontology_types_create(name: str, description: str = "", properties=None, tenant_id=None):
    """Create a new object type with optional property definitions."""
    from apps.ontology.services import ObjectTypeService

    tid = _tenant(tenant_id)
    ot = ObjectTypeService.create(
        tid, name=name, description=description, properties=properties or []
    )
    return {"id": str(ot.id), "name": ot.name, "version": ot.version}


# ── Objects ──────────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.objects.list")
def tool_ontology_objects_list(type_id: str = "", limit: int = 100, tenant_id=None):
    """List object instances, optionally filtered by type."""
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    qs = ObjectService.list(tid, object_type_id=type_id or None)[:limit]
    return [
        {
            "id": str(o.id),
            "object_type": o.object_type.name,
            "properties": o.properties,
            "version": o.version,
        }
        for o in qs
    ]


@mcp_app.tool(name="voyant.ontology.objects.create")
def tool_ontology_objects_create(type_id: str, properties: dict, tenant_id=None):
    """Create a new object instance with schema validation."""
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    obj = ObjectService.create(tid, type_id, properties)
    return {
        "id": str(obj.id),
        "object_type": obj.object_type.name,
        "properties": obj.properties,
        "version": obj.version,
    }


@mcp_app.tool(name="voyant.ontology.objects.get")
def tool_ontology_objects_get(object_id: str, tenant_id=None):
    """Get an object instance with its properties and type info."""
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    try:
        obj = ObjectService.get(tid, object_id)
    except Exception:
        return {"error": "Object not found"}
    return {
        "id": str(obj.id),
        "object_type": obj.object_type.name,
        "properties": obj.properties,
        "version": obj.version,
        "created_at": obj.created_at.isoformat(),
    }


@mcp_app.tool(name="voyant.ontology.objects.update")
def tool_ontology_objects_update(object_id: str, properties: dict, version: int = None, tenant_id=None):
    """Update an object instance with optimistic concurrency."""
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    obj = ObjectService.update(tid, object_id, properties, version=version)
    return {
        "id": str(obj.id),
        "properties": obj.properties,
        "version": obj.version,
    }


@mcp_app.tool(name="voyant.ontology.objects.batch_create")
def tool_ontology_objects_batch(type_id: str, items: list, tenant_id=None):
    """Batch create 1000+ object instances."""
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    objects = ObjectService.batch_create(tid, type_id, items)
    return {"created": len(objects), "ids": [str(o.id) for o in objects]}


# ── Links ────────────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.links.create")
def tool_ontology_links_create(
    link_type_id: str,
    source_object_id: str,
    target_object_id: str,
    properties: dict = None,
    tenant_id=None,
):
    """Create a link between two objects."""
    from apps.ontology.services import LinkService

    tid = _tenant(tenant_id)
    link = LinkService.create(
        tid, link_type_id, source_object_id, target_object_id, properties
    )
    return {
        "id": str(link.id),
        "link_type": link.link_type.name,
        "source": str(link.source_object_id),
        "target": str(link.target_object_id),
    }


@mcp_app.tool(name="voyant.ontology.links.delete")
def tool_ontology_links_delete(link_id: str, tenant_id=None):
    """Delete a link between two objects."""
    from apps.ontology.services import LinkService

    tid = _tenant(tenant_id)
    LinkService.delete(tid, link_id)
    return {"status": "deleted", "id": link_id}


# ── Traversal ────────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.traverse")
def tool_ontology_traverse(
    object_id: str,
    direction: str = "outgoing",
    max_depth: int = 1,
    link_type_name: str = "",
    tenant_id=None,
):
    """Traverse links from an object up to 10 hops."""
    from apps.ontology.services import LinkService

    tid = _tenant(tenant_id)
    results = LinkService.traverse(
        tid,
        object_id,
        link_type_name=link_type_name or None,
        direction=direction,
        max_depth=min(max_depth, 10),
    )
    return {"object_id": object_id, "results": results, "count": len(results)}


# ── Interfaces ───────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.interfaces.list")
def tool_ontology_interfaces_list(tenant_id=None):
    """List all interfaces (polymorphic type abstractions)."""
    tid = _tenant(tenant_id)
    ifaces = Interface.objects.filter(tenant_id=tid, deleted_at__isnull=True)
    return [
        {
            "id": str(i.id),
            "name": i.name,
            "description": i.description,
            "version": i.version,
            "required_properties": i.required_properties,
            "implementing_count": i.implementing_types.count(),
        }
        for i in ifaces
    ]


@mcp_app.tool(name="voyant.ontology.actions.execute")
def tool_ontology_actions_execute(
    action_type_id: str,
    object_id: str,
    params: dict = None,
    tenant_id=None,
):
    """Execute an action type on an object instance."""
    from apps.ontology.action_executor import ActionExecutor

    tid = _tenant(tenant_id)
    executor = ActionExecutor()
    result = executor.execute(tid, action_type_id, object_id, params or {})
    return {
        "success": result.success,
        "action_id": result.action_id,
        "changes": result.changes,
        "errors": result.errors,
    }


@mcp_app.tool(name="voyant.ontology.functions.run")
def tool_ontology_functions_run(
    function_id: str,
    input_data: dict = None,
    tenant_id=None,
):
    """Run an ontology function with the given input data."""
    from apps.ontology.function_runner import FunctionRunner

    tid = _tenant(tenant_id)
    runner = FunctionRunner()
    result = runner.run(tid, function_id, input_data or {})
    return {
        "success": result.success,
        "output": result.output,
        "duration_ms": result.duration_ms,
        "error": result.error,
    }
