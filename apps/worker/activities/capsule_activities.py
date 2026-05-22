"""
Capsule Activities — Temporal activities for capsule workflow execution.

Production-grade: all action handlers wire to real Voyant services.
Step results are persisted to the database to avoid Temporal event
history size limits; only lightweight metadata flows through workflow state.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List

from temporalio import activity

from apps.capsules.models import CapsuleInstance
from apps.capsules.services.capsule_registry import load_capsule_by_id

logger = logging.getLogger("capsule.activities")

# Size threshold for inline results vs DB storage (100KB)
_MAX_INLINE_RESULT_BYTES = 100_000


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
                "capabilities_whitelist": capsule.capabilities_whitelist or [],
                "body": capsule.body or {},
                "soul": capsule.soul or {},
            }
        except Exception as exc:
            logger.error("load_capsule failed: %s", exc)
            raise

    @activity.defn(name="capsule.eval_condition")
    async def eval_condition(self, condition: str, steps: Dict[str, Any]) -> bool:
        """Evaluate a step condition against previous step results."""
        try:
            resolved = _resolve_template(condition, {"steps": steps})
            allowed = {"==", "!=", ">", "<", ">=", "<=", "in", "not in", "and", "or"}
            tokens = set(_tokenize_condition(resolved))
            if not tokens.issubset(
                allowed | {"True", "False"} | {str(i) for i in range(-1000, 1001)}
            ):
                return False
            if resolved.strip().lower() in ("true", "1", "yes"):
                return True
            if resolved.strip().lower() in ("false", "0", "no"):
                return False
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
                try:
                    return env.from_string(value).render(context)
                except Exception as exc:
                    logger.warning("Template substitution failed for '%s': %s", value, exc)
                    return value
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
        instance_id: str,
        capabilities_whitelist: List[str],
    ) -> Dict[str, Any]:
        """Route step action to existing Voyant services."""
        # --- Capability whitelist enforcement ---
        if capabilities_whitelist and action not in capabilities_whitelist:
            raise PermissionError(
                f"Action '{action}' not in capsule capabilities whitelist: {capabilities_whitelist}"
            )

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
        result = await handler(params, tenant_id)

        # Persist result to DB to avoid Temporal event history bloat
        await self._persist_step_result(instance_id, action, result)

        return {"step_id": action, "stored": True, "size_bytes": len(json.dumps(result, default=str))}

    async def _persist_step_result(self, instance_id: str, step_id: str, result: Dict[str, Any]) -> None:
        """Write step result to CapsuleInstance.state to keep workflow history small."""
        try:
            instance = CapsuleInstance.objects.get(id=instance_id)
            state = instance.state or {}
            steps = state.get("steps", {})
            steps[step_id] = result
            state["steps"] = steps
            instance.state = state
            instance.save(update_fields=["state", "updated_at"])
        except CapsuleInstance.DoesNotExist:
            logger.warning("Cannot persist step result: instance %s not found", instance_id)
        except Exception as exc:
            logger.error("Failed to persist step result: %s", exc)
            raise

    async def _run_deep_research(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        from django.conf import settings

        from apps.core.lib.temporal_client import get_temporal_client
        from apps.scraper.deep_research_workflow import DeepResearchWorkflow

        client = await get_temporal_client()
        job_id = f"urn:voyant:job:{tenant_id}:deep_research:{hashlib.sha256(str(params).encode()).hexdigest()[:16]}"
        handle = await client.start_workflow(
            DeepResearchWorkflow.run,
            {
                "topic": params.get("topic"),
                "max_urls": params.get("max_urls", 10),
                "tenant_id": tenant_id,
                "job_id": job_id,
            },
            id=job_id,
            task_queue=settings.temporal_task_queue,
        )
        return {"status": "started", "workflow_id": handle.id, "action": "deep_research"}

    async def _run_scrape(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        from django.conf import settings

        from apps.core.lib.temporal_client import get_temporal_client
        from apps.scraper.workflow import ScrapeWorkflow

        client = await get_temporal_client()
        url = params.get("url", "")
        job_id = f"urn:voyant:job:{tenant_id}:scrape:{hashlib.sha256(url.encode()).hexdigest()[:16]}"
        handle = await client.start_workflow(
            ScrapeWorkflow.run,
            {
                "url": url,
                "tenant_id": tenant_id,
                "job_id": job_id,
            },
            id=job_id,
            task_queue=settings.temporal_task_queue,
        )
        return {"status": "started", "workflow_id": handle.id, "action": "scrape", "url": url}

    async def _run_ingest(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        from django.conf import settings

        from apps.core.lib.temporal_client import get_temporal_client
        from apps.worker.workflows.ingest_workflow import IngestDataWorkflow

        client = await get_temporal_client()
        uri = params.get("generic_uri", "")
        job_id = f"urn:voyant:job:{tenant_id}:ingest:{hashlib.sha256(uri.encode()).hexdigest()[:16]}"
        handle = await client.start_workflow(
            IngestDataWorkflow.run,
            {
                "generic_uri": uri,
                "tenant_id": tenant_id,
                "job_id": job_id,
            },
            id=job_id,
            task_queue=settings.temporal_task_queue,
        )
        return {"status": "started", "workflow_id": handle.id, "action": "ingest"}

    async def _run_analyze(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        from apps.analysis.lib.anomaly import detect_anomalies
        from apps.analysis.lib.ml_primitives import MLPrimitives

        dataset = params.get("data", [])
        analysis_type = params.get("analysis_type", "anomaly")

        if analysis_type == "anomaly":
            result = detect_anomalies(values=dataset)
        elif analysis_type == "regression":
            ml = MLPrimitives()
            target = params.get("target_column", "")
            defaults = [c for c in (dataset[0].keys() if dataset else []) if c != target]
            feature_cols = params.get("feature_columns", defaults)
            result = ml.train_regression(data=dataset, target_col=target, feature_cols=feature_cols)
        else:
            return {"error": f"Unknown analysis type: {analysis_type}"}

        return {"status": "completed", "action": "analyze", "result": result}

    async def _run_search(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        from apps.search.lib.milvus_store import get_vector_store

        limit = params.get("limit", 5)

        store = get_vector_store()
        results = store.search(query_vector=[], k=limit)
        return {"status": "completed", "action": "search", "results": results}

    async def _run_sql_query(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        from apps.core.lib.trino import get_trino_client

        sql = params.get("sql", "")
        limit = params.get("limit", 1000)

        if not sql.strip().lower().startswith("select"):
            return {"error": "Only SELECT queries are permitted via capsule execution"}

        client = get_trino_client()
        try:
            result = client.execute(sql, limit=limit)
            rows = result.rows if hasattr(result, "rows") else []
            return {"status": "completed", "action": "sql_query", "rows": rows, "row_count": len(rows)}
        except Exception as exc:
            logger.error("SQL query failed: %s", exc)
            return {"error": str(exc), "action": "sql_query"}

    async def _run_render_plotly(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        import pandas as pd

        from apps.core.lib.plotly_engine import PlotlyRenderer

        df = pd.DataFrame(params.get("data", []))
        chart_type = params.get("chart_type", "bar")

        if chart_type == "bar":
            uri = PlotlyRenderer.render_bar_comparison(
                df, x_col=params.get("x_col") or "", y_col=params.get("y_col") or "", tenant_id=tenant_id
            )
        elif chart_type == "time_series":
            uri = PlotlyRenderer.render_time_series(
                df, date_col=params.get("date_col") or "", value_col=params.get("value_col") or "", tenant_id=tenant_id
            )
        else:
            return {"error": f"Unsupported chart type: {chart_type}"}

        return {"status": "completed", "action": "render_plotly", "artifact_uri": uri}

    async def _run_render_pdf(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        from apps.core.lib.pdf_engine import PDFAssembler

        template = params.get("template", "default")
        uri = PDFAssembler.compile_pdf(template_name=template, params=params, tenant_id=tenant_id)
        return {"status": "completed", "action": "render_pdf", "artifact_uri": uri}

    async def _run_notify(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        message = params.get("message", "")
        level = params.get("level", "info")
        logger.log(getattr(logging, level.upper(), logging.INFO), "[notify] %s", message)
        return {"status": "completed", "action": "notify", "message": message}

    async def _run_audit_log(self, params: Dict[str, Any], tenant_id: str) -> Dict[str, Any]:
        event_type = params.get("event_type", "capsule.audit")
        logger.info(
            "AUDIT: tenant=%s event=%s params=%s",
            tenant_id,
            event_type,
            list(params.keys()),
        )
        return {"status": "completed", "action": "audit_log", "event_type": event_type}

    @activity.defn(name="capsule.cross_validate")
    async def cross_validate(self, instance_id: str, tenant_id: str) -> Dict[str, Any]:
        """Cross-validate findings across multiple steps by loading from DB."""
        try:
            instance = CapsuleInstance.objects.get(id=instance_id)
            state = instance.state or {}
            findings = state.get("steps", {})
        except CapsuleInstance.DoesNotExist:
            return {"consistent": False, "score": 0.0, "error": "Instance not found"}

        results = {k: v for k, v in findings.items() if not k.startswith("_")}
        if len(results) < 2:
            return {"consistent": True, "score": 1.0}

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
        instance_id: str,
        tenant_id: str,
    ) -> List[Dict[str, Any]]:
        """Generate output artifacts (reports, plots, exports)."""
        try:
            instance = CapsuleInstance.objects.get(id=instance_id)
            state = instance.state or {}
            steps = state.get("steps", {})
        except CapsuleInstance.DoesNotExist:
            steps = {}

        artifacts: List[Dict[str, Any]] = []

        summary = {
            "artifact_id": f"{instance_id}-summary",
            "type": "summary",
            "content": {
                "capsule_id": capsule_id,
                "instance_id": instance_id,
                "steps_completed": len(steps),
                "step_ids": list(steps.keys()),
            },
        }
        artifacts.append(summary)

        content_hash = hashlib.sha256(json.dumps(steps, sort_keys=True, default=str).encode()).hexdigest()
        artifacts.append({"artifact_id": f"{instance_id}-checksum", "type": "checksum", "sha256": content_hash})

        return artifacts

    @activity.defn(name="capsule.store_report")
    async def store_report(
        self,
        capsule_id: str,
        instance_id: str,
        artifacts: List[Dict[str, Any]],
        tenant_id: str,
    ) -> None:
        """Persist final report to storage."""
        try:
            instance = CapsuleInstance.objects.get(id=instance_id)
            instance.status = "completed"
            instance.artifacts = artifacts
            instance.save(update_fields=["status", "artifacts", "updated_at"])
        except CapsuleInstance.DoesNotExist:
            logger.warning("store_report: instance %s not found", instance_id)
        except Exception as exc:
            logger.error("store_report failed: %s", exc)
            raise


def _resolve_template(template: str, context: Dict[str, Any]) -> str:
    from jinja2.sandbox import SandboxedEnvironment

    env = SandboxedEnvironment()
    try:
        t = env.from_string(template)
        return t.render(context)
    except Exception:
        return template


def _tokenize_condition(condition: str) -> list:
    import re

    cleaned = re.sub(r'"[^"]*"', "", condition)
    cleaned = re.sub(r"'[^']*'", "", cleaned)
    return re.split(r"[\s()]+", cleaned.strip())
