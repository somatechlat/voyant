"""
Brave Search API client.

Requires a Brave Search API key (configured via settings).
Returns normalized SearchResultItem objects.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from apps.scraper.deep_research.schemas import SearchResultItem

logger = logging.getLogger(__name__)

BRAVE_API_URL = "https://api.search.brave.com/res/v1/web/search"


class BraveSearchClient:
    """Client for the Brave Search API."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.api_key or "",
            }
            self._client = httpx.AsyncClient(
                base_url=BRAVE_API_URL,
                headers=headers,
                timeout=30.0,
            )
        return self._client

    async def search(
        self,
        query: str,
        max_results: int = 10,
        tenant_id: str = "default",
    ) -> list[SearchResultItem]:
        """
        Execute a query against Brave Search and return normalized results.

        Args:
            query: The search query string.
            max_results: Maximum number of results (Brave max is 20 per offset).
            tenant_id: Tenant identifier for logging.

        Returns:
            List of SearchResultItem objects.
        """
        if not self.api_key:
            logger.info("[BraveSearch] no API key configured; skipping")
            return []

        logger.info(f"[BraveSearch] query='{query}' tenant={tenant_id}")
        client = await self._get_client()

        params: dict[str, Any] = {
            "q": query,
            "count": min(max_results, 20),
            "offset": 0,
            "text_decorations": False,
            "search_lang": "en",
        }

        try:
            response = await client.get("", params=params)
        except httpx.RequestError as exc:
            logger.warning(f"[BraveSearch] request error: {exc}")
            return []

        if response.status_code != 200:
            logger.warning(f"[BraveSearch] HTTP {response.status_code}")
            return []

        try:
            data = response.json()
        except Exception as exc:
            logger.warning(f"[BraveSearch] JSON parse error: {exc}")
            return []

        web_results = data.get("web", {}).get("results", [])
        extracted: list[SearchResultItem] = []
        for rank, item in enumerate(web_results[:max_results], start=1):
            extracted.append(
                SearchResultItem(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("description", ""),
                    engine="brave",
                    rank=rank,
                )
            )

        logger.info(f"[BraveSearch] returned {len(extracted)} results")
        return extracted

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
