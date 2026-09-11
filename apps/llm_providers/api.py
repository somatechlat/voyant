"""LLM Providers API — Admin endpoints for managing LLM providers and models."""

from __future__ import annotations

import logging
from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.core.security.auth import require_permission
from apps.llm_providers.models import ActiveLLMConfig, LLMModel, LLMProvider

logger = logging.getLogger(__name__)

llm_router = Router(tags=["llm-providers"], auth=require_permission("read:*"))


# ── Providers ────────────────────────────────────────────────────────────────


@llm_router.get("/providers")
def list_providers(request):
    """List all LLM providers with their models."""
    providers = LLMProvider.objects.all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "slug": p.slug,
            "description": p.description,
            "status": p.status,
            "api_base_url": p.api_base_url,
            "supports_chat": p.supports_chat,
            "supports_streaming": p.supports_streaming,
            "supports_json_mode": p.supports_json_mode,
            "supports_function_calling": p.supports_function_calling,
            "supports_vision": p.supports_vision,
            "is_system": p.is_system,
            "model_count": p.models.count(),  # type: ignore[attr-defined]
            "models": [
                {
                    "id": str(m.id),
                    "name": m.name,
                    "display_name": m.display_name,
                    "status": m.status,
                    "context_window": m.context_window,
                    "max_output_tokens": m.max_output_tokens,
                    "supports_vision": m.supports_vision,
                    "supports_function_calling": m.supports_function_calling,
                    "supports_json_mode": m.supports_json_mode,
                    "supports_reasoning": m.supports_reasoning,
                    "input_price": m.input_price,
                    "output_price": m.output_price,
                    "is_default": m.is_default,
                    "use_count": m.use_count,
                }
                for m in p.models.all()  # type: ignore[attr-defined]
            ],
        }
        for p in providers
    ]


@llm_router.post("/providers", auth=require_permission("write:settings"))
def create_provider(request, payload: dict[str, Any]):
    """Create a new LLM provider."""
    import slugify

    name = payload.get("name", "")
    if not name:
        raise HttpError(400, "name is required")

    slug = payload.get("slug") or slugify.slugify(name)

    if LLMProvider.objects.filter(slug=slug).exists():
        raise HttpError(409, f"Provider with slug '{slug}' already exists")

    provider = LLMProvider.objects.create(
        name=name,
        slug=slug,
        description=payload.get("description", ""),
        api_base_url=payload.get("api_base_url", ""),
        api_key=payload.get("api_key", ""),
        supports_chat=payload.get("supports_chat", True),
        supports_streaming=payload.get("supports_streaming", True),
        supports_json_mode=payload.get("supports_json_mode", False),
        supports_function_calling=payload.get("supports_function_calling", False),
        supports_vision=payload.get("supports_vision", False),
        default_headers=payload.get("default_headers", {}),
        rate_limit_rpm=payload.get("rate_limit_rpm", 0),
        timeout_seconds=payload.get("timeout_seconds", 30),
    )

    # Seed models if provided
    models_data = payload.get("models", [])
    for m in models_data:
        LLMModel.objects.create(
            provider=provider,
            name=m.get("name", ""),
            display_name=m.get("display_name", ""),
            description=m.get("description", ""),
            context_window=m.get("context_window", 4096),
            max_output_tokens=m.get("max_output_tokens", 4096),
            supports_vision=m.get("supports_vision", False),
            supports_function_calling=m.get("supports_function_calling", False),
            supports_json_mode=m.get("supports_json_mode", False),
            supports_reasoning=m.get("supports_reasoning", False),
            input_price=m.get("input_price", 0.0),
            output_price=m.get("output_price", 0.0),
            is_default=m.get("is_default", False),
        )

    return {
        "id": str(provider.id),
        "name": provider.name,
        "slug": provider.slug,
        "models_created": len(models_data),
    }


@llm_router.put("/providers/{provider_id}", auth=require_permission("write:settings"))
def update_provider(request, provider_id: str, payload: dict[str, Any]):
    """Update an LLM provider."""
    provider = LLMProvider.objects.filter(id=provider_id).first()
    if not provider:
        raise HttpError(404, "Provider not found")

    for field in [
        "name",
        "description",
        "api_base_url",
        "api_key",
        "status",
        "supports_chat",
        "supports_streaming",
        "supports_json_mode",
        "supports_function_calling",
        "supports_vision",
        "rate_limit_rpm",
        "timeout_seconds",
    ]:
        if field in payload:
            setattr(provider, field, payload[field])

    provider.save()
    return {"id": str(provider.id), "name": provider.name, "status": "updated"}


@llm_router.delete(
    "/providers/{provider_id}", auth=require_permission("write:settings")
)
def delete_provider(request, provider_id: str):
    """Delete an LLM provider (system providers cannot be deleted)."""
    provider = LLMProvider.objects.filter(id=provider_id).first()
    if not provider:
        raise HttpError(404, "Provider not found")
    if provider.is_system:
        raise HttpError(403, "System providers cannot be deleted")
    provider.delete()
    return {"status": "deleted", "provider_id": provider_id}


# ── Models ───────────────────────────────────────────────────────────────────


