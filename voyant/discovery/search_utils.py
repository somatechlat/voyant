"""
Search Utilities: Client for External API Documentation Discovery.

This module provides utilities for searching the web for API documentation and
specifications. It integrates with external search engine APIs (currently Serper)
to discover and retrieve metadata about APIs, which can then be parsed and added
to the Voyant discovery catalog.
"""

import logging
import os
import requests
from typing import Any, Dict, List, Optional

from voyant.core.circuit_breaker import CircuitBreakerConfig, CircuitBreakerOpenError, get_circuit_breaker
from voyant.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SearchClient:
    """
    A client for searching the web for API documentation and specifications using the Serper API.

    This client is designed to discover new services by querying public search engines
    for relevant API definitions (e.g., OpenAPI, Swagger). It incorporates a circuit
    breaker pattern for resilience against external API failures.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the SearchClient.

        Args:
            api_key (Optional[str]): The API key for the Serper search engine. If None,
                                     it defaults to the `SERPER_API_KEY` environment variable.
        """
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"

    def search_apis(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Searches for external API documentation matching a given query.

        This method leverages the Serper API to perform web searches and parses
        the results to identify potential API documentation links.

        Args:
            query (str): The search query string (e.g., "payments api documentation").
            limit (int, optional): The maximum number of search results to return. Defaults to 10.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, where each dictionary
                                  contains "title", "link", and "snippet" of a search result.
                                  Returns an empty list if the API key is missing or the search fails.
        """
        # Ensure that the Serper API key is available.
        if not self.api_key:
            logger.warning("SERPER_API_KEY not set. Returning empty search results for query: '%s'.", query)
            # Returning empty results on missing API key is a form of graceful degradation.
            return []

        # Configure a circuit breaker for the external Serper API to enhance resilience.
        # This prevents repeated calls to a failing external service.
        cb = get_circuit_breaker(
            "serper_api", CircuitBreakerConfig(failure_threshold=5, recovery_timeout=30)
        )

        def _perform_search_request():
            """Internal function to perform the actual HTTP request to the Serper API."""
            params = f"API documentation {query} OpenAPI Swagger"
            payload = {"q": params, "num": limit}
            headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}

            response = requests.post(
                self.base_url, headers=headers, json=payload, timeout=10
            )
            response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx).

            data = response.json()
            return self._parse_serper_results(data)

        try:
            # Execute the search request through the circuit breaker.
            return cb.call(_perform_search_request)
        except CircuitBreakerOpenError:
            logger.warning(
                "Serper API circuit breaker is open. Returning empty results for query: '%s'.", query
            )
            # On circuit open, return empty results as a graceful degradation strategy.
            return []
        except Exception as e:
            logger.error(f"External API search (Serper) failed for query '{query}': {e}")
            raise

    def _parse_serper_results(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Internal method: Parses the raw JSON response from the Serper API.

        Args:
            data (Dict[str, Any]): The raw JSON response received from the Serper API.

        Returns:
            List[Dict[str, str]]: A list of dictionaries, each containing "title", "link", and "snippet"
                                  extracted from the organic search results.
        """
        results = []
        if "organic" in data:
            for item in data["organic"]:
                results.append(
                    {
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                    }
                )
        return results
