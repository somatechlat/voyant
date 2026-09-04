"""Tests for apps.scraper.parsing.tika_client — TikaClient and TikaResult."""

import pytest

from apps.scraper.parsing.tika_client import TikaClient, TikaResult, get_tika_client


# ---------------------------------------------------------------------------
# TikaResult dataclass
# ---------------------------------------------------------------------------


class TestTikaResult:
    def test_default_values(self):
        result = TikaResult()
        assert result.content == ""
        assert result.content_type == ""
        assert result.metadata == {}
        assert result.language == ""
        assert result.pages == 0

    def test_with_values(self):
        result = TikaResult(
            content="Hello world",
            content_type="text/plain",
            metadata={"Author": "Test"},
            language="en",
            pages=5,
        )
        assert result.content == "Hello world"
        assert result.content_type == "text/plain"
        assert result.metadata == {"Author": "Test"}
        assert result.language == "en"
        assert result.pages == 5


# ---------------------------------------------------------------------------
# TikaClient initialization
# ---------------------------------------------------------------------------


class TestTikaClientInit:
    def test_init_default_url(self):
        """Client should initialize with settings URL."""
        client = TikaClient()
        # base_url comes from settings or is empty
        assert isinstance(client.base_url, str)

    def test_init_custom_url(self):
        client = TikaClient(base_url="http://tika:9998")
        assert client.base_url == "http://tika:9998"

    def test_client_initially_none(self):
        client = TikaClient(base_url="http://tika:9998")
        assert client._client is None


# ---------------------------------------------------------------------------
# TikaClient._get_client
# ---------------------------------------------------------------------------


class TestTikaClientGetClient:
    def test_creates_httpx_client(self):
        client = TikaClient(base_url="http://tika:9998")
        httpx_client = client._get_client()
        assert httpx_client is not None
        assert not httpx_client.is_closed

    def test_reuses_existing_client(self):
        client = TikaClient(base_url="http://tika:9998")
        c1 = client._get_client()
        c2 = client._get_client()
        assert c1 is c2


# ---------------------------------------------------------------------------
# TikaClient.is_available
# ---------------------------------------------------------------------------


class TestTikaClientIsAvailable:
    def test_unavailable_when_no_server(self):
        """When Tika server is unreachable, should return False."""
        client = TikaClient(base_url="http://127.0.0.1:19999")
        assert client.is_available() is False


# ---------------------------------------------------------------------------
# get_tika_client factory
# ---------------------------------------------------------------------------


class TestGetTikaClient:
    def test_factory_returns_tika_client(self):
        client = get_tika_client()
        assert isinstance(client, TikaClient)
