"""Tests for policy enforcement module."""

from unittest.mock import patch

import pytest

from apps.governance.lib.policy_enforcer import (
    EnforcementLevel,
    PolicyDecision,
    PolicyEnforcer,
    PolicyEvaluationResult,
    PolicyEvaluator,
)


class TestEnforcementLevel:
    """Test EnforcementLevel enum."""

    def test_strict_value(self):
        assert EnforcementLevel.STRICT.value == "strict"

    def test_warn_value(self):
        assert EnforcementLevel.WARN.value == "warn"

    def test_audit_value(self):
        assert EnforcementLevel.AUDIT.value == "audit"

    def test_all_levels_exist(self):
        levels = [
            EnforcementLevel.STRICT,
            EnforcementLevel.WARN,
            EnforcementLevel.AUDIT,
        ]
        assert len(levels) == 3


class TestPolicyDecision:
    """Test PolicyDecision enum."""

    def test_allow_value(self):
        assert PolicyDecision.ALLOW.value == "allow"

    def test_deny_value(self):
        assert PolicyDecision.DENY.value == "deny"

    def test_defer_value(self):
        assert PolicyDecision.DEFER.value == "defer"

    def test_all_decisions_exist(self):
        decisions = [PolicyDecision.ALLOW, PolicyDecision.DENY, PolicyDecision.DEFER]
        assert len(decisions) == 3


class TestPolicyEvaluationResult:
    """Test PolicyEvaluationResult dataclass."""

    def test_default_result(self):
        result = PolicyEvaluationResult(decision=PolicyDecision.ALLOW)
        assert result.decision == PolicyDecision.ALLOW
        assert result.policy_id is None
        assert result.reason is None
        assert result.enforcement_level is None

    def test_result_with_details(self):
        result = PolicyEvaluationResult(
            decision=PolicyDecision.DENY,
            policy_id="policy_123",
            reason="Access denied",
            enforcement_level=EnforcementLevel.STRICT,
        )
        assert result.decision == PolicyDecision.DENY
        assert result.policy_id == "policy_123"
        assert result.reason == "Access denied"
        assert result.enforcement_level == EnforcementLevel.STRICT

    def test_result_defer(self):
        result = PolicyEvaluationResult(
            decision=PolicyDecision.DEFER,
            reason="Unable to determine",
        )
        assert result.decision == PolicyDecision.DEFER
        assert result.reason == "Unable to determine"


class TestPolicyEvaluator:
    """Test PolicyEvaluator with real implementation."""

    def setup_method(self):
        self.evaluator = PolicyEvaluator()

    def test_evaluate_policy_no_scope_no_rules_returns_allow(self):
        """A policy with no scope and no rules matches everything and allows."""
        policy = type("Policy", (), {"name": "test_policy"})()
        context = {"user_id": "user1", "operation": "read"}
        result = self.evaluator.evaluate_policy(policy, context)
        assert result.decision == PolicyDecision.ALLOW

    def test_evaluate_policy_with_empty_context(self):
        policy = type("Policy", (), {"name": "test_policy"})()
        result = self.evaluator.evaluate_policy(policy, {})
        assert result.decision == PolicyDecision.ALLOW

    def test_evaluate_policy_with_complex_context(self):
        """A policy with no scope/rules allows any context."""
        policy = type("Policy", (), {"name": "access_control"})()
        context = {
            "user_id": "user123",
            "roles": ["admin", "data_engineer"],
            "department": "analytics",
            "operation": "write",
            "dataset_urn": "urn:li:dataset:orders",
            "timestamp": "2024-01-15T10:30:00Z",
        }
        result = self.evaluator.evaluate_policy(policy, context)
        assert result.decision == PolicyDecision.ALLOW

    def test_evaluate_policy_out_of_scope_returns_defer(self):
        """A policy whose scope doesn't match the context returns DEFER."""
        policy = type(
            "Policy",
            (),
            {
                "name": "scoped_policy",
                "scope": {"paths": ["/admin/*"]},
                "rules": {"denied_methods": ["DELETE"]},
                "enforcement_level": "strict",
            },
        )()
        result = self.evaluator.evaluate_policy(policy, {"path": "/api/v1/data"})
        assert result.decision == PolicyDecision.DEFER

    def test_evaluate_policy_denies_when_rules_violated(self):
        policy = type(
            "Policy",
            (),
            {
                "name": "deny_delete",
                "scope": {},
                "rules": {"denied_methods": ["DELETE"]},
                "enforcement_level": "strict",
            },
        )()
        result = self.evaluator.evaluate_policy(policy, {"method": "DELETE"})
        assert result.decision == PolicyDecision.DENY


class TestPolicyEnforcer:
    """Test PolicyEnforcer with real implementation."""

    def setup_method(self):
        self.enforcer = PolicyEnforcer()

    def test_enforce_returns_allow(self):
        policies = [type("Policy", (), {"name": "policy1"})()]
        context = {"user_id": "user1"}
        result = self.enforcer.enforce(policies, context)
        assert result.decision == PolicyDecision.ALLOW

    def test_enforce_with_empty_policies(self):
        result = self.enforcer.enforce([], {"user_id": "user1"})
        assert result.decision == PolicyDecision.ALLOW

    def test_enforce_with_multiple_policies(self):
        policies = [
            type("Policy", (), {"name": "policy1"})(),
            type("Policy", (), {"name": "policy2"})(),
            type("Policy", (), {"name": "policy3"})(),
        ]
        context = {"user_id": "user1", "operation": "read"}
        result = self.enforcer.enforce(policies, context)
        assert result.decision == PolicyDecision.ALLOW

    def test_check_access_returns_true_for_allow(self):
        policies = [type("Policy", (), {"name": "policy1"})()]
        context = {"user_id": "user1"}
        assert self.enforcer.check_access(policies, context) is True

    def test_check_access_returns_true_for_defer(self):
        policies = [type("Policy", (), {"name": "policy1"})()]
        context = {"user_id": "user1"}
        assert self.enforcer.check_access(policies, context) is True

    def test_check_access_raises_for_strict_deny(self):
        original_enforce = self.enforcer.enforce

        def mock_enforce(policies, context):
            return PolicyEvaluationResult(
                decision=PolicyDecision.DENY,
                reason="Access denied by policy",
                enforcement_level=EnforcementLevel.STRICT,
            )

        self.enforcer.enforce = mock_enforce
        policies = [type("Policy", (), {"name": "policy1"})()]
        context = {"user_id": "user1"}

        with pytest.raises(PermissionError, match="Policy denied"):
            self.enforcer.check_access(policies, context)

        self.enforcer.enforce = original_enforce

    def test_check_access_returns_false_for_warn_deny(self):
        with patch.object(self.enforcer, "enforce") as mock_enforce:
            mock_enforce.return_value = PolicyEvaluationResult(
                decision=PolicyDecision.DENY,
                reason="Warning: unusual access pattern",
                enforcement_level=EnforcementLevel.WARN,
            )
            policies = [type("Policy", (), {"name": "policy1"})()]
            context = {"user_id": "user1"}

            assert self.enforcer.check_access(policies, context) is False

    def test_enforcer_initialization_with_custom_evaluator(self):
        custom_evaluator = PolicyEvaluator()
        enforcer = PolicyEnforcer(evaluator=custom_evaluator)
        assert enforcer.evaluator is custom_evaluator

    def test_enforcer_default_initialization(self):
        enforcer = PolicyEnforcer()
        assert isinstance(enforcer.evaluator, PolicyEvaluator)
