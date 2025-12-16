"""
Discovery Activities

Temporal activities for auto-discovery of APIs.
Adheres to Vibe Coding Rules: Integrates Search/Parser real implementations.
"""
import logging
from typing import Any, Dict, List

from temporalio import activity

from voyant.discovery.search_utils import SearchClient
from voyant.discovery.spec_parser import SpecParser
# Note: DiscoveryRepo not yet implemented - will store results in catalog database

logger = logging.getLogger(__name__)

class DiscoveryActivities:
    def __init__(self):
        self.search = SearchClient()
        self.parser = SpecParser()
 

    @activity.defn
    def search_for_apis(self, params: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Search for API documentation.
        """
        query = params.get("query", "")
        limit = params.get("limit", 5)
        
        activity.logger.info(f"Searching for APIs matching: {query}")
        return self.search.search_apis(query, limit)

    @activity.defn
    def scan_spec_url(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scan and parse a spec URL.
        """
        url = params.get("url", "")
        activity.logger.info(f"Scanning spec at: {url}")
        
        try:
            spec = self.parser.parse_from_url(url)
            
            # Serialize for transport
            result = {
                "title": spec.title,
                "version": spec.version,
                "base_url": spec.base_url,
                "auth_type": spec.auth_type,
                "endpoint_count": len(spec.endpoints),
                "endpoints_sample": [
                    {"method": e.method, "path": e.path, "summary": e.summary}
                    for e in spec.endpoints[:5]
                ]
            }
            return result
            
        except Exception as e:
            activity.logger.error(f"Spec scan failed: {e}")
            raise
