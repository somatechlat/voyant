"""ML Platform API — REST endpoints for experiments, models, and serving."""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.ml_platform.models import (
    Experiment,
    ModelEndpoint,
    ModelVersion,
    RegisteredModel,
    Run,
    RunArtifact,
)

logger = logging.getLogger(__name__)

ml_router = Router(tags=["ml"], auth=require_permission("read:*"))


# ── Experiments ──────────────────────────────────────────────────────────────


@ml_router.get("/experiments")
def list_experiments(request):
    """List all experiments."""
    tenant_id = get_tenant_id(request)
    exps = Experiment.objects.filter(tenant_id=tenant_id).order_by("-created_at")
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "description": e.description,
            "tags": e.tags,
            "run_count": e.runs.count(),
            "created_at": e.created_at.isoformat(),
        }
        for e in exps
    ]


@ml_router.post("/experiments", auth=require_permission("write:ml"))
def create_experiment(request, payload: dict[str, Any]):
    """Create a new experiment."""
    tenant_id = get_tenant_id(request)
    exp = Experiment.objects.create(
        tenant_id=tenant_id,
        name=payload["name"],
        description=payload.get("description", ""),
        tags=payload.get("tags", {}),
    )
    return {"id": str(exp.id), "name": exp.name, "status": "created"}


@ml_router.get("/experiments/{experiment_id}")
def get_experiment(request, experiment_id: str):
    """Get experiment with its runs."""
    tenant_id = get_tenant_id(request)
    exp = Experiment.objects.filter(id=experiment_id, tenant_id=tenant_id).first()
    if not exp:
        raise HttpError(404, "Experiment not found")

    runs = Run.objects.filter(experiment=exp).order_by("-started_at")[:50]
    return {
        "id": str(exp.id),
        "name": exp.name,
        "description": exp.description,
        "tags": exp.tags,
        "runs": [
            {
                "id": str(r.id),
                "name": r.name,
                "status": r.status,
                "params": r.params,
                "metrics": r.metrics,
                "started_at": r.started_at.isoformat(),
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
            }
            for r in runs
        ],
    }


# ── Runs ─────────────────────────────────────────────────────────────────────


@ml_router.post("/experiments/{experiment_id}/runs", auth=require_permission("write:ml"))
def create_run(request, experiment_id: str, payload: dict[str, Any]):
    """Log a new run for an experiment."""
    tenant_id = get_tenant_id(request)
    exp = Experiment.objects.filter(id=experiment_id, tenant_id=tenant_id).first()
    if not exp:
        raise HttpError(404, "Experiment not found")

    run = Run.objects.create(
        tenant_id=tenant_id,
        experiment=exp,
        name=payload.get("name", ""),
        params=payload.get("params", {}),
        metrics=payload.get("metrics", {}),
        tags=payload.get("tags", {}),
    )
    return {"id": str(run.id), "status": run.status}


@ml_router.put("/runs/{run_id}/metrics", auth=require_permission("write:ml"))
def update_run_metrics(request, run_id: str, payload: dict[str, Any]):
    """Update metrics for a run."""
    tenant_id = get_tenant_id(request)
    run = Run.objects.filter(id=run_id, tenant_id=tenant_id).first()
    if not run:
        raise HttpError(404, "Run not found")

    metrics = run.metrics or {}
    metrics.update(payload.get("metrics", {}))
    run.metrics = metrics

    if payload.get("status"):
        run.status = payload["status"]
    if payload.get("status") in ("finished", "failed", "killed"):
        from datetime import UTC, datetime

        run.ended_at = datetime.now(UTC)

    run.save()
    return {"id": str(run.id), "status": run.status, "metrics": run.metrics}


# ── Model Registry ───────────────────────────────────────────────────────────


@ml_router.get("/models")
def list_models(request):
    """List all registered models."""
    tenant_id = get_tenant_id(request)
    models_list = RegisteredModel.objects.filter(tenant_id=tenant_id).order_by("-created_at")
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "description": m.description,
            "version_count": m.versions.count(),
            "latest_stage": _get_latest_stage(m),
            "created_at": m.created_at.isoformat(),
        }
        for m in models_list
    ]


