"""
Google Custom Search Engine (CSE) client.

Requires a Google API key and a programmable search engine ID.
Returns normalized SearchResultItem objects.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from apps.scraper.deep_research.schemas import SearchResultItem

logger = logging.getLogger(__name__)

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


class GoogleCSEClient:
    """Client for Google Custom Search API."""

    def __init__(
        self,
        api_key: str | None = None,
        cx: str | None = None,
    ) -> None:
        self.api_key = api_key
        self.cx = cx
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def search(
        self,
        query: str,
        max_results: int = 10,
        tenant_id: str = "default",
    ) -> list[SearchResultItem]:
        """
        Execute a query against Google CSE and return normalized results.

        Args:
            query: The search query string.
            max_results: Maximum number of results (Google max is 10 per query).
            tenant_id: Tenant identifier for logging.

        Returns:
            List of SearchResultItem objects.
        """
        if not self.api_key or not self.cx:
            logger.info("[GoogleCSE] missing API key or CX; skipping")
            return []

        logger.info(f"[GoogleCSE] query='{query}' tenant={tenant_id}")
        client = await self._get_client()

        # Google CSE returns max 10 results per call; paginate if needed.
        extracted: list[SearchResultItem] = []
        start_index = 1
        remaining = max_results

        while remaining > 0:
            num = min(remaining, 10)
            params: dict[str, Any] = {
                "key": self.api_key,
                "cx": self.cx,
                "q": query,
                "num": num,
                "start": start_index,
            }

            try:
                response = await client.get(GOOGLE_CSE_URL, params=params)
            except httpx.RequestError as exc:
                logger.warning(f"[GoogleCSE] request error: {exc}")
                break

            if response.status_code != 200:
                logger.warning(f"[GoogleCSE] HTTP {response.status_code}")
                break

            try:
                data = response.json()
            except Exception as exc:
                logger.warning(f"[GoogleCSE] JSON parse error: {exc}")
                break

            items = data.get("items", [])
            if not items:
                break

            for rank_offset, item in enumerate(items, start=0):
                extracted.append(
                    SearchResultItem(
                        url=item.get("link", ""),
                        title=item.get("title", ""),
                        snippet=item.get("snippet", ""),
                        engine="google_cse",
                        rank=start_index + rank_offset,
                    )
                )

            remaining -= len(items)
            start_index += len(items)

            if len(items) < num:
                break

        logger.info(f"[GoogleCSE] returned {len(extracted)} results")
        return extracted

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
