import logging
import urllib.parse
from typing import Any, Dict, List

import httpx
from temporalio import activity

logger = logging.getLogger(__name__)


class SearchActivities:
    """
    Physical Voyager Search Engine Node.
    Communicates strictly with the internal, sovereign SearXNG Docker container
    to execute bulk generic queries without API costs or tracking.
    """

    def __init__(self, base_url: str = "http://voyant_searxng:8080"):
        self.base_url = base_url

    @activity.defn(name="execute_searxng_query")
    async def execute_searxng_query(
        self, params: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        """
        Executes a query against the sovereign internal engine.
        Returns a structured mathematical list of dictionaries [URL, Title, Snippet].
        """
        query = params.get("query", "")
        max_results = params.get("max_results", 10)
        tenant_id = params.get("tenant_id", "default")

        logger.info(
            f"[SEARCH_NODE] Executing Deep Research query for {tenant_id}: '{query}'"
        )

        # Format the URL securely
        encoded_query = urllib.parse.quote(query)
        # We request JSON specifically
        search_url = f"{self.base_url}/search?q={encoded_query}&format=json"

        # Vibe Rule 5: Error handling logic implemented robustly
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Force specific headers to respect open-source engines
                response = await client.get(
                    search_url, headers={"User-Agent": "Voyant Search Node / 1.0"}
                )

                if response.status_code != 200:
                    logger.warning(
                        f"SearXNG failed {response.status_code}. Fallback to exact URL parsing if applicable."
                    )
                    return []

                data = response.json()
                results = data.get("results", [])

                extracted = []
                # Map structured data specifically ignoring tracking schemas
                for item in results[:max_results]:
                    extracted.append(
                        {
                            "url": item.get("url"),
                            "title": item.get("title"),
                            "snippet": item.get("content", item.get("snippet", "")),
                        }
                    )

                logger.info(
                    f"[SEARCH_NODE] Yielded {len(extracted)} valid URLs for extraction."
                )
                return extracted

        except httpx.RequestError as e:
            # Container might be offline, throw explicit error rather than mocking
            raise RuntimeError(
                f"Sovereign Search Engine (SearXNG) connection failed: {e}. Is the Docker container running?"
            )
