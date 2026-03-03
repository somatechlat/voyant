"""
Voyant Core — Policy Enforcement.

This module provides request-level policy authorization against an external
Policy Engine (if configured). When `soma_policy_url` is not configured, all
policy checks are skipped and requests are allowed through.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional
from uuid import UUID

import httpx

from apps.core.config import get_settings
from apps.core.middleware import (
    get_authorization,
    get_request_id,
    get_soma_session_id,
    get_soma_user_id,
    get_tenant_id,
    get_traceparent,
)

logger = logging.getLogger(__name__)


# ── Exception Hierarchy ────────────────────────────────────────────────────────


class PolicyError(RuntimeError):
    """Base exception for all policy-related failures."""


class SomaIntegrationError(PolicyError):
    """Alias kept for backward compatibility with existing exception handlers."""


class SomaContextError(PolicyError):
    """Raised when required context (session ID, user ID) is missing."""


class SomaPolicyDenied(PolicyError):
    """Raised when the Policy Engine explicitly denies an action."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class SomaPolicyUnavailable(PolicyError):
    """Raised when the Policy Engine is unreachable or returns an invalid response."""


# ── Context ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PolicyContext:
    """All request context required for policy evaluation."""

    tenant_id: str
    user_id: str
    session_id: str
    request_id: str
    traceparent: str
    authorization: str

    def headers(self) -> dict[str, str]:
        """Build HTTP headers for forwarding to the Policy Engine."""
        h: dict[str, str] = {}
        if self.tenant_id:
            h["X-Tenant-ID"] = self.tenant_id
        if self.user_id:
            h["X-User-ID"] = self.user_id
        if self.session_id:
            h["X-Soma-Session-ID"] = self.session_id
        if self.request_id:
            h["X-Request-ID"] = self.request_id
        if self.traceparent:
            h["traceparent"] = self.traceparent
        if self.authorization:
            h["Authorization"] = self.authorization
        return h


def get_policy_context() -> PolicyContext:
    """Build PolicyContext from the current request's middleware-populated vars."""
    return PolicyContext(
        tenant_id=get_tenant_id(),
        user_id=get_soma_user_id(),
        session_id=get_soma_session_id(),
        request_id=get_request_id(),
        traceparent=get_traceparent(),
        authorization=get_authorization(),
    )


# Backward-compatible alias used by existing code that called get_soma_context().
def get_soma_context() -> PolicyContext:
    return get_policy_context()


# ── Internal Helpers ───────────────────────────────────────────────────────────


def _ensure_suffix(base_url: str, suffix: str) -> str:
    normalized = base_url.rstrip("/")
    return normalized if normalized.endswith(suffix) else f"{normalized}{suffix}"


def _parse_uuid(value: str) -> Optional[UUID]:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _require_context_for_policy(context: PolicyContext) -> None:
    if not context.session_id or not context.user_id:
        raise SomaContextError(
            "Missing X-Soma-Session-ID or X-User-ID in request context. "
            "Policy enforcement requires both headers."
        )


# ── Enforce Policy ─────────────────────────────────────────────────────────────


async def enforce_policy(
    action: str,
    prompt: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Evaluate an action against the external Policy Engine.

    Returns None if policy enforcement is disabled (soma_policy_url not set).
    Raises SomaPolicyDenied if the action is rejected.
    Raises SomaPolicyUnavailable if the engine is unreachable.

    Args:
        action: The action key being evaluated (e.g. 'ingest', 'analyze').
        prompt: Human-legible description of the operation for policy context.
        metadata: Additional key/value context for the policy evaluation.
    """
    settings = get_settings()
    if not settings.soma_policy_url:
        logger.debug("Policy engine URL not configured — skipping enforcement.")
        return None

    context = get_policy_context()
    _require_context_for_policy(context)

    payload = {
        "session_id": context.session_id,
        "tenant": context.tenant_id or "default",
        "user": context.user_id,
        "prompt": prompt,
        "role": "agent",
        "metadata": {
            "action": action,
            "request_id": context.request_id,
            **(metadata or {}),
        },
    }

    endpoint = _ensure_suffix(settings.soma_policy_url, "/v1/evaluate")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                endpoint, json=payload, headers=context.headers()
            )
    except httpx.RequestError as exc:
        raise SomaPolicyUnavailable(f"Policy Engine unreachable: {exc}") from exc

    if response.status_code >= 500:
        raise SomaPolicyUnavailable(f"Policy Engine returned {response.status_code}.")

    try:
        data = response.json()
    except Exception as exc:
        raise SomaPolicyUnavailable("Policy Engine returned invalid JSON.") from exc

    decision = data.get("decision", "").upper()
    if decision == "DENY":
        raise SomaPolicyDenied(
            f"Policy denied action '{action}'.",
            details=data.get("details"),
        )

    return data
