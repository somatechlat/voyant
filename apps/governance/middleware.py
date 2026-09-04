"""Governance policy enforcement middleware.

Intercepts every Django request, builds a context dict from the HTTP
request metadata, fetches active ``Policy`` objects for the current
tenant, and runs them through the ``PolicyEnforcer``.

When a policy with ``enforcement_level="strict"`` denies the request the
middleware returns HTTP 403 immediately.  For ``warn`` and ``audit``
levels the request proceeds but a violation record is written to the
``voyant.audit`` logger and, where possible, to the ``AuditLog`` model.

Data-contract compliance is also checked for write operations that
target governed datasets (datasets with an active ``DataContract``).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from django.http import JsonResponse

from apps.core.middleware import get_tenant_id, get_soma_user_id

from apps.governance.lib.policy_enforcer import (
    EnforcementLevel,
    PolicyDecision,
    PolicyEnforcer,
    PolicyEvaluationResult,
)

__all__ = ["GovernancePolicyMiddleware"]

logger = logging.getLogger("voyant.governance")
audit_logger = logging.getLogger("voyant.audit")

# Paths that should never be blocked by governance policies.
_EXEMPT_PATH_PREFIXES: tuple[str, ...] = (
    "/health",
    "/ready",
    "/healthz",
    "/readyz",
    "/admin",
    "/static",
    "/favicon.ico",
)

# HTTP methods that are considered "data operations" for contract checks.
_DATA_MUTATION_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _build_context(request: Any) -> dict[str, Any]:
    """Extract a context dict from a Django ``HttpRequest``."""
    # Resolve user info – prefer the RBACMiddleware-injected user.
    user_id = get_soma_user_id() or ""
    roles: list[str] = []
    user = getattr(request, "user", None)
    if user is not None and getattr(user, "is_authenticated", False):
        user_id = user_id or str(getattr(user, "pk", ""))
        roles = list(getattr(user, "roles", []))

    # Collect headers (lower-cased keys for consistent lookups).
    headers: dict[str, str] = {
        k.lower(): v for k, v in request.headers.items()
    }

    return {
        "method": request.method or "",
        "path": request.path,
        "user_id": user_id,
        "roles": roles,
        "tenant_id": get_tenant_id(request),
        "content_length": int(request.headers.get("Content-Length", 0) or 0),
        "headers": headers,
        "operation": _infer_operation(request),
    }


def _infer_operation(request: Any) -> str:
    """Map HTTP method + path to a governance operation name."""
    method = (request.method or "").upper()
    path = request.path

    if method == "GET":
        if "/lineage" in path or "/search" in path:
            return "read"
        return "read"
    if method == "DELETE":
        return "delete"
    if method in ("POST", "PUT", "PATCH"):
        return "write"
    return "read"


def _log_audit_event(
    *,
    request: Any,
    result: PolicyEvaluationResult,
    tenant_id: str,
    blocked: bool,
    duration_ms: float,
) -> None:
    """Write a structured audit log entry for the policy decision."""
    actor = get_soma_user_id() or "anonymous"
    action = "policy.enforced" if not blocked else "policy.blocked"
    outcome = "denied" if blocked else "success"

    details: dict[str, Any] = {
        "policy_id": result.policy_id,
        "decision": result.decision.value,
        "enforcement_level": result.enforcement_level.value if result.enforcement_level else None,
        "reason": result.reason,
        "method": request.method,
        "path": request.path,
        "duration_ms": round(duration_ms, 2),
    }

    # Structured log for the audit trail.
    audit_logger.info(
        "governance_policy %s | actor=%s tenant=%s policy=%s decision=%s reason=%s path=%s",
        action,
        actor,
        tenant_id,
        result.policy_id,
        result.decision.value,
        result.reason,
        request.path,
    )

    # Best-effort DB audit log (non-blocking – swallow errors so we never
    # break the request pipeline because of a logging failure).
    try:
        from apps.core.models import AuditLog

        AuditLog.objects.create(
            actor=actor,
            action=action,
            resource_type="policy",
            resource_id=result.policy_id or "unknown",
            outcome=outcome,
            details=details,
            tenant_id=tenant_id,
            ip_address=_get_client_ip(request),
            user_agent=request.headers.get("User-Agent", ""),
        )
    except Exception:
        logger.debug("Failed to write AuditLog entry", exc_info=True)


def _get_client_ip(request: Any) -> str | None:
    """Extract client IP, respecting X-Forwarded-For."""
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _check_data_contracts(request: Any, context: dict[str, Any]) -> PolicyEvaluationResult | None:
    """Check DataContract compliance for data-mutation requests.

    Returns a ``PolicyEvaluationResult`` with DENY if a contract
    violation is detected, or ``None`` if no contract applies or the
    check passes.
    """
    if context["method"] not in _DATA_MUTATION_METHODS:
        return None

    # Try to find a dataset_urn from the request path or body.
    dataset_urn = _extract_dataset_urn(request)
    if not dataset_urn:
        return None

    try:
        from apps.governance.models import DataContract

        contracts = DataContract.objects.filter(
            dataset_urn=dataset_urn,
            status=DataContract.Status.ACTIVE,
        )
        if not contracts.exists():
            return None

        # For each active contract, verify the request doesn't violate
        # its quality rules (e.g. required fields, schema constraints).
        for contract in contracts:
            violation = _validate_request_against_contract(request, contract)
            if violation:
                return PolicyEvaluationResult(
                    decision=PolicyDecision.DENY,
                    policy_id=str(contract.id),
                    reason=f"DataContract '{contract.name}' violation: {violation}",
                    enforcement_level=EnforcementLevel.STRICT,
                )
    except Exception:
        logger.debug("DataContract check skipped due to error", exc_info=True)

    return None


def _extract_dataset_urn(request: Any) -> str:
    """Best-effort extraction of a dataset URN from the request."""
    # Parse query string from the full path (works even without Django's
    # QueryDict being populated, e.g. in unit tests).
    from urllib.parse import parse_qs, urlparse

    full_path = request.get_full_path() if hasattr(request, "get_full_path") else request.path
    parsed = urlparse(full_path)
    params = parse_qs(parsed.query)
    urn_list = params.get("dataset_urn") or params.get("urn")
    if urn_list:
        return str(urn_list[0])

    # Check common path patterns: /api/v1/datasets/<urn>/...
    parts = request.path.strip("/").split("/")
    if "datasets" in parts:
        idx = parts.index("datasets")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    return ""


def _validate_request_against_contract(request: Any, contract: Any) -> str | None:
    """Validate a request body against a DataContract's quality rules.

    Returns an error message string on violation, or ``None`` on success.
    """
    quality_rules: list[dict] = getattr(contract, "quality_rules", []) or []
    if not quality_rules:
        return None

    # Parse request body if JSON.
    import json

    try:
        body: dict[str, Any] = json.loads(request.body) if request.body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    for rule in quality_rules:
        rule_type = rule.get("type", "")
        column = rule.get("column", "")

        if rule_type == "required_field" and column:
            if column not in body:
                return f"Required field '{column}' is missing"

        if rule_type == "not_null" and column:
            if column in body and body[column] is None:
                return f"Field '{column}' must not be null"

    return None


# ---------------------------------------------------------------------------
# Middleware class
# ---------------------------------------------------------------------------

class GovernancePolicyMiddleware:
    """Django middleware that enforces active governance policies.

    Place this **after** ``TenantMiddleware`` and ``RBACMiddleware`` in the
    ``MIDDLEWARE`` list so that tenant and user context are available.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response
        self._enforcer = PolicyEnforcer()

    def __call__(self, request: Any) -> Any:
        # Skip exempt paths (health checks, static files, admin).
        if request.path.startswith(_EXEMPT_PATH_PREFIXES):
            return self.get_response(request)

        start = time.monotonic()
        context = _build_context(request)
        tenant_id = context["tenant_id"]

        # 1. Fetch active policies for this tenant.
        policies = self._get_active_policies(tenant_id)

        # 2. Evaluate policies.
        result = self._enforcer.enforce(policies, context)

        # 3. Check data contracts for mutation requests.
        if result.decision != PolicyDecision.DENY:
            contract_result = _check_data_contracts(request, context)
            if contract_result and contract_result.decision == PolicyDecision.DENY:
                result = contract_result

        duration_ms = (time.monotonic() - start) * 1000

        # 4. Act on the decision.
        if result.decision == PolicyDecision.DENY:
            _log_audit_event(
                request=request,
                result=result,
                tenant_id=tenant_id,
                blocked=(result.enforcement_level == EnforcementLevel.STRICT),
                duration_ms=duration_ms,
            )

            if result.enforcement_level == EnforcementLevel.STRICT:
                return JsonResponse(
                    {
                        "error": "Forbidden",
                        "message": result.reason or "Request blocked by governance policy",
                        "policy_id": result.policy_id,
                    },
                    status=403,
                )
            # warn / audit – request proceeds (already logged above).

        elif result.decision == PolicyDecision.ALLOW:
            # Log at debug level for successful policy checks.
            logger.debug(
                "Policy check passed for %s %s (tenant=%s)",
                request.method,
                request.path,
                tenant_id,
            )

        response = self.get_response(request)

        # Attach policy metadata header for observability.
        if result.policy_id:
            response["X-Governance-Policy-ID"] = result.policy_id
        response["X-Governance-Decision"] = result.decision.value

        return response

    @staticmethod
    def _get_active_policies(tenant_id: str) -> list[Any]:
        """Fetch active policies for the given tenant.

        Uses a try/except so the middleware is safe to use even when the
        database is unavailable (e.g. during migrations or tests that
        don't set up the DB).
        """
        try:
            from apps.governance.models import Policy

            return list(
                Policy.objects.filter(
                    tenant_id=tenant_id,
                    status=Policy.Status.ACTIVE,
                )
            )
        except Exception:
            logger.debug("Could not fetch policies for tenant %s", tenant_id, exc_info=True)
            return []
