"""Pipeline Builder API — Django Ninja REST endpoints.

Provides CRUD for pipelines, steps, pipeline runs, and
the ability to trigger pipeline execution via Temporal workflows.
"""

from __future__ import annotations

import logging
from typing import Any

from django.utils import timezone as tz
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

pipelines_router = Router(tags=["pipelines"], auth=require_permission("read:*"))


# ── Schemas ──────────────────────────────────────────────────────────────────


class PipelineCreateIn(Schema):
    name: str
    description: str = ""
    schedule: str = ""
    schedule_timezone: str = "UTC"
    config: dict[str, Any] = {}


class PipelineUpdateIn(Schema):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    schedule: str | None = None
    schedule_timezone: str | None = None
    config: dict[str, Any] | None = None


class PipelineOut(Schema):
    id: str
    name: str
    description: str
    status: str
    schedule: str
    schedule_timezone: str
    config: dict[str, Any]
    version: int
    step_count: int = 0
    tenant_id: str
    created_at: str
    updated_at: str


class StepCreateIn(Schema):
    step_type: str
    name: str = ""
    order: int = 0
    config: dict[str, Any] = {}
    retry_count: int = 0
    timeout_seconds: int = 300


class StepUpdateIn(Schema):
    step_type: str | None = None
    name: str | None = None
    order: int | None = None
    config: dict[str, Any] | None = None
    retry_count: int | None = None
    timeout_seconds: int | None = None


class StepOut(Schema):
    id: str
    pipeline_id: str
    step_type: str
    name: str
    order: int
    config: dict[str, Any]
    retry_count: int
    timeout_seconds: int


class PipelineRunOut(Schema):
    id: str
    pipeline_id: str
    status: str
    triggered_by: str
    trigger_type: str
    parameters: dict[str, Any]
    started_at: str | None = None
    completed_at: str | None = None
    steps_completed: int
    steps_total: int
    error_message: str
    temporal_workflow_id: str
    tenant_id: str
    created_at: str
    updated_at: str


class StepRunOut(Schema):
    id: str
    pipeline_run_id: str
    step_id: str
    status: str
    started_at: str | None = None
    completed_at: str | None = None
    output_data: dict[str, Any]
    error_message: str
    attempt: int


# ── Pipeline CRUD ────────────────────────────────────────────────────────────


def _to_pipeline_out(p: Any, step_count: int = 0) -> dict[str, Any]:
    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "status": p.status,
        "schedule": p.schedule,
        "schedule_timezone": p.schedule_timezone,
        "config": p.config,
        "version": p.version,
        "step_count": step_count,
        "tenant_id": p.tenant_id,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }


def _to_step_out(s: Any) -> dict[str, Any]:
    return {
        "id": str(s.id),
        "pipeline_id": str(s.pipeline_id),
        "step_type": s.step_type,
        "name": s.name,
        "order": s.order,
        "config": s.config,
        "retry_count": s.retry_count,
        "timeout_seconds": s.timeout_seconds,
    }


def _to_run_out(r: Any) -> dict[str, Any]:
    return {
        "id": str(r.id),
        "pipeline_id": str(r.pipeline_id),
        "status": r.status,
        "triggered_by": r.triggered_by,
        "trigger_type": r.trigger_type,
        "parameters": r.parameters,
        "started_at": r.started_at.isoformat() if r.started_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        "steps_completed": r.steps_completed,
        "steps_total": r.steps_total,
        "error_message": r.error_message,
        "temporal_workflow_id": r.temporal_workflow_id,
        "tenant_id": r.tenant_id,
        "created_at": r.created_at.isoformat(),
        "updated_at": r.updated_at.isoformat(),
    }


@pipelines_router.post(
    "", response={201: PipelineOut}, auth=require_permission("write:pipelines")
)
def create_pipeline(request, payload: PipelineCreateIn):
    """Create a new pipeline."""
    from apps.pipelines.models import Pipeline

    tenant_id = get_tenant_id(request)
    pipeline = Pipeline.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        schedule=payload.schedule,
        schedule_timezone=payload.schedule_timezone,
        config=payload.config,
    )
    return 201, _to_pipeline_out(pipeline, step_count=0)


