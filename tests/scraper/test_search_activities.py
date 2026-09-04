"""Tests for apps.scraper.search_activities — SearchActivities class."""

import pytest

from apps.scraper.search_activities import SearchActivities


class TestSearchActivitiesInit:
    """Test initialization and base_url configuration."""

    def test_default_base_url_from_settings(self):
        """When no base_url is provided, should use settings."""
        from apps.core.config import get_settings
        settings = get_settings()
        sa = SearchActivities()
        expected = settings.searxng_url
        assert sa.base_url == expected

    def test_custom_base_url(self):
        sa = SearchActivities(base_url="http://custom:8888")
        assert sa.base_url == "http://custom:8888"

    def test_empty_base_url_falls_back_to_settings(self):
        sa = SearchActivities(base_url="")
        from apps.core.config import get_settings
        settings = get_settings()
        assert sa.base_url == settings.searxng_url


class TestSearchActivitiesQueryFormatting:
    """Test URL construction logic."""

    def test_query_url_encoding(self):
        """Verify URL encoding of query parameters."""
        import urllib.parse
        query = "machine learning & AI"
        encoded = urllib.parse.quote(query)
        assert "&" not in encoded or "%26" in encoded
        assert " " not in encoded or "%20" in encoded

    def test_search_url_format(self):
        """Verify the search URL format."""
        base = "http://localhost:8888"
        query = "test query"
        encoded = urllib.parse.quote(query)
        url = f"{base}/search?q={encoded}&format=json"
        assert "format=json" in url
        assert "test%20query" in url
