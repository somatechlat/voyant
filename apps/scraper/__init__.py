# Voyant Scraper Module
# DataScraper - Pure Execution Web Scraping Tools
# Production Standard v3 Compliant - No LLM Integration

# Note: Do NOT import Django models here - causes AppRegistryNotReady
# Import models directly: from apps.scraper.models import ScrapeJob

__version__ = "1.0.0"
default_app_config = "voyant.scraper.apps.ScraperConfig"
