"""Policy enforcement engine.

Evaluates active GovernancePolicy rules against request context and returns
ALLOW / DENY / DEFER decisions.  Supports three enforcement levels:

- **strict** – request is blocked when a policy denies it.
- **warn**   – request proceeds but a warning is logged.
- **audit**  – request proceeds; decision is recorded for compliance.
"""

from __future__ import annotations

import fnmatch
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

__all__ = [
    "EnforcementLevel",
    "PolicyDecision",
    "PolicyEvaluationResult",
    "PolicyEvaluator",
    "PolicyEnforcer",
]

logger = logging.getLogger(__name__)


class EnforcementLevel(Enum):
    """Policy enforcement levels."""

    STRICT = "strict"  # Deny if policy violated
    WARN = "warn"  # Allow but warn
    AUDIT = "audit"  # Allow but log


class PolicyDecision(Enum):
    """Result of a policy evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    DEFER = "defer"  # Unable to determine


@dataclass
class PolicyEvaluationResult:
    """Result of policy evaluation.

    Attributes:
        decision: The policy decision (ALLOW, DENY, or DEFER).
        policy_id: ID of the policy that made this decision (if applicable).
        reason: Human-readable explanation of the decision.
        enforcement_level: The enforcement level that was applied.
    """

    decision: PolicyDecision
    policy_id: str | None = None
    reason: str | None = None
    enforcement_level: EnforcementLevel | None = None


# ---------------------------------------------------------------------------
# Scope matching helpers
# ---------------------------------------------------------------------------


def _match_pattern(value: str, pattern: str) -> bool:
    """Return True if *value* matches a glob-style *pattern*."""
    return fnmatch.fnmatch(value, pattern)


def _scope_matches(scope: dict[str, Any], context: dict[str, Any]) -> bool:
    """Check whether a policy's scope applies to the given request context.

    Scope keys (all optional – missing means "match everything"):
        paths       – list of glob patterns matched against ``request.path``
        methods     – list of HTTP methods (upper-case)
        roles       – list of roles the user must *at least one of*
        datasets    – list of dataset URN globs
        operations  – list of operation names (read, write, delete, …)

    Returns ``True`` when the scope applies (i.e. the policy should be
    evaluated).  An empty scope matches every request.
    """
    if not scope:
        return True

    # paths
    paths: list[str] | None = scope.get("paths")
    if paths:
        request_path: str = context.get("path", "")
        if not any(_match_pattern(request_path, p) for p in paths):
            return False

    # methods
    methods: list[str] | None = scope.get("methods")
    if methods:
        request_method: str = context.get("method", "").upper()
        if request_method not in [m.upper() for m in methods]:
            return False

    # roles – user must have at least one of the listed roles
    roles: list[str] | None = scope.get("roles")
    if roles:
        user_roles: list[str] = context.get("roles", [])
        if not set(roles) & set(user_roles):
            return False

    # datasets
    datasets: list[str] | None = scope.get("datasets")
    if datasets:
        target_dataset: str = context.get("dataset_urn", "")
        if not any(_match_pattern(target_dataset, d) for d in datasets):
            return False

    # operations
    operations: list[str] | None = scope.get("operations")
    if operations:
        op: str = context.get("operation", "")
        if op not in operations:
            return False

    return True


# ---------------------------------------------------------------------------
# Rule evaluation helpers
# ---------------------------------------------------------------------------


def _evaluate_rules(
    rules: dict[str, Any], context: dict[str, Any]
) -> tuple[bool, str | None]:
    """Evaluate policy rules against the request context.

    Supported rule keys:
        allowed_roles      – list[str]  – deny if user has NONE of these roles
        denied_roles       – list[str]  – deny if user has ANY of these roles
        allowed_methods    – list[str]  – deny if HTTP method not in list
        denied_methods     – list[str]  – deny if HTTP method in list
        allowed_paths      – list[str]  – deny if path doesn't match any
        denied_paths       – list[str]  – deny if path matches any
        require_auth       – bool       – deny if no authenticated user
        max_request_body   – int        – deny if content-length exceeds (bytes)
        required_headers   – list[str]  – deny if any header is missing
        allowed_operations – list[str]  – deny if operation not in list
        denied_operations  – list[str]  – deny if operation in list

    Returns:
        ``(allowed, reason)`` – ``True`` means the request is allowed.
    """
    if not rules:
        return True, None

    # --- Role checks ---
    allowed_roles: list[str] | None = rules.get("allowed_roles")
    if allowed_roles:
        user_roles: list[str] = context.get("roles", [])
        if not (set(allowed_roles) & set(user_roles)):
            return False, f"User lacks required role (need one of: {allowed_roles})"

    denied_roles: list[str] | None = rules.get("denied_roles")
    if denied_roles:
        user_roles = context.get("roles", [])
        intersection = set(denied_roles) & set(user_roles)
        if intersection:
            return False, f"User has denied role(s): {intersection}"

    # --- Method checks ---
    allowed_methods: list[str] | None = rules.get("allowed_methods")
    if allowed_methods:
        method: str = context.get("method", "").upper()
        if method not in [m.upper() for m in allowed_methods]:
            return False, f"HTTP method {method} not allowed"

    denied_methods: list[str] | None = rules.get("denied_methods")
    if denied_methods:
        method = context.get("method", "").upper()
        if method in [m.upper() for m in denied_methods]:
            return False, f"HTTP method {method} is denied"

    # --- Path checks ---
    allowed_paths: list[str] | None = rules.get("allowed_paths")
    if allowed_paths:
        path: str = context.get("path", "")
        if not any(_match_pattern(path, p) for p in allowed_paths):
            return False, f"Path {path} is not in allowed paths"

    denied_paths: list[str] | None = rules.get("denied_paths")
    if denied_paths:
        path = context.get("path", "")
        if any(_match_pattern(path, p) for p in denied_paths):
            return False, f"Path {path} matches a denied path pattern"

    # --- Auth requirement ---
    if rules.get("require_auth") and not context.get("user_id"):
        return False, "Authentication required"

    # --- Request body size ---
    max_body: int | None = rules.get("max_request_body")
    if max_body is not None:
        content_length: int = context.get("content_length", 0)
        if content_length > max_body:
            return (
                False,
                f"Request body ({content_length} bytes) exceeds limit ({max_body} bytes)",
            )

    # --- Required headers ---
    required_headers: list[str] | None = rules.get("required_headers")
    if required_headers:
        present: set[str] = {k.lower() for k in context.get("headers", {}).keys()}
        missing = [h for h in required_headers if h.lower() not in present]
        if missing:
            return False, f"Missing required header(s): {missing}"

    # --- Operation checks ---
    allowed_operations: list[str] | None = rules.get("allowed_operations")
    if allowed_operations:
        op: str = context.get("operation", "")
        if op not in allowed_operations:
            return False, f"Operation '{op}' is not allowed"

    denied_operations: list[str] | None = rules.get("denied_operations")
    if denied_operations:
        op = context.get("operation", "")
        if op in denied_operations:
            return False, f"Operation '{op}' is denied"

    return True, None


# ---------------------------------------------------------------------------
# Core classes
# ---------------------------------------------------------------------------


class PolicyEvaluator:
    """Evaluates a single policy against a request context."""

    def evaluate_policy(
        self, policy: Any, context: dict[str, Any]
    ) -> PolicyEvaluationResult:
        """Evaluate if *context* violates *policy* rules.

        Args:
            policy: A ``Policy`` model instance (or duck-typed object) with
                ``id``, ``rules``, ``scope``, and ``enforcement_level`` attrs.
            context: Evaluation context – see ``_evaluate_rules`` for keys.

        Returns:
            ``PolicyEvaluationResult`` with decision and reason.
        """
        policy_id = str(getattr(policy, "id", "unknown"))
        policy_name = getattr(policy, "name", policy_id)
        enforcement_raw: str = getattr(policy, "enforcement_level", "strict")
        try:
            enforcement = EnforcementLevel(enforcement_raw)
        except ValueError:
            enforcement = EnforcementLevel.STRICT

        scope: dict[str, Any] = getattr(policy, "scope", {}) or {}
        rules: dict[str, Any] = getattr(policy, "rules", {}) or {}

        # 1. Scope check – if the policy doesn't apply to this context, defer.
        if not _scope_matches(scope, context):
            return PolicyEvaluationResult(
                decision=PolicyDecision.DEFER,
                policy_id=policy_id,
                reason=f"Policy '{policy_name}' scope does not match context",
                enforcement_level=enforcement,
            )

        # 2. Rule evaluation
        allowed, reason = _evaluate_rules(rules, context)

        if allowed:
            return PolicyEvaluationResult(
                decision=PolicyDecision.ALLOW,
                policy_id=policy_id,
                reason=f"Policy '{policy_name}' passed",
                enforcement_level=enforcement,
            )

        return PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            policy_id=policy_id,
            reason=reason,
            enforcement_level=enforcement,
        )


class PolicyEnforcer:
    """Enforces policies with configurable enforcement levels.

    Evaluates all supplied policies and returns the *most restrictive*
    decision (DENY > DEFER > ALLOW).
    """

    def __init__(self, evaluator: PolicyEvaluator | None = None) -> None:
        self.evaluator: PolicyEvaluator = evaluator or PolicyEvaluator()

    def enforce(
        self, policies: list[Any], context: dict[str, Any]
    ) -> PolicyEvaluationResult:
        """Enforce all applicable policies for the given context.

        Returns the most restrictive decision across all policies.

        Args:
            policies: List of Policy model instances to evaluate.
            context: Evaluation context (user, operation, resource, etc.).

        Returns:
            ``PolicyEvaluationResult`` with aggregated decision.
        """
        if not policies:
            return PolicyEvaluationResult(decision=PolicyDecision.ALLOW)

        most_restrictive: PolicyEvaluationResult = PolicyEvaluationResult(
            decision=PolicyDecision.ALLOW,
        )
        priority = {
            PolicyDecision.DENY: 0,
            PolicyDecision.DEFER: 1,
            PolicyDecision.ALLOW: 2,
        }

        for policy in policies:
            result = self.evaluator.evaluate_policy(policy, context)
            if priority[result.decision] < priority[most_restrictive.decision]:
                most_restrictive = result
            # Short-circuit on DENY – can't get more restrictive.
            if most_restrictive.decision == PolicyDecision.DENY:
                break

        return most_restrictive

    def check_access(self, policies: list[Any], context: dict[str, Any]) -> bool:
        """Check if access is allowed under policies.

        Raises ``PermissionError`` if STRICT enforcement denies access.

        Returns:
            ``True`` if access is allowed or deferred, ``False`` if denied
            at WARN/AUDIT level.
        """
        result = self.enforce(policies, context)
        if result.decision == PolicyDecision.DENY:
            if result.enforcement_level == EnforcementLevel.STRICT:
                raise PermissionError(f"Policy denied: {result.reason}")
            elif result.enforcement_level == EnforcementLevel.WARN:
                logger.warning("Policy warning: %s", result.reason)
            else:
                logger.info("Policy audit: %s", result.reason)
        return result.decision in (PolicyDecision.ALLOW, PolicyDecision.DEFER)
