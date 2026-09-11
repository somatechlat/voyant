"""
MLflow-Compatible API — Drop-in REST endpoints for MLflow Python client.

Provides /api/2.0/mlflow/* endpoints that mirror the MLflow Tracking Server
API surface, enabling `mlflow.set_tracking_uri("voyant")` compatibility.

Part of Voyant v4.0 Phase 3.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from django.db.models import Q
from ninja import Router
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission
from apps.ml_platform.models import (
    Experiment,
    ModelVersion,
    RegisteredModel,
    Run,
)

mlflow_router = Router(tags=["mlflow-compat"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _ts_ms(dt: datetime | None) -> int | None:
    """Convert a datetime to epoch milliseconds (MLflow convention)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _experiment_to_mlflow(exp: Experiment) -> dict[str, Any]:
    """Serialize an Experiment to MLflow response format."""
    tags = exp.tags or {}
    tag_list = (
        [{"key": k, "value": v} for k, v in tags.items()]
        if isinstance(tags, dict)
        else tags
    )
    return {
        "experiment_id": str(exp.id),
        "name": exp.name,
        "artifact_location": exp.artifact_location or "",
        "lifecycle_stage": "active",
        "last_update_time": _ts_ms(exp.updated_at),
        "creation_time": _ts_ms(exp.created_at),
        "tags": tag_list,
    }


def _run_info_to_mlflow(run: Run) -> dict[str, Any]:
    """Serialize Run info to MLflow RunInfo format."""
    status_map = {
        "running": "RUNNING",
        "finished": "FINISHED",
        "failed": "FAILED",
        "killed": "KILLED",
    }
    return {
        "run_uuid": str(run.id),
        "run_id": str(run.id),
        "run_name": run.name or "",
        "experiment_id": str(run.experiment_id),  # type: ignore[attr-defined]
        "status": status_map.get(run.status, run.status.upper()),
        "start_time": _ts_ms(run.started_at),
        "end_time": _ts_ms(run.ended_at),
        "artifact_uri": "",
        "lifecycle_stage": "active",
    }


def _run_to_mlflow(run: Run) -> dict[str, Any]:
    """Serialize full Run (info + data) to MLflow format."""
    params = run.params or {}
    metrics = run.metrics or {}
    tags = run.tags or {}

    param_list = [{"key": k, "value": str(v)} for k, v in params.items()]
    metric_list = [
        {"key": k, "value": v, "timestamp": _now_ms(), "step": 0}
        for k, v in metrics.items()
    ]
    tag_list = [{"key": k, "value": str(v)} for k, v in tags.items()]

    return {
        "info": _run_info_to_mlflow(run),
        "data": {
            "params": param_list,
            "metrics": metric_list,
            "tags": tag_list,
        },
    }


def _registered_model_to_mlflow(model: RegisteredModel) -> dict[str, Any]:
    """Serialize RegisteredModel to MLflow format."""
    tags = model.tags or {}
    tag_list = (
        [{"key": k, "value": v} for k, v in tags.items()]
        if isinstance(tags, dict)
        else tags
    )

    versions = ModelVersion.objects.filter(registered_model=model).order_by("version")
    version_list = [_model_version_brief(mv) for mv in versions]

    return {
        "name": model.name,
        "description": model.description or "",
        "creation_timestamp": _ts_ms(model.created_at),
        "last_updated_timestamp": _ts_ms(model.updated_at),
        "tags": tag_list,
        "latest_versions": version_list,
    }


def _model_version_brief(mv: ModelVersion) -> dict[str, Any]:
    """Brief model version for list endpoints."""
    stage_map = {
        "none": "None",
        "staging": "Staging",
        "production": "Production",
        "archived": "Archived",
    }
    return {
        "version": str(mv.version),
        "current_stage": stage_map.get(mv.stage, mv.stage),
        "run_id": str(mv.run_id) if mv.run_id else "",  # type: ignore[attr-defined]
        "status": "READY",
        "name": mv.registered_model.name if hasattr(mv, "registered_model") else "",
    }


