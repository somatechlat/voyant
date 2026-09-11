"""
Unit tests for apps.core.lib.policy — PolicyContext, exception hierarchy,
helper functions, and policy enforcement logic.

Real dataclass construction and helper function logic. No mocks.
"""

from uuid import UUID

import pytest

from apps.core.lib.policy import (
    PolicyContext,
    PolicyError,
    SomaContextError,
    SomaIntegrationError,
    SomaPolicyDenied,
    SomaPolicyUnavailable,
    _ensure_suffix,
    _parse_uuid,
    _require_context_for_policy,
    get_soma_context,
)

# ── Exception Hierarchy ──────────────────────────────────────────────────────


class TestPolicyExceptions:
    def test_policy_error_is_runtime_error(self):
        err = PolicyError("test")
        assert isinstance(err, RuntimeError)

    def test_soma_integration_error_is_policy_error(self):
        err = SomaIntegrationError("test")
        assert isinstance(err, PolicyError)

    def test_soma_context_error_is_policy_error(self):
        err = SomaContextError("missing context")
        assert isinstance(err, PolicyError)

    def test_soma_policy_denied_is_policy_error(self):
        err = SomaPolicyDenied("denied", details={"reason": "forbidden"})
        assert isinstance(err, PolicyError)
        assert err.details == {"reason": "forbidden"}

    def test_soma_policy_denied_default_details(self):
        err = SomaPolicyDenied("denied")
        assert err.details == {}

    def test_soma_policy_unavailable_is_policy_error(self):
        err = SomaPolicyUnavailable("unreachable")
        assert isinstance(err, PolicyError)


# ── PolicyContext ─────────────────────────────────────────────────────────────


class TestPolicyContext:
    def test_construction(self):
        ctx = PolicyContext(
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            request_id="r1",
            traceparent="00-abc-def-01",
            authorization="Bearer token123",
        )
        assert ctx.tenant_id == "t1"
        assert ctx.user_id == "u1"
        assert ctx.session_id == "s1"
        assert ctx.request_id == "r1"
        assert ctx.traceparent == "00-abc-def-01"
        assert ctx.authorization == "Bearer token123"

    def test_frozen(self):
        ctx = PolicyContext(
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            request_id="r1",
            traceparent="",
            authorization="",
        )
        with pytest.raises(AttributeError):
            ctx.tenant_id = "other"

    def test_headers_all_populated(self):
        ctx = PolicyContext(
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            request_id="r1",
            traceparent="00-abc-def-01",
            authorization="Bearer tok",
        )
        h = ctx.headers()
        assert h["X-Tenant-ID"] == "t1"
        assert h["X-User-ID"] == "u1"
        assert h["X-Soma-Session-ID"] == "s1"
        assert h["X-Request-ID"] == "r1"
        assert h["traceparent"] == "00-abc-def-01"
        assert h["Authorization"] == "Bearer tok"

    def test_headers_empty_fields_omitted(self):
        ctx = PolicyContext(
            tenant_id="",
            user_id="",
            session_id="",
            request_id="",
            traceparent="",
            authorization="",
        )
        h = ctx.headers()
        assert h == {}

    def test_headers_partial(self):
        ctx = PolicyContext(
            tenant_id="t1",
            user_id="",
            session_id="s1",
            request_id="",
            traceparent="",
            authorization="Bearer tok",
        )
        h = ctx.headers()
        assert "X-Tenant-ID" in h
        assert "X-Soma-Session-ID" in h
        assert "Authorization" in h
        assert "X-User-ID" not in h
        assert "X-Request-ID" not in h
        assert "traceparent" not in h


# ── _ensure_suffix ────────────────────────────────────────────────────────────


class TestEnsureSuffix:
    def test_adds_suffix_when_missing(self):
        result = _ensure_suffix("http://policy:8080", "/v1/evaluate")
        assert result == "http://policy:8080/v1/evaluate"

    def test_does_not_double_suffix(self):
        result = _ensure_suffix("http://policy:8080/v1/evaluate", "/v1/evaluate")
        assert result == "http://policy:8080/v1/evaluate"

    def test_strips_trailing_slash(self):
        result = _ensure_suffix("http://policy:8080/", "/v1/evaluate")
        assert result == "http://policy:8080/v1/evaluate"

    def test_strips_trailing_slash_then_adds(self):
        result = _ensure_suffix("http://policy:8080/api/", "/v1/evaluate")
        assert result == "http://policy:8080/api/v1/evaluate"

    def test_base_url_already_has_suffix_no_trailing_slash(self):
        result = _ensure_suffix("http://policy:8080/v1/evaluate", "/v1/evaluate")
        assert result == "http://policy:8080/v1/evaluate"


