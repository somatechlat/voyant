"""Intent Engine API — REST endpoints for natural language intent translation.

Hardened with:
- Per-tenant rate limiting (configurable, default 100 requests/hour)
- Per-user rate limiting (configurable, default 20 requests/minute)
- Redis-backed sliding window counters
- Proper error handling for plan validation and limit violations
"""

from __future__ import annotations

import logging
import time
from typing import Any

from ninja import Router
from ninja.errors import HttpError

from apps.core.middleware import get_tenant_id
from apps.core.security.auth import require_permission

logger = logging.getLogger(__name__)

intent_router = Router(tags=["intent"], auth=require_permission("read:*"))


# ── Rate Limiter ───────────────────────────────────────────────────────────


class RateLimiter:
    """Redis-backed sliding window rate limiter.

    Uses Redis sorted sets for precise sliding window counting.
    Falls back to allowing all requests if Redis is unavailable.
    """

    # Default limits (configurable via settings)
    TENANT_RATE_LIMIT = 100  # requests per hour per tenant
    TENANT_RATE_WINDOW = 3600  # 1 hour in seconds
    USER_RATE_LIMIT = 20  # requests per minute per user
    USER_RATE_WINDOW = 60  # 1 minute in seconds

    def __init__(self):
        self._redis = None
        self._redis_checked = False

    def _get_redis(self):
        """Lazy-init Redis connection from settings."""
        if self._redis_checked:
            return self._redis
        self._redis_checked = True
        try:
            from apps.core.config import get_settings

            settings = get_settings()
            if settings.redis_url:
                import redis

                self._redis = redis.from_url(settings.redis_url, decode_responses=True)
                # Test connection
                self._redis.ping()
        except Exception as exc:
            logger.warning("Redis not available for rate limiting: %s", exc)
            self._redis = None
        return self._redis

    def check_rate_limit(
        self,
        tenant_id: str,
        user_id: str = "",
    ) -> tuple[bool, int, str]:
        """Check if the request is within rate limits.

        Returns:
            (allowed, retry_after_seconds, reason)
            If allowed is False, retry_after_seconds indicates when to retry.
        """
        redis_client = self._get_redis()

        if redis_client is None:
            # Redis unavailable — allow request (fail open for availability)
            return True, 0, ""

        now = time.time()

        # Check tenant rate limit
        tenant_key = f"voyant:ratelimit:tenant:{tenant_id}"
        tenant_allowed, tenant_retry = self._check_window(
            redis_client,
            tenant_key,
            now,
            self.TENANT_RATE_WINDOW,
            self.TENANT_RATE_LIMIT,
        )
        if not tenant_allowed:
            return False, tenant_retry, "tenant_rate_limit"

        # Check per-user rate limit (if user_id available)
        if user_id:
            user_key = f"voyant:ratelimit:user:{user_id}"
            user_allowed, user_retry = self._check_window(
                redis_client,
                user_key,
                now,
                self.USER_RATE_WINDOW,
                self.USER_RATE_LIMIT,
            )
            if not user_allowed:
                return False, user_retry, "user_rate_limit"

        return True, 0, ""

    def _check_window(
        self,
        redis_client,
        key: str,
        now: float,
        window_seconds: int,
        max_requests: int,
    ) -> tuple[bool, int]:
        """Check a sliding window rate limit.

        Returns (allowed, retry_after_seconds).
        """
        try:
            pipe = redis_client.pipeline()
            window_start = now - window_seconds

            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current entries
            pipe.zcard(key)
            # Add current request
            pipe.zadd(key, {f"{now}": now})
            # Set TTL on the key
            pipe.expire(key, window_seconds)

            results = pipe.execute()
            current_count = results[1]

            if current_count >= max_requests:
                # Find the oldest entry to calculate retry-after
                oldest = redis_client.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(oldest[0][1] + window_seconds - now) + 1
                else:
                    retry_after = window_seconds
                return False, max(retry_after, 1)

            return True, 0

        except Exception as exc:
            logger.warning("Rate limit check failed: %s", exc)
            return True, 0  # Fail open


