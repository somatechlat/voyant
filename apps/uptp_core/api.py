"""
UPTP Core API endpoints.

Provides REST endpoints for template CRUD, instance execution,
and template validation.
"""

from __future__ import annotations

import logging
from typing import Any

from ninja import Field, Router, Schema
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

uptp_router = Router(tags=["uptp"], auth=require_permission("read:*"))


# =============================================================================
# Schemas
# =============================================================================


class TemplateCreateRequest(Schema):
    """Request to create a UPTP template."""

    name: str = Field(..., description="Unique template name")
    description: str = Field("", description="Human-readable description")
    template_body: dict[str, Any] = Field(
        default_factory=dict,
        description="Template definition as JSON",
    )
    category: str = Field(..., description="Execution category")
    tags: list[str] = Field(default_factory=list, description="Searchable tags")
    parameters_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for parameter validation",
    )
    output_schema: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for output format",
    )


class TemplateUpdateRequest(Schema):
    """Request to update a UPTP template."""

    name: str | None = None
    description: str | None = None
    template_body: dict[str, Any] | None = None
    category: str | None = None
    tags: list[str] | None = None
    parameters_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None
    status: str | None = None


class TemplateResponse(Schema):
    """Response for a UPTP template."""

    id: str
    name: str
    description: str
    template_body: dict[str, Any]
    version: int
    status: str
    category: str
    tags: list[str]
    parameters_schema: dict[str, Any]
    output_schema: dict[str, Any]
    is_system: bool
    created_by: str
    created_at: str
    updated_at: str
    instance_count: int = 0


class TemplateListResponse(Schema):
    """Paginated list of templates."""

    templates: list[TemplateResponse]
    total: int


class InstanceCreateRequest(Schema):
    """Request to create and execute a UPTP instance."""

    template_id: str = Field(..., description="Template ID to execute")
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameter values for this execution",
    )
    trigger_source: str = Field("api", description="What triggered this instance")
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )


class InstanceResponse(Schema):
    """Response for a UPTP instance."""

    id: str
    template_id: str
    template_name: str = ""
    parameters: dict[str, Any]
    rendered_body: dict[str, Any]
    status: str
    result: Any = None
    error_message: str
    execution_urn: str
    execution_category: str
    duration_ms: int | None
    trigger_source: str
    metadata: dict[str, Any]
    created_at: str
    started_at: str | None
    finished_at: str | None


class InstanceListResponse(Schema):
    """Paginated list of instances."""

    instances: list[InstanceResponse]
    total: int


class ValidateParametersRequest(Schema):
    """Request to validate parameters against a template."""

    template_id: str = Field(..., description="Template ID")
    parameters: dict[str, Any] = Field(..., description="Parameters to validate")


class ValidationResultResponse(Schema):
    """Result of parameter validation."""

    valid: bool
    errors: list[str] = []
    rendered_body: dict[str, Any] = {}


# =============================================================================
# Helpers
# =============================================================================


def _template_to_response(template: Any) -> TemplateResponse:
    """Convert a UPTPTemplate model instance to API response."""
    return TemplateResponse(
        id=str(template.id),
        name=template.name,
        description=template.description,
        template_body=template.template_body,
        version=template.version,
        status=template.status,
        category=template.category,
        tags=template.tags or [],
        parameters_schema=template.parameters_schema or {},
        output_schema=template.output_schema or {},
        is_system=template.is_system,
        created_by=template.created_by,
        created_at=template.created_at.isoformat(),
        updated_at=template.updated_at.isoformat(),
        instance_count=template.instances.count(),
    )


def _instance_to_response(instance: Any) -> InstanceResponse:
    """Convert a UPTPInstance model instance to API response."""
    return InstanceResponse(
        id=str(instance.id),
        template_id=str(instance.template_id),
        template_name=getattr(instance.template, "name", ""),
        parameters=instance.parameters,
        rendered_body=instance.rendered_body,
        status=instance.status,
        result=instance.result,
        error_message=instance.error_message,
        execution_urn=instance.execution_urn,
        execution_category=instance.execution_category,
        duration_ms=instance.duration_ms,
        trigger_source=instance.trigger_source,
        metadata=instance.metadata,
        created_at=instance.created_at.isoformat(),
        started_at=instance.started_at.isoformat() if instance.started_at else None,
        finished_at=instance.finished_at.isoformat() if instance.finished_at else None,
    )


# =============================================================================
# Template CRUD
# =============================================================================


