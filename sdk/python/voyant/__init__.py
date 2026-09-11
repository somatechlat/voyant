"""
Voyant Python SDK — Official client library for the Voyant Data Intelligence API.

Usage::

    from voyant import VoyantClient

    client = VoyantClient(base_url="http://localhost:8000", token="your-token")

    # Sources
    sources = client.sources.list()
    source = client.sources.create(name="my-db", source_type="postgres", connection_config={...})

    # Jobs
    jobs = client.jobs.list()
    job = client.jobs.get("job-id-123")

    # Scraper
    result = client.scraper.fetch(url="https://example.com")
    client.scraper.start_scrape(urls=["https://example.com"])

    # Ontology
    types = client.ontology.list_types()

    # ML Platform
    models = client.ml.list_models()

    # Governance
    search_results = client.governance.search("customer_data")

    # Auth
    auth_resp = client.auth.login(username="admin", password="secret")
"""

from __future__ import annotations

from voyant.client import VoyantClient

__all__ = ["VoyantClient"]
__version__ = "1.0.0"
