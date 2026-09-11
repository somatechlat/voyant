"""ML Platform API — REST endpoints for experiments, models, and serving."""

from __future__ import annotations

import json
import logging
from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import get_current_user, require_permission
from apps.ml_platform.models import (
    Experiment,
    ModelEndpoint,
    ModelVersion,
    RegisteredModel,
    Run,
    ServingMetric,
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
            "run_count": e.runs.count(),  # type: ignore[attr-defined]
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


@ml_router.post(
    "/experiments/{experiment_id}/runs", auth=require_permission("write:ml")
)
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
    models_list = RegisteredModel.objects.filter(tenant_id=tenant_id).order_by(
        "-created_at"
    )
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "description": m.description,
            "version_count": m.versions.count(),  # type: ignore[attr-defined]
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

    last_version = (
        ModelVersion.objects.filter(registered_model=model).order_by("-version").first()
    )
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


@ml_router.put(
    "/model-versions/{version_id}/stage", auth=require_permission("write:ml")
)
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

    # If transitioning to production, check if approval is needed
    if new_stage == ModelVersion.STAGE_PRODUCTION:
        from apps.approvals.services import ApprovalService

        user = get_current_user(request)
        approval = ApprovalService.request_deployment_approval(
            tenant_id=tenant_id,
            model_version_id=str(mv.id),
            model_name=mv.registered_model.name,
            version=mv.version,
            requester_id=user.user_id,
            metrics=mv.metrics,
        )

        if approval.status == "pending":
            raise HttpError(
                403,
                f"Production deployment requires approval. "
                f"Approval request {approval.id} has been created.",
            )

    mv.stage = new_stage
    mv.save(update_fields=["stage"])
    return {"id": str(mv.id), "version": mv.version, "stage": mv.stage}


# ── Model Serving ────────────────────────────────────────────────────────────


@ml_router.get("/endpoints")
def list_endpoints(request):
    """List model serving endpoints."""
    tenant_id = get_tenant_id(request)
    endpoints = ModelEndpoint.objects.filter(tenant_id=tenant_id).order_by(
        "-created_at"
    )
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "status": e.status,
            "model_version": str(e.model_version_id) if e.model_version_id else None,  # type: ignore[attr-defined]
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
    return {
        "id": str(endpoint.id),
        "name": endpoint.name,
        "path": endpoint.endpoint_path,
    }


@ml_router.get("/experiments/{experiment_id}/runs")
def list_experiment_runs(request, experiment_id: str):
    """List runs for a specific experiment with detailed metrics."""
    tenant_id = get_tenant_id(request)
    exp = Experiment.objects.filter(id=experiment_id, tenant_id=tenant_id).first()
    if not exp:
        raise HttpError(404, "Experiment not found")

    runs = Run.objects.filter(experiment=exp, tenant_id=tenant_id).order_by(
        "-started_at"
    )
    return {
        "experiment_id": str(exp.id),
        "experiment_name": exp.name,
        "runs": [
            {
                "id": str(r.id),
                "name": r.name,
                "status": r.status,
                "params": r.params,
                "metrics": r.metrics,
                "tags": r.tags,
                "started_at": r.started_at.isoformat(),
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
            }
            for r in runs
        ],
        "total_count": runs.count(),
    }


@ml_router.get("/models/{model_id}/versions")
def list_model_versions(request, model_id: str):
    """List all versions for a registered model."""
    tenant_id = get_tenant_id(request)
    model = RegisteredModel.objects.filter(id=model_id, tenant_id=tenant_id).first()
    if not model:
        raise HttpError(404, "Model not found")

    versions = ModelVersion.objects.filter(
        registered_model=model, tenant_id=tenant_id
    ).order_by("-version")
    return {
        "model_id": str(model.id),
        "model_name": model.name,
        "versions": [
            {
                "id": str(v.id),
                "version": v.version,
                "stage": v.stage,
                "status": v.status,
                "run_id": str(v.run_id) if v.run_id else None,  # type: ignore[attr-defined]
                "storage_path": v.storage_path,
                "metrics": v.metrics,
                "description": v.description,
                "created_at": v.created_at.isoformat(),
            }
            for v in versions
        ],
        "total_count": versions.count(),
    }


@ml_router.post("/models/{model_id}/deploy", auth=require_permission("write:ml"))
def deploy_model(request, model_id: str, payload: dict[str, Any]):
    """Deploy a model version to a serving endpoint."""
    tenant_id = get_tenant_id(request)
    model = RegisteredModel.objects.filter(id=model_id, tenant_id=tenant_id).first()
    if not model:
        raise HttpError(404, "Model not found")

    version_id = payload.get("version_id")
    if not version_id:
        raise HttpError(400, "version_id is required")

    mv = ModelVersion.objects.filter(
        id=version_id, registered_model=model, tenant_id=tenant_id
    ).first()
    if not mv:
        raise HttpError(404, "Model version not found")

    endpoint_name = payload.get("endpoint_name", model.name)
    config = payload.get("config", {})

    # Create or update serving endpoint
    endpoint, created = ModelEndpoint.objects.update_or_create(
        tenant_id=tenant_id,
        name=endpoint_name,
        defaults={
            "model_version": mv,
            "status": ModelEndpoint.STATUS_ACTIVE,
            "config": config,
            "endpoint_path": f"/v1/ml/predict/{endpoint_name}",
        },
    )

    # Promote version to production if requested — requires approval
    if payload.get("promote_to_production", False):
        from apps.approvals.services import ApprovalService

        user = get_current_user(request)
        approval = ApprovalService.request_deployment_approval(
            tenant_id=tenant_id,
            model_version_id=str(mv.id),
            model_name=model.name,
            version=mv.version,
            requester_id=user.user_id,
            metrics=mv.metrics,
        )

        if approval.status == "approved":
            mv.stage = ModelVersion.STAGE_PRODUCTION
            mv.save(update_fields=["stage"])
        else:
            return {
                "id": str(endpoint.id),
                "name": endpoint.name,
                "status": endpoint.status,
                "endpoint_path": endpoint.endpoint_path,
                "model_version": mv.version,
                "action": "created" if created else "updated",
                "approval_request_id": str(approval.id),
                "approval_status": approval.status,
                "message": (
                    f"Endpoint created/updated but production deployment "
                    f"requires approval. Request {approval.id} is {approval.status}."
                ),
            }

    return {
        "id": str(endpoint.id),
        "name": endpoint.name,
        "status": endpoint.status,
        "endpoint_path": endpoint.endpoint_path,
        "model_version": mv.version,
        "action": "created" if created else "updated",
    }


@ml_router.get("/endpoints/{endpoint_id}/metrics")
def get_endpoint_metrics(request, endpoint_id: str):
    """Get metrics for a model serving endpoint."""
    tenant_id = get_tenant_id(request)
    endpoint = ModelEndpoint.objects.filter(id=endpoint_id, tenant_id=tenant_id).first()
    if not endpoint:
        raise HttpError(404, "Endpoint not found")

    model_version_info = None
    if endpoint.model_version_id:  # type: ignore[attr-defined]
        mv = endpoint.model_version
        model_version_info = {
            "id": str(mv.id),
            "version": mv.version,
            "stage": mv.stage,
            "model_name": mv.registered_model.name,
        }

    return {
        "id": str(endpoint.id),
        "name": endpoint.name,
        "status": endpoint.status,
        "endpoint_path": endpoint.endpoint_path,
        "invocation_count": endpoint.invocation_count,
        "avg_latency_ms": endpoint.avg_latency_ms,
        "config": endpoint.config,
        "model_version": model_version_info,
        "uptime_info": {
            "created_at": endpoint.created_at.isoformat(),
            "updated_at": endpoint.updated_at.isoformat(),
        },
    }


# ── Prediction Endpoints ────────────────────────────────────────────────────


@ml_router.post("/predict/{endpoint_name}", auth=require_permission("write:ml"))
def predict(request, endpoint_name: str, payload: dict[str, Any]):
    """
    Real-time prediction endpoint.

    Accepts input data and routes to the loaded model for the named endpoint.
    Returns prediction results with latency information.

    Body::

        {"input_data": [1, 2, 3, 4]}  or  {"input_data": {"features": [...]}}
    """
    tenant_id = get_tenant_id(request)
    endpoint = ModelEndpoint.objects.filter(
        name=endpoint_name, tenant_id=tenant_id
    ).first()
    if not endpoint:
        raise HttpError(404, f"Endpoint '{endpoint_name}' not found")

    input_data = payload.get("input_data")
    if input_data is None:
        raise HttpError(400, "input_data is required in the request body")

    try:
        from apps.ml_platform.serving import get_serving_engine

        engine = get_serving_engine()
        result = engine.predict(str(endpoint.id), input_data)
        return result
    except ValueError as exc:
        raise HttpError(404, str(exc))
    except RuntimeError as exc:
        raise HttpError(422, str(exc))
    except Exception as exc:
        logger.exception("Prediction failed for endpoint %s", endpoint_name)
        raise HttpError(500, f"Prediction failed: {exc}")


@ml_router.post("/predict-batch/{endpoint_name}", auth=require_permission("write:ml"))
def predict_batch(request, endpoint_name: str, payload: dict[str, Any]):
    """
    Batch prediction via Temporal workflow.

    Submits a dataset to the batch prediction workflow. Returns immediately
    with workflow tracking information.

    Body::

        {"input_dataset": [{"features": [1,2]}, {"features": [3,4]}, ...]}
    """
    tenant_id = get_tenant_id(request)
    endpoint = ModelEndpoint.objects.filter(
        name=endpoint_name, tenant_id=tenant_id
    ).first()
    if not endpoint:
        raise HttpError(404, f"Endpoint '{endpoint_name}' not found")

    input_dataset = payload.get("input_dataset")
    if not input_dataset or not isinstance(input_dataset, list):
        raise HttpError(400, "input_dataset (list) is required in the request body")

    try:
        from apps.ml_platform.serving import get_serving_engine

        engine = get_serving_engine()
        result = engine.batch_predict(str(endpoint.id), input_dataset)
        return result
    except ValueError as exc:
        raise HttpError(404, str(exc))
    except Exception as exc:
        logger.exception("Batch prediction failed for endpoint %s", endpoint_name)
        raise HttpError(500, f"Batch prediction failed: {exc}")


# ── Deployment Monitoring & Management ───────────────────────────────────────


@ml_router.get("/deployments/{deployment_id}/metrics")
def get_deployment_metrics(request, deployment_id: str):
    """
    Get serving performance metrics for a deployment.

    Returns latency percentiles (p50/p95/p99), throughput, error rate,
    and request counts from the most recent metric buckets.
    """
    tenant_id = get_tenant_id(request)
    endpoint = ModelEndpoint.objects.filter(
        id=deployment_id, tenant_id=tenant_id
    ).first()
    if not endpoint:
        raise HttpError(404, "Deployment not found")

    metrics = ServingMetric.objects.filter(
        deployment=endpoint
    ).order_by("-timestamp")[:60]  # Last 60 minutes

    return {
        "deployment_id": str(endpoint.id),
        "deployment_name": endpoint.name,
        "total_invocations": endpoint.invocation_count,
        "avg_latency_ms": endpoint.avg_latency_ms,
        "metrics": [
            {
                "timestamp": m.timestamp.isoformat(),
                "latency_p50": m.latency_p50,
                "latency_p95": m.latency_p95,
                "latency_p99": m.latency_p99,
                "throughput_rps": m.throughput_rps,
                "error_rate": m.error_rate,
                "request_count": m.request_count,
            }
            for m in metrics
        ],
    }


@ml_router.get("/deployments/{deployment_id}/drift")
def get_deployment_drift(request, deployment_id: str):
    """
    Get drift reports for a deployment.

    Returns per-feature drift measurements including metric type,
    computed value, threshold, and drift status.
    """
    tenant_id = get_tenant_id(request)
    endpoint = ModelEndpoint.objects.filter(
        id=deployment_id, tenant_id=tenant_id
    ).first()
    if not endpoint:
        raise HttpError(404, "Deployment not found")

    try:
        from apps.ml_platform.drift import get_drift_detector

        detector = get_drift_detector()
        report = detector.generate_drift_report(deployment_id)
        return report
    except ValueError as exc:
        raise HttpError(404, str(exc))


@ml_router.post(
    "/deployments/{deployment_id}/rollback", auth=require_permission("write:ml")
)
def rollback_deployment(request, deployment_id: str, payload: dict[str, Any] | None = None):
    """
    Rollback a deployment to the previous model version.

    Finds the current production version, demotes it, and promotes the
    previous version. Updates the endpoint to point to the new version.

    Body (optional)::

        {"target_version_id": "uuid-of-specific-version"}  — if omitted, auto-detects previous
    """
    tenant_id = get_tenant_id(request)
    endpoint = ModelEndpoint.objects.filter(
        id=deployment_id, tenant_id=tenant_id
    ).first()
    if not endpoint:
        raise HttpError(404, "Deployment not found")

    if not endpoint.model_version_id:
        raise HttpError(400, "Deployment has no model version to rollback from")

    current_mv = endpoint.model_version
    payload = payload or {}

    # Determine target version
    target_version_id = payload.get("target_version_id")
    if target_version_id:
        target_mv = ModelVersion.objects.filter(
            id=target_version_id,
            registered_model=current_mv.registered_model,
            tenant_id=tenant_id,
        ).first()
        if not target_mv:
            raise HttpError(404, "Target model version not found")
    else:
        # Auto-find the previous version
        target_mv = (
            ModelVersion.objects.filter(
                registered_model=current_mv.registered_model,
                version__lt=current_mv.version,
                tenant_id=tenant_id,
            )
            .order_by("-version")
            .first()
        )
        if not target_mv:
            raise HttpError(
                400, "No previous version available for rollback"
            )

    # Demote current version
    current_mv.stage = ModelVersion.STAGE_ARCHIVED
    current_mv.save(update_fields=["stage", "updated_at"])

    # Promote target version
    target_mv.stage = ModelVersion.STAGE_PRODUCTION
    target_mv.save(update_fields=["stage", "updated_at"])

    # Update endpoint
    endpoint.model_version = target_mv
    endpoint.save(update_fields=["model_version", "updated_at"])

    # Evict old model from serving cache (best-effort)
    try:
        from apps.ml_platform.serving import get_serving_engine

        engine = get_serving_engine()
        from apps.ml_platform.serving import _model_cache

        _model_cache.remove(str(current_mv.id))
        # Pre-load the rollback target
        engine.load_model(str(target_mv.id))
    except Exception:
        logger.debug("Cache management during rollback failed", exc_info=True)

    return {
        "deployment_id": str(endpoint.id),
        "deployment_name": endpoint.name,
        "action": "rollback",
        "from_version": current_mv.version,
        "to_version": target_mv.version,
        "to_version_id": str(target_mv.id),
    }


def _get_latest_stage(model: RegisteredModel) -> str:
    """Get the stage of the latest version."""
    latest = model.versions.order_by("-version").first()  # type: ignore[attr-defined]
    return latest.stage if latest else "none"


# ── Agent Definition endpoints ──────────────────────────────────────────────


@ml_router.get("/agents", auth=require_permission("read:ml"))
def list_agents(request):
    """List all agent definitions."""
    from apps.ml_platform.models import AgentDefinition

    tenant_id = get_tenant_id(request)
    agents = AgentDefinition.objects.filter(tenant_id=tenant_id).order_by("-created_at")
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "status": a.status,
            "model": a.model_name,
            "tools_count": len(a.tools),
            "created_at": a.created_at.isoformat(),
        }
        for a in agents
    ]


