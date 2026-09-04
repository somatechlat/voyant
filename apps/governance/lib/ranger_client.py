"""
Apache Ranger Policy Enforcement Client (FR-22).

Provides integration with Apache Ranger for centralized policy-based access
control. Evaluates access requests against Ranger policies for table, column,
and row-level security.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import httpx

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


class AccessDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    NOT_DETERMINED = "not_determined"


class ResourceType(StrEnum):
    TABLE = "table"
    COLUMN = "column"
    DATABASE = "database"
    URI = "uri"


@dataclass
class AccessRequest:
    """A request to evaluate access against Ranger policies."""

    user: str
    groups: list[str]
    resource_type: ResourceType
    resource_name: str
    database: str = ""
    column: str = ""
    action: str = "select"


@dataclass
class AccessResult:
    """Result of a Ranger policy evaluation."""

    decision: AccessDecision
    policy_id: int | None = None
    policy_name: str = ""
    reason: str = ""


@dataclass
class RangerPolicy:
    """Represents a Ranger policy."""

    id: int
    name: str
    service: str
    resources: dict[str, Any] = field(default_factory=dict)
    policy_items: list[dict[str, Any]] = field(default_factory=list)
    is_enabled: bool = True


class RangerClient:
    """
    Client for Apache Ranger REST API.

    Provides policy evaluation, policy management, and audit log access
    for centralized authorization across the Voyant platform.
    """

    def __init__(self, base_url: str | None = None):
        settings = get_settings()
        self.base_url = base_url or getattr(settings, "ranger_url", "")
        self.service_name = getattr(settings, "ranger_service_name", "voyant")
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=10.0,
                auth=(
                    getattr(get_settings(), "ranger_admin_user", "admin"),
                    getattr(get_settings(), "ranger_admin_password", ""),
                ),
            )
        return self._client

    def check_access(self, request: AccessRequest) -> AccessResult:
        """
        Evaluate an access request against Ranger policies.

        Uses the Ranger REST API to check if the specified user/group
        has permission to perform the requested action on the resource.
        """
        payload = {
            "request": {
                "user": request.user,
                "groups": request.groups,
                "resource": {
                    request.resource_type.value: request.resource_name,
                },
                "action": request.action,
            }
        }
        if request.database:
            payload["request"]["resource"]["database"] = request.database
        if request.column:
            payload["request"]["resource"]["column"] = request.column

        try:
            resp = self._get_client().post(
                f"/service/{self.service_name}/policies/evaluate",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            decision_str = data.get("decision", "not_determined")
            return AccessResult(
                decision=AccessDecision(decision_str),
                policy_id=data.get("policyId"),
                policy_name=data.get("policyName", ""),
                reason=data.get("reason", ""),
            )
        except httpx.HTTPStatusError as exc:
            logger.warning("Ranger access check failed: %s", exc)
            return AccessResult(
                decision=AccessDecision.NOT_DETERMINED,
                reason=f"Ranger API error: {exc.response.status_code}",
            )
        except Exception as exc:
            logger.warning("Ranger unavailable: %s", exc)
            return AccessResult(
                decision=AccessDecision.NOT_DETERMINED,
                reason=f"Ranger unavailable: {exc}",
            )

    def list_policies(self, service: str | None = None) -> list[RangerPolicy]:
        """List all policies for a service."""
        svc = service or self.service_name
        resp = self._get_client().get(f"/service/{svc}/policies")
        resp.raise_for_status()
        data = resp.json()
        policies = data if isinstance(data, list) else data.get("policies", [])
        return [
            RangerPolicy(
                id=p.get("id", 0),
                name=p.get("name", ""),
                service=svc,
                resources=p.get("resources", {}),
                policy_items=p.get("policyItems", []),
                is_enabled=p.get("isEnabled", True),
            )
            for p in policies
        ]

    def create_policy(self, policy: dict[str, Any]) -> dict:
        """Create a new Ranger policy."""
        resp = self._get_client().post(
            f"/service/{self.service_name}/policies",
            json=policy,
        )
        resp.raise_for_status()
        return resp.json()

    def is_available(self) -> bool:
        """Check if Ranger is reachable."""
        try:
            resp = self._get_client().get("/service/public/v2/api/service")
            return resp.status_code == 200
        except Exception:
            return False


def get_ranger_client() -> RangerClient:
    """Factory function for the singleton Ranger client."""
    return RangerClient()
