"""
Voyant MCP — ontology engine tools (14 tools).

Covers: Object Types, Objects, Links, Traversal, Interfaces,
Actions, and Functions.

All tools call into the ontology service layer (services.py,
action_executor.py, function_runner.py) — no duplicated business logic.
"""

import logging

from django_mcp import mcp_app

from apps.core.config import get_settings
from apps.mcp.tools_core import _tenant

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Object Types ─────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.types.list")
def tool_ontology_types_list(tenant_id=None):
    """List all object types with property and instance counts."""
    from apps.ontology.models import Object, ObjectType, Property

    tid = _tenant(tenant_id)
    types = ObjectType.objects.filter(tenant_id=tid, deleted_at__isnull=True).order_by(
        "name"
    )
    return [
        {
            "id": str(ot.id),
            "name": ot.name,
            "description": ot.description,
            "version": ot.version,
            "property_count": Property.objects.filter(object_type=ot).count(),
            "instance_count": Object.objects.filter(
                object_type=ot, deleted_at__isnull=True
            ).count(),
        }
        for ot in types
    ]


@mcp_app.tool(name="voyant.ontology.types.get")
def tool_ontology_types_get(type_id: str, tenant_id=None):
    """Get an object type with its full property definitions."""
    from apps.ontology.models import Property
    from apps.ontology.services import ObjectTypeService

    tid = _tenant(tenant_id)
    try:
        ot = ObjectTypeService.get(tid, type_id)
    except Exception:
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
def tool_ontology_types_create(
    name: str, description: str = "", properties=None, tenant_id=None
):
    """Create a new object type with optional property definitions."""
    from apps.ontology.services import ObjectTypeService

    tid = _tenant(tenant_id)
    try:
        ot = ObjectTypeService.create(
            tid, name=name, description=description, properties=properties or []
        )
        return {"id": str(ot.id), "name": ot.name, "version": ot.version}
    except Exception as exc:
        logger.exception("Failed to create object type %s", name)
        return {"error": str(exc)}


# ── Objects ──────────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.objects.list")
def tool_ontology_objects_list(type_id: str = "", limit: int = 100, tenant_id=None):
    """List object instances, optionally filtered by type."""
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    try:
        qs = ObjectService.list(tid, object_type_id=type_id or None)[:limit]
        return [
            {
                "id": str(o.id),
                "object_type": o.object_type.name,
                "object_type_id": str(o.object_type_id),  # type: ignore[attr-defined]
                "properties": o.properties,
                "version": o.version,
                "created_at": o.created_at.isoformat(),
            }
            for o in qs
        ]
    except Exception as exc:
        logger.exception("Failed to list objects")
        return {"error": str(exc)}


@mcp_app.tool(name="voyant.ontology.objects.create")
def tool_ontology_objects_create(type_id: str, properties: dict, tenant_id=None):
    """Create a new object instance with schema validation."""
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    try:
        obj = ObjectService.create(tid, type_id, properties)
        return {
            "id": str(obj.id),
            "object_type": obj.object_type.name,
            "properties": obj.properties,
            "version": obj.version,
        }
    except Exception as exc:
        logger.exception("Failed to create object in type %s", type_id)
        return {"error": str(exc)}


@mcp_app.tool(name="voyant.ontology.objects.get")
def tool_ontology_objects_get(object_id: str, tenant_id=None):
    """Get an object instance with its properties, type info, and links."""
    from apps.ontology.models import Link
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    try:
        obj = ObjectService.get(tid, object_id)
    except Exception:
        return {"error": "Object not found"}

    # Fetch outgoing and incoming links for graph context
    outgoing = Link.objects.filter(
        source_object=obj, deleted_at__isnull=True
    ).select_related("link_type", "target_object")
    incoming = Link.objects.filter(
        target_object=obj, deleted_at__isnull=True
    ).select_related("link_type", "source_object")

    return {
        "id": str(obj.id),
        "object_type": obj.object_type.name,
        "object_type_id": str(obj.object_type_id),  # type: ignore[attr-defined]
        "properties": obj.properties,
        "version": obj.version,
        "created_at": obj.created_at.isoformat(),
        "outgoing_links": [
            {
                "link_id": str(lk.id),
                "link_type": lk.link_type.name,
                "target_object_id": str(lk.target_object_id),  # type: ignore[attr-defined]
                "target_object_type": lk.target_object.object_type.name,
                "properties": lk.properties,
            }
            for lk in outgoing
        ],
        "incoming_links": [
            {
                "link_id": str(lk.id),
                "link_type": lk.link_type.name,
                "source_object_id": str(lk.source_object_id),  # type: ignore[attr-defined]
                "source_object_type": lk.source_object.object_type.name,
                "properties": lk.properties,
            }
            for lk in incoming
        ],
    }


@mcp_app.tool(name="voyant.ontology.objects.update")
def tool_ontology_objects_update(
    object_id: str,
    properties: dict,
    version: int = None,
    tenant_id=None,  # type: ignore[reportArgumentType]
):
    """Update an object instance with optimistic concurrency."""
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    try:
        obj = ObjectService.update(tid, object_id, properties, version=version)
        return {
            "id": str(obj.id),
            "properties": obj.properties,
            "version": obj.version,
        }
    except Exception as exc:
        logger.exception("Failed to update object %s", object_id)
        return {"error": str(exc)}