@ml_router.post("/agents", auth=require_permission("write:ml"))
def create_agent(request, payload: dict[str, Any]):
    """Create a new agent definition."""
    from apps.ml_platform.models import AgentDefinition

    tenant_id = get_tenant_id(request)
    agent = AgentDefinition.objects.create(
        tenant_id=tenant_id,
        name=payload.get("name", ""),
        description=payload.get("description", ""),
        system_prompt=payload.get("system_prompt", ""),
        model_provider=payload.get("model_provider", "groq"),
        model_name=payload.get("model_name", "openai/gpt-oss-120b"),
        temperature=payload.get("temperature", 0.1),
        max_tokens=payload.get("max_tokens", 4096),
        tools=payload.get("tools", []),
        guardrails=payload.get("guardrails", {}),
    )
    return {"id": str(agent.id), "name": agent.name, "status": agent.status}


@ml_router.get("/agents/{agent_id}", auth=require_permission("read:ml"))
def get_agent(request, agent_id: str):
    """Get agent definition with evaluations."""
    from apps.ml_platform.models import AgentDefinition

    tenant_id = get_tenant_id(request)
    agent = AgentDefinition.objects.filter(id=agent_id, tenant_id=tenant_id).first()
    if not agent:
        raise HttpError(404, "Agent not found")
    evals = agent.evaluations.all().order_by("-completed_at")[:10]  # type: ignore[attr-defined]
    return {
        "id": str(agent.id),
        "name": agent.name,
        "status": agent.status,
        "system_prompt": agent.system_prompt,
        "model_provider": agent.model_provider,
        "model_name": agent.model_name,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "tools": agent.tools,
        "guardrails": agent.guardrails,
        "evaluations": [
            {
                "id": str(e.id),
                "name": e.name,
                "status": e.status,
                "overall_score": e.overall_score,
                "run_count": e.run_count,
            }
            for e in evals
        ],
    }