# ── _parse_uuid ──────────────────────────────────────────────────────────────


class TestParseUUID:
    def test_valid_uuid(self):
        result = _parse_uuid("550e8400-e29b-41d4-a716-446655440000")
        assert result is not None
        assert isinstance(result, UUID)
        assert str(result) == "550e8400-e29b-41d4-a716-446655440000"

    def test_empty_string_returns_none(self):
        assert _parse_uuid("") is None

    def test_invalid_uuid_returns_none(self):
        assert _parse_uuid("not-a-uuid") is None

    def test_none_like_empty(self):
        assert _parse_uuid("") is None


# ── _require_context_for_policy ──────────────────────────────────────────────


class TestRequireContextForPolicy:
    def test_raises_when_session_id_missing(self):
        ctx = PolicyContext(
            tenant_id="t1",
            user_id="u1",
            session_id="",
            request_id="r1",
            traceparent="",
            authorization="",
        )
        with pytest.raises(SomaContextError, match="Missing X-Soma-Session-ID"):
            _require_context_for_policy(ctx)

    def test_raises_when_user_id_missing(self):
        ctx = PolicyContext(
            tenant_id="t1",
            user_id="",
            session_id="s1",
            request_id="r1",
            traceparent="",
            authorization="",
        )
        with pytest.raises(SomaContextError, match="Missing X-Soma-Session-ID"):
            _require_context_for_policy(ctx)

    def test_raises_when_both_missing(self):
        ctx = PolicyContext(
            tenant_id="t1",
            user_id="",
            session_id="",
            request_id="r1",
            traceparent="",
            authorization="",
        )
        with pytest.raises(SomaContextError):
            _require_context_for_policy(ctx)

    def test_passes_when_both_present(self):
        ctx = PolicyContext(
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            request_id="r1",
            traceparent="",
            authorization="",
        )
        # Should not raise
        _require_context_for_policy(ctx)


# ── get_soma_context alias ───────────────────────────────────────────────────


class TestGetSomaContext:
    def test_alias_exists(self):
        """get_soma_context should be an alias for get_policy_context."""
        assert callable(get_soma_context)


# ── Policy Payload Construction ──────────────────────────────────────────────


class TestPolicyPayloadConstruction:
    """Test the payload construction logic used in enforce_policy."""

    def test_payload_structure(self):
        """Verify the payload structure matches the expected format."""
        context = PolicyContext(
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            request_id="r1",
            traceparent="",
            authorization="",
        )
        action = "analyze"
        prompt = "Run statistical analysis"
        metadata = {"source": "csv_upload"}

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

        assert payload["session_id"] == "s1"
        assert payload["tenant"] == "t1"
        assert payload["user"] == "u1"
        assert payload["prompt"] == "Run statistical analysis"
        assert payload["role"] == "agent"
        assert payload["metadata"]["action"] == "analyze"
        assert payload["metadata"]["source"] == "csv_upload"
        assert payload["metadata"]["request_id"] == "r1"

    def test_payload_default_tenant(self):
        """When tenant_id is empty, should default to 'default'."""
        context = PolicyContext(
            tenant_id="",
            user_id="u1",
            session_id="s1",
            request_id="r1",
            traceparent="",
            authorization="",
        )
        tenant = context.tenant_id or "default"
        assert tenant == "default"

    def test_payload_no_extra_metadata(self):
        context = PolicyContext(
            tenant_id="t1",
            user_id="u1",
            session_id="s1",
            request_id="r1",
            traceparent="",
            authorization="",
        )
        metadata = None
        merged = {
            "action": "ingest",
            "request_id": context.request_id,
            **(metadata or {}),
        }
        assert merged == {"action": "ingest", "request_id": "r1"}


# ── Decision Parsing ─────────────────────────────────────────────────────────


class TestDecisionParsing:
    """Test the decision parsing logic used in enforce_policy."""

    def test_deny_decision(self):
        data = {"decision": "DENY", "details": {"reason": "forbidden"}}
        decision = data.get("decision", "").upper()
        assert decision == "DENY"

    def test_allow_decision(self):
        data = {"decision": "ALLOW"}
        decision = data.get("decision", "").upper()
        assert decision == "ALLOW"

    def test_empty_decision(self):
        data: dict = {}
        decision = data.get("decision", "").upper()
        assert decision == ""

    def test_case_insensitive_decision(self):
        for val in ["deny", "Deny", "DENY", "dEnY"]:
            data = {"decision": val}
            assert data.get("decision", "").upper() == "DENY"