@mcp_app.tool(name="voyant.ontology.objects.batch_create")
def tool_ontology_objects_batch(type_id: str, items: list, tenant_id=None):
    """Batch create 1000+ object instances."""
    from apps.ontology.services import ObjectService

    tid = _tenant(tenant_id)
    try:
        objects = ObjectService.batch_create(tid, type_id, items)
        return {"created": len(objects), "ids": [str(o.id) for o in objects]}
    except Exception as exc:
        logger.exception("Failed to batch create objects in type %s", type_id)
        return {"error": str(exc)}


# ── Links ────────────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.links.create")
def tool_ontology_links_create(
    link_type_id: str,
    source_object_id: str,
    target_object_id: str,
    properties: dict = None,  # type: ignore[reportArgumentType]
    tenant_id=None,
):
    """Create a link between two objects."""
    from apps.ontology.services import LinkService

    tid = _tenant(tenant_id)
    try:
        link = LinkService.create(
            tid, link_type_id, source_object_id, target_object_id, properties
        )
        return {
            "id": str(link.id),
            "link_type": link.link_type.name,
            "source": str(link.source_object_id),  # type: ignore[attr-defined]
            "target": str(link.target_object_id),  # type: ignore[attr-defined]
        }
    except Exception as exc:
        logger.exception("Failed to create link")
        return {"error": str(exc)}


@mcp_app.tool(name="voyant.ontology.links.delete")
def tool_ontology_links_delete(link_id: str, tenant_id=None):
    """Delete a link between two objects."""
    from apps.ontology.services import LinkService

    tid = _tenant(tenant_id)
    try:
        LinkService.delete(tid, link_id)
        return {"status": "deleted", "id": link_id}
    except Exception as exc:
        logger.exception("Failed to delete link %s", link_id)
        return {"error": str(exc)}


# ── Traversal ────────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.traverse")
def tool_ontology_traverse(
    object_id: str,
    direction: str = "outgoing",
    max_depth: int = 1,
    link_type_name: str = "",
    tenant_id=None,
):
    """Traverse links from an object up to 10 hops (outgoing, incoming, or both)."""
    from apps.ontology.services import LinkService

    tid = _tenant(tenant_id)
    try:
        results = LinkService.traverse(
            tid,
            object_id,
            link_type_name=link_type_name or None,
            direction=direction,
            max_depth=min(max_depth, 10),
        )
        return {"object_id": object_id, "results": results, "count": len(results)}
    except Exception as exc:
        logger.exception("Failed to traverse from object %s", object_id)
        return {"error": str(exc)}


# ── Interfaces ───────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.interfaces.list")
def tool_ontology_interfaces_list(tenant_id=None):
    """List all interfaces (polymorphic type abstractions)."""
    from apps.ontology.models import Interface

    tid = _tenant(tenant_id)
    ifaces = Interface.objects.filter(tenant_id=tid, deleted_at__isnull=True)
    return [
        {
            "id": str(i.id),
            "name": i.name,
            "description": i.description,
            "version": i.version,
            "required_properties": i.required_properties,
            "optional_properties": i.optional_properties,
            "implementing_types": [str(t.id) for t in i.implementing_types.all()],
        }
        for i in ifaces
    ]


# ── Actions ──────────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.actions.execute")
def tool_ontology_actions_execute(
    action_type_id: str,
    object_id: str,
    params: dict = None,  # type: ignore[reportArgumentType]
    tenant_id=None,
):
    """Execute an action type on an object instance.

    Validates parameters against the action schema, checks pre-condition
    rules, applies changes, runs side effects, and records execution for
    undo support.
    """
    from apps.ontology.action_executor import ActionExecutor

    tid = _tenant(tenant_id)
    try:
        executor = ActionExecutor()
        result = executor.execute(tid, action_type_id, object_id, params or {})
        return {
            "success": result.success,
            "action_id": result.action_id,
            "object_id": result.object_id,
            "changes": result.changes,
            "side_effects_executed": result.side_effects_executed,
            "errors": result.errors,
        }
    except Exception as exc:
        logger.exception("Failed to execute action %s on %s", action_type_id, object_id)
        return {"error": str(exc)}


# ── Functions ────────────────────────────────────────────────────────────────


@mcp_app.tool(name="voyant.ontology.functions.run")
def tool_ontology_functions_run(
    function_id: str,
    input_data: dict = None,  # type: ignore[reportArgumentType]
    tenant_id=None,
):
    """Run an ontology function with the given input data.

    Executes the function in a sandboxed subprocess with timeout and
    memory limits. Returns the function's output, duration, and any
    errors.
    """
    from apps.ontology.function_runner import FunctionRunner

    tid = _tenant(tenant_id)
    try:
        runner = FunctionRunner()
        result = runner.run(tid, function_id, input_data or {})
        return {
            "success": result.success,
            "function_id": result.function_id,
            "output": result.output,
            "duration_ms": result.duration_ms,
            "error": result.error,
        }
    except Exception as exc:
        logger.exception("Failed to run function %s", function_id)
        return {"error": str(exc)}