@ml_router.put("/agents/{agent_id}", auth=require_permission("write:ml"))
def update_agent(request, agent_id: str, payload: dict[str, Any]):
    """Update an agent definition."""
    from apps.ml_platform.models import AgentDefinition

    tenant_id = get_tenant_id(request)
    agent = AgentDefinition.objects.filter(id=agent_id, tenant_id=tenant_id).first()
    if not agent:
        raise HttpError(404, "Agent not found")
    for field in [
        "name",
        "description",
        "system_prompt",
        "model_provider",
        "model_name",
        "temperature",
        "max_tokens",
        "tools",
        "guardrails",
        "status",
    ]:
        if field in payload:
            setattr(agent, field, payload[field])
    agent.save()
    return {"id": str(agent.id), "name": agent.name, "status": agent.status}


@ml_router.delete("/agents/{agent_id}", auth=require_permission("write:ml"))
def delete_agent(request, agent_id: str):
    """Delete an agent definition."""
    from apps.ml_platform.models import AgentDefinition

    tenant_id = get_tenant_id(request)
    deleted, _ = AgentDefinition.objects.filter(
        id=agent_id, tenant_id=tenant_id
    ).delete()
    if not deleted:
        raise HttpError(404, "Agent not found")
    return {"status": "deleted"}


