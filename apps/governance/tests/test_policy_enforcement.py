"""Tests for governance policy enforcement middleware and enforcer logic."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpRequest, JsonResponse

from apps.governance.lib.policy_enforcer import (
    EnforcementLevel,
    PolicyDecision,
    PolicyEnforcer,
    PolicyEvaluator,
    _evaluate_rules,
    _scope_matches,
)
from apps.governance.middleware import (
    GovernancePolicyMiddleware,
    _build_context,
    _extract_dataset_urn,
    _infer_operation,
    _validate_request_against_contract,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_policy(
    *,
    policy_id: str = "pol-1",
    name: str = "test-policy",
    rules: dict | None = None,
    scope: dict | None = None,
    enforcement_level: str = "strict",
    status: str = "active",
) -> SimpleNamespace:
    """Create a lightweight policy-like object (no DB needed)."""
    return SimpleNamespace(
        id=policy_id,
        name=name,
        rules=rules or {},
        scope=scope or {},
        enforcement_level=enforcement_level,
        status=status,
    )


def _make_request(
    method: str = "GET",
    path: str = "/api/v1/datasets",
    user_id: str = "user-1",
    headers: dict | None = None,
    body: bytes = b"",
) -> HttpRequest:
    """Create a minimal Django test request."""
    req = HttpRequest()
    req.method = method
    # Split path and query string so get_full_path() works correctly.
    if "?" in path:
        req.path, query_string = path.split("?", 1)
        req.META["QUERY_STRING"] = query_string
    else:
        req.path = path
    req.META["REMOTE_ADDR"] = "127.0.0.1"
    if headers:
        for k, v in headers.items():
            req.META[f"HTTP_{k.upper().replace('-', '_')}"] = v
    if body:
        req._body = body  # noqa: SLF001
        req.META["CONTENT_LENGTH"] = str(len(body))
    return req


# ===========================================================================
# Scope matching
# ===========================================================================


class TestScopeMatching:
    """Test _scope_matches helper."""

    def test_empty_scope_matches_everything(self):
        assert _scope_matches({}, {"path": "/anything"}) is True

    def test_path_scope_match(self):
        scope = {"paths": ["/api/v1/datasets/*"]}
        assert _scope_matches(scope, {"path": "/api/v1/datasets/orders"}) is True
        assert _scope_matches(scope, {"path": "/api/v1/users"}) is False

    def test_method_scope_match(self):
        scope = {"methods": ["POST", "PUT"]}
        assert _scope_matches(scope, {"method": "POST"}) is True
        assert _scope_matches(scope, {"method": "GET"}) is False

    def test_roles_scope_requires_overlap(self):
        scope = {"roles": ["admin", "data_engineer"]}
        assert _scope_matches(scope, {"roles": ["admin"]}) is True
        assert _scope_matches(scope, {"roles": ["viewer"]}) is False
        assert _scope_matches(scope, {"roles": []}) is False

    def test_combined_scope(self):
        scope = {"paths": ["/api/*"], "methods": ["DELETE"]}
        assert _scope_matches(scope, {"path": "/api/v1/x", "method": "DELETE"}) is True
        assert _scope_matches(scope, {"path": "/api/v1/x", "method": "GET"}) is False

    def test_operations_scope(self):
        scope = {"operations": ["write", "delete"]}
        assert _scope_matches(scope, {"operation": "write"}) is True
        assert _scope_matches(scope, {"operation": "read"}) is False


# ===========================================================================
# Rule evaluation
# ===========================================================================


class TestRuleEvaluation:
    """Test _evaluate_rules helper."""

    def test_empty_rules_allow(self):
        allowed, reason = _evaluate_rules({}, {})
        assert allowed is True
        assert reason is None

    def test_allowed_roles_pass(self):
        rules = {"allowed_roles": ["admin"]}
        allowed, _ = _evaluate_rules(rules, {"roles": ["admin"]})
        assert allowed is True

    def test_allowed_roles_fail(self):
        rules = {"allowed_roles": ["admin"]}
        allowed, reason = _evaluate_rules(rules, {"roles": ["viewer"]})
        assert allowed is False
        assert "required role" in reason.lower()  # type: ignore[reportOptionalMemberAccess]

    def test_denied_roles_block(self):
        rules = {"denied_roles": ["banned"]}
        allowed, reason = _evaluate_rules(rules, {"roles": ["banned", "viewer"]})
        assert allowed is False
        assert "denied role" in reason.lower()  # type: ignore[reportOptionalMemberAccess]

    def test_denied_methods(self):
        rules = {"denied_methods": ["DELETE"]}
        allowed, _ = _evaluate_rules(rules, {"method": "DELETE"})
        assert allowed is False

    def test_allowed_methods(self):
        rules = {"allowed_methods": ["GET", "POST"]}
        assert _evaluate_rules(rules, {"method": "GET"})[0] is True
        assert _evaluate_rules(rules, {"method": "DELETE"})[0] is False

    def test_denied_paths(self):
        rules = {"denied_paths": ["/admin/*"]}
        allowed, _ = _evaluate_rules(rules, {"path": "/admin/secrets"})
        assert allowed is False

    def test_require_auth(self):
        rules = {"require_auth": True}
        assert _evaluate_rules(rules, {"user_id": ""})[0] is False
        assert _evaluate_rules(rules, {"user_id": "u1"})[0] is True

    def test_max_request_body(self):
        rules = {"max_request_body": 1024}
        assert _evaluate_rules(rules, {"content_length": 500})[0] is True
        assert _evaluate_rules(rules, {"content_length": 2048})[0] is False

    def test_required_headers(self):
        rules = {"required_headers": ["X-Tenant-ID"]}
        assert _evaluate_rules(rules, {"headers": {"x-tenant-id": "t1"}})[0] is True
        assert _evaluate_rules(rules, {"headers": {}})[0] is False

    def test_denied_operations(self):
        rules = {"denied_operations": ["delete"]}
        assert _evaluate_rules(rules, {"operation": "delete"})[0] is False
        assert _evaluate_rules(rules, {"operation": "read"})[0] is True


# ===========================================================================
# PolicyEvaluator (real implementation)
# ===========================================================================


class TestPolicyEvaluator:
    """Test the real PolicyEvaluator logic."""

    def setup_method(self):
        self.evaluator = PolicyEvaluator()

    def test_out_of_scope_returns_defer(self):
        policy = _make_policy(
            scope={"paths": ["/api/v1/admin/*"]},
            rules={"allowed_roles": ["admin"]},
        )
        result = self.evaluator.evaluate_policy(policy, {"path": "/api/v1/datasets"})
        assert result.decision == PolicyDecision.DEFER

    def test_in_scope_allows(self):
        policy = _make_policy(
            scope={"paths": ["/api/*"]},
            rules={"allowed_roles": ["admin"]},
        )
        result = self.evaluator.evaluate_policy(
            policy, {"path": "/api/v1/datasets", "roles": ["admin"]}
        )
        assert result.decision == PolicyDecision.ALLOW

    def test_in_scope_denies(self):
        policy = _make_policy(
            scope={"paths": ["/api/*"]},
            rules={"allowed_roles": ["admin"]},
        )
        result = self.evaluator.evaluate_policy(
            policy, {"path": "/api/v1/datasets", "roles": ["viewer"]}
        )
        assert result.decision == PolicyDecision.DENY
        assert result.enforcement_level == EnforcementLevel.STRICT

    def test_warn_enforcement_level(self):
        policy = _make_policy(
            enforcement_level="warn",
            rules={"denied_methods": ["DELETE"]},
        )
        result = self.evaluator.evaluate_policy(policy, {"method": "DELETE"})
        assert result.decision == PolicyDecision.DENY
        assert result.enforcement_level == EnforcementLevel.WARN

    def test_audit_enforcement_level(self):
        policy = _make_policy(
            enforcement_level="audit",
            rules={"denied_paths": ["/legacy/*"]},
        )
        result = self.evaluator.evaluate_policy(policy, {"path": "/legacy/old"})
        assert result.decision == PolicyDecision.DENY
        assert result.enforcement_level == EnforcementLevel.AUDIT

    def test_empty_rules_allow(self):
        policy = _make_policy(rules={})
        result = self.evaluator.evaluate_policy(policy, {"path": "/anything"})
        assert result.decision == PolicyDecision.ALLOW


# ===========================================================================
# PolicyEnforcer (real implementation)
# ===========================================================================


class TestPolicyEnforcer:
    """Test the real PolicyEnforcer aggregation logic."""

    def setup_method(self):
        self.enforcer = PolicyEnforcer()

    def test_no_policies_returns_allow(self):
        result = self.enforcer.enforce([], {"path": "/x"})
        assert result.decision == PolicyDecision.ALLOW

    def test_single_allow_policy(self):
        policy = _make_policy(rules={"allowed_roles": ["admin"]})
        result = self.enforcer.enforce([policy], {"roles": ["admin"]})
        assert result.decision == PolicyDecision.ALLOW

    def test_single_deny_policy(self):
        policy = _make_policy(rules={"denied_methods": ["DELETE"]})
        result = self.enforcer.enforce([policy], {"method": "DELETE"})
        assert result.decision == PolicyDecision.DENY

    def test_deny_overrides_allow(self):
        allow_policy = _make_policy(
            policy_id="allow-pol",
            rules={"allowed_roles": ["admin"]},
        )
        deny_policy = _make_policy(
            policy_id="deny-pol",
            rules={"denied_methods": ["DELETE"]},
        )
        result = self.enforcer.enforce(
            [allow_policy, deny_policy],
            {"roles": ["admin"], "method": "DELETE"},
        )
        assert result.decision == PolicyDecision.DENY
        assert result.policy_id == "deny-pol"

    def test_defer_overrides_allow(self):
        """A policy that doesn't match scope returns DEFER, which is more
        restrictive than ALLOW."""
        scoped_policy = _make_policy(
            scope={"paths": ["/admin/*"]},
            rules={"denied_methods": ["DELETE"]},
        )
        result = self.enforcer.enforce(
            [scoped_policy],
            {"path": "/api/v1/data", "method": "DELETE"},
        )
        # Scoped-out policy returns DEFER, but no DENY → overall DEFER
        assert result.decision == PolicyDecision.DEFER

    def test_check_access_raises_for_strict_deny(self):
        policy = _make_policy(
            enforcement_level="strict",
            rules={"require_auth": True},
        )
        with pytest.raises(PermissionError, match="Policy denied"):
            self.enforcer.check_access([policy], {"user_id": ""})

    def test_check_access_returns_false_for_warn_deny(self):
        policy = _make_policy(
            enforcement_level="warn",
            rules={"denied_methods": ["DELETE"]},
        )
        assert self.enforcer.check_access([policy], {"method": "DELETE"}) is False

    def test_check_access_returns_true_for_allow(self):
        policy = _make_policy(rules={"allowed_roles": ["admin"]})
        assert self.enforcer.check_access([policy], {"roles": ["admin"]}) is True

    def test_short_circuit_on_first_deny(self):
        """Once a DENY is found, remaining policies are not evaluated."""
        deny_policy = _make_policy(policy_id="deny", rules={"require_auth": True})
        # This policy would ALLOW but should never be reached.
        allow_policy = _make_policy(policy_id="allow", rules={})
        result = self.enforcer.enforce(
            [deny_policy, allow_policy],
            {"user_id": ""},
        )
        assert result.decision == PolicyDecision.DENY
        assert result.policy_id == "deny"


# ===========================================================================
# Middleware helpers
# ===========================================================================


class TestMiddlewareHelpers:
    """Test standalone helper functions in the middleware module."""

    def test_infer_operation_get(self):
        req = _make_request(method="GET", path="/api/v1/datasets")
        assert _infer_operation(req) == "read"

    def test_infer_operation_delete(self):
        req = _make_request(method="DELETE", path="/api/v1/datasets/1")
        assert _infer_operation(req) == "delete"

    def test_infer_operation_post(self):
        req = _make_request(method="POST", path="/api/v1/jobs")
        assert _infer_operation(req) == "write"

    def test_extract_dataset_urn_from_query(self):
        req = _make_request(path="/api/v1/data?dataset_urn=urn:li:dataset:orders")
        assert _extract_dataset_urn(req) == "urn:li:dataset:orders"

    def test_extract_dataset_urn_from_path(self):
        req = _make_request(path="/api/v1/datasets/urn:li:dataset:orders/details")
        assert _extract_dataset_urn(req) == "urn:li:dataset:orders"

    def test_extract_dataset_urn_empty(self):
        req = _make_request(path="/api/v1/jobs")
        assert _extract_dataset_urn(req) == ""

    def test_validate_request_against_contract_required_field(self):
        contract = SimpleNamespace(
            name="orders-contract",
            quality_rules=[{"type": "required_field", "column": "order_id"}],
        )
        req = _make_request(
            method="POST",
            body=json.dumps({"amount": 100}).encode(),
        )
        violation = _validate_request_against_contract(req, contract)
        assert violation is not None
        assert "order_id" in violation

    def test_validate_request_against_contract_passes(self):
        contract = SimpleNamespace(
            name="orders-contract",
            quality_rules=[{"type": "required_field", "column": "order_id"}],
        )
        req = _make_request(
            method="POST",
            body=json.dumps({"order_id": "123", "amount": 100}).encode(),
        )
        assert _validate_request_against_contract(req, contract) is None

    def test_validate_not_null_rule(self):
        contract = SimpleNamespace(
            name="c",
            quality_rules=[{"type": "not_null", "column": "email"}],
        )
        req = _make_request(body=json.dumps({"email": None}).encode())
        assert _validate_request_against_contract(req, contract) is not None

    def test_validate_no_rules_passes(self):
        contract = SimpleNamespace(name="c", quality_rules=[])
        req = _make_request(body=b"{}")
        assert _validate_request_against_contract(req, contract) is None

    def test_build_context_extracts_fields(self):
        req = _make_request(
            method="POST",
            path="/api/v1/datasets",
            headers={"X-Tenant-ID": "t1"},
        )
        ctx = _build_context(req)
        assert ctx["method"] == "POST"
        assert ctx["path"] == "/api/v1/datasets"
        assert ctx["operation"] == "write"


# ===========================================================================
# GovernancePolicyMiddleware
# ===========================================================================


class TestGovernancePolicyMiddleware:
    """Test the middleware as a Django middleware callable."""

    def _make_middleware(self, get_response=None):
        if get_response is None:
            get_response = MagicMock(return_value=JsonResponse({"ok": True}))
        return GovernancePolicyMiddleware(get_response)

    @patch.object(GovernancePolicyMiddleware, "_get_active_policies", return_value=[])
    def test_exempt_path_skips_enforcement(self, mock_policies):
        mw = self._make_middleware()
        req = _make_request(path="/healthz")
        resp = mw(req)
        assert resp.status_code == 200
        mock_policies.assert_not_called()

    @patch.object(GovernancePolicyMiddleware, "_get_active_policies", return_value=[])
    def test_no_policies_allows_request(self, mock_policies):
        mw = self._make_middleware()
        req = _make_request(path="/api/v1/datasets")
        resp = mw(req)
        assert resp.status_code == 200

    @patch.object(
        GovernancePolicyMiddleware,
        "_get_active_policies",
        return_value=[
            _make_policy(
                rules={"denied_methods": ["DELETE"]},
                enforcement_level="strict",
            )
        ],
    )
    def test_strict_deny_returns_403(self, mock_policies):
        mw = self._make_middleware()
        req = _make_request(method="DELETE", path="/api/v1/datasets/1")
        resp = mw(req)
        assert resp.status_code == 403
        body = json.loads(resp.content)
        assert (
            "blocked" in body["message"].lower() or "denied" in body["message"].lower()
        )

    @patch.object(
        GovernancePolicyMiddleware,
        "_get_active_policies",
        return_value=[
            _make_policy(
                rules={"denied_methods": ["DELETE"]},
                enforcement_level="warn",
            )
        ],
    )
    def test_warn_deny_allows_request_through(self, mock_policies):
        mw = self._make_middleware()
        req = _make_request(method="DELETE", path="/api/v1/datasets/1")
        resp = mw(req)
        # warn level should NOT block
        assert resp.status_code == 200

    @patch.object(
        GovernancePolicyMiddleware,
        "_get_active_policies",
        return_value=[
            _make_policy(
                rules={"denied_methods": ["DELETE"]},
                enforcement_level="audit",
            )
        ],
    )
    def test_audit_deny_allows_request_through(self, mock_policies):
        mw = self._make_middleware()
        req = _make_request(method="DELETE", path="/api/v1/datasets/1")
        resp = mw(req)
        assert resp.status_code == 200

    @patch.object(
        GovernancePolicyMiddleware,
        "_get_active_policies",
        return_value=[_make_policy(rules={})],  # empty rules → allows everything
    )
    def test_allowed_request_passes(self, mock_policies):
        mw = self._make_middleware()
        req = _make_request(path="/api/v1/datasets")
        resp = mw(req)
        assert resp.status_code == 200

    @patch.object(
        GovernancePolicyMiddleware,
        "_get_active_policies",
        return_value=[
            _make_policy(rules={})  # empty rules → allows, headers still attached
        ],
    )
    def test_governance_headers_attached(self, mock_policies):
        mw = self._make_middleware()
        req = _make_request(path="/api/v1/datasets")
        resp = mw(req)
        assert "X-Governance-Decision" in resp

    @patch.object(GovernancePolicyMiddleware, "_get_active_policies", return_value=[])
    def test_health_endpoints_bypass(self, mock_policies):
        mw = self._make_middleware()
        for path in ("/health", "/ready", "/healthz", "/readyz"):
            req = _make_request(path=path)
            resp = mw(req)
            assert resp.status_code == 200

    @patch.object(
        GovernancePolicyMiddleware,
        "_get_active_policies",
        return_value=[
            _make_policy(
                rules={"allowed_roles": ["admin"]},
                enforcement_level="strict",
            )
        ],
    )
    @patch("apps.governance.middleware._check_data_contracts", return_value=None)
    def test_strict_deny_blocks_and_logs_audit(self, mock_contracts, mock_policies):
        mw = self._make_middleware()
        req = _make_request(path="/api/v1/datasets", headers={"X-Tenant-ID": "t1"})
        with patch("apps.governance.middleware._log_audit_event") as mock_audit:
            resp = mw(req)
            assert resp.status_code == 403
            mock_audit.assert_called_once()

    @patch.object(
        GovernancePolicyMiddleware,
        "_get_active_policies",
        return_value=[
            _make_policy(
                rules={"allowed_roles": ["admin"]},
                enforcement_level="warn",
            )
        ],
    )
    def test_warn_deny_logs_but_does_not_block(self, mock_policies):
        mw = self._make_middleware()
        req = _make_request(path="/api/v1/datasets")
        with patch("apps.governance.middleware._log_audit_event") as mock_audit:
            resp = mw(req)
            # warn level: request proceeds
            assert resp.status_code == 200
            # but audit event is still logged
            mock_audit.assert_called_once()
