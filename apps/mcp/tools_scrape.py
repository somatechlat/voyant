"""
Voyant MCP — Scrape & UPTP Tools.

Tools for web scraping execution (fetch, deep archive, OCR, PDF parse,
transcription, data extraction) and the UPTP template execution router.

All scrape tools delegate directly to the activity classes. No intelligence
or decision logic runs here — pure, mechanical MCP-to-activity bridging.

Extracted from mcp/tools.py (Rule 245 compliance — 723-line split).
"""

from django_mcp import mcp_app

from apps.core.api_utils import run_async
from apps.scraper.activities import FetchActivities, ParseActivities
from apps.uptp_core.engine import UPTPExecutionEngine
from apps.uptp_core.schemas import TemplateExecutionRequest

# Singleton activity instances reused across tool calls.
_fetch_activities = FetchActivities()
_parse_activities = ParseActivities()


@mcp_app.tool(name="scrape.fetch")
def tool_scrape_fetch(
    url: str,
    engine: str = "playwright",
    wait_for=None,
    scroll: bool = False,
    timeout: int = 30,
    wait_until=None,
    settle_ms=None,
    block_resources=None,
    capture_json: bool = False,
    capture_url_contains=None,
    capture_max_bytes=None,
    capture_max_items=None,
):
    """
    Fetch a web page and return HTML + metadata.

    Args:
        url: Target URL (SSRF-protected).
        engine: 'playwright' (JS rendering), 'httpx' (static), or 'scrapy'.
        wait_for: CSS selector to wait for before capturing.
        scroll: Scroll to bottom before capture.
        timeout: Request timeout in seconds.
        wait_until: Playwright navigation event ('domcontentloaded', 'networkidle').
        settle_ms: Extra delay after navigation before capturing.
        block_resources: Block images/media/fonts to speed up rendering.
        capture_json: Capture XHR/fetch JSON responses intercepted during load.
        capture_url_contains: Filter for which JSON XHR URLs to capture.
        capture_max_bytes: Max size per captured JSON body.
        capture_max_items: Max number of JSON responses to capture.
    """
    return run_async(
        _fetch_activities.fetch_page,
        {
            "url": url,
            "engine": engine,
            "wait_for": wait_for,
            "scroll": scroll,
            "timeout": timeout,
            "wait_until": wait_until,
            "settle_ms": settle_ms,
            "block_resources": block_resources,
            "capture_json": capture_json,
            "capture_url_contains": capture_url_contains,
            "capture_max_bytes": capture_max_bytes,
            "capture_max_items": capture_max_items,
        },
    )


@mcp_app.tool(name="scrape.deep_archive")
async def tool_scrape_deep_archive(
    url: str,
    interaction_selectors: list[str] = None,
    download_patterns: list[str] = None,
    target_dir: str = "scrapes/unknown",
    wait_settle_ms: int = 2000,
    timeout_ms: int = 60000,
):
    """
    Generic deep archival web scrape for SPAs and tabbed interfaces.

    Navigates to the URL, programmatically clicks each selector in
    `interaction_selectors` and waits for DOM to settle after each click,
    then downloads all links matching `download_patterns` to `target_dir`.

    Returns a manifest dict with all captured HTML states and downloaded files.
    """
    return await _fetch_activities.deep_archive(
        {
            "url": url,
            "interaction_selectors": interaction_selectors or [],
            "download_patterns": download_patterns or [],
            "target_dir": target_dir,
            "wait_settle_ms": wait_settle_ms,
            "timeout_ms": timeout_ms,
        }
    )


@mcp_app.tool(name="scrape.extract")
def tool_scrape_extract(html: str, selectors, url: str = ""):
    """
    Extract structured data from HTML using CSS or XPath selectors.

    Args:
        html: Raw HTML string to parse.
        selectors: Dict mapping field names to CSS/XPath selectors.
        url: Source URL for metadata context.
    """
    return run_async(
        _parse_activities.extract_data,
        {"html": html, "selectors": selectors, "url": url},
    )


@mcp_app.tool(name="scrape.ocr")
def tool_scrape_ocr(images, language: str = "spa+eng"):
    """
    Run Tesseract OCR on a list of image URLs or local file paths.

    Args:
        images: List of image URLs or local paths.
        language: Tesseract language pack (e.g. 'spa+eng', 'eng').
    """
    return run_async(
        _parse_activities.process_ocr,
        {"images": images, "language": language},
    )


@mcp_app.tool(name="scrape.parse_pdf")
def tool_scrape_parse_pdf(pdf_url: str, extract_tables: bool = False):
    """
    Parse a PDF document to extract text, metadata, and optionally tables.

    Args:
        pdf_url: URL or local path of the PDF file.
        extract_tables: Whether to extract tables via pdfplumber.
    """
    return run_async(
        _parse_activities.parse_pdf,
        {"pdf_url": pdf_url, "extract_tables": extract_tables},
    )


@mcp_app.tool(name="scrape.transcribe")
def tool_scrape_transcribe(media_urls, language: str = "es"):
    """
    Transcribe audio/video files to text using OpenAI Whisper.

    Args:
        media_urls: List of media file URLs.
        language: Language code (e.g. 'es', 'en').
    """
    return run_async(
        _parse_activities.transcribe_media,
        {"media_urls": media_urls, "language": language},
    )


@mcp_app.tool(name="voyant.templates.execute")
def tool_execute_template(
    template_id: str, category: str, tenant_id: str, params: dict, job_name: str = None
):
    """
    [UPTP Core Router] Universal Data Box execution entry point.

    Dispatches any template execution request through the UPTP engine.
    Supports all registered template categories (analysis, generation, reporting, etc.).
    The engine handles routing to the correct mathematical or structural template.

    Args:
        template_id: Dot-notation template identifier (e.g. 'analysis.correlation').
        category: Template category matching TemplateCategory enum.
        tenant_id: Tenant ID for data isolation.
        params: Template-specific parameters dict.
        job_name: Optional human-readable job label.
    """
    request_payload = TemplateExecutionRequest(
        template_id=template_id,
        category=category,
        tenant_id=tenant_id,
        params=params,
        job_name=job_name,
    )
    return UPTPExecutionEngine.dispatch_execution(request_payload)
