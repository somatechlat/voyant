"""
Tests for API Version Negotiation

Verifies Accept header version negotiation middleware.
Reference: docs/CANONICAL_ROADMAP.md - P3 Extensibility
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from starlette.testclient import TestClient

from voyant.api.middleware import (
    APIVersionMiddleware,
    get_api_version,
    get_version_info,
    SUPPORTED_VERSIONS,
    DEFAULT_VERSION,
    CURRENT_VERSION,
)


class TestVersionInfo:
    """Test version info helpers."""

    def test_get_version_info_returns_dict(self):
        """Should return version info dict."""
        info = get_version_info()
        assert "current_version" in info
        assert "supported_versions" in info
        assert "default_version" in info
        assert "accept_format" in info

    def test_current_version_is_v1(self):
        """Current version should be v1."""
        assert CURRENT_VERSION == "v1"

    def test_supported_versions_includes_v1(self):
        """v1 should be in supported versions."""
        assert "v1" in SUPPORTED_VERSIONS

    def test_default_version_is_v1(self):
        """Default version should be v1."""
        assert DEFAULT_VERSION == "v1"


class TestVersionNegotiationIntegration:
    """Integration tests with test client."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from voyant.api.app import app
        return TestClient(app)

    def test_version_endpoint_exists(self, client):
        """GET /version should return version info."""
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert data["current_version"] == "v1"
        assert "v1" in data["supported_versions"]

    def test_response_includes_version_header(self, client):
        """Response should include X-API-Version header."""
        response = client.get("/version")
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "v1"

    def test_accept_header_with_vendor_format(self, client):
        """Should accept application/vnd.voyant.v1+json."""
        response = client.get(
            "/version",
            headers={"Accept": "application/vnd.voyant.v1+json"}
        )
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"

    def test_x_api_version_header_override(self, client):
        """X-API-Version header should override Accept header."""
        response = client.get(
            "/version",
            headers={"X-API-Version": "v1"}
        )
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"

    def test_unsupported_version_returns_406(self, client):
        """Unsupported version should return 406 Not Acceptable."""
        response = client.get(
            "/version",
            headers={"Accept": "application/vnd.voyant.v99+json"}
        )
        assert response.status_code == 406
        data = response.json()
        assert data["error"] == "Not Acceptable"
        assert "v99" in data["message"]
        assert "supported_versions" in data

    def test_health_endpoints_skip_version_check(self, client):
        """Health endpoints should skip version negotiation."""
        response = client.get("/health")
        assert response.status_code == 200
        # Should work even without version header

    def test_default_version_when_no_header(self, client):
        """Should use default version when no version specified."""
        response = client.get("/version")
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"


class TestVersionPatternParsing:
    """Test version pattern extraction."""

    def test_extract_version_from_vendor_format(self):
        """Should extract version from application/vnd.voyant.v1+json."""
        from voyant.api.middleware import VERSION_PATTERN
        
        match = VERSION_PATTERN.search("application/vnd.voyant.v1+json")
        assert match is not None
        assert match.group(1) == "1"

    def test_extract_version_v2(self):
        """Should extract v2 from vendor format."""
        from voyant.api.middleware import VERSION_PATTERN
        
        match = VERSION_PATTERN.search("application/vnd.voyant.v2+json")
        assert match is not None
        assert match.group(1) == "2"

    def test_no_match_for_plain_json(self):
        """Should not match plain application/json."""
        from voyant.api.middleware import VERSION_PATTERN
        
        match = VERSION_PATTERN.search("application/json")
        assert match is None


class TestVersionContextVariable:
    """Test API version context variable."""

    def test_get_api_version_default(self):
        """Should return default when not set."""
        # Context variable has default of v1
        assert get_api_version() == "v1"