def _model_version_to_mlflow(mv: ModelVersion) -> dict[str, Any]:
    """Full model version serialization."""
    stage_map = {
        "none": "None",
        "staging": "Staging",
        "production": "Production",
        "archived": "Archived",
    }
    return {
        "version": str(mv.version),
        "name": mv.registered_model.name,
        "current_stage": stage_map.get(mv.stage, mv.stage),
        "description": mv.description or "",
        "status": "READY",
        "run_id": str(mv.run_id) if mv.run_id else "",  # type: ignore[attr-defined]
        "run_link": "",
        "source": mv.storage_path or "",
        "creation_timestamp": _ts_ms(mv.created_at),
        "last_updated_timestamp": _ts_ms(mv.updated_at),
    }


def _mlflow_tags_to_dict(tags: list[dict] | None) -> dict[str, Any]:
    """Convert MLflow [{key, value}] tag list to a plain dict."""
    if not tags:
        return {}
    return {t["key"]: t["value"] for t in tags if "key" in t and "value" in t}


def _parse_filter(filter_str: str | None) -> Q:
    """Parse a simple MLflow filter string into a Django Q object.

    Supports: `name = 'value'`, `name LIKE '%value%'`
    Returns empty Q (match-all) for unparseable input.
    """
    if not filter_str:
        return Q()

    import re

    # Match patterns like: name = 'value' or name LIKE '%value%'
    exact_match = re.match(r"(\w+)\s*=\s*'([^']*)'", filter_str)
    if exact_match:
        field, value = exact_match.group(1), exact_match.group(2)
        if field == "name":
            return Q(name=value)
        return Q()

    like_match = re.match(r"(\w+)\s+LIKE\s+'([^']*)'", filter_str, re.IGNORECASE)
    if like_match:
        field, pattern = like_match.group(1), like_match.group(2)
        django_pattern = pattern.replace("%", "").replace("_", "?")
        if field == "name":
            return Q(name__icontains=django_pattern)
        return Q()

    return Q()


def _parse_run_filter(filter_str: str | None) -> Q:
    """Parse MLflow run search filter into Django Q object.

    Supports: `status = 'RUNNING'`, `tags.key = 'value'`,
              `params.key = 'value'`, `metrics.key > 0.5`
    """
    if not filter_str:
        return Q()

    import re

    q = Q()
    # Split on AND (case-insensitive)
    clauses = re.split(r"\s+AND\s+", filter_str, flags=re.IGNORECASE)

    for clause in clauses:
        clause = clause.strip()

        # status = 'value'
        m = re.match(r"status\s*=\s*'([^']*)'", clause)
        if m:
            status_map = {
                "RUNNING": "running",
                "FINISHED": "finished",
                "FAILED": "failed",
                "KILLED": "killed",
            }
            q &= Q(status=status_map.get(m.group(1).upper(), m.group(1).lower()))
            continue

        # tags.`key` = 'value' or tags.key = 'value'
        m = re.match(r"tags\.`?([^`']+?)`?\s*=\s*'([^']*)'", clause)
        if m:
            # JSONField containment for tags
            q &= Q(tags__contains={m.group(1): m.group(2)})
            continue

        # params.`key` = 'value'
        m = re.match(r"params\.`?([^`']+?)`?\s*=\s*'([^']*)'", clause)
        if m:
            q &= Q(params__contains={m.group(1): m.group(2)})
            continue

    return q


# ── Experiment Endpoints ─────────────────────────────────────────────────────


@mlflow_router.post(
    "/experiments/create",
    auth=require_permission("write:ml"),
)
def mlflow_create_experiment(request, payload: dict[str, Any]):
    """Create an experiment (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    name = payload.get("name")
    if not name:
        raise HttpError(400, "Experiment name is required")

    if Experiment.objects.filter(tenant_id=tenant_id, name=name).exists():
        raise HttpError(400, f"Experiment '{name}' already exists")

    exp = Experiment.objects.create(
        tenant_id=tenant_id,
        name=name,
        artifact_location=payload.get("artifact_location", ""),
        tags=_mlflow_tags_to_dict(payload.get("tags")),
    )
    return {"experiment_id": str(exp.id)}


@mlflow_router.get("/experiments/get")
def mlflow_get_experiment(
    request,
    experiment_id: str = None,
    experiment_name: str = None,  # type: ignore[reportArgumentType]
):
    """Get experiment by ID or name (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)

    if experiment_id:
        exp = Experiment.objects.filter(id=experiment_id, tenant_id=tenant_id).first()
    elif experiment_name:
        exp = Experiment.objects.filter(
            name=experiment_name, tenant_id=tenant_id
        ).first()
    else:
        raise HttpError(400, "Either experiment_id or experiment_name is required")

    if not exp:
        raise HttpError(404, "Experiment not found")

    return {"experiment": _experiment_to_mlflow(exp)}


