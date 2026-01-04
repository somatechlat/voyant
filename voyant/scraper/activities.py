"""
Voyant Scraper - Temporal Activities

Pure execution activities for web scraping.
VIBE Standard v3 Compliant - NO LLM integration.

Agent-Tool Architecture:
- Agent provides selectors and parameters
- Activities execute mechanical operations
- Return raw results to agent
"""

from datetime import datetime
from typing import Any, Dict, List
from temporalio import activity

import logging

logger = logging.getLogger(__name__)


class ScrapeActivities:
    """
    Pure execution scrape activities.

    Each activity performs a single mechanical operation.
    NO intelligence, NO LLM, NO decision making.
    """

    @activity.defn(name="fetch_page")
    async def fetch_page(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch a web page using a specified engine (Playwright, httpx, or Scrapy).
        This activity is a mechanical executor and includes SSRF protection.
        Args:
            params: A dictionary containing fetch parameters:
                - url (str): The URL to fetch.
                - engine (str): The fetch engine to use ('playwright', 'httpx', 'scrapy').
                                Defaults to 'playwright'.
                - wait_for (str, optional): A CSS selector to wait for before returning content.
                - scroll (bool): Whether to scroll to the bottom of the page.
                - timeout (int): Request timeout in seconds.
        Returns:
            A dictionary with the page's HTML, final URL, status code, and fetch time.
        Raises:
            activity.ApplicationError: If the URL is blocked by SSRF protection or if
                                       the fetch operation fails.
        """
        from voyant.scraper.security import validate_url, SSRFError

        url = params.get("url")
        engine = params.get("engine", "playwright")
        wait_for = params.get("wait_for")
        scroll = params.get("scroll", False)
        timeout = params.get("timeout", 30)

        # SSRF Protection (Zero-Bypass)
        try:
            validate_url(url)
        except SSRFError as e:
            raise activity.ApplicationError(f"SSRF blocked: {e}", non_retryable=True)

        activity.heartbeat(f"Fetching {url} with {engine}")

        try:
            if engine == "playwright":
                result = await self._fetch_playwright(url, wait_for, scroll, timeout)
            elif engine == "httpx":
                result = await self._fetch_httpx(url, timeout)
            elif engine == "scrapy":
                result = await self._fetch_scrapy(url, timeout)
            else:
                # Default to httpx for unknown engines
                result = await self._fetch_httpx(url, timeout)

            return result

        except Exception as e:
            logger.error(f"Fetch failed for {url}: {e}")
            raise activity.ApplicationError(
                f"Fetch failed: {e}", non_retryable=False  # May retry
            )

    async def _fetch_playwright(
        self, url: str, wait_for: str = None, scroll: bool = False, timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Fetch a URL using Playwright to support JavaScript rendering.
        Args:
            url: The URL to fetch.
            wait_for: A CSS selector to wait for.
            scroll: Whether to scroll to the bottom of the page.
            timeout: Request timeout in seconds.
        Returns:
            A dictionary containing the page's HTML and metadata.
        """
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                locale="es-EC",
            )
            page = await context.new_page()

            response = await page.goto(
                url, wait_until="networkidle", timeout=timeout * 1000
            )

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=timeout * 1000)

            if scroll:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(1000)

            html = await page.content()

            await browser.close()

            return {
                "html": html,
                "url": url,
                "status_code": response.status if response else 0,
                "fetched_at": datetime.utcnow().isoformat(),
            }

    async def _fetch_httpx(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Fetch a URL using httpx for fast, static HTML retrieval.
        Args:
            url: The URL to fetch.
            timeout: Request timeout in seconds.
        Returns:
            A dictionary containing the page's HTML and metadata.
        """
        import httpx

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; VoyantBot/1.0)",
                    "Accept-Language": "es-EC,es;q=0.9,en;q=0.8",
                },
            )

            return {
                "html": response.text,
                "url": str(response.url),
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "fetched_at": datetime.utcnow().isoformat(),
            }

    async def _fetch_scrapy(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Fetch a URL using Scrapy patterns. Currently falls back to httpx.
        Args:
            url: The URL to fetch.
            timeout: Request timeout in seconds.
        Returns:
            A dictionary containing the page's HTML and metadata.
        """
        # For now, fallback to httpx until Scrapy integration is complete
        return await self._fetch_httpx(url, timeout)

    @activity.defn(name="extract_data")
    async def extract_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from HTML using CSS selectors or XPath.
        This is a mechanical activity that executes selectors provided by an agent.
        Args:
            params: A dictionary containing extraction parameters:
                - html (str): The raw HTML content to parse.
                - selectors (dict): A mapping of field names to selectors.
                - url (str): The source URL for context.
        Returns:
            A dictionary containing the extracted data, along with image and media URLs.
        """
        html = params.get("html", "")
        selectors = params.get("selectors", {})
        url = params.get("url", "")

        activity.heartbeat(f"Extracting from {url}")

        from lxml import html as lxml_html

        try:
            tree = lxml_html.fromstring(html)
        except Exception as e:
            logger.error(f"HTML parse error: {e}")
            return {"error": f"Parse failed: {e}", "url": url}

        result = {"url": url, "extracted_at": datetime.utcnow().isoformat()}

        for field, selector in selectors.items():
            try:
                if isinstance(selector, str):
                    result[field] = self._extract_single(tree, selector)
                elif isinstance(selector, dict):
                    result[field] = self._extract_nested(tree, selector)
            except Exception as e:
                result[field] = None
                logger.warning(f"Selector {field} failed: {e}")

        # Also extract images and media for optional OCR/transcription
        result["images"] = tree.xpath("//img/@src")
        result["media_urls"] = tree.xpath("//video/source/@src | //audio/source/@src")

        return result

    def _extract_single(self, tree, selector: str):
        """
        Extract a list of values from an lxml tree using a single selector.
        Supports XPath, CSS selectors, and attribute/text extraction.
        Args:
            tree: The lxml HTML tree to parse.
            selector: The CSS selector or XPath to use.
        Returns:
            A list of extracted strings.
        """
        if selector.startswith("//"):
            # XPath
            return tree.xpath(selector)
        elif "::" in selector:
            # CSS pseudo-element
            parts = selector.split("::")
            css = parts[0]
            pseudo = parts[1] if len(parts) > 1 else "text"

            from lxml.cssselect import CSSSelector

            sel = CSSSelector(css)
            elements = sel(tree)

            if pseudo == "text":
                return [
                    el.text_content().strip() for el in elements if el.text_content()
                ]
            elif pseudo.startswith("attr("):
                attr = pseudo[5:-1]
                return [el.get(attr) for el in elements if el.get(attr)]
            else:
                return [el.text_content().strip() for el in elements]
        else:
            # Plain CSS
            from lxml.cssselect import CSSSelector

            sel = CSSSelector(selector)
            elements = sel(tree)
            return [el.text_content().strip() for el in elements if el.text_content()]

    def _extract_nested(self, tree, selector_config: dict):
        """
        Extract structured data from a list of elements.
        Each element in the root selector is treated as a row.
        Args:
            tree: The lxml HTML tree to parse.
            selector_config: A dictionary defining the structure:
                - root (str): The selector for the container elements.
                - fields (dict): A mapping of field names to selectors for sub-elements.
        Returns:
            A list of dictionaries, where each dictionary represents a row.
        """
        root_selector = selector_config.get("root", "")
        fields = selector_config.get("fields", {})

        if root_selector.startswith("//"):
            items = tree.xpath(root_selector)
        else:
            from lxml.cssselect import CSSSelector

            sel = CSSSelector(root_selector)
            items = sel(tree)

        results = []
        for item in items:
            row = {}
            for field, selector in fields.items():
                try:
                    values = self._extract_single(item, selector)
                    row[field] = values[0] if values else None
                except Exception:
                    row[field] = None
            results.append(row)

        return results

    @activity.defn(name="process_ocr")
    async def process_ocr(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a list of images with OCR (Tesseract) to extract text.
        This is a mechanical activity for text extraction.
        Args:
            params: A dictionary containing OCR parameters:
                - images (list): A list of image URLs or local file paths.
                - language (str): The language pack to use for OCR (e.g., 'eng', 'spa').
                                  Defaults to 'spa+eng'.
        Returns:
            A dictionary containing the combined extracted text and individual results.
        """
        images = params.get("images", [])
        language = params.get("language", "spa+eng")

        activity.heartbeat(f"OCR processing {len(images)} images")

        results = []
        combined_text = []

        for image_url in images[:10]:  # Limit to 10 images
            try:
                # Download image if URL
                if image_url.startswith(("http://", "https://")):
                    import httpx

                    async with httpx.AsyncClient() as client:
                        resp = await client.get(image_url)
                        image_data = resp.content
                else:
                    with open(image_url, "rb") as f:
                        image_data = f.read()

                # OCR with Tesseract
                import pytesseract
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(image_data))
                text = pytesseract.image_to_string(img, lang=language)

                if text.strip():
                    results.append({"source": image_url, "text": text.strip()})
                    combined_text.append(text.strip())

            except Exception as e:
                logger.warning(f"OCR failed for {image_url}: {e}")
                results.append({"source": image_url, "error": str(e)})

        return {
            "text": "\n\n".join(combined_text),
            "results": results,
            "processed": len(results),
        }

    @activity.defn(name="transcribe_media")
    async def transcribe_media(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transcribe audio or video files using Whisper.
        This is a mechanical activity for speech-to-text conversion.
        Args:
            params: A dictionary containing transcription parameters:
                - media_urls (list): A list of media file URLs.
                - language (str): The language of the media. Defaults to 'es'.
        Returns:
            A dictionary containing a list of transcription results.
        """
        media_urls = params.get("media_urls", [])
        language = params.get("language", "es")

        activity.heartbeat(f"Transcribing {len(media_urls)} media files")

        transcriptions = []

        for media_url in media_urls[:5]:  # Limit to 5 files
            try:
                # Download media
                import httpx
                import tempfile

                async with httpx.AsyncClient() as client:
                    resp = await client.get(media_url)

                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                        f.write(resp.content)
                        temp_path = f.name

                # Transcribe with Whisper
                import whisper

                model = whisper.load_model("base")
                result = model.transcribe(temp_path, language=language)

                transcriptions.append(
                    {
                        "source": media_url,
                        "text": result["text"],
                        "segments": result.get("segments", []),
                    }
                )

                # Cleanup
                import os

                os.unlink(temp_path)

            except Exception as e:
                logger.warning(f"Transcription failed for {media_url}: {e}")
                transcriptions.append({"source": media_url, "error": str(e)})

        return {
            "transcriptions": transcriptions,
            "processed": len(transcriptions),
        }

    @activity.defn(name="parse_pdf")
    async def parse_pdf(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a PDF document to extract text, metadata, and tables.
        Uses Apache Tika for text/metadata and pdfplumber for tables.
        Args:
            params: A dictionary containing PDF parsing parameters:
                - pdf_url (str): The URL or local path of the PDF file.
                - extract_tables (bool): Whether to extract tables using pdfplumber.
        Returns:
            A dictionary with the extracted text, metadata, and optional table data.
        """
        pdf_url = params.get("pdf_url", "")
        extract_tables = params.get("extract_tables", False)

        activity.heartbeat(f"Parsing PDF: {pdf_url}")

        try:
            # Download PDF if URL
            if pdf_url.startswith(("http://", "https://")):
                from voyant.scraper.security import validate_url

                validate_url(pdf_url)

                import httpx
                import tempfile

                async with httpx.AsyncClient() as client:
                    resp = await client.get(pdf_url)

                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                        f.write(resp.content)
                        pdf_path = f.name
            else:
                pdf_path = pdf_url

            # Parse with Tika
            from tika import parser as tika_parser

            parsed = tika_parser.from_file(pdf_path)

            result = {
                "text": parsed.get("content", "").strip(),
                "metadata": parsed.get("metadata", {}),
            }

            # Extract tables with pdfplumber
            if extract_tables:
                import pdfplumber

                tables = []
                with pdfplumber.open(pdf_path) as pdf:
                    for i, page in enumerate(pdf.pages):
                        for table in page.extract_tables():
                            tables.append({"page": i + 1, "data": table})
                result["tables"] = tables

            return result

        except Exception as e:
            logger.error(f"PDF parse failed: {e}")
            return {"error": str(e), "source": pdf_url}

    @activity.defn(name="store_artifact")
    async def store_artifact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store extracted data as a JSON artifact in an object store.
        This activity is a placeholder for integration with a full artifact store.
        Args:
            params: A dictionary containing artifact parameters:
                - job_id (str): The ID of the parent job.
                - tenant_id (str): The tenant ID for partitioning.
                - url (str): The original source URL of the data.
                - data (dict): The extracted data to be stored.
        Returns:
            A dictionary containing a reference to the stored artifact.
        """
        import json
        import hashlib

        job_id = params.get("job_id")
        tenant_id = params.get("tenant_id", "default")
        url = params.get("url", "")
        data = params.get("data", {})

        activity.heartbeat(f"Storing artifact for {url}")

        # Serialize data
        content = json.dumps(data, ensure_ascii=False, indent=2)
        content_bytes = content.encode("utf-8")

        # Content-addressable hash
        content_hash = hashlib.sha256(content_bytes).hexdigest()

        # Storage path
        artifact_id = f"scrape-{job_id}-{content_hash[:12]}"
        storage_path = f"s3://voyant-artifacts/{tenant_id}/scrape/{artifact_id}.json"

        # TODO: Integrate with voyant.core.artifact_store
        # For now, just record metadata

        return {
            "artifact_id": artifact_id,
            "storage_path": storage_path,
            "content_hash": content_hash,
            "size_bytes": len(content_bytes),
            "url": url,
        }

    @activity.defn(name="finalize_job")
    async def finalize_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finalize a scrape job by updating its status and recording final metrics.
        This is a placeholder for updating the job's status in a database.
        Args:
            params: A dictionary containing final job metrics:
                - job_id (str): The ID of the job to finalize.
                - pages_fetched (int): Total number of pages successfully fetched.
                - bytes_processed (int): Total bytes processed.
                - artifact_count (int): Total number of artifacts created.
                - error_count (int): Total number of errors encountered.
        Returns:
            A summary dictionary of the finalized job status.
        """
        job_id = params.get("job_id")
        pages_fetched = params.get("pages_fetched", 0)
        bytes_processed = params.get("bytes_processed", 0)
        artifact_count = params.get("artifact_count", 0)
        error_count = params.get("error_count", 0)

        activity.heartbeat(f"Finalizing job {job_id}")

        # TODO: Update Django model
        # ScrapeJob.objects.filter(job_id=job_id).update(
        #     status='succeeded' if error_count == 0 else 'partial',
        #     pages_fetched=pages_fetched,
        #     bytes_processed=bytes_processed,
        #     finished_at=datetime.utcnow(),
        # )

        return {
            "job_id": job_id,
            "status": "succeeded" if error_count == 0 else "partial",
            "pages_fetched": pages_fetched,
            "bytes_processed": bytes_processed,
            "artifact_count": artifact_count,
            "error_count": error_count,
            "finished_at": datetime.utcnow().isoformat(),
        }
