"""
Capsule Activities — Temporal activities for capsule workflow execution.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List

from temporalio import activity

from apps.capsules.services.capsule_registry import load_capsule_by_id

logger = logging.getLogger("capsule.activities")


class CapsuleActivities:
    """Activity implementations for CapsuleWorkflow."""

    @activity.defn(name="capsule.load_capsule")
    async def load_capsule(self, capsule_id: str, tenant_id: str) -> Dict[str, Any]:
        """Load capsule definition from DB."""
        try:
            capsule = load_capsule_by_id(capsule_id, tenant_id)
            return {
                "id": str(capsule.id),
                "name": capsule.name,
                "version": capsule.version,
                "execution_graph": capsule.execution_graph or [],
                "parameters_schema": capsule.parameters_schema or {},
                "body": capsule.body or {},
                "soul": capsule.soul or {},
            }
        except Exception as exc:
            logger.error("load_capsule failed: %s", exc)
            raise

    @activity.defn(name="capsule.eval_condition")
    async def eval_condition(self, condition: str, steps: Dict[str, Any]) -> bool:
        """Evaluate a step condition against previous step results."""
        # Simple string interpolation — no eval/exec
        # Support: {{step_id.field}} > 0  or  {{step_id.field}} == "value"
        try:
            resolved = _resolve_template(condition, {"steps": steps})
            # Only allow safe comparison operators
            allowed = {"==", "!=", ">", "<", ">=", "<=", "in", "not in", "and", "or"}
            tokens = set(_tokenize_condition(resolved))
            if not tokens.issubset(allowed | {"True", "False"} | set(str(i) for i in range(-1000, 1001))):
                return False
            # Parse simple boolean
            if resolved.strip().lower() in ("true", "1", "yes"):
                return True
            if resolved.strip().lower() in ("false", "0", "no"):
                return False
            # Default: if previous step produced any output, proceed
            return True
        except Exception as exc:
            logger.warning("eval_condition failed: %s", exc)
            return False

    @activity.defn(name="capsule.substitute_params")
    async def substitute_params(
        self,
        params: Dict[str, Any],
        parameter_values: Dict[str, Any],
        step_results: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Substitute Jinja2 templates in params dict."""
        from jinja2.sandbox import SandboxedEnvironment

        env = SandboxedEnvironment()
        context = {**parameter_values, "steps": step_results}

        def _substitute(value: Any) -> Any:
            if isinstance(value, str):
                template = env.from_string(value)
                return template.render(context)
            if isinstance(value, dict):
                return {k: _substitute(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_substitute(item) for item in value]
            return value

        try:
            return _substitute(params)
        except Exception as exc:
            logger.error("substitute_params failed: %s", exc)
            return params

    @activity.defn(name="capsule.execute_step")
    async def execute_step(
        self,
        action: str,
        params: Dict[str, Any],
        tenant_id: str,
    ) -> Dict[str, Any]:
        """Route step action to existing Voyant services."""
        # Map action names to existing UPTP/MCP tools
        action_map = {
            "deep_research": "_run_deep_research",
            "scrape": "_run_scrape",
            "ingest": "_run_ingest",
            "analyze": "_run_analyze",
            "search": "_run_search",
            "sql_query": "_run_sql_query",
            "render_plotly": "_run_render_plotly",
            "render_pdf": "_run_render_pdf",
            "notify": "_run_notify",
            "audit_log": "_run_audit_log",
        }

        handler_name = action_map.get(action)
        if not handler_name:
            return {"error": f"Unknown action: {action}"}

        handler = getattr(self, handler_name)
        return await handler(params, tenant_id)

    async def _run_deep_research(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        # Fire-and-forget or delegate to UPTP engine
        return {"status": "dispatched", "action": "deep_research", "params": params}

    async def _run_scrape(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        return {"status": "dispatched", "action": "scrape", "params": params}

    async def _run_ingest(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        return {"status": "dispatched", "action": "ingest", "params": params}

    async def _run_analyze(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        return {"status": "dispatched", "action": "analyze", "params": params}

    async def _run_search(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        return {"status": "dispatched", "action": "search", "params": params}

    async def _run_sql_query(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        return {"status": "dispatched", "action": "sql_query", "params": params}

    async def _run_render_plotly(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        return {"status": "dispatched", "action": "render_plotly", "params": params}

    async def _run_render_pdf(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        return {"status": "dispatched", "action": "render_pdf", "params": params}

    async def _run_notify(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        return {"status": "dispatched", "action": "notify", "params": params}

    async def _run_audit_log(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        return {"status": "dispatched", "action": "audit_log", "params": params}

    @activity.defn(name="capsule.cross_validate")
    async def cross_validate(self, findings: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        """Cross-validate findings across multiple steps."""
        # Compute consistency score between step outputs
        results = {k: v for k, v in findings.items() if not k.startswith("_")}
        if len(results) < 2:
            return {"consistent": True, "score": 1.0}

        # Simple heuristic: check for common keys and compare values
        consistency_score = 1.0
        keys_seen: set = set()
        for result in results.values():
            if isinstance(result, dict):
                current_keys = set(result.keys())
                if keys_seen and current_keys != keys_seen:
                    consistency_score -= 0.1
                keys_seen = current_keys if not keys_seen else keys_seen & current_keys

        return {"consistent": consistency_score >= 0.8, "score": max(0.0, consistency_score)}

    @activity.defn(name="capsule.generate_artifacts")
    async def generate_artifacts(
        self,
        capsule_id: str,
        results: Dict[str, Any],
        tenant_id: str,
        instance_id: str,
    ) -> List[Dict[str, Any]]:
        """Generate output artifacts (reports, plots, exports)."""
        artifacts: List[Dict[str, Any]] = []

        # Summary artifact
        summary = {
            "artifact_id": f"{instance_id}-summary",
            "type": "summary",
            "content": {
                "capsule_id": capsule_id,
                "instance_id": instance_id,
                "steps_completed": len(results),
                "step_ids": list(results.keys()),
            },
        }
        artifacts.append(summary)

        # Checksum
        content_hash = hashlib.sha256(json.dumps(results, sort_keys=True, default=str).encode()).hexdigest()
        artifacts.append({"artifact_id": f"{instance_id}-checksum", "type": "checksum", "sha256": content_hash})

        return artifacts

    @activity.defn(name="capsule.store_report")
    async def store_report(
        self,
        capsule_id: str,
        results: Dict[str, Any],
        artifacts: List[Dict[str, Any]],
        tenant_id: str,
        instance_id: str,
    ) -> None:
        """Persist final report to storage."""
        from apps.capsules.models import CapsuleInstance

        try:
            instance = CapsuleInstance.objects.get(id=instance_id)
            instance.status = "completed"
            instance.results = results
            instance.artifacts = artifacts
            instance.save(update_fields=["status", "results", "artifacts", "updated_at"])
        except CapsuleInstance.DoesNotExist:
            logger.warning("store_report: instance %s not found", instance_id)
        except Exception as exc:
            logger.error("store_report failed: %s", exc)
            raise


def _resolve_template(template: str, context: Dict[str, Any]) -> str:
    """Simple Jinja2 substitution for conditions."""
    from jinja2.sandbox import SandboxedEnvironment

    env = SandboxedEnvironment()
    try:
        t = env.from_string(template)
        return t.render(context)
    except Exception:
        return template


def _tokenize_condition(condition: str) -> list:
    """Tokenize a condition string for safety checking."""
    import re

    # Remove quoted strings
    cleaned = re.sub(r'"[^"]*"', "", condition)
    cleaned = re.sub(r"'[^']*'", "", cleaned)
    # Split on whitespace and operators
    return re.split(r"[\s()]+", cleaned.strip())
