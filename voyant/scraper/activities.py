"""
Voyant Scraper - Temporal Activities

Activity implementations for scrape workflow.
Following Voyant's established activity patterns.
"""
from datetime import datetime
from typing import Any, Dict, List
from temporalio import activity

import logging

logger = logging.getLogger(__name__)


class ScrapeActivities:
    """
    Scrape workflow activities.
    
    Each method is an activity that can be executed by the Temporal worker.
    """
    
    @activity.defn
    async def fetch_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch a web page using the specified engine.
        
        Params:
            url: str - URL to fetch
            engine: str - playwright, selenium, scrapy, beautifulsoup
            actions: list - Optional browser actions
        """
        url = params.get("url")
        engine = params.get("engine", "playwright")
        actions = params.get("actions", [])
        
        logger.info(f"Fetching {url} with {engine}")
        
        if engine == "playwright":
            from voyant.scraper.browser.playwright_client import PlaywrightClient
            client = PlaywrightClient()
            if actions:
                html = await client.fetch_with_actions(url, actions)
            else:
                html = await client.fetch_async(url)
        elif engine == "selenium":
            from voyant.scraper.browser.selenium_client import SeleniumClient
            client = SeleniumClient()
            if actions:
                html = client.fetch_with_actions(url, actions)
            else:
                html = client.fetch(url)
        elif engine == "scrapy":
            from voyant.scraper.browser.scrapy_client import ScrapyClient
            client = ScrapyClient()
            html = client.fetch(url)
        else:
            from voyant.scraper.browser.beautifulsoup_client import BeautifulSoupClient
            client = BeautifulSoupClient()
            html = client.fetch(url)
        
        return {
            "url": url,
            "html": html,
            "fetched_at": datetime.utcnow().isoformat(),
        }
    
    @activity.defn
    async def extract_with_llm(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data using LLM-generated selectors.
        
        Params:
            html: str - Page HTML
            llm_prompt: str - What to extract
            url: str - Source URL
        """
        html = params.get("html", "")
        llm_prompt = params.get("llm_prompt", "")
        url = params.get("url", "")
        
        logger.info(f"Extracting from {url} with LLM: {llm_prompt[:50]}...")
        
        from voyant.scraper.extraction.llm_selectors import LLMSelectorGenerator, SelectorEngine
        
        generator = LLMSelectorGenerator()
        selectors = await generator.generate_selectors(html, llm_prompt)
        
        # Apply selectors
        extracted = SelectorEngine.apply_selectors(
            html, 
            selectors.get("selectors", [])
        )
        
        # Find images and media
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'lxml')
        images = [img.get('src') for img in soup.find_all('img') if img.get('src')]
        media_urls = [
            v.get('src') for v in soup.find_all(['video', 'audio']) if v.get('src')
        ]
        
        return {
            "url": url,
            "extracted_data": extracted,
            "selectors_used": selectors,
            "images": images[:10],  # Limit
            "media_urls": media_urls[:5],
        }
    
    @activity.defn
    async def extract_basic(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract data using provided CSS/XPath selectors.
        
        Params:
            html: str - Page HTML
            selectors: list - Selector definitions
            url: str - Source URL
        """
        html = params.get("html", "")
        selectors = params.get("selectors", [])
        url = params.get("url", "")
        
        logger.info(f"Basic extraction from {url}")
        
        from voyant.scraper.extraction.llm_selectors import SelectorEngine
        from bs4 import BeautifulSoup
        
        extracted = {}
        if selectors:
            extracted = SelectorEngine.apply_selectors(html, selectors)
        else:
            # Default: extract title and text
            soup = BeautifulSoup(html, 'lxml')
            extracted = {
                "title": soup.title.string if soup.title else "",
                "text": soup.get_text(separator="\n", strip=True)[:5000],
            }
        
        return {
            "url": url,
            "extracted_data": extracted,
            "images": [],
            "media_urls": [],
        }
    
    @activity.defn
    async def process_ocr(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process images with OCR.
        
        Params:
            images: list - Image URLs or paths
        """
        images = params.get("images", [])
        
        logger.info(f"Processing OCR for {len(images)} images")
        
        from voyant.scraper.media.ocr import OCRProcessor
        import httpx
        
        processor = OCRProcessor()
        all_text = []
        
        for image_url in images:
            try:
                # Download image
                async with httpx.AsyncClient() as client:
                    response = await client.get(image_url, timeout=30)
                    image_bytes = response.content
                
                result = processor.process_image_bytes(image_bytes)
                all_text.append(result.get("text", ""))
            except Exception as e:
                logger.warning(f"OCR failed for {image_url}: {e}")
        
        return {
            "text": "\n\n".join(all_text),
            "image_count": len(images),
            "processed_count": len(all_text),
        }
    
    @activity.defn
    async def process_media(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process audio/video with transcription.
        
        Params:
            media_urls: list - Media URLs
        """
        media_urls = params.get("media_urls", [])
        
        logger.info(f"Processing transcription for {len(media_urls)} media files")
        
        from voyant.scraper.media.transcription import TranscriptionProcessor
        import httpx
        import tempfile
        import os
        
        processor = TranscriptionProcessor()
        transcriptions = []
        
        for media_url in media_urls:
            try:
                # Download media
                async with httpx.AsyncClient() as client:
                    response = await client.get(media_url, timeout=120)
                    media_bytes = response.content
                
                # Determine format
                format = "mp4" if "video" in response.headers.get("content-type", "") else "mp3"
                is_video = "video" in response.headers.get("content-type", "")
                
                result = processor.transcribe_bytes(media_bytes, format, is_video)
                transcriptions.append({
                    "url": media_url,
                    "text": result.get("text", ""),
                })
            except Exception as e:
                logger.warning(f"Transcription failed for {media_url}: {e}")
        
        return {
            "transcriptions": transcriptions,
            "media_count": len(media_urls),
        }
    
    @activity.defn
    async def store_artifact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store extracted data as artifact in MinIO.
        
        Params:
            job_id: str
            tenant_id: str
            url: str
            data: dict
        """
        import json
        import uuid
        
        job_id = params.get("job_id")
        tenant_id = params.get("tenant_id")
        url = params.get("url")
        data = params.get("data", {})
        
        logger.info(f"Storing artifact for {url}")
        
        # Generate artifact ID
        artifact_id = f"{job_id}/{uuid.uuid4()}.json"
        
        # Store in MinIO
        from voyant.core.artifact_store import get_artifact_store
        
        store = get_artifact_store()
        json_data = json.dumps(data, indent=2)
        
        store.put_object(
            bucket="voyant-artifacts",
            key=artifact_id,
            data=json_data.encode(),
            content_type="application/json"
        )
        
        # Create artifact record
        from voyant.scraper.models import ScrapeArtifact, ScrapeJob
        
        artifact = ScrapeArtifact.objects.create(
            artifact_id=artifact_id,
            job_id=job_id,
            artifact_type="json",
            format="json",
            storage_path=f"s3://voyant-artifacts/{artifact_id}",
            size_bytes=len(json_data),
        )
        
        return {
            "artifact_id": artifact_id,
            "size_bytes": len(json_data),
            "storage_path": artifact.storage_path,
        }
    
    @activity.defn
    async def finalize_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update job status to completed.
        
        Params:
            job_id: str
            pages_fetched: int
            bytes_processed: int
            artifact_count: int
            error_count: int
        """
        from django.utils import timezone
        from voyant.scraper.models import ScrapeJob
        
        job_id = params.get("job_id")
        
        logger.info(f"Finalizing job {job_id}")
        
        job = ScrapeJob.objects.get(job_id=job_id)
        job.status = ScrapeJob.Status.SUCCEEDED if params.get("error_count", 0) == 0 else ScrapeJob.Status.FAILED
        job.pages_fetched = params.get("pages_fetched", 0)
        job.bytes_processed = params.get("bytes_processed", 0)
        job.finished_at = timezone.now()
        job.save()
        
        return {
            "job_id": job_id,
            "status": job.status,
        }
