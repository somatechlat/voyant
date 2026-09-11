"""Attribute-Based Access Control (ABAC) engine and models.

Supplements the existing RBAC system (SpiceDB) with fine-grained
attribute-based policy evaluation. ABAC policies evaluate subject,
resource, and environment attributes against a combining algorithm
(deny-overrides) to produce an access decision.

GOV-F-012
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from django.db import models

from apps.core.models import TenantModel, UUIDModel

logger = logging.getLogger("voyant.governance")

__all__ = [
    "ABACPolicy",
    "ABACDecision",
    "ABACEngine",
    "evaluate_abac",
]


# ---------------------------------------------------------------------------
# Decision enum
# ---------------------------------------------------------------------------


class ABACDecision(str, Enum):
    """Outcome of an ABAC policy evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"


# ---------------------------------------------------------------------------
# Django Model
# ---------------------------------------------------------------------------


class ABACPolicy(TenantModel, UUIDModel):
    """Attribute-Based Access Control policy.

    Each policy declares conditions on subject, resource, and environment
    attributes. When all conditions match, the policy produces its
    configured decision (allow/deny).

    Policies are evaluated in priority order (lower number = higher priority).
    The combining algorithm is **deny-overrides**: if *any* matching policy
    returns DENY, the final decision is DENY regardless of how many ALLOW
    policies matched.
    """

    class Decision(models.TextChoices):
        ALLOW = "allow", "Allow"
        DENY = "deny", "Deny"

    STATUS_ACTIVE = "active"
    STATUS_INACTIVE = "inactive"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_INACTIVE, "Inactive"),
    ]

    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Unique policy name",
    )
    description = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )

    # Subject conditions (who is requesting)
    subject_attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Subject attribute conditions: {"roles": ["analyst"], '
            '"department": "finance", "clearance_level": {"gte": 3}}'
        ),
    )

    # Resource conditions (what is being accessed)
    resource_attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Resource attribute conditions: {"type": "dataset", '
            '"classification": ["public", "internal"], "owner_team": "$subject.team"}'
        ),
    )

    # Environment conditions (context of the request)
    environment_attributes = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            'Environment attribute conditions: {"time_of_day": {"gte": "08:00", "lte": "18:00"}, '
            '"ip_range": "10.0.0.0/8", "day_of_week": ["mon", "tue", "wed", "thu", "fri"]}'
        ),
    )

    # Decision
    decision = models.CharField(
        max_length=10,
        choices=Decision.choices,
        default=Decision.DENY,
        help_text="Decision when all conditions match",
    )

    # Ordering
    priority = models.IntegerField(
        default=100,
        help_text="Lower number = higher priority. Evaluated in ascending order.",
    )

    class Meta(TenantModel.Meta, UUIDModel.Meta):
        db_table = "governance_abac_policy"
        verbose_name = "ABAC Policy"
        verbose_name_plural = "ABAC Policies"
        indexes = [
            models.Index(fields=["tenant_id", "status"]),
            models.Index(fields=["priority"]),
        ]

    def __str__(self) -> str:
        return f"ABAC({self.name} [{self.decision}] p={self.priority})"


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class ABACEngine:
    """Evaluates ABAC policies using deny-overrides combining algorithm.

    Usage::

        engine = ABACEngine(tenant_id="tenant-1")
        decision = engine.evaluate(
            subject={"id": "u1", "roles": ["analyst"], "department": "finance"},
            resource={"type": "dataset", "classification": "internal"},
            environment={"ip_address": "10.0.1.50"},
        )
        # decision == ABACDecision.ALLOW
    """

    def __init__(self, tenant_id: str | None = None) -> None:
        self._tenant_id = tenant_id

    def evaluate(
        self,
        *,
        subject: dict[str, Any],
        resource: dict[str, Any],
        environment: dict[str, Any],
    ) -> ABACDecision:
        """Evaluate all active policies and return the combined decision.

        Combining algorithm: **deny-overrides**
        - Any matching policy with decision=deny → final DENY
        - Otherwise, if at least one matching policy has decision=allow → ALLOW
        - If no policies match → NOT_APPLICABLE (treated as ALLOW by default)

        Parameters
        ----------
        subject:
            Subject attributes (e.g., user roles, department, clearance).
        resource:
            Resource attributes (e.g., type, classification, owner).
        environment:
            Environment attributes (e.g., time, IP, device).

        Returns
        -------
        ABACDecision
        """
        policies = self._get_active_policies()
        if not policies:
            return ABACDecision.NOT_APPLICABLE

        has_allow = False
        for policy in policies:
            if not self._matches_conditions(policy, subject, resource, environment):
                continue

            if policy.decision == ABACPolicy.Decision.DENY:
                logger.info(
                    "ABAC DENY: policy=%s matched subject=%s resource=%s",
                    policy.name,
                    subject.get("id"),
                    resource.get("type"),
                )
                return ABACDecision.DENY

            if policy.decision == ABACPolicy.Decision.ALLOW:
                has_allow = True

        if has_allow:
            return ABACDecision.ALLOW
        return ABACDecision.NOT_APPLICABLE

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _get_active_policies(self) -> list[ABACPolicy]:
        """Fetch active policies ordered by priority."""
        try:
            qs = ABACPolicy.objects.filter(status=ABACPolicy.STATUS_ACTIVE)
            if self._tenant_id:
                qs = qs.filter(tenant_id=self._tenant_id)
            return list(qs.order_by("priority"))
        except Exception:
            logger.debug("ABACPolicy query failed", exc_info=True)
            return []

    @staticmethod
    def _matches_conditions(
        policy: ABACPolicy,
        subject: dict[str, Any],
        resource: dict[str, Any],
        environment: dict[str, Any],
    ) -> bool:
        """Check whether a policy's conditions all match the request context."""
        if not _match_dict(policy.subject_attributes, subject, subject):
            return False
        if not _match_dict(policy.resource_attributes, resource, subject):
            return False
        if not _match_dict(policy.environment_attributes, environment, subject):
            return False
        return True