@pipelines_router.get("", response=list[PipelineOut])
def list_pipelines(request, status: str | None = None, limit: int = 50):
    """List pipelines for the current tenant."""
    from apps.pipelines.models import Pipeline

    tenant_id = get_tenant_id(request)
    qs = Pipeline.objects.filter(tenant_id=tenant_id, deleted_at__isnull=True)
    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by("-created_at")[:limit]
    results = []
    for p in qs:
        step_count = p.steps.count() if hasattr(p, "steps") else 0  # type: ignore[attr-defined]
        results.append(_to_pipeline_out(p, step_count=step_count))
    return results


@pipelines_router.get("/{pipeline_id}", response=PipelineOut)
def get_pipeline(request, pipeline_id: str):
    """Get pipeline details."""
    from apps.pipelines.models import Pipeline

    tenant_id = get_tenant_id(request)
    pipeline = Pipeline.objects.filter(
        id=pipeline_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not pipeline:
        raise HttpError(404, f"Pipeline {pipeline_id} not found")
    step_count = pipeline.steps.count() if hasattr(pipeline, "steps") else 0  # type: ignore[attr-defined]
    return _to_pipeline_out(pipeline, step_count=step_count)


@pipelines_router.put(
    "/{pipeline_id}", response=PipelineOut, auth=require_permission("write:pipelines")
)
def update_pipeline(request, pipeline_id: str, payload: PipelineUpdateIn):
    """Update a pipeline."""
    from apps.pipelines.models import Pipeline

    tenant_id = get_tenant_id(request)
    pipeline = Pipeline.objects.filter(
        id=pipeline_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not pipeline:
        raise HttpError(404, f"Pipeline {pipeline_id} not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pipeline, field, value)
    pipeline.version += 1
    pipeline.save()
    step_count = pipeline.steps.count() if hasattr(pipeline, "steps") else 0  # type: ignore[attr-defined]
    return _to_pipeline_out(pipeline, step_count=step_count)


@pipelines_router.delete("/{pipeline_id}", auth=require_permission("write:pipelines"))
def delete_pipeline(request, pipeline_id: str):
    """Soft-delete a pipeline."""
    from apps.pipelines.models import Pipeline

    tenant_id = get_tenant_id(request)
    pipeline = Pipeline.objects.filter(
        id=pipeline_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not pipeline:
        raise HttpError(404, f"Pipeline {pipeline_id} not found")

    pipeline.deleted_at = tz.now()
    pipeline.save(update_fields=["deleted_at"])
    return {"deleted": True, "id": pipeline_id}


# ── Pipeline Steps CRUD ──────────────────────────────────────────────────────


@pipelines_router.post(
    "/{pipeline_id}/steps",
    response={201: StepOut},
    auth=require_permission("write:pipelines"),
)
def create_step(request, pipeline_id: str, payload: StepCreateIn):
    """Add a step to a pipeline."""
    from apps.pipelines.models import Pipeline, PipelineStep

    tenant_id = get_tenant_id(request)
    pipeline = Pipeline.objects.filter(
        id=pipeline_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not pipeline:
        raise HttpError(404, f"Pipeline {pipeline_id} not found")

    step = PipelineStep.objects.create(
        pipeline=pipeline,
        step_type=payload.step_type,
        name=payload.name,
        order=payload.order,
        config=payload.config,
        retry_count=payload.retry_count,
        timeout_seconds=payload.timeout_seconds,
    )
    return 201, _to_step_out(step)


@pipelines_router.get("/{pipeline_id}/steps", response=list[StepOut])
def list_steps(request, pipeline_id: str):
    """List steps for a pipeline."""
    from apps.pipelines.models import PipelineStep

    qs = PipelineStep.objects.filter(pipeline_id=pipeline_id).order_by("order")
    return [_to_step_out(s) for s in qs]


@pipelines_router.put(
    "/steps/{step_id}",
    response=StepOut,
    auth=require_permission("write:pipelines"),
)
def update_step(request, step_id: str, payload: StepUpdateIn):
    """Update a pipeline step."""
    from apps.pipelines.models import PipelineStep

    step = PipelineStep.objects.filter(id=step_id).first()
    if not step:
        raise HttpError(404, f"Step {step_id} not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(step, field, value)
    step.save()
    return _to_step_out(step)


@pipelines_router.delete("/steps/{step_id}", auth=require_permission("write:pipelines"))
def delete_step(request, step_id: str):
    """Delete a pipeline step."""
    from apps.pipelines.models import PipelineStep

    step = PipelineStep.objects.filter(id=step_id).first()
    if not step:
        raise HttpError(404, f"Step {step_id} not found")

    step.delete()
    return {"deleted": True, "id": step_id}


# ── Pipeline Runs ────────────────────────────────────────────────────────────


@pipelines_router.post(
    "/{pipeline_id}/run",
    response={202: PipelineRunOut},
    auth=require_permission("write:pipelines"),
)
def trigger_run(request, pipeline_id: str, params: dict[str, Any] | None = None):
    """Trigger a pipeline run. Starts a Temporal workflow for execution."""
    from apps.pipelines.models import Pipeline, PipelineRun

    tenant_id = get_tenant_id(request)
    pipeline = Pipeline.objects.filter(
        id=pipeline_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not pipeline:
        raise HttpError(404, f"Pipeline {pipeline_id} not found")

    if pipeline.status != "active":
        raise HttpError(
            400, f"Pipeline must be 'active' to run (current: {pipeline.status})"
        )

    step_count = pipeline.steps.count()  # type: ignore[attr-defined]

    run = PipelineRun.objects.create(
        tenant_id=tenant_id,
        pipeline=pipeline,
        status="queued",
        triggered_by=(
            request.user.username
            if hasattr(request, "user") and request.user.is_authenticated
            else "api"
        ),
        trigger_type="api",
        parameters=params or {},
        steps_total=step_count,
    )

    # Attempt to start Temporal workflow
    try:
        from apps.core.api_utils import run_async
        from apps.core.lib.temporal_client import get_temporal_client

        client = run_async(get_temporal_client)
        workflow_id = f"pipeline-{run.id}"
        run_async(
            client.start_workflow,
            "PipelineExecutionWorkflow",
            {
                "pipeline_id": str(pipeline.id),
                "run_id": str(run.id),
                "tenant_id": tenant_id,
                "parameters": params or {},
            },
            id=workflow_id,
            task_queue="voyant-pipelines",
        )
        run.status = "running"
        run.temporal_workflow_id = workflow_id
        run.started_at = tz.now()
        run.save(update_fields=["status", "temporal_workflow_id", "started_at"])
    except Exception as exc:
        logger.warning(
            "Failed to start Temporal workflow for pipeline run %s: %s", run.id, exc
        )
        run.status = "running"
        run.started_at = tz.now()
        run.save(update_fields=["status", "started_at"])

    return 202, _to_run_out(run)


@pipelines_router.get("/{pipeline_id}/runs", response=list[PipelineRunOut])
def list_runs(request, pipeline_id: str, status: str | None = None, limit: int = 20):
    """List runs for a pipeline."""
    from apps.pipelines.models import PipelineRun

    tenant_id = get_tenant_id(request)
    qs = PipelineRun.objects.filter(pipeline_id=pipeline_id, tenant_id=tenant_id)
    if status:
        qs = qs.filter(status=status)
    qs = qs.order_by("-created_at")[:limit]
    return [_to_run_out(r) for r in qs]


@pipelines_router.get("/runs/{run_id}", response=PipelineRunOut)
def get_run(request, run_id: str):
    """Get pipeline run details."""
    from apps.pipelines.models import PipelineRun

    tenant_id = get_tenant_id(request)
    run = PipelineRun.objects.filter(id=run_id, tenant_id=tenant_id).first()
    if not run:
        raise HttpError(404, f"Pipeline run {run_id} not found")
    return _to_run_out(run)


@pipelines_router.post(
    "/runs/{run_id}/cancel",
    auth=require_permission("write:pipelines"),
)
def cancel_run(request, run_id: str):
    """Cancel a running pipeline."""
    from apps.pipelines.models import PipelineRun

    tenant_id = get_tenant_id(request)
    run = PipelineRun.objects.filter(id=run_id, tenant_id=tenant_id).first()
    if not run:
        raise HttpError(404, f"Pipeline run {run_id} not found")

    if run.status not in ("queued", "running"):
        raise HttpError(400, f"Cannot cancel run in '{run.status}' status")

    # Cancel Temporal workflow if we have an ID
    if run.temporal_workflow_id:
        try:
            from apps.core.api_utils import run_async
            from apps.core.lib.temporal_client import get_temporal_client

            client = run_async(get_temporal_client)
            handle = client.get_workflow_handle(run.temporal_workflow_id)
            run_async(handle.cancel)
        except Exception as exc:
            logger.warning(
                "Failed to cancel Temporal workflow %s: %s",
                run.temporal_workflow_id,
                exc,
            )

    run.status = "cancelled"
    run.completed_at = tz.now()
    run.save(update_fields=["status", "completed_at"])
    return {"status": "cancelled", "run_id": str(run.id)}


@pipelines_router.get("/runs/{run_id}/steps", response=list[StepRunOut])
def list_step_runs(request, run_id: str):
    """Get step execution details for a pipeline run."""
    from apps.pipelines.models import PipelineStepRun

    qs = PipelineStepRun.objects.filter(pipeline_run_id=run_id).select_related("step")
    return [
        {
            "id": str(sr.id),
            "pipeline_run_id": str(sr.pipeline_run_id),  # type: ignore[attr-defined]
            "step_id": str(sr.step_id),  # type: ignore[attr-defined]
            "status": sr.status,
            "started_at": sr.started_at.isoformat() if sr.started_at else None,
            "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
            "output_data": sr.output_data,
            "error_message": sr.error_message,
            "attempt": sr.attempt,
        }
        for sr in qs
    ]


# ── DAG Validation ───────────────────────────────────────────────────────────


class DAGStepIn(Schema):
    id: str
    step_type: str
    name: str = ""
    config: dict[str, Any] = {}


class DAGEdgeIn(Schema):
    source: str
    target: str


class DAGValidateIn(Schema):
    steps: list[DAGStepIn]
    edges: list[DAGEdgeIn]


class DAGValidationOut(Schema):
    valid: bool
    errors: list[dict[str, Any]]
    warnings: list[dict[str, Any]]
    execution_order: list[str]


@pipelines_router.post(
    "/{pipeline_id}/validate",
    response=DAGValidationOut,
    auth=require_permission("write:pipelines"),
)
def validate_pipeline_dag(request, pipeline_id: str, payload: DAGValidateIn | None = None):
    """Validate the pipeline DAG structure.

    If a payload is provided, validates the supplied steps/edges directly
    (useful for pre-save validation in the UI). Otherwise, reads the
    pipeline's current steps and their depends_on relationships.
    """
    from apps.pipelines.models import Pipeline, PipelineStep
    from apps.pipelines.validator import validate_dag

    tenant_id = get_tenant_id(request)
    pipeline = Pipeline.objects.filter(
        id=pipeline_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not pipeline:
        raise HttpError(404, f"Pipeline {pipeline_id} not found")

    if payload:
        steps_data = [s.model_dump() for s in payload.steps]
        edges_data = [e.model_dump() for e in payload.edges]
    else:
        # Build from DB
        db_steps = list(PipelineStep.objects.filter(pipeline=pipeline).order_by("order"))
        steps_data = [
            {
                "id": str(s.id),
                "step_type": s.step_type,
                "name": s.name,
                "config": s.config,
            }
            for s in db_steps
        ]
        edges_data = []
        for s in db_steps:
            for dep in s.depends_on.all():
                edges_data.append({"source": str(dep.id), "target": str(s.id)})

    result = validate_dag(steps_data, edges_data)
    return result.to_dict()


# ── Pipeline Import / Export ─────────────────────────────────────────────────


class PipelineExportOut(Schema):
    name: str
    description: str
    schedule: str
    schedule_timezone: str
    config: dict[str, Any]
    steps: list[dict[str, Any]]
    edges: list[dict[str, Any]]


@pipelines_router.get("/{pipeline_id}/export", response=PipelineExportOut)
def export_pipeline(request, pipeline_id: str):
    """Export a pipeline definition as JSON (for import/sharing)."""
    from apps.pipelines.models import Pipeline, PipelineStep

    tenant_id = get_tenant_id(request)
    pipeline = Pipeline.objects.filter(
        id=pipeline_id, tenant_id=tenant_id, deleted_at__isnull=True
    ).first()
    if not pipeline:
        raise HttpError(404, f"Pipeline {pipeline_id} not found")

    db_steps = list(PipelineStep.objects.filter(pipeline=pipeline).order_by("order"))
    steps = []
    edges = []
    for s in db_steps:
        steps.append({
            "id": str(s.id),
            "step_type": s.step_type,
            "name": s.name,
            "order": s.order,
            "config": s.config,
            "retry_count": s.retry_count,
            "timeout_seconds": s.timeout_seconds,
        })
        for dep in s.depends_on.all():
            edges.append({"source": str(dep.id), "target": str(s.id)})

    return {
        "name": pipeline.name,
        "description": pipeline.description,
        "schedule": pipeline.schedule,
        "schedule_timezone": pipeline.schedule_timezone,
        "config": pipeline.config,
        "steps": steps,
        "edges": edges,
    }


class PipelineImportIn(Schema):
    name: str
    description: str = ""
    schedule: str = ""
    schedule_timezone: str = "UTC"
    config: dict[str, Any] = {}
    steps: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []


@pipelines_router.post(
    "/import",
    response={201: PipelineOut},
    auth=require_permission("write:pipelines"),
)
def import_pipeline(request, payload: PipelineImportIn):
    """Import a pipeline from a JSON definition."""
    from apps.pipelines.models import Pipeline, PipelineStep
    from apps.pipelines.validator import validate_dag

    tenant_id = get_tenant_id(request)

    # Validate DAG before importing
    if payload.steps:
        result = validate_dag(payload.steps, payload.edges)
        if not result.valid:
            raise HttpError(
                400,
                f"Invalid pipeline DAG: {'; '.join(e.message for e in result.errors)}",
            )

    pipeline = Pipeline.objects.create(
        tenant_id=tenant_id,
        name=payload.name,
        description=payload.description,
        schedule=payload.schedule,
        schedule_timezone=payload.schedule_timezone,
        config=payload.config,
    )

    # Create steps with dependency mapping
    step_id_map: dict[str, PipelineStep] = {}
    for step_data in payload.steps:
        old_id = step_data.get("id", "")
        step = PipelineStep.objects.create(
            pipeline=pipeline,
            step_type=step_data.get("step_type", "custom"),
            name=step_data.get("name", ""),
            order=step_data.get("order", 0),
            config=step_data.get("config", {}),
            retry_count=step_data.get("retry_count", 0),
            timeout_seconds=step_data.get("timeout_seconds", 300),
        )
        if old_id:
            step_id_map[old_id] = step

    # Wire up edges as depends_on relationships
    for edge_data in payload.edges:
        src_id = edge_data.get("source", "")
        tgt_id = edge_data.get("target", "")
        src_step = step_id_map.get(src_id)
        tgt_step = step_id_map.get(tgt_id)
        if src_step and tgt_step:
            tgt_step.depends_on.add(src_step)

    step_count = pipeline.steps.count()  # type: ignore[attr-defined]
    return 201, _to_pipeline_out(pipeline, step_count=step_count)


# ── Transform Catalog ────────────────────────────────────────────────────────


@pipelines_router.get("/transforms/catalog")
def list_transforms(request):
    """List all available transform types for the palette."""
    from apps.pipelines.transforms import TransformRegistry

    return TransformRegistry.list_types()


# ── Run Detail with Step Runs ────────────────────────────────────────────────


class PipelineRunDetailOut(PipelineRunOut):
    step_runs: list[StepRunOut] = []


@pipelines_router.get("/runs/{run_id}/detail", response=PipelineRunDetailOut)
def get_run_detail(request, run_id: str):
    """Get pipeline run details including step-level execution records."""
    from apps.pipelines.models import PipelineRun, PipelineStepRun

    tenant_id = get_tenant_id(request)
    run = PipelineRun.objects.filter(id=run_id, tenant_id=tenant_id).first()
    if not run:
        raise HttpError(404, f"Pipeline run {run_id} not found")

    run_data = _to_run_out(run)
    step_runs_qs = PipelineStepRun.objects.filter(pipeline_run_id=run.id).select_related("step")
    run_data["step_runs"] = [
        {
            "id": str(sr.id),
            "pipeline_run_id": str(sr.pipeline_run_id),  # type: ignore[attr-defined]
            "step_id": str(sr.step_id),  # type: ignore[attr-defined]
            "status": sr.status,
            "started_at": sr.started_at.isoformat() if sr.started_at else None,
            "completed_at": sr.completed_at.isoformat() if sr.completed_at else None,
            "output_data": sr.output_data,
            "error_message": sr.error_message,
            "attempt": sr.attempt,
        }
        for sr in step_runs_qs
    ]
    return run_data
