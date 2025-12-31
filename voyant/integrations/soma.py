"""SomaAgentHub integration helpers for policy, memory, and orchestration."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx

from voyant.api.middleware import (
    get_authorization,
    get_request_id,
    get_soma_session_id,
    get_soma_user_id,
    get_tenant_id,
    get_traceparent,
)
from voyant.core.config import get_settings

logger = logging.getLogger(__name__)


class SomaIntegrationError(RuntimeError):
    """Base error for Soma integration failures."""


class SomaContextError(SomaIntegrationError):
    """Missing or invalid Soma context required for integration."""


class SomaPolicyDenied(SomaIntegrationError):
    """Policy denied a requested action."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


class SomaPolicyUnavailable(SomaIntegrationError):
    """Policy engine unavailable or returned an invalid response."""


@dataclass(frozen=True)
class SomaContext:
    tenant_id: str
    user_id: str
    session_id: str
    request_id: str
    traceparent: str
    authorization: str

    def headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.tenant_id:
            headers["X-Tenant-ID"] = self.tenant_id
        if self.user_id:
            headers["X-User-ID"] = self.user_id
        if self.session_id:
            headers["X-Soma-Session-ID"] = self.session_id
        if self.request_id:
            headers["X-Request-ID"] = self.request_id
        if self.traceparent:
            headers["traceparent"] = self.traceparent
        if self.authorization:
            headers["Authorization"] = self.authorization
        return headers


def get_soma_context() -> SomaContext:
    """Return Soma context derived from request headers."""
    return SomaContext(
        tenant_id=get_tenant_id(),
        user_id=get_soma_user_id(),
        session_id=get_soma_session_id(),
        request_id=get_request_id(),
        traceparent=get_traceparent(),
        authorization=get_authorization(),
    )


def _ensure_suffix(base_url: str, suffix: str) -> str:
    normalized = base_url.rstrip("/")
    if normalized.endswith(suffix):
        return normalized
    return f"{normalized}{suffix}"


def _parse_uuid(value: str) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _require_context_for_policy(context: SomaContext) -> None:
    if not context.session_id or not context.user_id:
        raise SomaContextError("Missing X-Soma-Session-ID or X-User-ID header")


async def enforce_policy(
    action: str,
    prompt: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Enforce Soma policy if configured."""
    settings = get_settings()
    if not settings.soma_policy_url:
        return None

    context = get_soma_context()
    _require_context_for_policy(context)

    payload = {
        "session_id": context.session_id,
        "tenant": context.tenant_id or "default",
        "user": context.user_id,
        "prompt": prompt,
        "role": "agent",
        "metadata": {
            "action": action,
            "extra": metadata or {},
        },
    }

    endpoint = _ensure_suffix(settings.soma_policy_url, "/v1/evaluate")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                endpoint, json=payload, headers=context.headers()
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SomaPolicyUnavailable("Policy engine unavailable") from exc

    data = response.json()
    allowed = bool(data.get("allowed"))
    if not allowed:
        raise SomaPolicyDenied("Policy denied request", details=data)
    return data


async def remember_summary(
    job_id: str,
    status: str,
    summary: dict[str, Any],
    manifest: list[dict[str, Any]],
) -> None:
    """Persist analysis summaries to Soma memory when configured."""
    settings = get_settings()
    if not settings.soma_memory_url:
        return

    context = get_soma_context()
    if not context.session_id:
        logger.warning("Skipping Soma memory write: missing X-Soma-Session-ID")
        return

    key = f"voyant:{context.tenant_id}:{context.session_id}:{job_id}"
    payload = {
        "key": key,
        "value": {
            "job_id": job_id,
            "status": status,
            "summary": summary,
            "manifest": manifest,
            "tenant_id": context.tenant_id,
            "session_id": context.session_id,
        },
    }

    endpoint = _ensure_suffix(settings.soma_memory_url, "/v1/remember")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                endpoint, json=payload, headers=context.headers()
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Soma memory write failed: %s", exc)


def map_job_status_to_task_status(status: str) -> str:
    mapping = {
        "queued": "RECEIVED",
        "running": "RUNNING",
        "completed": "COMPLETED",
        "failed": "FAILED",
        "cancelled": "CANCELLED",
    }
    return mapping.get(status, "RECEIVED")


async def create_task_for_job(
    job_id: str,
    job_type: str,
    source_id: str | None,
    description: str,
) -> str | None:
    """Create a Soma orchestrator task for a job if configured."""
    settings = get_settings()
    if not settings.soma_orchestrator_url:
        return None

    context = get_soma_context()
    tenant_uuid = _parse_uuid(context.tenant_id)
    user_uuid = _parse_uuid(context.user_id)
    if not tenant_uuid or not user_uuid:
        logger.warning("Skipping Soma task create: tenant/user is not UUID")
        return None

    payload = {
        "tenant_id": str(tenant_uuid),
        "user_principal_id": str(user_uuid),
        "source_application": "VOYANT",
        "original_request_text": description,
        "task_type": f"VOYANT_{job_type.upper()}",
        "labels": {
            "job_id": job_id,
            "job_type": job_type,
            "source_id": source_id or "",
            "soma_session_id": context.session_id,
        },
    }

    endpoint = _ensure_suffix(settings.soma_orchestrator_url, "/v1/tasks")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.post(
                endpoint, json=payload, headers=context.headers()
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Soma task create failed: %s", exc)
            return None

    data = response.json()
    task_id = data.get("id")
    if not task_id:
        logger.warning("Soma task create missing id in response")
        return None
    return str(task_id)


async def update_task_status(
    task_id: str,
    status: str,
    reason: str | None = None,
) -> None:
    """Update a Soma orchestrator task status when configured."""
    settings = get_settings()
    if not settings.soma_orchestrator_url:
        return

    context = get_soma_context()
    tenant_uuid = _parse_uuid(context.tenant_id)
    if not tenant_uuid:
        logger.warning("Skipping Soma task update: tenant is not UUID")
        return

    mapped_status = map_job_status_to_task_status(status)
    params = {"status": mapped_status}
    if reason:
        params["reason"] = reason
    if context.user_id and _parse_uuid(context.user_id):
        params["actor_principal_id"] = context.user_id

    endpoint = _ensure_suffix(
        settings.soma_orchestrator_url, f"/v1/tasks/{task_id}/status"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.patch(
                endpoint, params=params, headers=context.headers()
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("Soma task update failed: %s", exc)
