"""
SearXNG sovereign search client.

Wraps the internal SearXNG Docker container with JSON output parsing.
No API keys required — this is the zero-cost, zero-tracking fallback.
"""

from __future__ import annotations

import logging
import urllib.parse

import httpx

from apps.scraper.deep_research.schemas import SearchResultItem

logger = logging.getLogger(__name__)


class SearXNGClient:
    """Client for the sovereign SearXNG search engine node."""

    def __init__(self, base_url: str = "") -> None:
        from apps.core.config import get_settings
        self.base_url = (base_url or get_settings().searxng_url).rstrip("/")

    async def search(
        self,
        query: str,
        max_results: int = 10,
        tenant_id: str = "default",
    ) -> list[SearchResultItem]:
        """
        Execute a query against SearXNG and return normalized results.

        Args:
            query: The search query string.
            max_results: Maximum number of results to return.
            tenant_id: Tenant identifier for logging.

        Returns:
            List of SearchResultItem objects.
        """
        logger.info(f"[SearXNG] query='{query}' tenant={tenant_id}")
        encoded = urllib.parse.quote(query)
        url = f"{self.base_url}/search?q={encoded}&format=json"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    url,
                    headers={"User-Agent": "Voyant Search Node / 1.0"},
                )
        except httpx.RequestError as exc:
            logger.warning(f"[SearXNG] connection error: {exc}")
            return []

        if response.status_code != 200:
            logger.warning(f"[SearXNG] HTTP {response.status_code}")
            return []

        try:
            data = response.json()
        except Exception as exc:
            logger.warning(f"[SearXNG] JSON parse error: {exc}")
            return []

        raw_results = data.get("results", [])
        extracted: list[SearchResultItem] = []
        for rank, item in enumerate(raw_results[:max_results], start=1):
            extracted.append(
                SearchResultItem(
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    snippet=item.get("content", item.get("snippet", "")),
                    engine="searxng",
                    rank=rank,
                )
            )

        logger.info(f"[SearXNG] returned {len(extracted)} results")
        return extracted

    async def healthcheck(self) -> bool:
        """Return True if the SearXNG node responds to a ping."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.base_url}/healthz")
                return resp.status_code == 200
        except Exception:
            return False