# Singleton rate limiter
_rate_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Get the singleton rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def _get_user_id(request) -> str:
    """Extract user ID from request context."""
    try:
        from apps.core.middleware import current_user_var

        user = current_user_var.get()
        if user and hasattr(user, "user_id"):
            return user.user_id
    except Exception:
        pass
    # Fallback: use session key or remote addr
    return request.headers.get("X-User-ID", request.META.get("REMOTE_ADDR", ""))


def _check_rate_limits(request, tenant_id: str) -> None:
    """Check rate limits and raise HttpError(429) if exceeded."""
    user_id = _get_user_id(request)
    limiter = get_rate_limiter()
    allowed, retry_after, reason = limiter.check_rate_limit(tenant_id, user_id)

    if not allowed:
        logger.warning(
            "Rate limit exceeded: tenant=%s user=%s reason=%s retry_after=%d",
            tenant_id,
            user_id,
            reason,
            retry_after,
        )
        raise RateLimitError(retry_after, reason)


class RateLimitError(HttpError):
    """Rate limit exceeded error with Retry-After header."""

    def __init__(self, retry_after: int, reason: str = ""):
        self.status_code = 429
        self.retry_after = retry_after
        self.reason = reason
        super().__init__(
            429,
            f"Rate limit exceeded ({reason}). Retry after {retry_after} seconds.",
        )


# ── API Endpoints ──────────────────────────────────────────────────────────


@intent_router.post("/intent/query")
def query_intent(request, payload: dict[str, Any]):
    """Translate natural language intent into an execution plan.

    The Intent Engine:
    1. Classifies the intent type (query, pipeline, scraper, analyze)
    2. Resolves the tenant's ontology schema
    3. Calls LLM (with failover) to generate a structured execution plan
    4. Validates the plan against limits, security, and the ontology
    5. Returns the plan (optionally executes it)

    Rate limited: 100 req/hour per tenant, 20 req/min per user.
    """
    from apps.intent.engine import (
        PlanLimitExceeded,
        PlanValidationError,
        get_intent_engine,
    )

    intent_text = payload.get("intent", "")
    if not intent_text:
        raise HttpError(400, "intent is required")

    tenant_id = get_tenant_id(request)
    _check_rate_limits(request, tenant_id)

    engine = get_intent_engine()

    try:
        plan = engine.generate_plan(intent_text, tenant_id)
    except PlanValidationError as exc:
        raise HttpError(400, f"Plan validation failed: {exc}")
    except PlanLimitExceeded as exc:
        raise HttpError(413, f"Plan exceeds limits: {exc}")

    # Optionally execute
    execute = payload.get("execute", False)
    if execute:
        result = engine.execute_plan(plan, tenant_id)
        return {"plan": plan.to_dict(), "execution": result}

    return {"plan": plan.to_dict()}


@intent_router.post("/intent/execute")
def execute_intent(request, payload: dict[str, Any]):
    """Generate AND execute an intent plan in one call.

    Rate limited: 100 req/hour per tenant, 20 req/min per user.
    """
    from apps.intent.engine import (
        PlanLimitExceeded,
        PlanValidationError,
        get_intent_engine,
    )

    intent_text = payload.get("intent", "")
    if not intent_text:
        raise HttpError(400, "intent is required")

    tenant_id = get_tenant_id(request)
    _check_rate_limits(request, tenant_id)

    engine = get_intent_engine()

    try:
        plan = engine.generate_plan(intent_text, tenant_id)
    except PlanValidationError as exc:
        raise HttpError(400, f"Plan validation failed: {exc}")
    except PlanLimitExceeded as exc:
        raise HttpError(413, f"Plan exceeds limits: {exc}")

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
        "rate_limits": {
            "tenant_per_hour": RateLimiter.TENANT_RATE_LIMIT,
            "user_per_minute": RateLimiter.USER_RATE_LIMIT,
        },
    }


@intent_router.put("/intent/config", auth=require_permission("write:settings"))
def update_intent_config(request, payload: dict[str, Any]):
    """Update Intent Engine configuration at runtime.

    Changes are persisted to SystemSetting model and take effect
    after the next request (no restart needed).
    """
    from apps.core.models import SystemSetting

    allowed_keys = {
        "llm_provider",
        "llm_model",
        "llm_api_url",
        "llm_api_key",
        "llm_temperature",
        "llm_max_tokens",
        "llm_timeout_seconds",
        "llm_cache_enabled",
        "intent_engine_enabled",
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
