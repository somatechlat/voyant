"""
OCTOPUS Pydantic Schemas.

Defines OctopusRequest (unified input), OctopusResult (unified output),
BrowserAction (browser automation step), and OctopusARM enum.

All schemas use `extra="forbid"` to prevent silent parameter injection.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OctopusARM(StrEnum):
    """The eight scraping arms of the OCTOPUS engine."""

    STATIC = "static"            # ARM-1: httpx + parsel — fast static pages
    DYNAMIC = "dynamic"          # ARM-2: Playwright + Chromium — JS rendering
    EVASION = "evasion"          # ARM-3: curl-cffi + camoufox — anti-bot bypass
    CRAWL = "crawl"              # ARM-4: Scrapy — large-scale site crawl
    API_INTERCEPT = "api_intercept"  # ARM-5: Playwright XHR/JSON capture
    DOCUMENT = "document"        # ARM-6: pdfplumber + unstructured
    OCR = "ocr"                  # ARM-7a: Tesseract image OCR
    TRANSCRIBE = "transcribe"    # ARM-7b: Whisper audio/video transcription
    ARCHIVE = "archive"          # ARM-8: Playwright interactive deep archiving


class BrowserAction(BaseModel):
    """A single browser automation step for ARM-2, ARM-3b, ARM-5, ARM-8."""

    type: str = Field(
        ...,
        description="Action type: click|fill|scroll|wait|screenshot|hover|select|keyboard",
    )
    selector: str | None = None
    value: str | None = None
    timeout_ms: int = 5000
    path: str | None = None  # For screenshot action

    model_config = ConfigDict(extra="forbid")


class CrawledPage(BaseModel):
    """One page result from ARM-4 (Scrapy crawl)."""

    url: str
    status: int
    html: str
    extracted_fields: dict[str, Any] = {}

    model_config = ConfigDict(extra="allow")


class OctopusRequest(BaseModel):
    """
    Unified request schema for all OCTOPUS ARM invocations.
    The Agent provides ALL intelligence. OCTOPUS executes mechanically.
    """

    # ── Core (required) ────────────────────────────────────────────────
    url: str = Field(..., description="Primary URL to process")
    arm: OctopusARM = Field(..., description="Which scraping strategy to use")
    tenant_id: str = Field(..., description="Tenant isolation identifier")

    # ── Named selectors (ARM-1, ARM-2, ARM-4) ──────────────────────────
    css_selectors: dict[str, str] = Field(
        default_factory=dict,
        description='{"field_name": "css.selector"} — named extractions',
    )
    xpath_selectors: dict[str, str] = Field(
        default_factory=dict,
        description='{"field_name": "//xpath"} — named extractions',
    )
    extract_links: bool = False
    extract_metadata: bool = True  # OpenGraph, Schema.org, meta tags

    # ── Browser actions (ARM-2, ARM-3b, ARM-5, ARM-8) ──────────────────
    wait_until: str = "domcontentloaded"
    wait_for: str | None = None  # CSS selector to wait for
    scroll: bool = False
    settle_ms: int = 0
    block_resources: bool = True
    actions: list[BrowserAction] = Field(default_factory=list)

    # ── ARM-3: Evasion ─────────────────────────────────────────────────
    evasion_mode: str = "curl_cffi"  # "curl_cffi" | "camoufox"
    impersonate: str = "chrome124"   # curl-cffi browser target
    proxy_url: str | None = None  # "http://user:pass@host:port" — never logged

    # ── ARM-4: Crawl ───────────────────────────────────────────────────
    start_urls: list[str] = Field(default_factory=list)
    max_depth: int = 1
    follow_links: bool = False
    obey_robots: bool = True
    download_delay: float = 0.5
    concurrent_requests: int = 16
    allowed_domains: list[str] = Field(default_factory=list)
    sitemap_url: str | None = None

    # ── ARM-5: API Interception ────────────────────────────────────────
    capture_json: bool = True
    capture_url_contains: list[str] = Field(default_factory=list)
    capture_max_bytes: int = 524288   # 512KB per response
    capture_max_items: int = 25

    # ── ARM-6: Document ────────────────────────────────────────────────
    extract_tables: bool = True
    document_password: str | None = None
    output_format: str = "json"  # "text" | "json" | "markdown"

    # ── ARM-7: OCR / Transcription ─────────────────────────────────────
    language: str = "eng"            # Tesseract lang or Whisper language code
    whisper_model: str = "base"      # "tiny"|"base"|"small"|"medium"|"large"
    transcription_format: str = "text"  # "text" | "json" | "srt"
    ocr_confidence_threshold: int = 60

    # ── ARM-8: Archive ─────────────────────────────────────────────────
    interaction_selectors: list[str] = Field(default_factory=list)
    download_patterns: list[str] = Field(default_factory=list)
    target_dir: str = "scrapes/archive"
    wait_settle_ms: int = 2000
    timeout_ms: int = 60000

    # ── Global ─────────────────────────────────────────────────────────
    timeout_seconds: int = 60
    verify_ssl: bool = True
    job_id: str | None = None

    model_config = ConfigDict(extra="forbid")


class OctopusResult(BaseModel):
    """
    Unified result schema for all OCTOPUS ARM invocations.
    Always returned — success=False on error, never raises to caller.
    """

    # ── Identity ───────────────────────────────────────────────────────
    arm: str
    url: str
    tenant_id: str
    job_id: str | None = None

    # ── Execution metadata ─────────────────────────────────────────────
    success: bool
    duration_ms: int = 0
    fetched_at: str = ""

    # ── HTML content (ARM-1/2/3/5) ─────────────────────────────────────
    html: str | None = None
    status_code: int | None = None
    response_headers: dict[str, str] | None = None
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    discovered_links: list[str] = Field(default_factory=list)

    # ── Metadata (ARM-1/2) ─────────────────────────────────────────────
    page_metadata: dict[str, Any] = Field(default_factory=dict)

    # ── JSON capture (ARM-5) ───────────────────────────────────────────
    captured_json: list[dict[str, Any]] = Field(default_factory=list)

    # ── Document (ARM-6) ───────────────────────────────────────────────
    document_text: str | None = None
    document_tables: list[Any] | None = None
    document_metadata: dict[str, Any] | None = None

    # ── OCR (ARM-7a) ───────────────────────────────────────────────────
    ocr_text: str | None = None
    ocr_blocks: list[dict[str, Any]] = Field(default_factory=list)

    # ── Transcription (ARM-7b) ─────────────────────────────────────────
    transcription: str | None = None
    transcription_language: str | None = None
    transcription_segments: list[dict[str, Any]] = Field(default_factory=list)

    # ── Crawl (ARM-4) ─────────────────────────────────────────────────
    crawled_pages: list[CrawledPage] = Field(default_factory=list)
    total_pages: int = 0

    # ── Archive (ARM-8) ───────────────────────────────────────────────
    archive_manifest: dict[str, Any] | None = None
    files_downloaded: list[dict[str, Any]] = Field(default_factory=list)
    interaction_states: dict[str, str] = Field(default_factory=dict)

    # ── Artifact storage ───────────────────────────────────────────────
    artifact_uri: str | None = None
    artifact_size_bytes: int = 0

    # ── Error ──────────────────────────────────────────────────────────
    error_code: str | None = None
    error_message: str | None = None

    model_config = ConfigDict(extra="allow")
