import logging
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from apps.scraper.activities import ScrapeActivities
    from apps.scraper.search_activities import SearchActivities

logger = logging.getLogger(__name__)


@workflow.defn(name="DeepResearchWorkflow")
class DeepResearchWorkflow:
    """
    The Google AI-style Deep Research Loop.
    1. Searches the sovereign SearXNG node.
    2. Broadcasts parallel Temporal workflows to scrape every URL via Playwright.
    3. Aggregates all text into the central system for the Agent to access.
    """

    @workflow.run
    async def run(self, params: dict) -> dict:
        topic = params.get("topic")
        tenant_id = params.get("tenant_id")
        job_id = params.get("job_id")
        max_urls = params.get("max_urls", 5)

        workflow.logger.info(
            f"[DEEP_RESEARCH] Initiating autonomous scraping suite for {tenant_id} on topic: {topic}"
        )

        # STEP 1: Search Node (Yields mathematical list of URLs)
        start_to_close_timeout = timedelta(minutes=2)

        search_params = {
            "query": topic,
            "max_results": max_urls,
            "tenant_id": tenant_id,
        }

        url_collection = await workflow.execute_activity(
            SearchActivities.execute_searxng_query,
            search_params,
            start_to_close_timeout=start_to_close_timeout,
        )

        if not url_collection:
            return {
                "status": "failed",
                "reason": "No URLs extracted from sovereign node.",
                "job_id": job_id,
            }

        workflow.logger.info(
            f"[DEEP_RESEARCH] Loop trigger: Found {len(url_collection)} nodes. Activating parallel Scrape mode."
        )

        # STEP 2: Agentic Autonomous Sub-Scraping (Playwright Loop)
        # We spawn native parallel Playwright workflows for every URL.
        scrape_timeouts = timedelta(minutes=10)

        scrape_futures = []
        for index, item in enumerate(url_collection):
            url = item.get("url")
            if url:
                # Triggering existing ScrapeActivities (Playwright mapping)
                scrape_params = {
                    "url": url,
                    "target_selector": "body",  # Deep Research wants all text
                    "tenant_id": tenant_id,
                    "job_id": f"{job_id}_node_{index}",
                }

                future = workflow.execute_activity(
                    ScrapeActivities.fetch_page,
                    scrape_params,
                    start_to_close_timeout=scrape_timeouts,
                    retry_policy=None,
                )
                scrape_futures.append(future)

        # Await all chunks in parallel completely autonomously
        all_chunked_html = await workflow.wait_all(scrape_futures)

        workflow.logger.info(
            f"[DEEP_RESEARCH] Extracted {len(all_chunked_html)} autonomous dumps for {tenant_id}."
        )

        return {
            "status": "success",
            "job_id": job_id,
            "urls_processed": len(url_collection),
            "topic": topic,
        }
