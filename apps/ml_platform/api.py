"""ML Platform API — REST endpoints for experiments, models, and serving."""

from __future__ import annotations

import json
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
    evals = agent.evaluations.all().order_by("-completed_at")[:10]
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
    for field in ["name", "description", "system_prompt", "model_provider", "model_name", "temperature", "max_tokens", "tools", "guardrails", "status"]:
        if field in payload:
            setattr(agent, field, payload[field])
    agent.save()
    return {"id": str(agent.id), "name": agent.name, "status": agent.status}


@ml_router.delete("/agents/{agent_id}", auth=require_permission("write:ml"))
def delete_agent(request, agent_id: str):
    """Delete an agent definition."""
    from apps.ml_platform.models import AgentDefinition

    tenant_id = get_tenant_id(request)
    deleted, _ = AgentDefinition.objects.filter(id=agent_id, tenant_id=tenant_id).delete()
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
    return {"id": str(evaluation.id), "name": evaluation.name, "status": evaluation.status}


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
            results.append({
                "input": input_text,
                "expected": expected,
                "output": output,
                "score": score,
                "tools_used": [s.get("tool", "") for s in plan.steps],
            })
        except Exception as exc:
            results.append({
                "input": input_text,
                "expected": expected,
                "output": f"Error: {exc}",
                "score": 0.0,
            })

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
