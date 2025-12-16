"""
Search Utilities

Wraps search engine APIs (e.g., Serper, DuckDuckGo) to discover API documentation.
Adheres to Vibe Coding Rules: Real API implementation (Mock fallback only if key missing).
"""
import os
import logging
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

class SearchClient:
    """
    Client for searching the web for API documentation and specs.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        # Default to Serper for structured JSON results
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"

    def search_apis(self, query: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        Search for APIs matching the query.
        
        UX Consultant: Graceful degradation - empty results vs crash
        """
        from voyant.core.circuit_breaker import get_circuit_breaker, CircuitBreakerOpenError, CircuitBreakerConfig
        
        params = f"API documentation {query} OpenAPI Swagger"
        
        if not self.api_key:
             # Vibe Rule #5: Graceful degradation logic
             logger.warning("SERPER_API_KEY not set. Returning empty search results.")
             return []
        
        # Get circuit breaker for Serper
        cb = get_circuit_breaker(
            "serper_api",
            CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=30
            )
        )
        
        def _search():
            """Inner function for circuit breaker."""
            payload = {
                "q": params,
                "num": limit
            }
            headers = {
                "X-API-KEY": self.api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            return self._parse_serper_results(data)
        
        try:
            return cb.call(_search)
        except CircuitBreakerOpenError:
            logger.warning(f"Serper API circuit breaker open. Returning empty results for: {query}")
            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def _parse_serper_results(self, data: Dict[str, Any]) -> List[Dict[str, str]]:
        results = []
        if "organic" in data:
            for item in data["organic"]:
                results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet")
                })
        return results
