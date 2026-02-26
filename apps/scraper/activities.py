"""
Voyant Scraper - Temporal Activities

Pure execution activities for web scraping.
Production Standard v3 Compliant - NO LLM integration.

Agent-Tool Architecture:
- Agent provides selectors and parameters
- Activities execute mechanical operations
- Return raw results to agent
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict

from temporalio import activity
from temporalio.exceptions import ApplicationError

from apps.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ScrapeActivities:
    """
    Pure execution scrape activities.

    Each activity performs a single mechanical operation.
    NO intelligence, NO LLM, NO decision making.
    """

    @staticmethod
    def _load_models():
        from apps.scraper.models import ScrapeArtifact, ScrapeJob

        return ScrapeJob, ScrapeArtifact

    @staticmethod
    def _heartbeat_safe(message: str) -> None:
        """Emit Temporal heartbeat only when running inside activity context."""
        try:
            activity.heartbeat(message)
        except RuntimeError:
            # REST/MCP direct execution path (not Temporal activity runtime).
            return

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
        from apps.scraper.security import SSRFError, validate_url

        url = params.get("url")
        engine = params.get("engine", settings.scraper_default_engine)
        wait_for = params.get("wait_for")
        scroll = params.get("scroll", False)
        timeout = params.get("timeout", settings.scraper_default_timeout_seconds)
        wait_until = params.get("wait_until") or settings.scraper_playwright_wait_until
        settle_ms = params.get("settle_ms")
        if settle_ms is None:
            settle_ms = settings.scraper_playwright_settle_ms_default
        block_resources = params.get("block_resources")
        if block_resources is None:
            block_resources = settings.scraper_playwright_block_resources_default
        capture_json = params.get(
            "capture_json", settings.scraper_playwright_capture_json_default
        )
        capture_url_contains = params.get("capture_url_contains") or None
        capture_max_bytes = params.get("capture_max_bytes")
        if capture_max_bytes is None:
            capture_max_bytes = settings.scraper_playwright_capture_max_bytes
        capture_max_items = params.get("capture_max_items")
        if capture_max_items is None:
            capture_max_items = settings.scraper_playwright_capture_max_items

        # SSRF Protection (Zero-Bypass)
        try:
            validate_url(url)
        except SSRFError as e:
            raise ApplicationError(f"SSRF blocked: {e}", non_retryable=True)

        self._heartbeat_safe(f"Fetching {url} with {engine}")

        try:
            if engine == "playwright":
                result = await self._fetch_playwright(
                    url,
                    wait_for=wait_for,
                    scroll=scroll,
                    timeout=timeout,
                    wait_until=str(wait_until),
                    settle_ms=int(settle_ms),
                    block_resources=bool(block_resources),
                    capture_json=bool(capture_json),
                    capture_url_contains=capture_url_contains,
                    capture_max_bytes=int(capture_max_bytes),
                    capture_max_items=int(capture_max_items),
                )
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
            raise ApplicationError(
                f"Fetch failed: {e}", non_retryable=False
            )  # May retry

    async def _fetch_playwright(
        self,
        url: str,
        wait_for: str | None = None,
        scroll: bool = False,
        timeout: int = 30,
        wait_until: str = "domcontentloaded",
        settle_ms: int = 0,
        block_resources: bool = True,
        capture_json: bool = False,
        capture_url_contains: list[str] | None = None,
        capture_max_bytes: int = 524288,
        capture_max_items: int = 25,
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
            captured_json: list[dict[str, Any]] = []
            capture_tasks: set[asyncio.Task] = set()
            capturing_enabled = True

            browser = None
            context = None
            page = None
            response = None
            html = ""

            try:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=settings.scraper_playwright_user_agent,
                    locale=settings.scraper_playwright_locale,
                )
                page = await context.new_page()

                if block_resources:

                    async def _route_handler(route, request) -> None:
                        try:
                            if request.resource_type in ("image", "media", "font"):
                                await route.abort()
                            else:
                                await route.continue_()
                        except Exception:
                            try:
                                await route.continue_()
                            except Exception:
                                return

                    await page.route("**/*", _route_handler)

                async def _maybe_capture_response(response) -> None:
                    # Capture only JSON XHR/fetch responses, with strict size limits.
                    try:
                        if not capture_json:
                            return
                        if len(captured_json) >= capture_max_items:
                            return
                        req = response.request
                        if req.resource_type not in ("xhr", "fetch"):
                            return
                        if response.status < 200 or response.status >= 300:
                            return
                        resp_url = str(response.url)
                        if capture_url_contains and not any(
                            s in resp_url for s in capture_url_contains
                        ):
                            return
                        ct = (response.headers or {}).get("content-type", "")
                        if "json" not in (ct or "").lower():
                            return
                        if len(captured_json) >= capture_max_items:
                            return
                        try:
                            body = await response.text()
                        except Exception:
                            return
                        if body is None:
                            return
                        if len(body) > capture_max_bytes:
                            return
                        try:
                            parsed = json.loads(body)
                        except Exception:
                            return
                        captured_json.append(
                            {
                                "url": resp_url,
                                "status": response.status,
                                "content_type": ct,
                                "body": parsed,
                            }
                        )
                    except Exception:
                        return

                if capture_json:

                    def _on_response(response) -> None:
                        # Playwright event handlers are sync; schedule async capture.
                        nonlocal capturing_enabled
                        if not capturing_enabled:
                            return
                        try:
                            task = asyncio.create_task(
                                _maybe_capture_response(response)
                            )
                        except RuntimeError:
                            # No running loop (shutdown); ignore.
                            return
                        capture_tasks.add(task)
                        task.add_done_callback(lambda t: capture_tasks.discard(t))

                    page.on("response", _on_response)

                # Note: "networkidle" can hang indefinitely on pages that keep long-lived
                # connections open (analytics, streaming, etc.). Make this configurable.
                response = await page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=timeout * 1000,
                )

                if wait_for:
                    await page.wait_for_selector(wait_for, timeout=timeout * 1000)

                if scroll:
                    await page.evaluate(
                        "window.scrollTo(0, document.body.scrollHeight)"
                    )
                    await page.wait_for_timeout(1000)

                if settle_ms and settle_ms > 0:
                    await page.wait_for_timeout(settle_ms)

                html = await page.content()
            finally:
                capturing_enabled = False
                if capture_tasks:
                    try:
                        await asyncio.gather(
                            *list(capture_tasks), return_exceptions=True
                        )
                    except Exception:
                        pass
                try:
                    if page is not None:
                        await page.close()
                except Exception:
                    pass
                try:
                    if context is not None:
                        await context.close()
                except Exception:
                    pass
                try:
                    if browser is not None:
                        await browser.close()
                except Exception:
                    pass

            result = {
                "html": html,
                "url": url,
                "status_code": response.status if response else 0,
                "fetched_at": datetime.utcnow().isoformat(),
            }
            if capture_json:
                result["captured_json"] = captured_json
            return result

    @activity.defn(name="deep_archive")
    async def deep_archive(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generic deep archival scrape. Connects to obfuscated SPAs/Tabbed interfaces,
        invokes UI clicks programmatically, and automatically intercepts and downloads
        matching files.
        """
        from playwright.async_api import async_playwright
        import httpx
        from urllib.parse import urljoin
        import os
        from pathlib import Path

        url = params.get("url")
        interaction_selectors = params.get("interaction_selectors", [])
        download_patterns = params.get("download_patterns", [])
        target_dir = params.get("target_dir", "scrapes/unknown")
        wait_settle_ms = params.get("wait_settle_ms", 2000)
        timeout_ms = params.get("timeout_ms", 60000)

        self._heartbeat_safe(f"Deep Archiving: {url}")

        # Security validation
        from apps.scraper.security import validate_url, SSRFError
        try:
            validate_url(url)
        except SSRFError as e:
            raise ApplicationError(f"SSRF blocked: {e}", non_retryable=True)

        out_dir = Path(target_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        files_dir = out_dir / "files"
        files_dir.mkdir(exist_ok=True)

        extracted_data = {
            "source_url": url,
            "target_dir": target_dir,
            "interaction_states": {},
            "files_downloaded": []
        }

        async def download_file(target_url, filename):
            self._heartbeat_safe(f"Downloading {filename}...")
            try:
                # We do NOT verify TLS for deep archival downloads to handle rogue certs universally
                async with httpx.AsyncClient(verify=False, timeout=60.0) as client:
                    resp = await client.get(target_url)
                    if resp.status_code == 200:
                        with open(files_dir / filename, "wb") as f:
                            f.write(resp.content)
                        return True
            except Exception as e:
                logger.error(f"Failed to download {target_url}: {e}")
            return False

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            # Ignore popups natively
            page.on("popup", lambda popup: None)

            try:
                await page.goto(url, wait_until="networkidle", timeout=timeout_ms)

                # Capture baseline DOM
                extracted_data["interaction_states"]["baseline"] = await page.content()

                # Process UI Interactions
                if interaction_selectors:
                    for selector in interaction_selectors:
                        self._heartbeat_safe(f"Clicking selector: {selector}")
                        try:
                            # 10s short timeout for buttons since they might be missing or hidden
                            element = await page.wait_for_selector(selector, timeout=10000)
                            if element:
                                await element.click()
                                await page.wait_for_timeout(wait_settle_ms)
                                # Capture new state
                                extracted_data["interaction_states"][selector] = await page.content()

                        except Exception as e:
                            logger.warning(f"Failed to interact with {selector}: {e}")

                # Find all downloadable files matching patterns in the current DOM state
                # We check the final state of the DOM
                if download_patterns:
                    self._heartbeat_safe(f"Scanning DOM for file downloads...")

                    # Ensure file matching matches anchor href attributes
                    file_links = await page.query_selector_all("a")
                    for link in file_links:
                        href = await link.get_attribute("href")

                        if not href:
                            continue

                        # Standard Link processing
                        matched = any(pattern.lower() in href.lower() for pattern in download_patterns)

                        if matched:
                            full_url = urljoin(page.url, href)
                            safe_name = f"artifact_{len(extracted_data['files_downloaded'])}.download"

                            if "archivo=" in href.lower():
                                safe_name = href.split("=")[-1].split("&")[0][:50]
                            elif href.split("?")[0].endswith(".pdf"):
                                safe_name = f"artifact_{len(extracted_data['files_downloaded'])}.pdf"

                            extracted_data["files_downloaded"].append({
                                "url": full_url,
                                "filename": safe_name
                            })
                            await download_file(full_url, safe_name)

                        # Deep JS embedded links like javascript:abrirDoc('/path/to/doc')
                        elif "javascript" in href.lower() and "'" in href:
                            extracted_path = href.split("'")[1]
                            matched_js = any(pattern.lower() in extracted_path.lower() for pattern in download_patterns)
                            if matched_js:
                                full_url = urljoin(page.url, extracted_path)
                                safe_name = f"js_artifact_{len(extracted_data['files_downloaded'])}.download"
                                if "archivo=" in extracted_path.lower():
                                    safe_name = extracted_path.split("=")[-1].split("&")[0][:50]

                                extracted_data["files_downloaded"].append({
                                    "url": full_url,
                                    "filename": safe_name
                                })
                                await download_file(full_url, safe_name)

            except Exception as e:
                logger.error(f"Deep archive failed during execution: {e}")
                extracted_data["error"] = str(e)
            finally:
                await browser.close()

            # Serialize payload to disk to ensure pure extraction
            json_path = out_dir / "deep_archive_manifest.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2, ensure_ascii=False)

            return extracted_data

    async def _fetch_httpx(self, url: str, timeout: int = 30) -> Dict[str, Any]:
        """
        Fetch a URL using httpx for fast, static HTML retrieval.
        Args:
            url: The URL to fetch.
            timeout: Request timeout in seconds.
        Returns:
            A dictionary containing the page's HTML and metadata.
        """
        import ssl

        import certifi
        import httpx

        if not settings.scraper_tls_verify:
            verify: bool | ssl.SSLContext = False
        elif settings.scraper_tls_trust_store == "certifi":
            # Certifi can lag OS trust stores. Keep it configurable.
            verify = ssl.create_default_context(cafile=certifi.where())
        else:
            # Use the OS trust store; this is the most compatible option in containerized
            # environments where system CAs are managed/updated independently.
            verify = ssl.create_default_context()

        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            verify=verify,
        ) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": settings.scraper_http_user_agent,
                    "Accept-Language": settings.scraper_http_accept_language,
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

        self._heartbeat_safe(f"Extracting from {url}")

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
        language = params.get("language", settings.scraper_default_ocr_language)

        self._heartbeat_safe(f"OCR processing {len(images)} images")

        results = []
        combined_text = []

        for image_url in images[: settings.scraper_max_ocr_images]:
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
                import io

                import pytesseract
                from PIL import Image

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
        language = params.get("language", settings.scraper_default_transcribe_language)

        if not settings.scraper_enable_transcribe:
            return {
                "transcriptions": [
                    {
                        "source": url,
                        "error_code": "TRANSCRIPTION_DISABLED",
                    }
                    for url in media_urls[: settings.scraper_max_transcribe_media]
                ],
                "processed": 0,
            }

        self._heartbeat_safe(f"Transcribing {len(media_urls)} media files")

        transcriptions = []

        for media_url in media_urls[: settings.scraper_max_transcribe_media]:
            try:
                # Download media
                import tempfile

                import httpx

                async with httpx.AsyncClient() as client:
                    resp = await client.get(media_url)

                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                        f.write(resp.content)
                        temp_path = f.name

                # Transcribe with Whisper
                try:
                    import whisper  # type: ignore
                except Exception as exc:
                    raise RuntimeError(
                        "Whisper is not installed in this runtime. "
                        "Enable transcription and include the transcription dependency set."
                    ) from exc

                model = whisper.load_model(settings.scraper_whisper_model_name)
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
                transcriptions.append(
                    {"source": media_url, "error_code": "TRANSCRIPTION_FAILED"}
                )

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

        self._heartbeat_safe(f"Parsing PDF: {pdf_url}")

        try:
            # Download PDF if URL
            if pdf_url.startswith(("http://", "https://")):
                from apps.scraper.security import validate_url

                validate_url(pdf_url)

                import tempfile

                import httpx

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
    def store_artifact(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store extracted data as a JSON artifact in an object store.

        Args:
            params: A dictionary containing artifact parameters:
                - job_id (str): The ID of the parent job.
                - tenant_id (str): The tenant ID for partitioning.
                - url (str): The original source URL of the data.
                - data (dict): The extracted data to be stored.
        Returns:
            A dictionary containing a reference to the stored artifact.
        """
        import hashlib

        from apps.core.lib.artifact_store import store_artifact

        _, ScrapeArtifact = self._load_models()
        job_id = params.get("job_id")
        tenant_id = params.get("tenant_id", settings.default_tenant_id)
        url = params.get("url", "")
        data = params.get("data", {})

        self._heartbeat_safe(f"Storing artifact for {url}")

        ref = store_artifact(
            content=data,
            artifact_type="scrape_json",
            metadata={"job_id": job_id, "tenant_id": tenant_id, "source_url": url},
        )
        content_hash = hashlib.sha256(str(ref.hash).encode("utf-8")).hexdigest()
        artifact_id = f"scrape-{job_id}-{content_hash[:12]}"
        storage_path = ref.hash

        ScrapeArtifact.objects.update_or_create(
            artifact_id=artifact_id,
            defaults={
                "job_id": job_id,
                "artifact_type": ScrapeArtifact.ArtifactType.JSON,
                "format": "json",
                "storage_path": storage_path,
                "content_hash": ref.hash,
                "size_bytes": ref.size_bytes,
                "source_url": url,
                "metadata": {"artifact_ref": ref.to_dict()},
            },
        )

        return {
            "artifact_id": artifact_id,
            "storage_path": storage_path,
            "content_hash": ref.hash,
            "size_bytes": ref.size_bytes,
            "url": url,
        }

    @activity.defn(name="finalize_job")
    def finalize_job(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Finalize a scrape job by updating its status and recording final metrics.
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

        self._heartbeat_safe(f"Finalizing job {job_id}")
        status = "succeeded" if error_count == 0 else "partial"
        ScrapeJob, _ = self._load_models()
        ScrapeJob.objects.filter(job_id=job_id).update(
            status=status,
            pages_fetched=pages_fetched,
            bytes_processed=bytes_processed,
            artifact_count=artifact_count,
            error_count=error_count,
            finished_at=datetime.utcnow(),
        )

        return {
            "job_id": job_id,
            "status": status,
            "pages_fetched": pages_fetched,
            "bytes_processed": bytes_processed,
            "artifact_count": artifact_count,
            "error_count": error_count,
            "finished_at": datetime.utcnow().isoformat(),
        }
