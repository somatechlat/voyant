"""
Unit tests for apps.discovery.lib.spec_parser — SpecParser.

Tests OpenAPI v3 and Swagger v2 parsing, auth type detection,
endpoint extraction, base URL resolution, and error handling.
Uses real SpecParser instances — no mocks.
"""

import pytest

from apps.discovery.lib.spec_parser import SpecParser


@pytest.fixture
def parser():
    return SpecParser()


# =========================================================================
# OpenAPI v3 parsing
# =========================================================================


class TestOpenAPIv3:
    def test_basic_parse(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "My API", "version": "2.1.0"},
            "servers": [{"url": "https://api.example.com/v2"}],
            "paths": {
                "/users": {
                    "get": {
                        "summary": "List users",
                        "parameters": [{"name": "limit", "in": "query"}],
                    },
                    "post": {
                        "summary": "Create user",
                        "security": [{"bearerAuth": []}],
                    },
                },
                "/users/{id}": {
                    "get": {"summary": "Get user"},
                    "delete": {"summary": "Delete user"},
                },
            },
        }
        result = parser.parse_spec(spec_data)
        assert result.title == "My API"
        assert result.version == "2.1.0"
        assert result.base_url == "https://api.example.com/v2"
        assert len(result.endpoints) == 4

    def test_endpoint_details(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {
                "/items": {
                    "get": {
                        "summary": "List items",
                        "parameters": [{"name": "page", "in": "query", "type": "integer"}],
                    }
                }
            },
        }
        result = parser.parse_spec(spec_data)
        ep = result.endpoints[0]
        assert ep.path == "/items"
        assert ep.method == "GET"
        assert ep.summary == "List items"
        assert len(ep.parameters) == 1

    def test_auth_detection_apikey(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "components": {
                "securitySchemes": {
                    "apiKey": {"type": "apiKey", "name": "X-API-Key", "in": "header"}
                }
            },
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert result.auth_type == "ApiKey"

    def test_auth_detection_bearer(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "components": {
                "securitySchemes": {
                    "bearer": {"type": "http", "scheme": "bearer"}
                }
            },
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert result.auth_type == "Bearer"

    def test_auth_detection_oauth2(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "components": {
                "securitySchemes": {
                    "oauth": {"type": "oauth2", "flows": {}}
                }
            },
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert result.auth_type == "OAuth2"

    def test_no_auth(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert result.auth_type == "none"

    def test_endpoint_auth_required_from_global(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "security": [{"bearerAuth": []}],
            "paths": {
                "/secured": {"get": {"summary": "Secured endpoint"}},
            },
        }
        result = parser.parse_spec(spec_data)
        assert result.endpoints[0].auth_required is True

    def test_endpoint_auth_required_from_local(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {
                "/secured": {
                    "get": {
                        "summary": "Secured",
                        "security": [{"apiKey": []}],
                    }
                },
            },
        }
        result = parser.parse_spec(spec_data)
        assert result.endpoints[0].auth_required is True

    def test_endpoint_no_auth(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {
                "/public": {"get": {"summary": "Public"}},
            },
        }
        result = parser.parse_spec(spec_data)
        assert result.endpoints[0].auth_required is False

    def test_base_url_fallback_to_source(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {},
        }
        result = parser.parse_spec(spec_data, source_url="https://docs.example.com/spec.json")
        assert result.base_url == "https://docs.example.com"

    def test_base_url_empty_when_no_servers_no_source(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert result.base_url == ""

    def test_filters_non_http_methods(self, parser):
        """Only standard HTTP methods should be extracted."""
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {
                "/x": {
                    "get": {"summary": "Get"},
                    "parameters": [{"name": "id", "in": "query"}],  # not a method
                    "head": {"summary": "Head"},  # not in allowed list
                }
            },
        }
        result = parser.parse_spec(spec_data)
        methods = [ep.method for ep in result.endpoints]
        assert methods == ["GET"]

    def test_raw_spec_preserved(self, parser):
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert result.raw_spec == spec_data

    def test_default_info_fields(self, parser):
        spec_data = {"openapi": "3.0.0", "paths": {}}
        result = parser.parse_spec(spec_data)
        assert result.title == "Unknown API"
        assert result.version == "1.0"


# =========================================================================
# Swagger v2 parsing
# =========================================================================


class TestSwaggerV2:
    def test_basic_parse(self, parser):
        spec_data = {
            "swagger": "2.0",
            "info": {"title": "Legacy API", "version": "0.9"},
            "host": "legacy.example.com",
            "basePath": "/api",
            "schemes": ["https"],
            "paths": {
                "/items": {
                    "get": {"summary": "List items"},
                    "post": {"summary": "Create item"},
                }
            },
        }
        result = parser.parse_spec(spec_data)
        assert result.title == "Legacy API"
        assert result.version == "0.9"
        assert result.base_url == "https://legacy.example.com/api"
        assert len(result.endpoints) == 2

    def test_swagger_base_url_no_host(self, parser):
        spec_data = {
            "swagger": "2.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {},
        }
        result = parser.parse_spec(spec_data, source_url="https://spec-host.com/swagger.json")
        assert result.base_url == "https://spec-host.com"

    def test_swagger_auth_detection(self, parser):
        spec_data = {
            "swagger": "2.0",
            "info": {"title": "T", "version": "1.0"},
            "securityDefinitions": {
                "api_key": {"type": "apiKey", "name": "api_key", "in": "header"}
            },
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert result.auth_type == "ApiKey"

    def test_swagger_schemes_fallback(self, parser):
        spec_data = {
            "swagger": "2.0",
            "info": {"title": "T", "version": "1.0"},
            "host": "example.com",
            "basePath": "/v1",
            # no schemes — should default to https
            "paths": {},
        }
        result = parser.parse_spec(spec_data)
        assert result.base_url == "https://example.com/v1"


# =========================================================================
# Error handling
# =========================================================================


class TestSpecParserErrors:
    def test_unknown_format_raises(self, parser):
        with pytest.raises(ValueError, match="Unknown API specification format"):
            parser.parse_spec({"info": {}, "paths": {}})

    def test_empty_dict_raises(self, parser):
        with pytest.raises(ValueError, match="Unknown API specification format"):
            parser.parse_spec({})

    def test_parse_from_url_invalid_url_raises(self, parser):
        with pytest.raises(ValueError, match="Failed to fetch specification"):
            parser.parse_from_url("https://this-domain-does-not-exist-12345.invalid/spec.json")

    def test_all_patch_methods(self, parser):
        """All five standard methods should be parsed."""
        spec_data = {
            "openapi": "3.0.0",
            "info": {"title": "T", "version": "1.0"},
            "paths": {
                "/r": {
                    "get": {"summary": "G"},
                    "post": {"summary": "P"},
                    "put": {"summary": "U"},
                    "delete": {"summary": "D"},
                    "patch": {"summary": "Pa"},
                }
            },
        }
        result = parser.parse_spec(spec_data)
        methods = sorted(ep.method for ep in result.endpoints)
        assert methods == ["DELETE", "GET", "PATCH", "POST", "PUT"]
