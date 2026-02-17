#!/usr/bin/env python3
"""DataScraper and MCP contract tests."""

import json

from voyant.scraper.parsing.html_parser import HTMLParser


def test_html_extraction() -> None:
    test_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page - Ecuador Companies</title></head>
    <body>
        <h1>Empresas del Ecuador</h1>
        <div class="company" data-ruc="1234567890001">
            <h2 class="name">Acme Corporation S.A.</h2>
            <p class="address">Av. Amazonas 1234, Quito</p>
            <span class="status">Activo</span>
        </div>
    </body>
    </html>
    """

    selectors = {
        "title": "title::text",
        "main_heading": "h1::text",
        "companies": {
            "root": ".company",
            "fields": {
                "name": ".name::text",
                "address": ".address::text",
                "status": ".status::text",
                "ruc": "::attr(data-ruc)",
            },
        },
    }

    parser = HTMLParser()
    result = parser.extract(test_html, selectors)

    assert result.get("title") == ["Test Page - Ecuador Companies"]
    assert result.get("main_heading") == ["Empresas del Ecuador"]
    assert len(result.get("companies", [])) == 1
    assert result["companies"][0]["name"] == "Acme Corporation S.A."


def test_mcp_scrape_tools_present() -> None:
    import os

    import django

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
    django.setup()

    from django_mcp import mcp_app

    tools = mcp_app._tool_manager.list_tools()  # noqa: SLF001 - SDK internal surface
    tool_names = {tool.name for tool in tools}

    scrape_tools = {
        "scrape.fetch",
        "scrape.extract",
        "scrape.ocr",
        "scrape.parse_pdf",
        "scrape.transcribe",
    }

    assert scrape_tools.issubset(tool_names)
    print(json.dumps(sorted(tool_names), indent=2))