@uptp_router.post(
    "/templates",
    response=TemplateResponse,
    auth=require_permission("write:uptp"),
)
def create_template(request, payload: TemplateCreateRequest):
    """Create a new UPTP template."""
    from apps.uptp_core.models import UPTPTemplate

    tenant_id = get_tenant_id(request)

    # Check for duplicate name
    if UPTPTemplate.objects.filter(
        tenant_id=tenant_id, name=payload.name
    ).exists():
        raise HttpError(409, f"Template '{payload.name}' already exists")

    template = UPTPTemplate.objects.create(
        name=payload.name,
        description=payload.description,
        template_body=payload.template_body,
        category=payload.category,
        tags=payload.tags,
        parameters_schema=payload.parameters_schema,
        output_schema=payload.output_schema,
        tenant_id=tenant_id,
        status="draft",
    )

    logger.info(
        "Created UPTP template '%s' (id=%s) for tenant %s",
        template.name,
        template.id,
        tenant_id,
    )
    return _template_to_response(template)


@uptp_router.get(
    "/templates",
    response=TemplateListResponse,
)
def list_templates(
    request,
    category: str | None = None,
    status: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List UPTP templates with optional filtering.

    Supports filtering by category, status, tag, and text search.
    """
    from apps.uptp_core.models import UPTPTemplate

    tenant_id = get_tenant_id(request)
    qs = UPTPTemplate.objects.filter(tenant_id=tenant_id)

    if category:
        qs = qs.filter(category=category)
    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(name__icontains=search)

    total = qs.count()
    templates = qs[offset : offset + limit]

    return TemplateListResponse(
        templates=[_template_to_response(t) for t in templates],
        total=total,
    )


@uptp_router.get(
    "/templates/{template_id}",
    response=TemplateResponse,
)
def get_template(request, template_id: str):
    """Get a UPTP template by ID."""
    from apps.uptp_core.models import UPTPTemplate

    tenant_id = get_tenant_id(request)
    template = UPTPTemplate.objects.filter(
        id=template_id, tenant_id=tenant_id
    ).first()
    if not template:
        raise HttpError(404, f"Template {template_id} not found")
    return _template_to_response(template)


@uptp_router.put(
    "/templates/{template_id}",
    response=TemplateResponse,
    auth=require_permission("write:uptp"),
)
def update_template(request, template_id: str, payload: TemplateUpdateRequest):
    """Update an existing UPTP template."""
    from apps.uptp_core.models import UPTPTemplate

    tenant_id = get_tenant_id(request)
    template = UPTPTemplate.objects.filter(
        id=template_id, tenant_id=tenant_id
    ).first()
    if not template:
        raise HttpError(404, f"Template {template_id} not found")

    if template.is_system:
        raise HttpError(403, "System templates cannot be modified")

    update_fields = []
    for field_name, value in payload.dict(exclude_unset=True).items():
        if value is not None:
            setattr(template, field_name, value)
            update_fields.append(field_name)

    if update_fields:
        template.version += 1
        update_fields.append("version")
        update_fields.append("updated_at")
        template.save(update_fields=update_fields)

    logger.info("Updated UPTP template %s to v%d", template.id, template.version)
    return _template_to_response(template)


@uptp_router.delete(
    "/templates/{template_id}",
    auth=require_permission("write:uptp"),
)
def delete_template(request, template_id: str):
    """Delete a UPTP template."""
    from apps.uptp_core.models import UPTPTemplate

    tenant_id = get_tenant_id(request)
    template = UPTPTemplate.objects.filter(
        id=template_id, tenant_id=tenant_id
    ).first()
    if not template:
        raise HttpError(404, f"Template {template_id} not found")

    if template.is_system:
        raise HttpError(403, "System templates cannot be deleted")

    if template.instances.filter(status="running").exists():
        raise HttpError(
            409,
            "Cannot delete template with running instances. "
            "Cancel running instances first.",
        )

    template.delete()
    logger.info("Deleted UPTP template %s", template_id)
    return {"status": "deleted", "template_id": template_id}


# =============================================================================
# Template Validation & Rendering
# =============================================================================


@uptp_router.post(
    "/templates/validate",
    response=ValidationResultResponse,
)
def validate_parameters(request, payload: ValidateParametersRequest):
    """
    Validate parameters against a template's schema.

    Returns validation errors and the rendered template body.
    """
    from apps.uptp_core.models import UPTPTemplate

    tenant_id = get_tenant_id(request)
    template = UPTPTemplate.objects.filter(
        id=payload.template_id, tenant_id=tenant_id
    ).first()
    if not template:
        raise HttpError(404, f"Template {payload.template_id} not found")

    errors = template.validate_parameters(payload.parameters)
    rendered = {}
    if not errors:
        try:
            rendered = template.render(payload.parameters)
        except Exception as exc:
            errors.append(f"Rendering failed: {exc}")

    return ValidationResultResponse(
        valid=len(errors) == 0,
        errors=errors,
        rendered_body=rendered,
    )


# =============================================================================
# Instance Execution
# =============================================================================


@uptp_router.post(
    "/instances",
    response=InstanceResponse,
    auth=require_permission("write:uptp"),
)
def create_instance(request, payload: InstanceCreateRequest):
    """
    Create and execute a UPTP instance.

    Validates parameters against the template schema, renders the template,
    and dispatches to the execution engine.
    """
    from apps.core.lib.metrics import record_job
    from apps.uptp_core.engine import UPTPExecutionEngine
    from apps.uptp_core.models import UPTPInstance, UPTPTemplate
    from apps.uptp_core.schemas import TemplateCategory, TemplateExecutionRequest

    tenant_id = get_tenant_id(request)

    template = UPTPTemplate.objects.filter(
        id=payload.template_id, tenant_id=tenant_id
    ).first()
    if not template:
        raise HttpError(404, f"Template {payload.template_id} not found")

    if template.status not in ("active", "draft"):
        raise HttpError(
            400, f"Template is {template.status} and cannot be executed"
        )

    # Validate parameters
    errors = template.validate_parameters(payload.parameters)
    if errors:
        raise HttpError(
            422,
            f"Parameter validation failed: {'; '.join(errors)}",
        )

    # Render the template
    rendered = template.render(payload.parameters)

    # Create the instance
    instance = UPTPInstance.objects.create(
        template=template,
        parameters=payload.parameters,
        rendered_body=rendered,
        status="pending",
        trigger_source=payload.trigger_source,
        metadata=payload.metadata,
        execution_category=template.category,
        tenant_id=tenant_id,
    )

    # Dispatch to execution engine
    try:
        category = TemplateCategory(template.category)
        execution_request = TemplateExecutionRequest(
            template_id=template.name,
            category=category,
            params=payload.parameters,
            tenant_id=tenant_id,
            job_name=f"uptp-{instance.id}",
        )
        result = UPTPExecutionEngine.dispatch_execution(execution_request)

        instance.execution_urn = result.get("job_urn", "")
        instance.workflow_instance_id = result.get("workflow_id", "")
        if result.get("status") == "accepted":
            instance.mark_running()
        elif result.get("status") == "success":
            instance.mark_succeeded(result)
        else:
            instance.mark_running()

        record_job("uptp_instance", "started")
    except Exception as exc:
        instance.mark_failed(str(exc))
        record_job("uptp_instance", "failed")
        raise HttpError(500, f"Execution dispatch failed: {exc}")

    logger.info(
        "Created UPTP instance %s from template '%s'",
        instance.id,
        template.name,
    )
    return _instance_to_response(instance)


@uptp_router.get(
    "/instances",
    response=InstanceListResponse,
)
def list_instances(
    request,
    template_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    """List UPTP instances with optional filtering."""
    from apps.uptp_core.models import UPTPInstance

    tenant_id = get_tenant_id(request)
    qs = UPTPInstance.objects.filter(tenant_id=tenant_id).select_related("template")

    if template_id:
        qs = qs.filter(template_id=template_id)
    if status:
        qs = qs.filter(status=status)

    total = qs.count()
    instances = qs[offset : offset + limit]

    return InstanceListResponse(
        instances=[_instance_to_response(i) for i in instances],
        total=total,
    )


@uptp_router.get(
    "/instances/{instance_id}",
    response=InstanceResponse,
)
def get_instance(request, instance_id: str):
    """Get a UPTP instance by ID."""
    from apps.uptp_core.models import UPTPInstance

    tenant_id = get_tenant_id(request)
    instance = UPTPInstance.objects.filter(
        id=instance_id, tenant_id=tenant_id
    ).select_related("template").first()
    if not instance:
        raise HttpError(404, f"Instance {instance_id} not found")
    return _instance_to_response(instance)


@uptp_router.post(
    "/instances/{instance_id}/cancel",
    auth=require_permission("write:uptp"),
)
def cancel_instance(request, instance_id: str):
    """Cancel a running UPTP instance."""
    from apps.uptp_core.models import UPTPInstance

    tenant_id = get_tenant_id(request)
    instance = UPTPInstance.objects.filter(
        id=instance_id, tenant_id=tenant_id
    ).first()
    if not instance:
        raise HttpError(404, f"Instance {instance_id} not found")

    if instance.status not in ("pending", "running"):
        raise HttpError(
            400, f"Instance is {instance.status} and cannot be cancelled"
        )

    # Cancel Temporal workflow if applicable
    if instance.workflow_instance_id:
        try:
            from apps.core.api_utils import run_async

            async def _cancel():
                from temporalio.client import Client

                client = await Client.connect("localhost:7233")
                handle = client.get_workflow_handle(
                    instance.workflow_instance_id
                )
                await handle.cancel()

            run_async(_cancel)
        except Exception as exc:
            logger.warning("Failed to cancel Temporal workflow: %s", exc)

    instance.mark_cancelled()
    return {"status": "cancelled", "instance_id": instance_id}