# ---------------------------------------------------------------------------
# Condition matching helpers
# ---------------------------------------------------------------------------


def _match_dict(
    conditions: dict[str, Any],
    attributes: dict[str, Any],
    subject: dict[str, Any],
) -> bool:
    """Match a set of conditions against attributes.

    Supports:
    - Exact match: ``{"key": "value"}``
    - List membership: ``{"key": ["a", "b"]}`` — attribute must be in list
    - Comparison operators: ``{"key": {"gte": 5, "lte": 10}}``
    - Subject reference: ``{"key": "$subject.attr"}`` — resolved from subject
    - Negation: ``{"key": {"not": "value"}}``
    """
    if not conditions:
        return True  # No conditions → always matches.

    for key, expected in conditions.items():
        actual = attributes.get(key)
        if not _match_value(expected, actual, subject):
            return False
    return True


def _match_value(
    expected: Any,
    actual: Any,
    subject: dict[str, Any],
) -> bool:
    """Match a single expected value against an actual value."""
    # Subject reference resolution
    if isinstance(expected, str) and expected.startswith("$subject."):
        ref_attr = expected[len("$subject."):]
        expected = subject.get(ref_attr)

    # Exact match
    if not isinstance(expected, dict) and not isinstance(expected, list):
        return actual == expected

    # List membership (actual must be in the list)
    if isinstance(expected, list):
        return actual in expected

    # Dict with operators
    if isinstance(expected, dict):
        if actual is None:
            return False

        # Negation
        if "not" in expected:
            return actual != expected["not"]

        # Numeric/string comparisons
        if "gte" in expected:
            if not _compare(actual, expected["gte"], ">="):
                return False
        if "lte" in expected:
            if not _compare(actual, expected["lte"], "<="):
                return False
        if "gt" in expected:
            if not _compare(actual, expected["gt"], ">"):
                return False
        if "lt" in expected:
            if not _compare(actual, expected["lt"], "<"):
                return False

        # Regex match
        if "regex" in expected:
            if not isinstance(actual, str):
                return False
            import re
            return bool(re.match(expected["regex"], actual))

        # Contains
        if "contains" in expected:
            if isinstance(actual, str):
                return expected["contains"] in actual
            if isinstance(actual, list):
                return expected["contains"] in actual
            return False

        # "in" operator
        if "in" in expected:
            return actual in expected["in"]

        return True

    return actual == expected


def _compare(actual: Any, expected: Any, op: str) -> bool:
    """Compare two values with a comparison operator."""
    try:
        if op == ">=":
            return actual >= expected
        elif op == "<=":
            return actual <= expected
        elif op == ">":
            return actual > expected
        elif op == "<":
            return actual < expected
    except TypeError:
        return False
    return False


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def evaluate_abac(
    *,
    tenant_id: str | None = None,
    subject: dict[str, Any],
    resource: dict[str, Any],
    environment: dict[str, Any] | None = None,
) -> ABACDecision:
    """Convenience function to evaluate ABAC policies.

    Parameters
    ----------
    tenant_id:
        Tenant scope. ``None`` evaluates across all tenants.
    subject:
        Subject attributes.
    resource:
        Resource attributes.
    environment:
        Environment attributes. Defaults to empty dict.

    Returns
    -------
    ABACDecision
    """
    engine = ABACEngine(tenant_id=tenant_id)
    return engine.evaluate(
        subject=subject,
        resource=resource,
        environment=environment or {},
    )
