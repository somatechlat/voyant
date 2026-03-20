from django.http import HttpResponse

from apps.core.middleware import (
    APIVersionMiddleware,
    RequestIdMiddleware,
    SomaContextMiddleware,
    TenantMiddleware,
    api_version_var,
    request_id_var,
    tenant_id_var,
)


def get_response(request):
    return HttpResponse("OK")


class TestMiddleware:
    def test_request_id_middleware_new(self, rf):
        middleware = RequestIdMiddleware(get_response)
        request = rf.get("/")
        response = middleware(request)

        assert "X-Request-ID" in response
        assert request_id_var.get() == response["X-Request-ID"]

    def test_request_id_middleware_existing(self, rf):
        middleware = RequestIdMiddleware(get_response)
        request = rf.get("/", HTTP_X_REQUEST_ID="test-id")
        response = middleware(request)

        assert response["X-Request-ID"] == "test-id"
        assert request_id_var.get() == "test-id"

    def test_tenant_middleware(self, rf):
        middleware = TenantMiddleware(get_response)
        request = rf.get("/", HTTP_X_TENANT_ID="tenant-123")
        middleware(request)

        assert tenant_id_var.get() == "tenant-123"

    def test_tenant_middleware_default(self, rf):
        middleware = TenantMiddleware(get_response)
        request = rf.get("/")
        middleware(request)

        assert tenant_id_var.get() == "default"

    def test_soma_context_middleware(self, rf):
        middleware = SomaContextMiddleware(get_response)
        request = rf.get(
            "/",
            HTTP_X_SOMA_SESSION_ID="session-abc",
            HTTP_X_USER_ID="user-456",
            HTTP_AUTHORIZATION="Bearer token123",
        )
        middleware(request)

        from apps.core.middleware import (
            authorization_var,
            soma_session_id_var,
            soma_user_id_var,
        )

        assert soma_session_id_var.get() == "session-abc"
        assert soma_user_id_var.get() == "user-456"
        assert authorization_var.get() == "Bearer token123"

    def test_api_version_middleware_header(self, rf):
        middleware = APIVersionMiddleware(get_response)
        request = rf.get("/", HTTP_X_API_VERSION="v1")
        response = middleware(request)

        assert response["X-API-Version"] == "v1"
        assert api_version_var.get() == "v1"

    def test_api_version_middleware_accept_header(self, rf):
        middleware = APIVersionMiddleware(get_response)
        request = rf.get("/", HTTP_ACCEPT="application/vnd.voyant.v1+json")
        response = middleware(request)

        assert response["X-API-Version"] == "v1"

    def test_api_version_middleware_invalid(self, rf):
        middleware = APIVersionMiddleware(get_response)
        request = rf.get("/", HTTP_X_API_VERSION="v99")
        response = middleware(request)

        assert response.status_code == 406
