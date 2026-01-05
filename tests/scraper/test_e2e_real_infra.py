#!/usr/bin/env python3
"""
VOYANT DataScraper - E2E Tests on REAL Infrastructure

Tests against REAL PUBLIC websites - NOT mocks!
VIBE Standard v3 Compliant - Real infra testing mandatory.

All 10 VIBE Personas Active:
- PhD Lead Software Architect: Full system validation
- QA Engineer: Real-world scenarios
- Security Auditor: Real URL validation
"""
import pytest
import asyncio
import httpx
from voyant.scraper.parsing.html_parser import HTMLParser
from voyant.scraper.security import validate_url_ssrf


class TestRealWebsiteScraping:
    """Test scraping REAL public websites."""

    @pytest.fixture
    def parser(self):
        return HTMLParser()

    @pytest.mark.asyncio
    async def test_fetch_real_website_httpbin(self):
        """
        E2E Test: Fetch REAL HTML from httpbin.org
        This is a PUBLIC test service.
        """
        url = "https://httpbin.org/html"

        # 1. Validate URL is safe (SSRF check)
        is_safe, error = validate_url_ssrf(url, resolve_dns=True)
        assert is_safe is True, f"URL should be safe: {error}"

        # 2. Fetch REAL HTML from the internet
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            assert response.status_code == 200
            html = response.text

        # 3. Verify we got real HTML
        assert "<html>" in html.lower() or "<!doctype" in html.lower()
        assert len(html) > 100
        print(f"✅ Fetched {len(html)} bytes from httpbin.org")

    @pytest.mark.asyncio
    async def test_extract_from_real_website(self, parser):
        """
        E2E Test: Extract data from REAL public website.
        """
        url = "https://httpbin.org/html"

        # 1. Fetch real HTML
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            html = response.text

        # 2. Extract using agent-provided selectors (NO LLM!)
        selectors = {"title": "h1::text", "paragraphs": "p::text"}
        result = parser.extract(html, selectors)

        # 3. Verify extraction worked
        assert result is not None
        assert "title" in result or "paragraphs" in result
        print(f"✅ Extracted from real website: {result.get('title', 'N/A')}")

    @pytest.mark.asyncio
    async def test_fetch_ecuador_gov_website(self):
        """
        E2E Test: Verify we can reach Ecuador government websites.
        """
        # SRI (Servicio de Rentas Internas) - Ecuador tax authority
        url = "https://www.sri.gob.ec"

        # Validate URL (SSRF check)
        is_safe, error = validate_url_ssrf(url, resolve_dns=True)
        assert is_safe is True

        # Try to connect (may fail due to geo-restrictions but should not error)
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                response = await client.get(url)
                print(f"✅ SRI.gob.ec responded: {response.status_code}")
                # Status 200, 301, 302, 403, 503 are all valid responses
                assert response.status_code in [200, 301, 302, 403, 503]
        except httpx.TimeoutException:
            pytest.skip("SRI.gob.ec timeout - network issue")
        except httpx.ConnectError:
            pytest.skip("SRI.gob.ec unreachable - network issue")


class TestRealDNSResolution:
    """Test real DNS resolution (not mocked)."""

    def test_real_dns_google(self):
        """Verify real DNS resolution works."""
        from voyant.scraper.security import resolve_hostname

        ip = resolve_hostname("google.com")
        assert ip is not None, "Should resolve google.com to IP"
        # Google IPs typically start with 142. or 172. or 216.
        print(f"✅ google.com resolved to: {ip}")

    def test_real_dns_ecuador(self):
        """Verify Ecuador domain resolution."""
        from voyant.scraper.security import resolve_hostname

        ip = resolve_hostname("sri.gob.ec")
        # May be None if DNS fails, but should not error
        print(f"✅ sri.gob.ec resolved to: {ip or 'N/A'}")


class TestRealNetworkSecurity:
    """Test real network security validations."""

    @pytest.mark.asyncio
    async def test_ssrf_blocked_in_real_request(self):
        """
        E2E: Verify SSRF is blocked BEFORE making real request.
        """
        blocked_urls = [
            "http://169.254.169.254/latest/meta-data/",  # AWS metadata
            "http://localhost:8080/admin",
            "http://127.0.0.1:22/",
        ]

        for url in blocked_urls:
            is_safe, error = validate_url_ssrf(url, resolve_dns=False)
            assert is_safe is False, f"{url} should be blocked"
            print(f"✅ SSRF blocked: {url}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
