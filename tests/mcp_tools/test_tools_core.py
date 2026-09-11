"""
Unit tests for apps.mcp.tools_core — Core MCP operational tools.

Tests the _tenant helper function and verifies tool function signatures.
Most tool functions require external services (Temporal, Trino, Milvus)
so we focus on the pure-logic helpers and schema validation.
"""

import inspect

from apps.core.config import get_settings

# =========================================================================
# _tenant helper
# =========================================================================


class TestTenantHelper:
    def test_returns_provided_tenant(self):
        from apps.mcp.tools_core import _tenant

        result = _tenant("custom-tenant")
        assert result == "custom-tenant"

    def test_returns_default_when_none(self):
        from apps.mcp.tools_core import _tenant

        settings = get_settings()
        result = _tenant(None)
        assert result == settings.default_tenant_id

    def test_returns_default_when_empty(self):
        from apps.mcp.tools_core import _tenant

        settings = get_settings()
        result = _tenant("")
        assert result == settings.default_tenant_id

    def test_returns_provided_when_nonempty(self):
        from apps.mcp.tools_core import _tenant

        result = _tenant("explicit-id")
        assert result == "explicit-id"


# =========================================================================
# Tool function signatures
# =========================================================================


class TestToolSignatures:
    """Verify that tool functions have the expected parameter signatures."""

    def test_tool_discover_signature(self):
        from apps.mcp.tools_core import tool_discover

        sig = inspect.signature(tool_discover)
        assert "hint" in sig.parameters

    def test_tool_connect_signature(self):
        from apps.mcp.tools_core import tool_connect

        sig = inspect.signature(tool_connect)
        params = set(sig.parameters.keys())
        assert "name" in params
        assert "source_type" in params
        assert "connection_config" in params
        assert "credentials" in params
        assert "tenant_id" in params

    def test_tool_ingest_signature(self):
        from apps.mcp.tools_core import tool_ingest

        sig = inspect.signature(tool_ingest)
        assert "source_id" in sig.parameters
        assert "mode" in sig.parameters
        assert sig.parameters["mode"].default == "full"

    def test_tool_profile_signature(self):
        from apps.mcp.tools_core import tool_profile

        sig = inspect.signature(tool_profile)
        assert sig.parameters["sample_size"].default == 10000

    def test_tool_sql_signature(self):
        from apps.mcp.tools_core import tool_sql

        sig = inspect.signature(tool_sql)
        assert sig.parameters["limit"].default == 1000

    def test_tool_search_signature(self):
        from apps.mcp.tools_core import tool_search

        sig = inspect.signature(tool_search)
        assert sig.parameters["limit"].default == 5

    def test_tool_status_signature(self):
        from apps.mcp.tools_core import tool_status

        sig = inspect.signature(tool_status)
        assert "job_id" in sig.parameters

    def test_tool_artifact_signature(self):
        from apps.mcp.tools_core import tool_artifact

        sig = inspect.signature(tool_artifact)
        assert "artifact_id" in sig.parameters
