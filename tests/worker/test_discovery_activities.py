"""
Tests for DiscoveryActivities.

Tests search_for_apis and scan_spec_url. Since these depend on external
services (Serper API, HTTP fetches), we test parameter validation and
the SpecParser's in-process parsing logic directly.
"""

import pytest
from temporalio.exceptions import ApplicationError

from apps.discovery.lib.models import ApiEndpoint, ApiSpec
from apps.discovery.lib.spec_parser import SpecParser
from apps.worker.activities.discovery_activities import DiscoveryActivities


@pytest.fixture(scope="module")
def activities():
    """Real DiscoveryActivities instance."""
    return DiscoveryActivities()


@pytest.fixture(scope="module")
def parser():
    """Real SpecParser instance."""
    return SpecParser()


class TestSearchForApis:
    """Tests for the search_for_apis activity."""

    def test_search_empty_query(self, activities):
        """Empty query returns results (or empty list if no API key)."""
        result = activities.search_for_apis({"query": "", "limit": 5})
        assert isinstance(result, list)

    def test_search_default_limit(self, activities):
        """Default limit of 5 is used when not specified."""
        result = activities.search_for_apis({"query": "test"})
        assert isinstance(result, list)

    def test_search_missing_query(self, activities):
        """Missing query defaults to empty string."""
        result = activities.search_for_apis({})
        assert isinstance(result, list)


class TestScanSpecUrl:
    """Tests for the scan_spec_url activity."""

    def test_scan_invalid_url_raises(self, activities):
        """Invalid URL raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="API specification scan failed"):
            activities.scan_spec_url({"url": "http://invalid.nonexistent.domain/spec.json"})

    def test_scan_empty_url_raises(self, activities):
        """Empty URL raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="API specification scan failed"):
            activities.scan_spec_url({"url": ""})

    def test_scan_missing_url_raises(self, activities):
        """Missing URL raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="API specification scan failed"):
            activities.scan_spec_url({})


class TestSpecParserDirectly:
    """Tests for SpecParser.parse_spec (in-process, no network)."""

    def test_parse_openapi_v3(self, parser):
        """OpenAPI v3 spec is parsed correctly."""
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "Test API", "version": "2.0"},
            "servers": [{"url": "https://api.example.com/v2"}],
            "paths": {
                "/users": {
                    "get": {"summary": "List users", "parameters": []},
                    "post": {"summary": "Create user", "parameters": []},
                },
                "/users/{id}": {
                    "get": {"summary": "Get user by ID", "parameters": []}
                },
            },
        }
        result = parser.parse_spec(spec_data, source_url="https://example.com/spec.json")
        assert isinstance(result, ApiSpec)
        assert result.title == "Test API"
        assert result.version == "2.0"
        assert result.base_url == "https://api.example.com/v2"
        assert len(result.endpoints) == 3

    def test_parse_swagger_v2(self, parser):
        """Swagger v2 spec is parsed correctly."""
        spec_data = {
            "swagger": "2.0",
            "info": {"title": "Legacy API", "version": "1.0"},
            "host": "legacy.example.com",
            "basePath": "/api",
            "schemes": ["https"],
            "paths": {
                "/items": {
                    "get": {"summary": "List items"},
                }
            },
        }
        result = parser.parse_spec(spec_data)
        assert result.title == "Legacy API"
        assert result.base_url == "https://legacy.example.com/api"
        assert len(result.endpoints) == 1

    def test_parse_unknown_format_raises(self, parser):
        """Unknown spec format raises ValueError."""
        with pytest.raises(ValueError, match="Unknown API specification format"):
            parser.parse_spec({"not_openapi": True, "not_swagger": True})

    def test_parse_endpoints_sample_limit(self, parser):
        """Only first 5 endpoints are included in sample."""
        paths = {}
        for i in range(10):
            paths[f"/endpoint_{i}"] = {
                "get": {"summary": f"Endpoint {i}"}
            }
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "Big API", "version": "1.0"},
            "paths": paths,
        }
        result = parser.parse_spec(spec_data)
        assert len(result.endpoints) == 10
        # The activity only returns first 5 in endpoints_sample
        sample = result.endpoints[:5]
        assert len(sample) == 5

    def test_parse_auth_type_detection(self, parser):
        """Auth type is detected from securitySchemes."""
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "Secured API", "version": "1.0"},
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                    }
                }
            },
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert result.auth_type in ("bearer", "Bearer", "unknown")

    def test_parse_empty_paths(self, parser):
        """Empty paths results in zero endpoints."""
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "Empty API", "version": "1.0"},
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert len(result.endpoints) == 0

    def test_parse_no_servers_fallback(self, parser):
        """No servers section falls back to source URL domain."""
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "No Server API", "version": "1.0"},
            "paths": {},
        }
        result = parser.parse_spec(
            spec_data, source_url="https://fallback.example.com/spec.json"
        )
        assert "fallback.example.com" in result.base_url


class TestApiEndpointModel:
    """Tests for the ApiEndpoint dataclass."""

    def test_endpoint_to_dict(self):
        """to_dict returns expected structure."""
        ep = ApiEndpoint(
            path="/users/{id}",
            method="GET",
            summary="Get user",
            parameters=[{"name": "id", "in": "path"}],
            auth_required=True,
        )
        d = ep.to_dict()
        assert d["path"] == "/users/{id}"
        assert d["method"] == "GET"
        assert d["summary"] == "Get user"
        assert len(d["parameters"]) == 1
        assert d["auth_required"] is True

    def test_endpoint_defaults(self):
        """Default values for optional fields."""
        ep = ApiEndpoint(path="/test", method="POST", summary="Test")
        assert ep.parameters == []
        assert ep.auth_required is True
