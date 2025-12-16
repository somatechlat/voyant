"""
Verification Script for Discovery Engine

Tests web search and spec parsing.
Requires: pip install requests
"""
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from voyant.discovery.search_utils import SearchClient
from voyant.discovery.spec_parser import SpecParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_discovery")

def test_search():
    logger.info("Testing Web Search...")
    # Mocking environment for test if key not present
    if not os.getenv("SERPER_API_KEY"):
        logger.warning("SERPER_API_KEY missing. Skipping real network search.")
        return

    client = SearchClient()
    results = client.search_apis("Stripe", limit=2)
    logger.info(f"Search Results: {len(results)}")
    for r in results:
        logger.info(f" - {r['title']}: {r['link']}")

def test_parser():
    logger.info("Testing Spec Parser...")
    parser = SpecParser()
    
    # Test with the famous Petstore spec
    url = "https://petstore.swagger.io/v2/swagger.json"
    
    try:
        spec = parser.parse_from_url(url)
        logger.info(f"Parsed Spec: {spec.title} (v{spec.version})")
        logger.info(f"Base URL: {spec.base_url}")
        logger.info(f"Auth Type: {spec.auth_type}")
        logger.info(f"Endpoint Count: {len(spec.endpoints)}")
        if spec.endpoints:
            e = spec.endpoints[0]
            logger.info(f"Sample Endpoint: {e.method} {e.path}")
            
    except Exception as e:
        logger.error(f"Parser Failed: {e}")

if __name__ == "__main__":
    test_search()
    test_parser()
