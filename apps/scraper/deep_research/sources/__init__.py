"""
Search source clients for Deep Research v2.

Supports SearXNG (sovereign), Brave Search API, and Google Custom Search API.
All clients return normalized SearchResultItem lists.
"""

from apps.scraper.deep_research.sources.brave_search import BraveSearchClient
from apps.scraper.deep_research.sources.google_cse import GoogleCSEClient
from apps.scraper.deep_research.sources.searxng_client import SearXNGClient

__all__ = ["SearXNGClient", "BraveSearchClient", "GoogleCSEClient"]
