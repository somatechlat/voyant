"""
Tests for API Version Negotiation and Middleware.

This module contains comprehensive tests to verify the correct functioning of
the API versioning middleware and related utilities in the Voyant application.
It ensures that the API properly negotiates versions based on `Accept` and
`X-API-Version` headers, handles unsupported versions gracefully, and maintains
version context.

Reference: docs/CANONICAL_ROADMAP.md - P3 Extensibility (API Versioning)
"""

from apps.core.middleware import (
    CURRENT_VERSION,
    DEFAULT_VERSION,
    SUPPORTED_VERSIONS,
    get_api_version,
    get_version_info,
)


class TestVersionInfo:
    """
    Tests for utility functions related to API version information retrieval.

    This class verifies that `get_version_info` provides correct details
    about the API's current, supported, and default versions.
    """

    def test_get_version_info_returns_dict(self):
        """
        Verifies that `get_version_info()` returns a dictionary containing
        expected keys: `current_version`, `supported_versions`, `default_version`, and `accept_format`.
        """
        info = get_version_info()
        assert "current_version" in info
        assert "supported_versions" in info
        assert "default_version" in info
        assert "accept_format" in info

    def test_current_version_is_v1(self):
        """
        Ensures that the `CURRENT_VERSION` constant is correctly set to "v1".
        """
        assert CURRENT_VERSION == "v1"

    def test_supported_versions_includes_v1(self):
        """
        Verifies that "v1" is included in the list of `SUPPORTED_VERSIONS`.
        """
        assert "v1" in SUPPORTED_VERSIONS

    def test_default_version_is_v1(self):
        """
        Confirms that the `DEFAULT_VERSION` constant is correctly set to "v1".
        """
        assert DEFAULT_VERSION == "v1"


class TestVersionNegotiationIntegration:
    """
    Integration tests for API version negotiation using a Django test client.

    These tests simulate HTTP requests with various versioning headers to ensure
    the API middleware correctly processes and responds according to the version.
    """

    def test_version_endpoint_exists(self, client):
        """
        Verifies that the `/version` endpoint is accessible and returns
        the expected API version information.
        """
        response = client.get("/version")
        assert response.status_code == 200
        data = response.json()
        assert data["current_version"] == "v1"
        assert "v1" in data["supported_versions"]

    def test_response_includes_version_header(self, client):
        """
        Ensures that all API responses include the `X-API-Version` header.
        """
        response = client.get("/version")
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "v1"

    def test_accept_header_with_vendor_format(self, client):
        """
        Verifies that the API correctly parses and uses the version specified
        in the `Accept` header using the custom vendor media type format
        (e.g., `application/vnd.voyant.v1+json`).
        """
        response = client.get(
            "/version", headers={"Accept": "application/vnd.voyant.v1+json"}
        )
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"

    def test_x_api_version_header_override(self, client):
        """
        Checks that the `X-API-Version` header takes precedence over the `Accept` header
        when both are present.
        """
        response = client.get("/version", headers={"X-API-Version": "v1"})
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"

    def test_unsupported_version_returns_406(self, client):
        """
        Ensures that requests for unsupported API versions result in a 406 Not Acceptable status.
        """
        response = client.get(
            "/version", headers={"Accept": "application/vnd.voyant.v99+json"}
        )
        assert response.status_code == 406
        data = response.json()
        assert data["error"] == "Not Acceptable"
        assert "v99" in data["message"]
        assert "supported_versions" in data

    def test_health_endpoints_skip_version_check(self, client):
        """
        Verifies that health-check related endpoints bypass version negotiation
        and are always accessible.
        """
        response = client.get("/health")
        assert response.status_code == 200
        # Should work even without an explicit version header.

    def test_default_version_when_no_header(self, client):
        """
        Confirms that the API defaults to `DEFAULT_VERSION` when no specific
        version is provided in the request headers.
        """
        response = client.get("/version")
        assert response.status_code == 200
        assert response.headers["X-API-Version"] == "v1"


class TestVersionPatternParsing:
    """
    Tests for the regular expression used to extract API version from media types.
    """

    def test_extract_version_from_vendor_format(self):
        """
        Verifies that the `VERSION_PATTERN` regex correctly extracts "1"
        from `application/vnd.voyant.v1+json`.
        """
        from apps.core.middleware import VERSION_PATTERN

        match = VERSION_PATTERN.search("application/vnd.voyant.v1+json")
        assert match is not None
        assert match.group(1) == "1"

    def test_extract_version_v2(self):
        """
        Verifies that the `VERSION_PATTERN` regex correctly extracts "2"
        from `application/vnd.voyant.v2+json`.
        """
        from apps.core.middleware import VERSION_PATTERN

        match = VERSION_PATTERN.search("application/vnd.voyant.v2+json")
        assert match is not None
        assert match.group(1) == "2"

    def test_no_match_for_plain_json(self):
        """
        Ensures that the `VERSION_PATTERN` regex does not match a plain
        `application/json` media type.
        """
        from apps.core.middleware import VERSION_PATTERN

        match = VERSION_PATTERN.search("application/json")
        assert match is None


class TestVersionContextVariable:
    """
    Tests for the `api_version` context variable, ensuring it holds the correct
    API version, especially when no version is explicitly set in the request.
    """

    def test_get_api_version_default(self):
        """
        Verifies that `get_api_version()` returns the default version ("v1")
        when no API version has been explicitly set in the request context.
        """
        # The context variable has a default of "v1".
        assert get_api_version() == "v1"
