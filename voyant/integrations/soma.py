"""
SomaAgentHub Integration Helpers.

This module provides helper functions and classes for integrating Voyant with
the SomaAgentHub ecosystem. It facilitates communication with Soma's Policy
Engine for authorization, Memory Gateway for persisting analysis summaries,
and Orchestrator for task lifecycle management.

Key functionalities include:
- Extracting Soma context from incoming request headers.
- Enforcing policies for sensitive actions.
- Storing job summaries and artifacts in Soma Memory.
- Updating task statuses in Soma Orchestrator.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional
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
settings = get_settings()


class SomaIntegrationError(RuntimeError):
    """Base exception for all Soma integration-related failures."""


class SomaContextError(SomaIntegrationError):
    """
    Exception raised when required Soma context (e.g., session ID, user ID) is missing or invalid.
    """


class SomaPolicyDenied(SomaIntegrationError):
    """
    Exception raised when a requested action is explicitly denied by the Soma Policy Engine.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """
        Initializes SomaPolicyDenied exception.

        Args:
            message (str): A human-readable message about the denial.
            details (Optional[dict[str, Any]]): Additional details about the policy denial.
        """
        super().__init__(message)
        self.details = details or {}


class SomaPolicyUnavailable(SomaIntegrationError):
    """
    Exception raised when the Soma Policy Engine is unavailable or returns an invalid response.
    """


@dataclass(frozen=True)
class SomaContext:
    """
    Encapsulates all relevant Soma context derived from incoming request headers.

    This context is essential for propagating session, user, and tenant information
    to SomaAgentHub components for consistent policy enforcement, logging, and memory access.

    Attributes:
        tenant_id (str): The tenant ID from the 'X-Tenant-ID' header.
        user_id (str): The user ID from the 'X-Soma-User-ID' header.
        session_id (str): The session ID from the 'X-Soma-Session-ID' header.
        request_id (str): The request ID from the 'X-Request-ID' header.
        traceparent (str): The distributed tracing context from the 'traceparent' header.
        authorization (str): The Authorization header value (e.g., "Bearer <token>").
    """

    tenant_id: str
    user_id: str
    session_id: str
    request_id: str
    traceparent: str
    authorization: str

    def headers(self) -> dict[str, str]:
        """
        Constructs a dictionary of HTTP headers containing the Soma context.

        Returns:
            dict[str, str]: A dictionary of HTTP headers suitable for forwarding to Soma services.
        """
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
    """
    Retrieves the current Soma context from the active request's headers.

    This function relies on middleware to populate thread-local context variables
    which are then aggregated into a `SomaContext` object.

    Returns:
        SomaContext: An object containing all available Soma context information.
    """
    return SomaContext(
        tenant_id=get_tenant_id(),
        user_id=get_soma_user_id(),
        session_id=get_soma_session_id(),
        request_id=get_request_id(),
        traceparent=get_traceparent(),
        authorization=get_authorization(),
    )


def _ensure_suffix(base_url: str, suffix: str) -> str:
    """
    Ensures a URL has a specific suffix, normalizing slashes.

    Args:
        base_url (str): The base URL string.
        suffix (str): The desired suffix (e.g., "/v1/evaluate").

    Returns:
        str: The normalized URL with the guaranteed suffix.
    """
    normalized = base_url.rstrip("/")
    if normalized.endswith(suffix):
        return normalized
    return f"{normalized}{suffix}"


def _parse_uuid(value: str) -> Optional[UUID]:
    """
    Attempts to parse a string into a UUID object.

    Args:
        value (str): The string to parse.

    Returns:
        Optional[UUID]: The UUID object if parsing is successful, None otherwise.
    """
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _require_context_for_policy(context: SomaContext) -> None:
    """
    Internal helper to validate essential Soma context for policy enforcement.

    Args:
        context (SomaContext): The current Soma context.

    Raises:
        SomaContextError: If required session or user IDs are missing.
    """
    if not context.session_id or not context.user_id:
        raise SomaContextError("Missing X-Soma-Session-ID or X-User-ID header in context. Policy cannot be enforced.")


