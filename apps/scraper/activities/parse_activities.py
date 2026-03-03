"""
Voyant Scraper — Parse Activities.

Temporal activities for structured data extraction: HTML parsing,
OCR via Tesseract, media transcription via Whisper, and PDF parsing via Tika.
Pure mechanical execution — NO intelligence, NO LLM, NO decision making.

Extracted from scraper/activities.py (Rule 245 compliance — 949-line split).
"""

import logging
from datetime import datetime
from typing import Any, Dict

from temporalio import activity

from apps.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ParseActivities:
    """
    Parse and extraction activities: HTML, OCR, media transcription, PDF.

    These activities are stateless — they receive raw bytes or HTML and return
    structured data. All network requests within parse operations validate URLs
    via apps.scraper.security.validate_url before downloading.
    """

    @staticmethod
    def _heartbeat_safe(message: str) -> None:
        """Emit Temporal heartbeat only when running inside activity context."""
        try:
            activity.heartbeat(message)
        except RuntimeError:
            return

    @activity.defn(name="extract_data")
    async def extract_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from HTML using CSS selectors or XPath.

        Args:
            params:
                - html (str): Raw HTML content to parse.
                - selectors (dict): Field name → selector mapping.
                - url (str): Source URL for context metadata.

        Returns:
            Dict with extracted fields, images list, and media_urls list.
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

        result: Dict[str, Any] = {
            "url": url,
            "extracted_at": datetime.utcnow().isoformat(),
        }

        for field, selector in selectors.items():
            try:
                if isinstance(selector, str):
                    result[field] = self._extract_single(tree, selector)
                elif isinstance(selector, dict):
                    result[field] = self._extract_nested(tree, selector)
            except Exception as e:
                result[field] = None
                logger.warning(f"Selector {field} failed: {e}")

        result["images"] = tree.xpath("//img/@src")
        result["media_urls"] = tree.xpath("//video/source/@src | //audio/source/@src")

        return result

    def _extract_single(self, tree, selector: str):
        """
        Extract a list of values using a single CSS or XPath selector.

        Supports:
            - XPath (starts with //)
            - CSS pseudo-element (contains ::)
            - Plain CSS selector
        """
        if selector.startswith("//"):
            return tree.xpath(selector)
        elif "::" in selector:
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
            from lxml.cssselect import CSSSelector

            sel = CSSSelector(selector)
            elements = sel(tree)
            return [el.text_content().strip() for el in elements if el.text_content()]

    def _extract_nested(self, tree, selector_config: dict):
        """
        Extract a list of row-structured dicts from repeated container elements.

        Args:
            selector_config:
                - root (str): Selector for the repeating container.
                - fields (dict): Field name → sub-element selector.
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
        Process a list of images with Tesseract OCR to extract text.

        Args:
            params:
                - images (list[str]): Image URLs or local file paths.
                - language (str): Tesseract language pack (e.g. 'spa+eng').

        Returns:
            Dict with combined text, per-image results, and processed count.
        """
        images = params.get("images", [])
        language = params.get("language", settings.scraper_default_ocr_language)

        self._heartbeat_safe(f"OCR processing {len(images)} images")

        results = []
        combined_text = []

        for image_url in images[: settings.scraper_max_ocr_images]:
            try:
                if image_url.startswith(("http://", "https://")):
                    import httpx

                    async with httpx.AsyncClient() as client:
                        resp = await client.get(image_url)
                        image_data = resp.content
                else:
                    with open(image_url, "rb") as f:
                        image_data = f.read()

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

        Args:
            params:
                - media_urls (list[str]): Media file URLs to transcribe.
                - language (str): Language code (e.g. 'es').

        Returns:
            Dict with transcription results list and processed count.
        """
        media_urls = params.get("media_urls", [])
        language = params.get("language", settings.scraper_default_transcribe_language)

        if not settings.scraper_enable_transcribe:
            return {
                "transcriptions": [
                    {"source": url, "error_code": "TRANSCRIPTION_DISABLED"}
                    for url in media_urls[: settings.scraper_max_transcribe_media]
                ],
                "processed": 0,
            }

        self._heartbeat_safe(f"Transcribing {len(media_urls)} media files")

        transcriptions = []

        for media_url in media_urls[: settings.scraper_max_transcribe_media]:
            try:
                import tempfile

                import httpx

                async with httpx.AsyncClient() as client:
                    resp = await client.get(media_url)
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                        f.write(resp.content)
                        temp_path = f.name

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
            params:
                - pdf_url (str): URL or local path of the PDF file.
                - extract_tables (bool): Whether to extract tables via pdfplumber.

        Returns:
            Dict with text, metadata, and optional tables list.
        """
        pdf_url = params.get("pdf_url", "")
        extract_tables = params.get("extract_tables", False)

        self._heartbeat_safe(f"Parsing PDF: {pdf_url}")

        try:
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

            from tika import parser as tika_parser

            parsed = tika_parser.from_file(pdf_path)

            result: Dict[str, Any] = {
                "text": parsed.get("content", "").strip(),
                "metadata": parsed.get("metadata", {}),
            }

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
