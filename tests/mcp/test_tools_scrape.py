"""
Unit tests for apps.mcp.tools_scrape — Scrape & UPTP MCP tools.

Tests tool function signatures and the TemplateExecutionRequest
construction in tool_execute_template.
Most tools delegate to async activity classes; we verify structure.
"""

import inspect

import pytest
from pydantic import ValidationError as PydanticValidationError

from apps.uptp_core.schemas import TemplateCategory, TemplateExecutionRequest


# =========================================================================
# Tool signature verification
# =========================================================================


class TestScrapeToolSignatures:
    def test_tool_scrape_fetch_signature(self):
        from apps.mcp.tools_scrape import tool_scrape_fetch

        sig = inspect.signature(tool_scrape_fetch)
        assert sig.parameters["url"].default is inspect.Parameter.empty
        assert sig.parameters["engine"].default == "playwright"
        assert sig.parameters["scroll"].default is False
        assert sig.parameters["timeout"].default == 30
        assert sig.parameters["capture_json"].default is False

    def test_tool_scrape_deep_archive_signature(self):
        from apps.mcp.tools_scrape import tool_scrape_deep_archive

        sig = inspect.signature(tool_scrape_deep_archive)
        assert sig.parameters["url"].default is inspect.Parameter.empty
        assert sig.parameters["target_dir"].default == "scrapes/unknown"
        assert sig.parameters["wait_settle_ms"].default == 2000
        assert sig.parameters["timeout_ms"].default == 60000

    def test_tool_scrape_extract_signature(self):
        from apps.mcp.tools_scrape import tool_scrape_extract

        sig = inspect.signature(tool_scrape_extract)
        assert "html" in sig.parameters
        assert "selectors" in sig.parameters
        assert sig.parameters["url"].default == ""

    def test_tool_scrape_ocr_signature(self):
        from apps.mcp.tools_scrape import tool_scrape_ocr

        sig = inspect.signature(tool_scrape_ocr)
        assert "images" in sig.parameters
        assert sig.parameters["language"].default == "spa+eng"

    def test_tool_scrape_parse_pdf_signature(self):
        from apps.mcp.tools_scrape import tool_scrape_parse_pdf

        sig = inspect.signature(tool_scrape_parse_pdf)
        assert "pdf_url" in sig.parameters
        assert sig.parameters["extract_tables"].default is False

    def test_tool_scrape_transcribe_signature(self):
        from apps.mcp.tools_scrape import tool_scrape_transcribe

        sig = inspect.signature(tool_scrape_transcribe)
        assert "media_urls" in sig.parameters
        assert sig.parameters["language"].default == "es"

    def test_tool_execute_template_signature(self):
        from apps.mcp.tools_scrape import tool_execute_template

        sig = inspect.signature(tool_execute_template)
        assert "template_id" in sig.parameters
        assert "category" in sig.parameters
        assert "tenant_id" in sig.parameters
        assert "params" in sig.parameters
        assert sig.parameters["job_name"].default is None


# =========================================================================
# TemplateExecutionRequest construction (as used by tool_execute_template)
# =========================================================================


class TestTemplateRequestConstruction:
    """Test that TemplateExecutionRequest can be constructed as the tool does."""

    def test_construct_with_all_fields(self):
        req = TemplateExecutionRequest(
            template_id="analysis.correlation",
            category="math",
            tenant_id="t-001",
            params={"table": "sales", "columns": ["a", "b"]},
            job_name="Correlation Analysis",
        )
        assert req.template_id == "analysis.correlation"
        assert req.category == TemplateCategory.MATH
        assert req.params["table"] == "sales"
        assert req.job_name == "Correlation Analysis"

    def test_construct_without_job_name(self):
        req = TemplateExecutionRequest(
            template_id="ingest.db.generic",
            category="ingestion",
            tenant_id="t-001",
            params={"generic_uri": "postgresql://u:p@h/db"},
        )
        assert req.job_name is None

    def test_construct_with_empty_params(self):
        req = TemplateExecutionRequest(
            template_id="render.chart.bar",
            category="render",
            tenant_id="t-001",
            params={},
        )
        assert req.params == {}

    def test_construct_invalid_category_raises(self):
        with pytest.raises(PydanticValidationError):
            TemplateExecutionRequest(
                template_id="x",
                category="invalid_category",
                tenant_id="t-001",
                params={},
            )

    def test_construct_missing_template_id_raises(self):
        with pytest.raises(PydanticValidationError):
            TemplateExecutionRequest(
                category="math",
                tenant_id="t-001",
                params={},
            )

    def test_construct_missing_tenant_id_raises(self):
        with pytest.raises(PydanticValidationError):
            TemplateExecutionRequest(
                template_id="x",
                category="math",
                params={},
            )


# =========================================================================
# Module-level singleton instances
# =========================================================================


class TestModuleSingletons:
    def test_fetch_activities_exists(self):
        from apps.mcp.tools_scrape import _fetch_activities

        assert _fetch_activities is not None

    def test_parse_activities_exists(self):
        from apps.mcp.tools_scrape import _parse_activities

        assert _parse_activities is not None