async def enforce_policy(
    action: str,
    prompt: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    Enforces a policy decision for a given action using the Soma Policy Engine.

    This function constructs a policy evaluation request, including contextual
    information, and sends it to the configured Soma Policy Engine.

    Args:
        action (str): The action being requested (e.g., "ingest", "analyze").
        prompt (str): A natural language description of the action, for policy evaluation.
        metadata (Optional[dict[str, Any]]): Additional metadata relevant to the policy decision.

    Returns:
        Optional[dict[str, Any]]: The policy decision response if the action is allowed, otherwise None.

    Raises:
        SomaContextError: If required Soma context is missing.
        SomaPolicyUnavailable: If the Policy Engine is unreachable or returns an invalid response.
        SomaPolicyDenied: If the requested action is explicitly denied by the policy.
    """
    settings = get_settings()
    if not settings.soma_policy_url:
        logger.debug("Soma Policy Engine URL not configured. Skipping policy enforcement.")
        return None

    context = get_soma_context()
    _require_context_for_policy(context)

    payload = {
        "session_id": context.session_id,
        "tenant": context.tenant_id or "default",
        "user": context.user_id,
        "prompt": prompt,
        "role": "agent",  # Voyant acts as an agent in the Soma ecosystem.
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
            logger.error("Soma Policy Engine request failed: %s", exc)
            raise SomaPolicyUnavailable("Policy engine unavailable or returned an error.") from exc

    data = response.json()
    allowed = bool(data.get("allowed"))
    if not allowed:
        raise SomaPolicyDenied("Policy denied request.", details=data)
    return data


async def remember_summary(
    job_id: str,
    status: str,
    summary: dict[str, Any],
    manifest: list[dict[str, Any]],
) -> None:
    """
    Persists analysis summaries and artifact manifests to the Soma Memory Gateway.

    This allows external agents to recall and utilize previous analysis results.

    Args:
        job_id (str): The ID of the Voyant job.
        status (str): The final status of the job (e.g., "completed", "failed").
        summary (dict[str, Any]): A high-level summary of the analysis results.
        manifest (list[dict[str, Any]]): A list detailing all generated artifacts.

    Raises:
        SomaIntegrationError: If Soma Memory Gateway is unavailable or the write fails.
    """
    settings = get_settings()
    if not settings.soma_memory_url:
        logger.debug("Soma Memory Gateway URL not configured. Skipping memory write.")
        return

    context = get_soma_context()
    if not context.session_id:
        logger.warning("Skipping Soma memory write: missing X-Soma-Session-ID in context.")
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
            logger.debug(f"Summary for job {job_id} remembered in Soma Memory.")
        except httpx.HTTPError as exc:
            logger.warning("Soma Memory Gateway write failed: %s", exc)
            raise SomaIntegrationError("Failed to write to Soma Memory Gateway.") from exc


def map_job_status_to_task_status(status: str) -> str:
    """
    Maps Voyant's internal job status to Soma Orchestrator's task status.

    Args:
        status (str): Voyant's internal job status.

    Returns:
        str: The corresponding Soma Orchestrator task status.
    """
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
    """
    Creates a new task in the Soma Orchestrator for a Voyant job.

    This registers the Voyant job with the Soma Orchestrator, allowing Soma
    to track its lifecycle and integrate it into larger agent workflows.

    Args:
        job_id (str): The ID of the Voyant job.
        job_type (str): The type of the Voyant job (e.g., "analyze", "ingest").
        source_id (Optional[str]): The source ID associated with the job.
        description (str): A brief description of the job.

    Returns:
        Optional[str]: The ID of the created Soma task, or None if task creation fails
                       or Soma Orchestrator is not configured.

    Raises:
        SomaIntegrationError: If Soma Orchestrator is unavailable or task creation fails.
    """
    settings = get_settings()
    if not settings.soma_orchestrator_url:
        logger.debug("Soma Orchestrator URL not configured. Skipping task creation.")
        return None

    context = get_soma_context()
    tenant_uuid = _parse_uuid(context.tenant_id)
    user_uuid = _parse_uuid(context.user_id)
    if not tenant_uuid or not user_uuid:
        logger.warning("Skipping Soma task creation: Tenant ID or User ID is not a valid UUID format.")
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
            logger.warning("Soma Orchestrator task creation failed: %s", exc)
            raise SomaIntegrationError("Failed to create task in Soma Orchestrator.") from exc

    data = response.json()
    task_id = data.get("id")
    if not task_id:
        logger.warning("Soma Orchestrator task creation response missing 'id'.")
        raise SomaIntegrationError("Soma Orchestrator did not return a task ID.")
    return str(task_id)


async def update_task_status(
    task_id: str,
    status: str,
    reason: str | None = None,
) -> None:
    """
    Updates the status of a task in the Soma Orchestrator.

    Args:
        task_id (str): The ID of the Soma task to update.
        status (str): The new status for the task (e.g., "running", "completed", "failed").
        reason (Optional[str]): An optional reason for the status update (e.g., error message).

    Raises:
        SomaIntegrationError: If Soma Orchestrator is unavailable or the update fails.
    """
    settings = get_settings()
    if not settings.soma_orchestrator_url:
        logger.debug("Soma Orchestrator URL not configured. Skipping task status update.")
        return

    context = get_soma_context()
    tenant_uuid = _parse_uuid(context.tenant_id)
    if not tenant_uuid:
        logger.warning("Skipping Soma task update: Tenant ID is not a valid UUID format.")
        return

    mapped_status = map_job_status_to_task_status(status)
    params = {"status": mapped_status}
    if reason:
        params["reason"] = reason
    if context.user_id and _parse_uuid(context.user_id):
        params["actor_principal_id"] = context.user_id # If user ID is a valid UUID, include as actor.

    endpoint = _ensure_suffix(
        settings.soma_orchestrator_url, f"/v1/tasks/{task_id}/status"
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.patch(
                endpoint, params=params, headers=context.headers()
            )
            response.raise_for_status()
            logger.debug(f"Soma task {task_id} status updated to {mapped_status}.")
        except httpx.HTTPError as exc:
            logger.warning("Soma Orchestrator task status update failed: %s", exc)
            raise SomaIntegrationError("Failed to update task status in Soma Orchestrator.") from exc
