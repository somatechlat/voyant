"""Tests for deep research search source clients — SearXNG, Brave, Google CSE."""

import pytest

from apps.scraper.deep_research.schemas import SearchResultItem
from apps.scraper.deep_research.sources.searxng_client import SearXNGClient
from apps.scraper.deep_research.sources.brave_search import BraveSearchClient
from apps.scraper.deep_research.sources.google_cse import GoogleCSEClient


# ---------------------------------------------------------------------------
# SearXNGClient
# ---------------------------------------------------------------------------


class TestSearXNGClient:
    def test_init_default_url(self):
        """Client should initialize with settings URL."""
        client = SearXNGClient()
        assert client.base_url  # Should not be empty

    def test_init_custom_url(self):
        client = SearXNGClient(base_url="http://custom:8888")
        assert client.base_url == "http://custom:8888"

    def test_init_strips_trailing_slash(self):
        client = SearXNGClient(base_url="http://host:8888/")
        assert client.base_url == "http://host:8888"

    @pytest.mark.asyncio
    async def test_search_returns_list_on_connection_failure(self):
        """When SearXNG is unreachable, should return empty list (not raise)."""
        client = SearXNGClient(base_url="http://127.0.0.1:19999")
        results = await client.search("test query", max_results=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_healthcheck_unreachable(self):
        client = SearXNGClient(base_url="http://127.0.0.1:19999")
        result = await client.healthcheck()
        assert result is False


# ---------------------------------------------------------------------------
# BraveSearchClient
# ---------------------------------------------------------------------------


class TestBraveSearchClient:
    def test_init_no_api_key(self):
        client = BraveSearchClient(api_key=None)
        assert client.api_key is None

    def test_init_with_api_key(self):
        client = BraveSearchClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"

    @pytest.mark.asyncio
    async def test_search_no_api_key_returns_empty(self):
        """Without API key, should return empty list immediately."""
        client = BraveSearchClient(api_key=None)
        results = await client.search("test", max_results=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_api_key_returns_empty(self):
        client = BraveSearchClient(api_key="")
        results = await client.search("test", max_results=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_close_without_client(self):
        """Closing when no client was created should not raise."""
        client = BraveSearchClient(api_key="test")
        await client.close()  # Should not raise


# ---------------------------------------------------------------------------
# GoogleCSEClient
# ---------------------------------------------------------------------------


class TestGoogleCSEClient:
    def test_init_no_credentials(self):
        client = GoogleCSEClient(api_key=None, cx=None)
        assert client.api_key is None
        assert client.cx is None

    def test_init_with_credentials(self):
        client = GoogleCSEClient(api_key="key123", cx="cx456")
        assert client.api_key == "key123"
        assert client.cx == "cx456"

    @pytest.mark.asyncio
    async def test_search_no_credentials_returns_empty(self):
        """Without API key or CX, should return empty list."""
        client = GoogleCSEClient(api_key=None, cx=None)
        results = await client.search("test", max_results=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_search_missing_cx_returns_empty(self):
        client = GoogleCSEClient(api_key="key", cx=None)
        results = await client.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_missing_key_returns_empty(self):
        client = GoogleCSEClient(api_key=None, cx="cx")
        results = await client.search("test")
        assert results == []

    @pytest.mark.asyncio
    async def test_close_without_client(self):
        client = GoogleCSEClient(api_key="key", cx="cx")
        await client.close()  # Should not raise


# ---------------------------------------------------------------------------
# SearchResultItem schema
# ---------------------------------------------------------------------------


class TestSearchResultItem:
    def test_basic_creation(self):
        item = SearchResultItem(url="https://example.com", title="Test", snippet="A snippet")
        assert item.url == "https://example.com"
        assert item.title == "Test"
        assert item.snippet == "A snippet"
        assert item.engine == ""
        assert item.rank == 0

    def test_with_engine_and_rank(self):
        item = SearchResultItem(url="https://a.com", engine="searxng", rank=1)
        assert item.engine == "searxng"
        assert item.rank == 1

    def test_model_dump(self):
        item = SearchResultItem(url="https://a.com", title="T")
        d = item.model_dump(mode="json")
        assert isinstance(d, dict)
        assert d["url"] == "https://a.com"