# ── Agent Evaluation endpoints ──────────────────────────────────────────────


@ml_router.post("/agents/{agent_id}/evaluations", auth=require_permission("write:ml"))
def create_evaluation(request, agent_id: str, payload: dict[str, Any]):
    """Create a new evaluation for an agent."""
    from apps.ml_platform.models import AgentDefinition, AgentEvaluation

    tenant_id = get_tenant_id(request)
    agent = AgentDefinition.objects.filter(id=agent_id, tenant_id=tenant_id).first()
    if not agent:
        raise HttpError(404, "Agent not found")
    evaluation = AgentEvaluation.objects.create(
        tenant_id=tenant_id,
        agent=agent,
        name=payload.get("name", f"eval-{agent.name}"),
        test_cases=payload.get("test_cases", []),
        judge_model=payload.get("judge_model", "openai/gpt-oss-120b"),
    )
    return {
        "id": str(evaluation.id),
        "name": evaluation.name,
        "status": evaluation.status,
    }


@ml_router.get("/agents/{agent_id}/evaluations", auth=require_permission("read:ml"))
def list_evaluations(request, agent_id: str):
    """List evaluations for an agent."""
    from apps.ml_platform.models import AgentEvaluation

    tenant_id = get_tenant_id(request)
    evals = AgentEvaluation.objects.filter(
        agent_id=agent_id, tenant_id=tenant_id
    ).order_by("-created_at")
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "status": e.status,
            "overall_score": e.overall_score,
            "run_count": e.run_count,
            "passed_count": e.passed_count,
        }
        for e in evals
    ]


