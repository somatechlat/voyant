"""
Voyant Scraper: Temporal Workflow for Web Scraping.

This module defines the high-level orchestration for executing web scraping jobs.
It operates as a "pure execution" component within an Agent-Tool architecture,
where an external agent provides the intelligence (e.g., URLs, selectors) and
this workflow handles the mechanical execution.

The workflow coordinates a series of activities to:
- Fetch web pages.
- Extract data using agent-provided selectors.
- Optionally process media (OCR, transcription).
- Store extracted data and artifacts.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

# This context manager is necessary to allow importing non-workflow/activity
# modules within the workflow definition. It passes control to the Python
# import system directly, bypassing Temporal's default import handling.
with workflow.unsafe.imports_passed_through():
    from apps.scraper.activities import ScrapeActivities
    from apps.core.config import get_settings


@workflow.defn
class ScrapeWorkflow:
    """
    Temporal workflow for orchestrating pure execution web scraping tasks.

    This workflow embodies the "Agent-Tool" architectural principle:
    - The external Agent provides all intelligence (URLs, selectors, options).
    - The ScrapeWorkflow executes the mechanical web operations reliably.
    - It returns the raw processed results and artifacts for the Agent to interpret.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the web scraping workflow based on parameters provided by an external agent.

        Args:
            params: A dictionary containing the scraping job configuration:
                - `job_id` (str): Unique identifier for the scraping job.
                - `urls` (List[str]): A list of URLs to scrape.
                - `selectors` (Dict): Agent-provided CSS/XPath selectors for data extraction.
                - `options` (Dict): Configuration for the scraping engine (e.g., 'engine', 'timeout', 'scroll', 'ocr', 'transcribe').
                - `tenant_id` (str): Identifier of the tenant initiating the job.

        Returns:
            A dictionary summarizing the scraping results, including job status,
            fetched page counts, processed bytes, artifact references, and any errors encountered.
        """
        job_id = params.get("job_id")
        urls = params.get("urls", [])
        selectors = params.get("selectors")  # These selectors are agent-provided.
        options = params.get("options", {})
        tenant_id = params.get("tenant_id", "default")
        settings = get_settings()

        if not urls:
            raise workflow.ApplicationError(
                "List of URLs is required for scraping.", non_retryable=True
            )

        # Initialize tracking variables for the workflow's progress and results.
        pages_fetched = 0
        bytes_processed = 0
        artifacts = []
        errors = []

        # Iterate through each URL to be scraped, processing them sequentially within the workflow.
        for url in urls:
            try:
                # 1. Fetch Page Activity: Retrieves the content of the specified URL.
                fetch_result = await workflow.execute_activity(
                    ScrapeActivities.fetch_page,
                    {
                        "url": url,
                        "engine": options.get(
                            "engine", "playwright"
                        ),  # e.g., 'playwright', 'httpx'.
                        "wait_for": options.get("wait_for"),
                        "scroll": options.get("scroll", False),
                        "timeout": options.get("timeout", 30),
                    },
                    start_to_close_timeout=timedelta(minutes=5),
                )

                pages_fetched += 1
                html = fetch_result.get("html", "")
                bytes_processed += len(html)

                # 2. Extract Data Activity: Parses the fetched HTML using agent-provided selectors.
                extract_result: Dict[str, Any]
                if selectors:
                    extract_result = await workflow.execute_activity(
                        ScrapeActivities.extract_data,
                        {
                            "html": html,
                            "selectors": selectors,
                            "url": url,
                        },
                        start_to_close_timeout=timedelta(minutes=1),
                    )
                else:
                    # If no selectors are provided, return the raw HTML for the agent to process directly.
                    extract_result = {
                        "raw_html": html,
                        "url": url,
                        "fetched_at": fetch_result.get("fetched_at"),
                    }

                # 3. Process OCR Activity (Optional): If OCR is enabled and images are found.
                if options.get("ocr") and extract_result.get("images"):
                    ocr_result = await workflow.execute_activity(
                        ScrapeActivities.process_ocr,
                        {
                            "images": extract_result.get("images", []),
                            "language": options.get("ocr_language", "spa+eng"),
                        },
                        start_to_close_timeout=timedelta(minutes=5),
                    )
                    extract_result["ocr_text"] = ocr_result.get("text", "")

                # 4. Transcribe Media Activity (Optional): If transcription is enabled and media URLs are found.
                if (
                    settings.scraper_enable_transcribe
                    and options.get("transcribe")
                    and extract_result.get("media_urls")
                ):
                    media_result = await workflow.execute_activity(
                        ScrapeActivities.transcribe_media,
                        {
                            "media_urls": extract_result.get("media_urls", []),
                            "language": options.get("media_language", "es"),
                        },
                        start_to_close_timeout=timedelta(minutes=10),
                    )
                    extract_result["transcriptions"] = media_result.get(
                        "transcriptions", []
                    )

                # 5. Store Artifact Activity: Persists the processed data/artifacts.
                artifact = await workflow.execute_activity(
                    ScrapeActivities.store_artifact,
                    {
                        "job_id": job_id,
                        "tenant_id": tenant_id,
                        "url": url,
                        "data": extract_result,
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                )
                artifacts.append(artifact)

            except Exception as e:
                # Log and collect errors for individual URLs, allowing the workflow to continue for other URLs.
                errors.append({"url": url, "error": str(e)})

        # 6. Finalize Job Activity: Updates the overall job status in the database.
        await workflow.execute_activity(
            ScrapeActivities.finalize_job,
            {
                "job_id": job_id,
                "pages_fetched": pages_fetched,
                "bytes_processed": bytes_processed,
                "artifact_count": len(artifacts),
                "error_count": len(errors),
            },
            start_to_close_timeout=timedelta(minutes=1),
        )

        # Return a summary of the scraping job for the agent to interpret.
        return {
            "job_id": job_id,
            "pages_fetched": pages_fetched,
            "bytes_processed": bytes_processed,
            "artifacts": artifacts,
            "errors": errors,
        }
