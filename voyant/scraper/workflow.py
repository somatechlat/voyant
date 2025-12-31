"""
Voyant Scraper - Temporal Workflow

Scrape workflow using Temporal for durable execution.
Following Voyant's established workflow patterns.
"""
from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from voyant.scraper.activities import ScrapeActivities


@workflow.defn
class ScrapeWorkflow:
    """
    Web scraping workflow.
    
    Orchestrates: Fetch → Extract → Process Media → Store Artifacts
    """
    
    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run web scraping workflow.
        
        Params:
            job_id: str - Job UUID
            urls: list[str] - URLs to scrape
            llm_prompt: str - Optional LLM extraction hints
            options: dict - Scraping options (engine, ocr, media, etc.)
            tenant_id: str - Tenant identifier
        """
        job_id = params.get("job_id")
        urls = params.get("urls", [])
        llm_prompt = params.get("llm_prompt", "")
        options = params.get("options", {})
        tenant_id = params.get("tenant_id", "default")
        
        if not urls:
            raise workflow.ApplicationError("urls is required")
        
        # Track results
        pages_fetched = 0
        bytes_processed = 0
        artifacts = []
        errors = []
        
        # 1. Fetch pages
        for url in urls:
            try:
                fetch_result = await workflow.execute_activity(
                    ScrapeActivities.fetch_page,
                    {
                        "url": url,
                        "engine": options.get("engine", "playwright"),
                        "actions": options.get("actions", []),
                    },
                    start_to_close_timeout=timedelta(minutes=5),
                )
                
                pages_fetched += 1
                bytes_processed += len(fetch_result.get("html", ""))
                
                # 2. Extract data (with LLM selectors if provided)
                if llm_prompt:
                    extract_result = await workflow.execute_activity(
                        ScrapeActivities.extract_with_llm,
                        {
                            "html": fetch_result.get("html", ""),
                            "llm_prompt": llm_prompt,
                            "url": url,
                        },
                        start_to_close_timeout=timedelta(minutes=2),
                    )
                else:
                    extract_result = await workflow.execute_activity(
                        ScrapeActivities.extract_basic,
                        {
                            "html": fetch_result.get("html", ""),
                            "selectors": options.get("selectors", []),
                            "url": url,
                        },
                        start_to_close_timeout=timedelta(minutes=1),
                    )
                
                # 3. Process media if enabled
                if options.get("ocr") and extract_result.get("images"):
                    ocr_result = await workflow.execute_activity(
                        ScrapeActivities.process_ocr,
                        {
                            "images": extract_result.get("images", []),
                        },
                        start_to_close_timeout=timedelta(minutes=5),
                    )
                    extract_result["ocr_text"] = ocr_result.get("text", "")
                
                if options.get("media") and extract_result.get("media_urls"):
                    media_result = await workflow.execute_activity(
                        ScrapeActivities.process_media,
                        {
                            "media_urls": extract_result.get("media_urls", []),
                        },
                        start_to_close_timeout=timedelta(minutes=10),
                    )
                    extract_result["transcriptions"] = media_result.get("transcriptions", [])
                
                # 4. Store artifact
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
                errors.append({"url": url, "error": str(e)})
        
        # 5. Update job status
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
        
        return {
            "job_id": job_id,
            "pages_fetched": pages_fetched,
            "bytes_processed": bytes_processed,
            "artifacts": artifacts,
            "errors": errors,
        }
