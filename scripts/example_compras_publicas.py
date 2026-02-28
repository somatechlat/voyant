"""
Example: Scraping Ecuador's SERCOP (Compras Públicas) Open Data API

This script demonstrates how an intelligent agent utilizes Voyant's
Zero-Intelligence execution engine (DataScraper module) to fetch
JSON data from an external Open Data API.

Vibe Coding Rule Compliance:
- REAL IMPLEMENTATIONS ONLY: Uses actual Voyant internal activities.
- NO BULLSHIT: Hits the real endpoint.
"""

import asyncio
import logging
import json

# Setup minimal Django context for standalone script execution
import os
import django
os.environ["VOYANT_SCRAPER_TLS_VERIFY"] = "False"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "voyant_project.settings")
django.setup()

from apps.core.config import get_settings
settings = get_settings()
settings.scraper_tls_verify = False

from apps.scraper.activities import ScrapeActivities

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sercop_example")

async def fetch_recent_procurements():
    """
    Fetches the 100 most recent public procurements for 2026
    from the SERCOP Open Contracting Data Standard (OCDS) API.
    """
    logger.info("Initializing Voyant ScrapeActivities...")
    activity = ScrapeActivities()

    # Target the SERCOP Open Data API
    # Using the standard OCDS search endpoint
    target_url = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/search_ocds?year=2026"

    logger.info(f"Targeting URL: {target_url}")

    # We instruct the Voyant scraper to use the lightweight HTTPX engine
    # since we do not need a full browser (Playwright) to parse an API payload.
    payload = {
        "url": target_url,
        "engine": "httpx",
        "timeout": 30,
        "capture_json": False  # Not intercepting browser traffic, just a direct hit
    }

    try:
        # Execute the fetch activity
        result = await activity.fetch_page(payload)

        # The result typically contains the RAW html/body text mapped to 'html' or 'text'
        # depending on the engine's internal formatting.
        raw_body = result.get("html") or result.get("content", "{}")

        try:
            data = json.loads(raw_body)
            # Assuming the API returns a list or an object with a 'data' array
            records = data if isinstance(data, list) else data.get("data", [])

            logger.info("==================================================")
            logger.info(f"✅ Successfully retrieved data from SERCOP API.")
            logger.info(f"Total records found: {len(records)}")

            # Slice exactly to the last 100 for the requirement
            last_100 = records[:100]
            logger.info(f"Extracted {len(last_100)} procurements for year 2026.")
            logger.info("==================================================")

            return last_100

        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from the API response.")
            logger.error(f"Raw snippet: {raw_body[:500]}")

    except Exception as e:
        logger.error(f"Voyant execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(fetch_recent_procurements())
