"""
Unit tests for apps.core.middleware — ContextVar accessors, middleware
request/response flow, API version extraction, and version info.

Real ContextVar state and middleware instantiation. No mocks.
"""

import uuid

from apps.core.middleware import (
    CURRENT_VERSION,
    DEFAULT_VERSION,
    SUPPORTED_VERSIONS,
    VERSION_PATTERN,
    APIVersionMiddleware,
    RBACMiddleware,
    RequestIdMiddleware,
    SomaContextMiddleware,
    TenantMiddleware,
    api_version_var,
    authorization_var,
    current_user_var,
    get_api_version,
    get_authorization,
    get_current_user,
    get_request_id,
    get_soma_session_id,
    get_soma_user_id,
    get_tenant_id,
    get_traceparent,
    get_version_info,
    request_id_var,
    soma_session_id_var,
    soma_user_id_var,
    tenant_id_var,
    traceparent_var,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


class FakeRequest:
    """Minimal request object for middleware testing."""

    def __init__(self, path="/api/v1/test", headers=None):
        self.path = path
        self.headers = headers or {}

    @property
    def META(self):
        return {}


class FakeResponse:
    """Minimal response object for middleware testing."""

    def __init__(self):
        self.headers = {}
        self.status_code = 200

    def __setitem__(self, key, value):
        self.headers[key] = value

    def __getitem__(self, key):
        return self.headers[key]


def _make_middleware(middleware_class, path="/api/v1/test", headers=None):
    """Create a middleware instance with a simple get_response."""
    response = FakeResponse()

    def get_response(request):
        return response

    mw = middleware_class(get_response)
    return mw, response


# ── Constants ─────────────────────────────────────────────────────────────────


class TestConstants:
    def test_supported_versions(self):
        assert SUPPORTED_VERSIONS == ["v1"]

    def test_default_version(self):
        assert DEFAULT_VERSION == "v1"

    def test_current_version(self):
        assert CURRENT_VERSION == "v1"

    def test_version_pattern(self):
        assert VERSION_PATTERN.pattern == r"application/vnd\.voyant\.v(\d+)\+json"


# ── ContextVar Accessors ─────────────────────────────────────────────────────


class TestContextVarAccessors:
    def test_get_request_id_default(self):
        request_id_var.set("")
        assert get_request_id() == ""

    def test_get_request_id_set(self):
        request_id_var.set("req-123")
        assert get_request_id() == "req-123"
        request_id_var.set("")

    def test_get_tenant_id_default(self):
        tenant_id_var.set("default")
        assert get_tenant_id() == "default"

    def test_get_tenant_id_set(self):
        tenant_id_var.set("tenant-abc")
        assert get_tenant_id() == "tenant-abc"
        tenant_id_var.set("default")

    def test_get_tenant_id_with_request(self):
        """When request is provided, should read from request headers."""
        req = FakeRequest(headers={"X-Tenant-ID": "from-request"})
        tenant_id_var.set("from-context")
        result = get_tenant_id(request=req)
        assert result == "from-request"
        tenant_id_var.set("default")

    def test_get_tenant_id_request_no_header(self):
        """When request has no X-Tenant-ID, should fall back to context var."""
        req = FakeRequest(headers={})
        tenant_id_var.set("from-context")
        result = get_tenant_id(request=req)
        assert result == "from-context"
        tenant_id_var.set("default")

    def test_get_api_version_default(self):
        api_version_var.set("v1")
        assert get_api_version() == "v1"

    def test_get_soma_session_id_default(self):
        soma_session_id_var.set("")
        assert get_soma_session_id() == ""

    def test_get_soma_session_id_set(self):
        soma_session_id_var.set("sess-abc")
        assert get_soma_session_id() == "sess-abc"
        soma_session_id_var.set("")

    def test_get_soma_user_id_default(self):
        soma_user_id_var.set("")
        assert get_soma_user_id() == ""

    def test_get_soma_user_id_set(self):
        soma_user_id_var.set("user-123")
        assert get_soma_user_id() == "user-123"
        soma_user_id_var.set("")

    def test_get_traceparent_default(self):
        traceparent_var.set("")
        assert get_traceparent() == ""

    def test_get_traceparent_set(self):
        traceparent_var.set("00-abc-def-01")
        assert get_traceparent() == "00-abc-def-01"
        traceparent_var.set("")

    def test_get_authorization_default(self):
        authorization_var.set("")
        assert get_authorization() == ""

    def test_get_authorization_set(self):
        authorization_var.set("Bearer token123")
        assert get_authorization() == "Bearer token123"
        authorization_var.set("")

    def test_get_current_user_default(self):
        current_user_var.set(None)
        assert get_current_user() is None

    def test_get_current_user_set(self):
        user = {"id": "u1", "name": "test"}
        current_user_var.set(user)
        assert get_current_user() == user
        current_user_var.set(None)


# ── RequestIdMiddleware ───────────────────────────────────────────────────────


class TestRequestIdMiddleware:
    def test_generates_request_id_when_missing(self):
        mw, response = _make_middleware(RequestIdMiddleware)
        req = FakeRequest(headers={})
        mw(req)
        assert "X-Request-ID" in response.headers
        # Should be a valid UUID
        rid = response.headers["X-Request-ID"]
        uuid.UUID(rid)  # Should not raise

    def test_preserves_existing_request_id(self):
        mw, response = _make_middleware(RequestIdMiddleware)
        req = FakeRequest(headers={"X-Request-ID": "custom-id-123"})
        mw(req)
        assert response.headers["X-Request-ID"] == "custom-id-123"

    def test_sets_context_var(self):
        mw, response = _make_middleware(RequestIdMiddleware)
        req = FakeRequest(headers={"X-Request-ID": "ctx-test"})
        mw(req)
        # Context var should have been set during the call
        # (it's set before get_response, so we check the response header)
        assert response.headers["X-Request-ID"] == "ctx-test"


# ── TenantMiddleware ──────────────────────────────────────────────────────────


class TestTenantMiddleware:
    def test_sets_tenant_from_header(self):
        mw, response = _make_middleware(TenantMiddleware)
        req = FakeRequest(headers={"X-Tenant-ID": "tenant-xyz"})
        mw(req)
        assert tenant_id_var.get() == "tenant-xyz"
        tenant_id_var.set("default")

    def test_defaults_to_default_tenant(self):
        mw, response = _make_middleware(TenantMiddleware)
        req = FakeRequest(headers={})
        mw(req)
        assert tenant_id_var.get() == "default"
        tenant_id_var.set("default")


# ── SomaContextMiddleware ─────────────────────────────────────────────────────


class TestSomaContextMiddleware:
    def test_sets_all_context_vars(self):
        mw, response = _make_middleware(SomaContextMiddleware)
        req = FakeRequest(headers={
            "X-Soma-Session-ID": "sess-1",
            "X-User-ID": "user-1",
            "traceparent": "00-abc-def-01",
            "Authorization": "Bearer tok",
        })
        mw(req)
        assert soma_session_id_var.get() == "sess-1"
        assert soma_user_id_var.get() == "user-1"
        assert traceparent_var.get() == "00-abc-def-01"
        assert authorization_var.get() == "Bearer tok"
        # Clean up
        soma_session_id_var.set("")
        soma_user_id_var.set("")
        traceparent_var.set("")
        authorization_var.set("")

    def test_defaults_to_empty_strings(self):
        mw, response = _make_middleware(SomaContextMiddleware)
        req = FakeRequest(headers={})
        mw(req)
        assert soma_session_id_var.get() == ""
        assert soma_user_id_var.get() == ""
        assert traceparent_var.get() == ""
        assert authorization_var.get() == ""


# ── APIVersionMiddleware ──────────────────────────────────────────────────────


class TestAPIVersionMiddleware:
    def test_health_path_skips_version_check(self):
        """Health endpoints should bypass version checking."""
        mw, response = _make_middleware(APIVersionMiddleware, path="/health")
        req = FakeRequest(path="/health")
        result = mw(req)
        # Should not return 406
        assert result.status_code == 200

    def test_ready_path_skips_version_check(self):
        mw, response = _make_middleware(APIVersionMiddleware, path="/ready")
        req = FakeRequest(path="/ready")
        result = mw(req)
        assert result.status_code == 200

    def test_healthz_path_skips_version_check(self):
        mw, response = _make_middleware(APIVersionMiddleware, path="/healthz")
        req = FakeRequest(path="/healthz")
        result = mw(req)
        assert result.status_code == 200

    def test_readyz_path_skips_version_check(self):
        mw, response = _make_middleware(APIVersionMiddleware, path="/readyz")
        req = FakeRequest(path="/readyz")
        result = mw(req)
        assert result.status_code == 200

    def test_no_version_defaults_to_v1(self):
        mw, response = _make_middleware(APIVersionMiddleware)
        req = FakeRequest(headers={})
        mw(req)
        assert response.headers.get("X-API-Version") == "v1"

    def test_header_version_v1_accepted(self):
        mw, response = _make_middleware(APIVersionMiddleware)
        req = FakeRequest(headers={"X-API-Version": "v1"})
        mw(req)
        assert response.headers.get("X-API-Version") == "v1"

    def test_unsupported_version_returns_406(self):
        mw, response = _make_middleware(APIVersionMiddleware)
        req = FakeRequest(headers={"X-API-Version": "v2"})
        result = mw(req)
        assert result.status_code == 406

    def test_accept_header_version(self):
        mw, response = _make_middleware(APIVersionMiddleware)
        req = FakeRequest(headers={"Accept": "application/vnd.voyant.v1+json"})
        mw(req)
        assert response.headers.get("X-API-Version") == "v1"

    def test_accept_header_unsupported_version(self):
        mw, response = _make_middleware(APIVersionMiddleware)
        req = FakeRequest(headers={"Accept": "application/vnd.voyant.v3+json"})
        result = mw(req)
        assert result.status_code == 406


class TestAPIVersionExtractVersion:
    """Test the _extract_version method directly."""

    def test_from_header(self):
        mw, _ = _make_middleware(APIVersionMiddleware)
        req = FakeRequest(headers={"X-API-Version": "v2"})
        assert mw._extract_version(req) == "2"

    def test_from_accept_header(self):
        mw, _ = _make_middleware(APIVersionMiddleware)
        req = FakeRequest(headers={"Accept": "application/vnd.voyant.v3+json"})
        assert mw._extract_version(req) == "3"

    def test_no_version(self):
        mw, _ = _make_middleware(APIVersionMiddleware)
        req = FakeRequest(headers={})
        assert mw._extract_version(req) is None

    def test_header_without_v_prefix(self):
        mw, _ = _make_middleware(APIVersionMiddleware)
        req = FakeRequest(headers={"X-API-Version": "1"})
        assert mw._extract_version(req) == "1"


# ── VERSION_PATTERN ──────────────────────────────────────────────────────────


class TestVersionPattern:
    def test_matches_valid_accept(self):
        match = VERSION_PATTERN.search("application/vnd.voyant.v1+json")
        assert match is not None
        assert match.group(1) == "1"

    def test_matches_v2(self):
        match = VERSION_PATTERN.search("application/vnd.voyant.v2+json")
        assert match is not None
        assert match.group(1) == "2"

    def test_no_match_plain_accept(self):
        match = VERSION_PATTERN.search("application/json")
        assert match is None

    def test_no_match_wrong_vendor(self):
        match = VERSION_PATTERN.search("application/vnd.other.v1+json")
        assert match is None


# ── RBACMiddleware ────────────────────────────────────────────────────────────


class TestRBACMiddleware:
    def test_no_auth_header_sets_none(self):
        mw, response = _make_middleware(RBACMiddleware)
        req = FakeRequest(headers={})
        mw(req)
        # After the request, current_user should be reset to None
        assert current_user_var.get() is None

    def test_non_bearer_auth_sets_none(self):
        mw, response = _make_middleware(RBACMiddleware)
        req = FakeRequest(headers={"Authorization": "Basic abc123"})
        mw(req)
        assert current_user_var.get() is None

    def test_empty_bearer_sets_none(self):
        mw, response = _make_middleware(RBACMiddleware)
        req = FakeRequest(headers={"Authorization": "Bearer "})
        mw(req)
        assert current_user_var.get() is None

    def test_resolve_user_no_auth(self):
        req = FakeRequest(headers={})
        result = RBACMiddleware._resolve_user(req)
        assert result is None

    def test_resolve_user_non_bearer(self):
        req = FakeRequest(headers={"Authorization": "Basic abc"})
        result = RBACMiddleware._resolve_user(req)
        assert result is None

    def test_resolve_user_empty_bearer(self):
        req = FakeRequest(headers={"Authorization": "Bearer "})
        result = RBACMiddleware._resolve_user(req)
        assert result is None


# ── get_version_info ─────────────────────────────────────────────────────────


class TestGetVersionInfo:
    def test_structure(self):
        info = get_version_info()
        assert info["current_version"] == "v1"
        assert info["supported_versions"] == ["v1"]
        assert info["default_version"] == "v1"
        assert "accept_format" in info

    def test_accept_format_template(self):
        info = get_version_info()
        assert "{version}" in info["accept_format"]
        assert "voyant" in info["accept_format"]
