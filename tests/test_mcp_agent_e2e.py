#!/usr/bin/env python3
"""django-mcp registration test for Voyant tool surface."""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")


def test_django_mcp_tool_registration() -> None:
    """Verify django-mcp exposes the expected dotted tool names."""
    django.setup()

    from django_mcp import mcp_app

    tools = mcp_app._tool_manager.list_tools()  # noqa: SLF001 - SDK internal surface
    tool_names = {tool.name for tool in tools}

    expected = {
        "voyant.discover",
        "voyant.connect",
        "voyant.ingest",
        "voyant.profile",
        "voyant.quality",
        "voyant.analyze",
        "voyant.kpi",
        "voyant.status",
        "voyant.artifact",
        "voyant.sql",
        "voyant.search",
        "voyant.lineage",
        "voyant.preset",
        "voyant.sources.list",
        "voyant.sources.get",
        "voyant.sources.delete",
        "voyant.jobs.list",
        "voyant.jobs.cancel",
        "voyant.artifacts.list",
        "voyant.tables.list",
        "voyant.tables.columns",
        "voyant.governance.schema",
        "voyant.quotas.tiers",
        "voyant.quotas.usage",
        "voyant.quotas.limits",
        "voyant.quotas.set_tier",
        "voyant.presets.list",
        "voyant.presets.get",
        "voyant.kpi_templates.list",
        "voyant.kpi_templates.categories",
        "voyant.kpi_templates.get",
        "voyant.kpi_templates.render",
        "voyant.discovery.services.list",
        "voyant.discovery.services.get",
        "voyant.discovery.services.register",
        "voyant.discovery.scan",
        "voyant.vector.search",
        "voyant.vector.index",
        "scrape.fetch",
        "scrape.extract",
        "scrape.ocr",
        "scrape.parse_pdf",
        "scrape.transcribe",
    }

    missing = expected - tool_names
    assert not missing, f"Missing MCP tools: {sorted(missing)}"
