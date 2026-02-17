"""
VOYANT DataScraper - HTML Parser Tests

Tests CSS selector and XPath extraction.
Production Standard v3 Compliant - Agent-provided selectors (NO LLM).

All 10 Production Personas Active:
- PhD Software Analyst: Data flow validation
- QA Engineer: Edge case testing
- Domain Expert (Ecuador): Spanish content handling
"""

import pytest
from voyant.scraper.parsing.html_parser import HTMLParser


class TestCSSSelectors:
    """Test CSS selector extraction."""

    @pytest.fixture
    def parser(self):
        return HTMLParser()

    @pytest.fixture
    def sample_html(self):
        return """
        <!DOCTYPE html>
        <html>
        <head><title>Empresas Ecuador</title></head>
        <body>
            <h1>Lista de Empresas</h1>
            <div class="company" data-ruc="1234567890001">
                <h2 class="name">Acme S.A.</h2>
                <p class="address">Quito, Ecuador</p>
                <span class="status active">Activo</span>
            </div>
            <div class="company" data-ruc="0987654321001">
                <h2 class="name">TechStart Cia. Ltda.</h2>
                <p class="address">Guayaquil, Ecuador</p>
                <span class="status inactive">Inactivo</span>
            </div>
        </body>
        </html>
        """

    def test_text_extraction(self, parser, sample_html):
        """Extract text content from elements."""
        selectors = {"title": "title::text"}
        result = parser.extract(sample_html, selectors)
        assert result["title"] == ["Empresas Ecuador"]

    def test_multiple_elements(self, parser, sample_html):
        """Extract multiple elements with same selector."""
        selectors = {"names": ".name::text"}
        result = parser.extract(sample_html, selectors)
        assert len(result["names"]) == 2
        assert "Acme S.A." in result["names"]
        assert "TechStart Cia. Ltda." in result["names"]

    def test_nested_extraction(self, parser, sample_html):
        """Extract nested data from repeated structures."""
        selectors = {
            "companies": {
                "root": ".company",
                "fields": {
                    "name": ".name::text",
                    "address": ".address::text",
                    "status": ".status::text",
                },
            }
        }
        result = parser.extract(sample_html, selectors)
        assert len(result["companies"]) == 2
        assert result["companies"][0]["name"] == "Acme S.A."
        assert result["companies"][1]["address"] == "Guayaquil, Ecuador"

    def test_default_text_extraction(self, parser, sample_html):
        """CSS without pseudo-element defaults to ::text."""
        selectors = {"heading": "h1"}
        result = parser.extract(sample_html, selectors)
        assert result["heading"] == ["Lista de Empresas"]


class TestXPathSelectors:
    """Test XPath selector extraction."""

    @pytest.fixture
    def parser(self):
        return HTMLParser()

    @pytest.fixture
    def sample_html(self):
        return """
        <html>
        <body>
            <table id="datos">
                <tr><th>RUC</th><th>Nombre</th></tr>
                <tr><td>1234567890001</td><td>Empresa A</td></tr>
                <tr><td>0987654321001</td><td>Empresa B</td></tr>
            </table>
        </body>
        </html>
        """

    def test_xpath_extraction(self, parser, sample_html):
        """Extract using XPath selectors."""
        selectors = {"rucs": "//table[@id='datos']//tr/td[1]/text()"}
        result = parser.extract(sample_html, selectors)
        assert len(result["rucs"]) == 2
        assert "1234567890001" in result["rucs"]


class TestHelperMethods:
    """Test helper extraction methods."""

    @pytest.fixture
    def parser(self):
        return HTMLParser()

    def test_get_all_links(self, parser):
        """Extract all links from HTML."""
        html = """
        <html>
        <body>
            <a href="https://sri.gob.ec">SRI</a>
            <a href="https://sercop.gob.ec">SERCOP</a>
            <a href="/internal">Internal</a>
        </body>
        </html>
        """
        links = parser.get_all_links(html)
        assert len(links) == 3
        assert "https://sri.gob.ec" in links

    def test_get_all_images(self, parser):
        """Extract all image sources."""
        html = """
        <html>
        <body>
            <img src="/logo.png" alt="Logo">
            <img src="https://cdn.example.com/image.jpg">
        </body>
        </html>
        """
        images = parser.get_all_images(html)
        assert len(images) == 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def parser(self):
        return HTMLParser()

    def test_empty_html(self, parser):
        """Handle empty HTML gracefully."""
        result = parser.extract("", {"title": "title::text"})
        # Should not crash, may return empty or error
        assert result is not None

    def test_invalid_selector(self, parser):
        """Handle invalid selectors gracefully."""
        html = "<html><body><p>Test</p></body></html>"
        result = parser.extract(html, {"invalid": "..invalid.."})
        assert result.get("invalid") is None or result.get("invalid") == []

    def test_spanish_content(self, parser):
        """Handle Spanish characters correctly."""
        html = """
        <html>
        <body>
            <p class="direccion">Av. Amazonas Nº 123, Quito</p>
            <p class="razon">Compañía Ñandú S.A.</p>
        </body>
        </html>
        """
        selectors = {"direccion": ".direccion::text", "razon": ".razon::text"}
        result = parser.extract(html, selectors)
        assert "Ñandú" in result["razon"][0]
        assert "Nº" in result["direccion"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