@mlflow_router.get("/experiments/search")
def mlflow_search_experiments(
    request,
    filter: str = None,  # type: ignore[reportArgumentType]
    max_results: int = 1000,
    order_by: str = None,  # type: ignore[reportArgumentType]
    page_token: str = None,  # type: ignore[reportArgumentType]
):
    """Search experiments (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    qs = Experiment.objects.filter(tenant_id=tenant_id)

    # Apply filter
    q = _parse_filter(filter)
    if q:
        qs = qs.filter(q)

    # Apply ordering
    if order_by:
        for ob in order_by.split(","):
            ob = ob.strip()
            if ob.startswith("name"):
                qs = qs.order_by("name")
            elif ob.startswith("creation_time"):
                qs = qs.order_by("created_at")
            elif ob.startswith("last_update_time"):
                qs = qs.order_by("updated_at")
    else:
        qs = qs.order_by("name")

    # Pagination via offset from page_token
    offset = 0
    if page_token:
        try:
            offset = int(page_token)
        except (ValueError, TypeError):
            offset = 0

    experiments = list(qs[offset : offset + max_results])
    next_token = str(offset + max_results) if len(experiments) == max_results else None

    result: dict[str, Any] = {
        "experiments": [_experiment_to_mlflow(e) for e in experiments],
    }
    if next_token:
        result["next_page_token"] = next_token

    return result


@mlflow_router.post(
    "/experiments/update",
    auth=require_permission("write:ml"),
)
def mlflow_update_experiment(request, payload: dict[str, Any]):
    """Update an experiment (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    exp_id = payload.get("experiment_id")
    if not exp_id:
        raise HttpError(400, "experiment_id is required")

    exp = Experiment.objects.filter(id=exp_id, tenant_id=tenant_id).first()
    if not exp:
        raise HttpError(404, "Experiment not found")

    if "new_name" in payload:
        new_name = payload["new_name"]
        if (
            Experiment.objects.filter(tenant_id=tenant_id, name=new_name)
            .exclude(id=exp.id)
            .exists()
        ):
            raise HttpError(400, f"Experiment '{new_name}' already exists")
        exp.name = new_name

    if "tags" in payload:
        exp.tags = _mlflow_tags_to_dict(payload["tags"])

    exp.save()
    return {}


@mlflow_router.post(
    "/experiments/delete",
    auth=require_permission("write:ml"),
)
def mlflow_delete_experiment(request, payload: dict[str, Any]):
    """Delete (soft-delete) an experiment (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    exp_id = payload.get("experiment_id")
    if not exp_id:
        raise HttpError(400, "experiment_id is required")

    deleted, _ = Experiment.objects.filter(id=exp_id, tenant_id=tenant_id).delete()
    if not deleted:
        raise HttpError(404, "Experiment not found")
    return {}


# ── Run Endpoints ────────────────────────────────────────────────────────────


@mlflow_router.post(
    "/runs/create",
    auth=require_permission("write:ml"),
)
def mlflow_create_run(request, payload: dict[str, Any]):
    """Create a run (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    exp_id = payload.get("experiment_id")
    if not exp_id:
        raise HttpError(400, "experiment_id is required")

    exp = Experiment.objects.filter(id=exp_id, tenant_id=tenant_id).first()
    if not exp:
        raise HttpError(404, "Experiment not found")

    run_name = payload.get("run_name", "")
    tags = _mlflow_tags_to_dict(payload.get("tags"))

    run = Run.objects.create(
        tenant_id=tenant_id,
        experiment=exp,
        name=run_name,
        tags=tags,
    )
    return {"run": _run_info_to_mlflow(run)}


@mlflow_router.get("/runs/get")
def mlflow_get_run(request, run_id: str = None, run_uuid: str = None):  # type: ignore[reportArgumentType]
    """Get a run (MLflow-compatible)."""
    rid = run_id or run_uuid
    if not rid:
        raise HttpError(400, "run_id is required")

    tenant_id = get_tenant_id(request)
    run = Run.objects.filter(id=rid, tenant_id=tenant_id).first()
    if not run:
        raise HttpError(404, "Run not found")

    return {"run": _run_to_mlflow(run)}


@mlflow_router.post(
    "/runs/update",
    auth=require_permission("write:ml"),
)
def mlflow_update_run(request, payload: dict[str, Any]):
    """Update a run (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    rid = payload.get("run_id") or payload.get("run_uuid")
    if not rid:
        raise HttpError(400, "run_id is required")

    run = Run.objects.filter(id=rid, tenant_id=tenant_id).first()
    if not run:
        raise HttpError(404, "Run not found")

    status_str = payload.get("status")
    if status_str:
        status_map = {
            "RUNNING": "running",
            "FINISHED": "finished",
            "FAILED": "failed",
            "KILLED": "killed",
        }
        run.status = status_map.get(status_str.upper(), status_str.lower())

        if run.status in ("finished", "failed", "killed"):
            end_time = payload.get("end_time")
            if end_time:
                run.ended_at = datetime.fromtimestamp(end_time / 1000, tz=UTC)
            else:
                run.ended_at = datetime.now(UTC)

    if "run_name" in payload:
        run.name = payload["run_name"]

    run.save()
    return {"run_info": _run_info_to_mlflow(run)}


@mlflow_router.post("/runs/search")
def mlflow_search_runs(request, payload: dict[str, Any]):
    """Search runs (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    experiment_ids = payload.get("experiment_ids", [])

    if experiment_ids:
        qs = Run.objects.filter(
            experiment_id__in=experiment_ids,
            tenant_id=tenant_id,
        )
    else:
        qs = Run.objects.filter(tenant_id=tenant_id)

    # Apply filter
    filter_str = payload.get("filter")
    q = _parse_run_filter(filter_str)
    if q:
        qs = qs.filter(q)

    # Ordering
    order_by = payload.get("order_by", [])
    if order_by:
        for ob in order_by:
            if ob.startswith("start_time"):
                qs = qs.order_by("-started_at")
            elif ob.startswith("end_time"):
                qs = qs.order_by("-ended_at")
    else:
        qs = qs.order_by("-started_at")

    # Pagination
    max_results = payload.get("max_results", 1000)
    offset = 0
    page_token = payload.get("page_token")
    if page_token:
        try:
            offset = int(page_token)
        except (ValueError, TypeError):
            offset = 0

    runs = list(qs[offset : offset + max_results])
    next_token = str(offset + max_results) if len(runs) == max_results else None

    result: dict[str, Any] = {
        "runs": [_run_to_mlflow(r) for r in runs],
    }
    if next_token:
        result["next_page_token"] = next_token

    return result


@mlflow_router.post(
    "/runs/delete",
    auth=require_permission("write:ml"),
)
def mlflow_delete_run(request, payload: dict[str, Any]):
    """Delete a run (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    rid = payload.get("run_id") or payload.get("run_uuid")
    if not rid:
        raise HttpError(400, "run_id is required")

    deleted, _ = Run.objects.filter(id=rid, tenant_id=tenant_id).delete()
    if not deleted:
        raise HttpError(404, "Run not found")
    return {}


@mlflow_router.post(
    "/runs/log-metric",
    auth=require_permission("write:ml"),
)
def mlflow_log_metric(request, payload: dict[str, Any]):
    """Log a single metric for a run (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    rid = payload.get("run_id") or payload.get("run_uuid")
    key = payload.get("key")
    value = payload.get("value")

    if not rid:
        raise HttpError(400, "run_id is required")
    if not key:
        raise HttpError(400, "key is required")
    if value is None:
        raise HttpError(400, "value is required")

    run = Run.objects.filter(id=rid, tenant_id=tenant_id).first()
    if not run:
        raise HttpError(404, "Run not found")

    metrics = run.metrics or {}
    metrics[key] = value
    run.metrics = metrics
    run.save(update_fields=["metrics", "updated_at"])
    return {}


@mlflow_router.post(
    "/runs/log-parameter",
    auth=require_permission("write:ml"),
)
def mlflow_log_parameter(request, payload: dict[str, Any]):
    """Log a single parameter for a run (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    rid = payload.get("run_id") or payload.get("run_uuid")
    key = payload.get("key")
    value = payload.get("value")

    if not rid:
        raise HttpError(400, "run_id is required")
    if not key:
        raise HttpError(400, "key is required")

    run = Run.objects.filter(id=rid, tenant_id=tenant_id).first()
    if not run:
        raise HttpError(404, "Run not found")

    params = run.params or {}
    params[key] = value
    run.params = params
    run.save(update_fields=["params", "updated_at"])
    return {}


@mlflow_router.post(
    "/runs/log-batch",
    auth=require_permission("write:ml"),
)
def mlflow_log_batch(request, payload: dict[str, Any]):
    """Log metrics, params, and tags in a single batch (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    rid = payload.get("run_id") or payload.get("run_uuid")
    if not rid:
        raise HttpError(400, "run_id is required")

    run = Run.objects.filter(id=rid, tenant_id=tenant_id).first()
    if not run:
        raise HttpError(404, "Run not found")

    updated_fields = set()

    # Batch metrics
    batch_metrics = payload.get("metrics", [])
    if batch_metrics:
        metrics = run.metrics or {}
        for m in batch_metrics:
            metrics[m["key"]] = m["value"]
        run.metrics = metrics
        updated_fields.add("metrics")

    # Batch params
    batch_params = payload.get("params", [])
    if batch_params:
        params = run.params or {}
        for p in batch_params:
            params[p["key"]] = p["value"]
        run.params = params
        updated_fields.add("params")

    # Batch tags
    batch_tags = payload.get("tags", [])
    if batch_tags:
        tags = run.tags or {}
        for t in batch_tags:
            tags[t["key"]] = t["value"]
        run.tags = tags
        updated_fields.add("tags")

    if updated_fields:
        updated_fields.add("updated_at")
        run.save(update_fields=list(updated_fields))

    return {}


# ── Registered Model Endpoints ───────────────────────────────────────────────


@mlflow_router.post(
    "/registered-models/create",
    auth=require_permission("write:ml"),
)
def mlflow_create_registered_model(request, payload: dict[str, Any]):
    """Create a registered model (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    name = payload.get("name")
    if not name:
        raise HttpError(400, "Model name is required")

    if RegisteredModel.objects.filter(tenant_id=tenant_id, name=name).exists():
        raise HttpError(400, f"Registered model '{name}' already exists")

    model = RegisteredModel.objects.create(
        tenant_id=tenant_id,
        name=name,
        description=payload.get("description", ""),
        tags=_mlflow_tags_to_dict(payload.get("tags")),
    )
    return {"registered_model": _registered_model_to_mlflow(model)}


@mlflow_router.get("/registered-models/get")
def mlflow_get_registered_model(request, name: str = None):  # type: ignore[reportArgumentType]
    """Get a registered model by name (MLflow-compatible)."""
    if not name:
        raise HttpError(400, "name query parameter is required")

    tenant_id = get_tenant_id(request)
    model = RegisteredModel.objects.filter(name=name, tenant_id=tenant_id).first()
    if not model:
        raise HttpError(404, f"Registered model '{name}' not found")

    return {"registered_model": _registered_model_to_mlflow(model)}


@mlflow_router.get("/registered-models/search")
def mlflow_search_registered_models(
    request,
    filter: str = None,  # type: ignore[reportArgumentType]
    max_results: int = 100,
    order_by: str = None,  # type: ignore[reportArgumentType]
    page_token: str = None,  # type: ignore[reportArgumentType]
):
    """Search registered models (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    qs = RegisteredModel.objects.filter(tenant_id=tenant_id)

    q = _parse_filter(filter)
    if q:
        qs = qs.filter(q)

    if order_by:
        for ob in order_by.split(","):
            ob = ob.strip()
            if "name" in ob:
                qs = qs.order_by("name")
    else:
        qs = qs.order_by("name")

    offset = 0
    if page_token:
        try:
            offset = int(page_token)
        except (ValueError, TypeError):
            offset = 0

    models = list(qs[offset : offset + max_results])
    next_token = str(offset + max_results) if len(models) == max_results else None

    result: dict[str, Any] = {
        "registered_models": [_registered_model_to_mlflow(m) for m in models],
    }
    if next_token:
        result["next_page_token"] = next_token

    return result


# ── Model Version Endpoints ──────────────────────────────────────────────────


@mlflow_router.post(
    "/model-versions/create",
    auth=require_permission("write:ml"),
)
def mlflow_create_model_version(request, payload: dict[str, Any]):
    """Create a model version (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    name = payload.get("name")
    if not name:
        raise HttpError(400, "Registered model name is required")

    model = RegisteredModel.objects.filter(name=name, tenant_id=tenant_id).first()
    if not model:
        raise HttpError(404, f"Registered model '{name}' not found")

    last_version = (
        ModelVersion.objects.filter(registered_model=model).order_by("-version").first()
    )
    new_version = (last_version.version + 1) if last_version else 1

    # Resolve run_id if provided
    run_id = payload.get("run_id")
    run_obj = None
    if run_id:
        run_obj = Run.objects.filter(id=run_id, tenant_id=tenant_id).first()

    mv = ModelVersion.objects.create(
        tenant_id=tenant_id,
        registered_model=model,
        version=new_version,
        run=run_obj,
        storage_path=payload.get("source", ""),
        description=payload.get("description", ""),
    )
    return {"model_version": _model_version_to_mlflow(mv)}


@mlflow_router.get("/model-versions/get")
def mlflow_get_model_version(
    request,
    name: str = None,  # type: ignore[reportArgumentType]
    version: str = None,  # type: ignore[reportArgumentType]
):
    """Get a model version (MLflow-compatible)."""
    if not name or not version:
        raise HttpError(400, "Both name and version query parameters are required")

    tenant_id = get_tenant_id(request)
    model = RegisteredModel.objects.filter(name=name, tenant_id=tenant_id).first()
    if not model:
        raise HttpError(404, f"Registered model '{name}' not found")

    try:
        ver_int = int(version)
    except (ValueError, TypeError):
        raise HttpError(400, "version must be an integer")

    mv = ModelVersion.objects.filter(
        registered_model=model, version=ver_int, tenant_id=tenant_id
    ).first()
    if not mv:
        raise HttpError(404, f"Model version {version} not found for '{name}'")

    return {"model_version": _model_version_to_mlflow(mv)}


@mlflow_router.post(
    "/model-versions/update",
    auth=require_permission("write:ml"),
)
def mlflow_update_model_version(request, payload: dict[str, Any]):
    """Update a model version (MLflow-compatible)."""
    tenant_id = get_tenant_id(request)
    name = payload.get("name")
    version = payload.get("version")

    if not name or not version:
        raise HttpError(400, "Both name and version are required")

    model = RegisteredModel.objects.filter(name=name, tenant_id=tenant_id).first()
    if not model:
        raise HttpError(404, f"Registered model '{name}' not found")

    try:
        ver_int = int(version)
    except (ValueError, TypeError):
        raise HttpError(400, "version must be an integer")

    mv = ModelVersion.objects.filter(
        registered_model=model, version=ver_int, tenant_id=tenant_id
    ).first()
    if not mv:
        raise HttpError(404, f"Model version {version} not found for '{name}'")

    if "description" in payload:
        mv.description = payload["description"]

    if "stage" in payload:
        stage_map = {
            "None": "none",
            "Staging": "staging",
            "Production": "production",
            "Archived": "archived",
        }
        new_stage = stage_map.get(payload["stage"], payload["stage"].lower())
        mv.stage = new_stage

    mv.save()
    return {"model_version": _model_version_to_mlflow(mv)}