@llm_router.get("/models")
def list_models(request, provider_id: str | None = None):
    """List all models across providers."""
    qs = LLMModel.objects.select_related("provider").all()
    if provider_id:
        qs = qs.filter(provider_id=provider_id)

    return [
        {
            "id": str(m.id),
            "provider_name": m.provider.name,
            "provider_slug": m.provider.slug,
            "name": m.name,
            "display_name": m.display_name,
            "description": m.description,
            "status": m.status,
            "context_window": m.context_window,
            "max_output_tokens": m.max_output_tokens,
            "supports_vision": m.supports_vision,
            "supports_function_calling": m.supports_function_calling,
            "supports_json_mode": m.supports_json_mode,
            "supports_reasoning": m.supports_reasoning,
            "input_price": m.input_price,
            "output_price": m.output_price,
            "is_default": m.is_default,
            "use_count": m.use_count,
            "avg_latency_ms": m.avg_latency_ms,
        }
        for m in qs
    ]


@llm_router.post(
    "/providers/{provider_id}/models", auth=require_permission("write:settings")
)
def add_model(request, provider_id: str, payload: dict[str, Any]):
    """Add a model to a provider."""
    provider = LLMProvider.objects.filter(id=provider_id).first()
    if not provider:
        raise HttpError(404, "Provider not found")

    model = LLMModel.objects.create(
        provider=provider,
        name=payload.get("name", ""),
        display_name=payload.get("display_name", ""),
        description=payload.get("description", ""),
        context_window=payload.get("context_window", 4096),
        max_output_tokens=payload.get("max_output_tokens", 4096),
        supports_vision=payload.get("supports_vision", False),
        supports_function_calling=payload.get("supports_function_calling", False),
        supports_json_mode=payload.get("supports_json_mode", False),
        supports_reasoning=payload.get("supports_reasoning", False),
        input_price=payload.get("input_price", 0.0),
        output_price=payload.get("output_price", 0.0),
        is_default=payload.get("is_default", False),
    )

    return {"id": str(model.id), "name": model.name, "provider": provider.name}


# ── Active Configuration ─────────────────────────────────────────────────────


@llm_router.get("/active")
def get_active_config(request):
    """Get the active LLM configuration for each purpose."""
    configs = ActiveLLMConfig.objects.select_related("provider", "model").all()
    result = {}
    for c in configs:
        result[c.purpose] = {
            "provider_id": str(c.provider_id) if c.provider_id else None,  # type: ignore[attr-defined]
            "provider_name": c.provider.name if c.provider else None,
            "model_id": str(c.model_id) if c.model_id else None,  # type: ignore[attr-defined]
            "model_name": c.model.name if c.model else None,
            "temperature": c.temperature,
            "max_tokens": c.max_tokens,
            "timeout_seconds": c.timeout_seconds,
        }
    return result


@llm_router.put("/active/{purpose}", auth=require_permission("write:settings"))
def set_active_config(request, purpose: str, payload: dict[str, Any]):
    """Set the active LLM for a purpose (intent, analysis, scraper, general)."""
    provider_id = payload.get("provider_id")
    model_id = payload.get("model_id")

    provider = (
        LLMProvider.objects.filter(id=provider_id).first() if provider_id else None
    )
    model = LLMModel.objects.filter(id=model_id).first() if model_id else None

    config, _ = ActiveLLMConfig.objects.update_or_create(
        purpose=purpose,
        defaults={
            "provider": provider,
            "model": model,
            "temperature": payload.get("temperature", 0.1),
            "max_tokens": payload.get("max_tokens", 4096),
            "timeout_seconds": payload.get("timeout_seconds", 30),
        },
    )

    # Also update the Intent Engine if purpose is 'intent'
    if purpose == "intent" and provider and model:
        _update_intent_engine_config(provider, model, payload)

    return {
        "purpose": purpose,
        "provider": provider.name if provider else None,
        "model": model.name if model else None,
        "status": "active",
    }


def _update_intent_engine_config(provider: LLMProvider, model: LLMModel, payload: dict):
    """Update the Intent Engine's LLM configuration."""
    from apps.intent.engine import get_intent_engine

    engine = get_intent_engine()
    engine._settings = engine._settings.model_copy(
        update={
            "llm_provider": provider.slug,
            "llm_api_url": provider.api_base_url,
            "llm_api_key": provider.api_key,
            "llm_model": model.name,
            "llm_temperature": payload.get("temperature", 0.1),
            "llm_max_tokens": payload.get("max_tokens", 4096),
            "llm_timeout_seconds": payload.get("timeout_seconds", 30),
        }
    )
    engine._plan_cache.clear()


@llm_router.post("/test", auth=require_permission("write:settings"))
def test_provider(request, payload: dict[str, Any]):
    """Test an LLM provider connection by sending a simple request."""
    import httpx

    provider_id = payload.get("provider_id")
    model_id = payload.get("model_id")

    provider = (
        LLMProvider.objects.filter(id=provider_id).first() if provider_id else None
    )
    model = LLMModel.objects.filter(id=model_id).first() if model_id else None

    if not provider:
        raise HttpError(404, "Provider not found")

    model_name = model.name if model else payload.get("model", "gpt-3.5-turbo")

    try:
        response = httpx.post(
            f"{provider.api_base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "messages": [{"role": "user", "content": "Say 'OK' and nothing else."}],
                "max_tokens": 10,
                "temperature": 0,
            },
            timeout=provider.timeout_seconds,
        )
        response.raise_for_status()
        data = response.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        usage = data.get("usage", {})

        return {
            "status": "success",
            "provider": provider.name,
            "model": model_name,
            "response": content[:200],
            "usage": usage,
            "latency_ms": response.elapsed.total_seconds() * 1000,
        }
    except Exception as exc:
        return {
            "status": "error",
            "provider": provider.name,
            "model": model_name,
            "error": str(exc),
        }
