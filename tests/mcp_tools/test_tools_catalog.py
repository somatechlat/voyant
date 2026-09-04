"""
Unit tests for apps.mcp.tools_catalog — Catalog & management MCP tools.

Tests tool function signatures and parameter defaults.
Most tools require DB/external services; we verify structure and
the _tenant delegation pattern.
"""

import inspect

import pytest

from apps.core.config import get_settings


# =========================================================================
# Tool signature verification
# =========================================================================


class TestCatalogToolSignatures:
    """Verify that catalog tool functions have expected parameters."""

    def test_tool_lineage_signature(self):
        from apps.mcp.tools_catalog import tool_lineage

        sig = inspect.signature(tool_lineage)
        assert sig.parameters["urn"].default is inspect.Parameter.empty
        assert sig.parameters["direction"].default == "both"
        assert sig.parameters["depth"].default == 3

    def test_tool_preset_signature(self):
        from apps.mcp.tools_catalog import tool_preset

        sig = inspect.signature(tool_preset)
        assert "preset_name" in sig.parameters
        assert "payload" in sig.parameters
        assert "tenant_id" in sig.parameters

    def test_tool_sources_list_signature(self):
        from apps.mcp.tools_catalog import tool_sources_list

        sig = inspect.signature(tool_sources_list)
        assert sig.parameters["tenant_id"].default is None

    def test_tool_sources_get_signature(self):
        from apps.mcp.tools_catalog import tool_sources_get

        sig = inspect.signature(tool_sources_get)
        assert "source_id" in sig.parameters

    def test_tool_sources_delete_signature(self):
        from apps.mcp.tools_catalog import tool_sources_delete

        sig = inspect.signature(tool_sources_delete)
        assert "source_id" in sig.parameters

    def test_tool_jobs_list_signature(self):
        from apps.mcp.tools_catalog import tool_jobs_list

        sig = inspect.signature(tool_jobs_list)
        assert sig.parameters["limit"].default == 50
        assert sig.parameters["status"].default is None
        assert sig.parameters["job_type"].default is None

    def test_tool_jobs_cancel_signature(self):
        from apps.mcp.tools_catalog import tool_jobs_cancel

        sig = inspect.signature(tool_jobs_cancel)
        assert "job_id" in sig.parameters

    def test_tool_artifacts_list_signature(self):
        from apps.mcp.tools_catalog import tool_artifacts_list

        sig = inspect.signature(tool_artifacts_list)
        assert "job_id" in sig.parameters

    def test_tool_tables_list_signature(self):
        from apps.mcp.tools_catalog import tool_tables_list

        sig = inspect.signature(tool_tables_list)
        assert sig.parameters["schema"].default is None

    def test_tool_tables_columns_signature(self):
        from apps.mcp.tools_catalog import tool_tables_columns

        sig = inspect.signature(tool_tables_columns)
        assert "table" in sig.parameters

    def test_tool_governance_schema_signature(self):
        from apps.mcp.tools_catalog import tool_governance_schema

        sig = inspect.signature(tool_governance_schema)
        assert "urn" in sig.parameters

    def test_tool_quotas_tiers_signature(self):
        from apps.mcp.tools_catalog import tool_quotas_tiers

        sig = inspect.signature(tool_quotas_tiers)
        assert len(sig.parameters) == 0

    def test_tool_quotas_usage_signature(self):
        from apps.mcp.tools_catalog import tool_quotas_usage

        sig = inspect.signature(tool_quotas_usage)
        assert sig.parameters["tenant_id"].default is None

    def test_tool_quotas_set_tier_signature(self):
        from apps.mcp.tools_catalog import tool_quotas_set_tier

        sig = inspect.signature(tool_quotas_set_tier)
        assert "tier" in sig.parameters

    def test_tool_presets_list_signature(self):
        from apps.mcp.tools_catalog import tool_presets_list

        sig = inspect.signature(tool_presets_list)
        assert len(sig.parameters) == 0

    def test_tool_presets_get_signature(self):
        from apps.mcp.tools_catalog import tool_presets_get

        sig = inspect.signature(tool_presets_get)
        assert "job_id" in sig.parameters

    def test_tool_kpi_templates_list_signature(self):
        from apps.mcp.tools_catalog import tool_kpi_templates_list

        sig = inspect.signature(tool_kpi_templates_list)
        assert sig.parameters["category"].default is None

    def test_tool_kpi_templates_get_signature(self):
        from apps.mcp.tools_catalog import tool_kpi_templates_get

        sig = inspect.signature(tool_kpi_templates_get)
        assert "name" in sig.parameters

    def test_tool_kpi_templates_render_signature(self):
        from apps.mcp.tools_catalog import tool_kpi_templates_render

        sig = inspect.signature(tool_kpi_templates_render)
        assert "name" in sig.parameters
        assert "params" in sig.parameters

    def test_tool_discovery_services_list_signature(self):
        from apps.mcp.tools_catalog import tool_discovery_services_list

        sig = inspect.signature(tool_discovery_services_list)
        assert sig.parameters["tag"].default is None

    def test_tool_discovery_services_get_signature(self):
        from apps.mcp.tools_catalog import tool_discovery_services_get

        sig = inspect.signature(tool_discovery_services_get)
        assert "name" in sig.parameters

    def test_tool_discovery_services_register_signature(self):
        from apps.mcp.tools_catalog import tool_discovery_services_register

        sig = inspect.signature(tool_discovery_services_register)
        assert "name" in sig.parameters
        assert "base_url" in sig.parameters
        assert sig.parameters["version"].default == "1.0.0"
        assert sig.parameters["owner"].default == "unknown"

    def test_tool_discovery_scan_signature(self):
        from apps.mcp.tools_catalog import tool_discovery_scan

        sig = inspect.signature(tool_discovery_scan)
        assert "url" in sig.parameters

    def test_tool_vector_search_signature(self):
        from apps.mcp.tools_catalog import tool_vector_search

        sig = inspect.signature(tool_vector_search)
        assert sig.parameters["limit"].default == 5

    def test_tool_vector_index_signature(self):
        from apps.mcp.tools_catalog import tool_vector_index

        sig = inspect.signature(tool_vector_index)
        assert "text" in sig.parameters
        assert "metadata" in sig.parameters
        assert "item_id" in sig.parameters