@ml_router.post("/models", auth=require_permission("write:ml"))
def register_model(request, payload: dict[str, Any]):
    """Register a new model."""
    tenant_id = get_tenant_id(request)
    model = RegisteredModel.objects.create(
        tenant_id=tenant_id,
        name=payload["name"],
        description=payload.get("description", ""),
        tags=payload.get("tags", {}),
    )
    return {"id": str(model.id), "name": model.name}


@ml_router.get("/models/{model_id}")
def get_model(request, model_id: str):
    """Get model with its versions."""
    tenant_id = get_tenant_id(request)
    model = RegisteredModel.objects.filter(id=model_id, tenant_id=tenant_id).first()
    if not model:
        raise HttpError(404, "Model not found")

    versions = ModelVersion.objects.filter(registered_model=model).order_by("-version")
    return {
        "id": str(model.id),
        "name": model.name,
        "description": model.description,
        "versions": [
            {
                "id": str(v.id),
                "version": v.version,
                "stage": v.stage,
                "status": v.status,
                "metrics": v.metrics,
                "description": v.description,
            }
            for v in versions
        ],
    }


@ml_router.post("/models/{model_id}/versions", auth=require_permission("write:ml"))
def create_model_version(request, model_id: str, payload: dict[str, Any]):
    """Create a new version for a registered model."""
    tenant_id = get_tenant_id(request)
    model = RegisteredModel.objects.filter(id=model_id, tenant_id=tenant_id).first()
    if not model:
        raise HttpError(404, "Model not found")

    last_version = ModelVersion.objects.filter(registered_model=model).order_by("-version").first()
    new_version = (last_version.version + 1) if last_version else 1

    mv = ModelVersion.objects.create(
        tenant_id=tenant_id,
        registered_model=model,
        version=new_version,
        run_id=payload.get("run_id"),
        storage_path=payload.get("storage_path", ""),
        metrics=payload.get("metrics", {}),
        description=payload.get("description", ""),
    )
    return {"id": str(mv.id), "version": new_version}


@ml_router.put("/model-versions/{version_id}/stage", auth=require_permission("write:ml"))
def transition_stage(request, version_id: str, payload: dict[str, Any]):
    """Transition model version stage."""
    tenant_id = get_tenant_id(request)
    mv = ModelVersion.objects.filter(id=version_id, tenant_id=tenant_id).first()
    if not mv:
        raise HttpError(404, "Model version not found")

    new_stage = payload.get("stage")
    valid_transitions = {
        "none": ["staging"],
        "staging": ["production", "archived"],
        "production": ["archived", "staging"],
        "archived": ["none"],
    }

    if new_stage not in valid_transitions.get(mv.stage, []):
        raise HttpError(
            400,
            f"Invalid transition: {mv.stage} → {new_stage}. Valid: {valid_transitions.get(mv.stage, [])}",
        )

    mv.stage = new_stage
    mv.save(update_fields=["stage"])
    return {"id": str(mv.id), "version": mv.version, "stage": mv.stage}


# ── Model Serving ────────────────────────────────────────────────────────────


@ml_router.get("/endpoints")
def list_endpoints(request):
    """List model serving endpoints."""
    tenant_id = get_tenant_id(request)
    endpoints = ModelEndpoint.objects.filter(tenant_id=tenant_id).order_by("-created_at")
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "status": e.status,
            "model_version": str(e.model_version_id) if e.model_version_id else None,
            "endpoint_path": e.endpoint_path,
            "invocation_count": e.invocation_count,
            "avg_latency_ms": e.avg_latency_ms,
        }
        for e in endpoints
    ]


@ml_router.post("/endpoints", auth=require_permission("write:ml"))
def create_endpoint(request, payload: dict[str, Any]):
    """Create a model serving endpoint."""
    tenant_id = get_tenant_id(request)
    endpoint = ModelEndpoint.objects.create(
        tenant_id=tenant_id,
        name=payload["name"],
        model_version_id=payload.get("model_version_id"),
        config=payload.get("config", {}),
        endpoint_path=f"/v1/ml/predict/{payload['name']}",
    )
    return {"id": str(endpoint.id), "name": endpoint.name, "path": endpoint.endpoint_path}


def _get_latest_stage(model: RegisteredModel) -> str:
    """Get the stage of the latest version."""
    latest = model.versions.order_by("-version").first()
    return latest.stage if latest else "none"
