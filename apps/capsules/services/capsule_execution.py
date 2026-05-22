"""
Capsule Execution Service.

Handles parameter substitution, validation, and dispatch to UPTP/Temporal.
Includes capability whitelist enforcement and structured audit logging.
"""

from __future__ import annotations

import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional

from jinja2.sandbox import SandboxedEnvironment

from apps.capsules.models import Capsule, CapsuleInstallation, CapsuleInstance
from apps.capsules.services.capsule_core import create_capsule_instance
from apps.core.config import get_settings

logger = logging.getLogger(__name__)

# Background thread pool for Temporal workflow dispatch (avoids blocking sync workers)
_capsule_dispatch_pool = ThreadPoolExecutor(max_workers=10, thread_name_prefix="capsule_dispatch")

# Sandboxed Jinja2 for parameter substitution
_jinja_env = SandboxedEnvironment()


def validate_parameters(capsule: Capsule, parameter_values: dict) -> tuple[bool, Optional[str]]:
    """Validate runtime parameters against the capsule's parameter schema."""
    schema = capsule.parameters_schema
    if not schema:
        return True, None

    for param_name, param_def in schema.items():
        if param_def.get("required", False) and param_name not in parameter_values:
            return False, f"Missing required parameter: {param_name}"

        if param_name in parameter_values:
            value = parameter_values[param_name]
            param_type = param_def.get("type", "string")

            if param_type == "string" and not isinstance(value, str):
                return False, f"Parameter {param_name} must be a string"
            elif param_type == "integer" and not isinstance(value, int):
                return False, f"Parameter {param_name} must be an integer"
            elif param_type == "number" and not isinstance(value, (int, float)):
                return False, f"Parameter {param_name} must be a number"
            elif param_type == "boolean" and not isinstance(value, bool):
                return False, f"Parameter {param_name} must be a boolean"

            if "options" in param_def and value not in param_def["options"]:
                return False, f"Parameter {param_name} must be one of {param_def['options']}"

    return True, None


def merge_parameters(
    capsule: Capsule,
    installation: Optional[CapsuleInstallation],
    runtime_values: dict,
) -> dict:
    """Merge parameter defaults -> installation overrides -> runtime values."""
    merged: dict = {}

    schema = capsule.parameters_schema or {}
    for name, defn in schema.items():
        if "default" in defn:
            merged[name] = defn["default"]

    if installation:
        merged.update(installation.parameter_overrides)

    merged.update(runtime_values)
    return merged


