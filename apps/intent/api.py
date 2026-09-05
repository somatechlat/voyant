"""Intent Engine API — REST endpoints for natural language intent translation."""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

intent_router = Router(tags=["intent"], auth=require_permission("read:*"))


@intent_router.post("/intent/query")
def query_intent(request, payload: dict[str, Any]):
    """Translate natural language intent into an execution plan.

    The Intent Engine:
    1. Classifies the intent type (query, pipeline, scraper, analyze)
    2. Resolves the tenant's ontology schema
    3. Calls Groq LLM to generate a structured execution plan
    4. Validates the plan against the ontology
    5. Returns the plan (optionally executes it)
    """
    from apps.intent.engine import get_intent_engine

    intent_text = payload.get("intent", "")
    if not intent_text:
        raise HttpError(400, "intent is required")

    tenant_id = get_tenant_id(request)
    engine = get_intent_engine()

    # Generate plan
    plan = engine.generate_plan(intent_text, tenant_id)

    # Optionally execute
    execute = payload.get("execute", False)
    if execute:
        result = engine.execute_plan(plan, tenant_id)
        return {"plan": plan.to_dict(), "execution": result}

    return {"plan": plan.to_dict()}


@intent_router.post("/intent/execute")
def execute_intent(request, payload: dict[str, Any]):
    """Generate AND execute an intent plan in one call."""
    from apps.intent.engine import get_intent_engine

    intent_text = payload.get("intent", "")
    if not intent_text:
        raise HttpError(400, "intent is required")

    tenant_id = get_tenant_id(request)
    engine = get_intent_engine()

    plan = engine.generate_plan(intent_text, tenant_id)
    result = engine.execute_plan(plan, tenant_id)

    return {"plan": plan.to_dict(), "execution": result}


@intent_router.get("/intent/config")
def get_intent_config(request):
    """Get current Intent Engine configuration."""
    from apps.core.config import get_settings

    s = get_settings()
    return {
        "provider": s.llm_provider,
        "model": s.llm_model,
        "api_url": s.llm_api_url,
        "temperature": s.llm_temperature,
        "max_tokens": s.llm_max_tokens,
        "timeout_seconds": s.llm_timeout_seconds,
        "cache_enabled": s.llm_cache_enabled,
        "engine_enabled": s.intent_engine_enabled,
    }


@intent_router.put("/intent/config", auth=require_permission("write:settings"))
def update_intent_config(request, payload: dict[str, Any]):
    """Update Intent Engine configuration at runtime.

    Changes are persisted to SystemSetting model and take effect
    after the next request (no restart needed).
    """
    from apps.core.models import SystemSetting

    allowed_keys = {
        "llm_provider", "llm_model", "llm_api_url", "llm_api_key",
        "llm_temperature", "llm_max_tokens", "llm_timeout_seconds",
        "llm_cache_enabled", "intent_engine_enabled",
    }

    updated = []
    for key, value in payload.items():
        if key not in allowed_keys:
            continue

        setting, _ = SystemSetting.objects.get_or_create(
            key=key,
            defaults={
                "value": str(value),
                "value_type": _infer_type(value),
                "description": f"Intent Engine config: {key}",
                "is_secret": "key" in key.lower(),
            },
        )
        setting.value = str(value)
        setting.save(update_fields=["value", "updated_at"])
        updated.append(key)

    # Clear plan cache on config change
    from apps.intent.engine import get_intent_engine
    engine = get_intent_engine()
    engine._plan_cache.clear()

    return {"updated": updated, "status": "ok"}


@intent_router.get("/intent/cache/stats")
def get_cache_stats(request):
    """Get Intent Engine cache statistics."""
    from apps.intent.engine import get_intent_engine

    engine = get_intent_engine()
    return {
        "cached_plans": len(engine._plan_cache),
        "cache_enabled": engine._settings.llm_cache_enabled,
    }


@intent_router.post("/intent/cache/clear", auth=require_permission("write:settings"))
def clear_cache(request):
    """Clear the Intent Engine plan cache."""
    from apps.intent.engine import get_intent_engine

    engine = get_intent_engine()
    count = len(engine._plan_cache)
    engine._plan_cache.clear()
    return {"cleared": count, "status": "ok"}


def _infer_type(value: Any) -> str:
    """Infer SystemSetting value type from Python type."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "float"
    return "string"