@ml_router.post("/evaluations/{eval_id}/run", auth=require_permission("execute:ml"))
def run_evaluation(request, eval_id: str):
    """Run an evaluation against its test cases."""
    from apps.ml_platform.models import AgentEvaluation

    tenant_id = get_tenant_id(request)
    evaluation = AgentEvaluation.objects.filter(id=eval_id, tenant_id=tenant_id).first()
    if not evaluation:
        raise HttpError(404, "Evaluation not found")

    from django.utils import timezone

    evaluation.status = "running"
    evaluation.started_at = timezone.now()
    evaluation.save(update_fields=["status", "started_at"])

    results = []
    total_score = 0.0
    passed = 0

    for tc in evaluation.test_cases:
        input_text = tc.get("input", "")
        expected = tc.get("expected", "")
        try:
            from apps.intent.engine import get_intent_engine

            engine = get_intent_engine()
            plan = engine.generate_plan(input_text, tenant_id)
            exec_result = engine.execute_plan(plan, tenant_id)
            output = json.dumps(exec_result, default=str)[:2000]
            score = 1.0 if exec_result.get("steps") else 0.0
            if score >= 0.8:
                passed += 1
            total_score += score
            results.append(
                {
                    "input": input_text,
                    "expected": expected,
                    "output": output,
                    "score": score,
                    "tools_used": [s.get("tool", "") for s in plan.steps],
                }
            )
        except Exception as exc:
            results.append(
                {
                    "input": input_text,
                    "expected": expected,
                    "output": f"Error: {exc}",
                    "score": 0.0,
                }
            )

    evaluation.results = results
    evaluation.run_count = len(results)
    evaluation.passed_count = passed
    evaluation.overall_score = total_score / len(results) if results else 0.0
    evaluation.status = "completed"
    evaluation.completed_at = timezone.now()
    evaluation.save()

    return {
        "id": str(evaluation.id),
        "status": evaluation.status,
        "overall_score": evaluation.overall_score,
        "run_count": evaluation.run_count,
        "passed_count": evaluation.passed_count,
    }
