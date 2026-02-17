"""
Discovery Activities: Building Blocks for API and Service Discovery.

This module defines Temporal activities responsible for discovering external
APIs and parsing their specifications (e.g., OpenAPI/Swagger). These activities
are crucial for enabling the Voyant platform to automatically identify and
integrate with new services.

Architectural Note:
The full `DiscoveryRepo` (for persistent storage and management of discovered
services in a catalog database) is noted as not yet fully implemented.
Current functionality focuses on active discovery and parsing.
"""

import logging
from typing import Any, Dict, List

from temporalio import activity
from temporalio.exceptions import ApplicationError

from voyant.discovery.search_utils import SearchClient
from voyant.discovery.spec_parser import SpecParser

logger = logging.getLogger(__name__)


class DiscoveryActivities:
    """
    A collection of Temporal activities related to API and service discovery.

    These activities encapsulate the logic for searching for API documentation
    and parsing API specifications from external URLs.
    """

    def __init__(self):
        """
        Initializes the DiscoveryActivities with instances of SearchClient and SpecParser.
        """
        self.search = SearchClient()
        self.parser = SpecParser()

    @activity.defn(name="search_for_apis")
    def search_for_apis(self, params: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Searches for external API documentation based on a given query.

        This activity uses an external `SearchClient` to find relevant API
        specifications or documentation online.

        Args:
            params: A dictionary containing search parameters:
                - `query` (str): The search query string.
                - `limit` (int, optional): The maximum number of results to return. Defaults to 5.

        Returns:
            A list of dictionaries, where each dictionary represents a found API,
            including its name, URL, and a brief description.

        Raises:
            Exception: For any errors encountered during the search operation.
        """
        query = params.get("query", "")
        limit = params.get("limit", 5)

        activity.logger.info(f"Searching for APIs matching query: '{query}' (limit: {limit}).")
        return self.search.search_apis(query, limit)

    @activity.defn(name="scan_spec_url")
    def scan_spec_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scans and parses an OpenAPI specification from a given URL.

        This activity downloads the specification and extracts key metadata
        such as the API's title, version, base URL, and a sample of its endpoints.

        Args:
            params: A dictionary containing scan parameters:
                - `url` (str): The URL to the OpenAPI specification file (e.g., JSON or YAML).

        Returns:
            A dictionary summarizing the parsed API specification.

        Raises:
            Exception: If the URL is invalid, the specification cannot be downloaded,
                       or parsing fails.
        """
        url = params.get("url", "")
        activity.logger.info(f"Scanning API specification from URL: '{url}'.")

        try:
            spec = self.parser.parse_from_url(url)

            # Serialize the parsed specification data for transport back to the workflow.
            result = {
                "title": spec.title,
                "version": spec.version,
                "base_url": spec.base_url,
                "auth_type": spec.auth_type,
                "endpoint_count": len(spec.endpoints),
                "endpoints_sample": [
                    {"method": e.method, "path": e.path, "summary": e.summary}
                    for e in spec.endpoints[:5]
                ],
            }
            activity.logger.info(f"Successfully scanned spec for '{spec.title}' v{spec.version}.")
            return result

        except Exception as e:
            activity.logger.error(f"API specification scan failed for URL '{url}': {e}")
            raise activity.ApplicationError(
                f"API specification scan failed: {e}", non_retryable=True
            ) from e