def substitute_parameters(
    template_dict: dict,
    parameters: dict,
    step_results: Optional[dict] = None,
) -> dict:
    """Substitute {{var}} expressions in a dict using Jinja2 sandboxed."""
    step_results = step_results or {}

    def _resolve(value: Any) -> Any:
        if isinstance(value, str):
            try:
                return _jinja_env.from_string(value).render(
                    **parameters, steps=step_results
                )
            except Exception as exc:
                logger.warning("Template substitution failed for '%s': %s", value, exc)
                return value
        elif isinstance(value, dict):
            return {k: _resolve(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_resolve(item) for item in value]
        return value

    return _resolve(template_dict)


def _check_capabilities(capsule: Capsule, action: str) -> None:
    """Enforce capability whitelist before executing any action."""
    whitelist = capsule.capabilities_whitelist or []
    if whitelist and action not in whitelist:
        raise PermissionError(
            f"Action '{action}' not in capsule '{capsule.name}' capabilities whitelist: {whitelist}"
        )


def execute_capsule_sync(
    capsule: Capsule,
    parameter_values: dict,
    tenant_id: str,
    session_id: Optional[str] = None,
) -> dict:
    """Execute a simple capsule synchronously via UPTP."""
    valid, error = validate_parameters(capsule, parameter_values)
    if not valid:
        raise ValueError(error)

    instance = create_capsule_instance(
        capsule=capsule,
        session_id=session_id or f"sync-{uuid.uuid4().hex[:8]}",
        parameter_values=parameter_values,
        triggered_by="api",
    )

    graph = capsule.execution_graph or []
    if len(graph) == 1:
        step = graph[0]
        _check_capabilities(capsule, step["action"])
        resolved_params = substitute_parameters(step.get("params", {}), parameter_values)

        from apps.uptp_core.engine import UPTPExecutionEngine
        from apps.uptp_core.schemas import TemplateCategory, TemplateExecutionRequest

        request = TemplateExecutionRequest(
            template_id=step["action"],
            category=TemplateCategory.INGESTION,
            params=resolved_params,
            tenant_id=tenant_id,
            job_name=f"capsule_sync_{step['action']}",
        )
        result = UPTPExecutionEngine.dispatch_execution(request)

        instance.status = CapsuleInstance.STATUS_COMPLETED
        instance.state = {"result": result}
        instance.save()
        return result

    return dispatch_capsule_workflow(capsule, parameter_values, tenant_id, session_id)


def dispatch_capsule_workflow(
    capsule: Capsule,
    parameter_values: dict,
    tenant_id: str,
    session_id: Optional[str] = None,
) -> dict:
    """Dispatch a capsule to Temporal workflow for multi-step execution."""
    valid, error = validate_parameters(capsule, parameter_values)
    if not valid:
        raise ValueError(error)

    # Validate all steps are in capabilities whitelist before dispatching
    for step in capsule.execution_graph or []:
        _check_capabilities(capsule, step.get("action", ""))

    instance = create_capsule_instance(
        capsule=capsule,
        session_id=session_id or f"wf-{uuid.uuid4().hex[:8]}",
        parameter_values=parameter_values,
        triggered_by="mcp",
    )

    job_urn = f"urn:voyant:job:{tenant_id}:{capsule.name}:{instance.id}"
    instance.job_urn = job_urn
    instance.save(update_fields=["job_urn"])

    def _dispatch():
        try:
            from apps.core.api_utils import run_async
            from apps.core.lib.temporal_client import get_temporal_client
            from apps.worker.workflows.capsule_workflow import CapsuleWorkflow

            settings = get_settings()
            client = run_async(get_temporal_client)
            run_async(
                client.start_workflow,
                CapsuleWorkflow.run,
                {
                    "capsule_id": str(capsule.id),
                    "parameter_values": parameter_values,
                    "tenant_id": tenant_id,
                    "instance_id": str(instance.id),
                },
                id=job_urn,
                task_queue=settings.temporal_task_queue,
            )
            logger.info("Capsule workflow dispatched: %s", job_urn)
        except Exception as exc:
            logger.error("Failed to dispatch capsule workflow %s: %s", job_urn, exc)

    _capsule_dispatch_pool.submit(_dispatch)

    return {
        "status": "accepted",
        "dispatch_type": "temporal_capsule_workflow_started",
        "job_urn": job_urn,
        "instance_id": str(instance.id),
        "message": f"Capsule {capsule.name} workflow started.",
    }


class CapsuleExecutionService:
    """High-level service for capsule execution (used by UPTP engine)."""

    def run_capsule(
        self,
        installation_id: str,
        parameter_values: dict,
        tenant_id: str,
        session_id: str = "",
    ) -> dict:
        """Execute a capsule via its installation ID."""
        installation = CapsuleInstallation.objects.select_related("capsule").get(
            id=installation_id, tenant_id=tenant_id, is_enabled=True
        )
        capsule = installation.capsule
        merged = merge_parameters(capsule, installation, parameter_values)
        valid, error = validate_parameters(capsule, merged)
        if not valid:
            raise ValueError(error)

        graph = capsule.execution_graph or []
        if len(graph) == 1:
            return execute_capsule_sync(capsule, merged, tenant_id, session_id)
        return dispatch_capsule_workflow(capsule, merged, tenant_id, session_id)

    def run_capsule_by_id(
        self,
        capsule_id: str,
        parameter_values: dict,
        tenant_id: str,
        session_id: str = "",
    ) -> dict:
        """Execute a capsule directly by ID (no installation required)."""
        from apps.capsules.services.capsule_registry import load_capsule_by_id

        capsule = load_capsule_by_id(capsule_id, tenant_id)
        merged = merge_parameters(capsule, None, parameter_values)
        valid, error = validate_parameters(capsule, merged)
        if not valid:
            raise ValueError(error)

        graph = capsule.execution_graph or []
        if len(graph) == 1:
            return execute_capsule_sync(capsule, merged, tenant_id, session_id)
        return dispatch_capsule_workflow(capsule, merged, tenant_id, session_id)


def get_instance_status(instance_id: str) -> dict:
    """Get the status of a capsule instance."""
    try:
        instance = CapsuleInstance.objects.select_related("capsule").get(id=instance_id)
    except CapsuleInstance.DoesNotExist:
        raise ValueError(f"Instance {instance_id} not found")

    return {
        "instance_id": str(instance.id),
        "capsule_name": instance.capsule.name,
        "status": instance.status,
        "job_urn": instance.job_urn,
        "state": instance.state,
        "parameter_values": instance.parameter_values,
        "started_at": instance.started_at.isoformat() if instance.started_at else None,
        "completed_at": instance.completed_at.isoformat() if instance.completed_at else None,
        "error_message": instance.error_message,
    }
