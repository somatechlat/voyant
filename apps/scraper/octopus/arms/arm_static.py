"""
ARM-1: Static scraping with httpx + parsel.

Fast, lightweight extraction for static HTML pages using CSS and
XPath selectors.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from parsel import Selector

from apps.core.config import get_settings
from apps.scraper.octopus.schemas import OctopusRequest, OctopusResult

logger = logging.getLogger(__name__)
settings = get_settings()


def _extract_metadata(html: str) -> dict[str, Any]:
    """Extract OpenGraph, Schema.org, and meta tags from HTML."""
    sel = Selector(text=html)
    metadata: dict[str, Any] = {}

    title = sel.css("title::text").get("")
    if title:
        metadata["title"] = title.strip()

    description = sel.css('meta[name="description"]::attr(content)').get("") or sel.css(
        'meta[property="og:description"]::attr(content)'
    ).get("")
    if description:
        metadata["description"] = description.strip()

    og_title = sel.css('meta[property="og:title"]::attr(content)').get("")
    if og_title:
        metadata["og_title"] = og_title.strip()

    og_image = sel.css('meta[property="og:image"]::attr(content)').get("")
    if og_image:
        metadata["og_image"] = og_image.strip()

    canonical = sel.css('link[rel="canonical"]::attr(href)').get("")
    if canonical:
        metadata["canonical"] = canonical.strip()

    schema_scripts = sel.css('script[type="application/ld+json"]::text').getall()
    schemas: list[dict[str, Any]] = []
    for script in schema_scripts:
        try:
            import json

            schemas.append(json.loads(script))
        except Exception:
            continue
    if schemas:
        metadata["schema_org"] = schemas

    return metadata


def _extract_fields(html: str, request: OctopusRequest) -> dict[str, Any]:
    """Extract named fields via CSS and XPath selectors using parsel."""
    sel = Selector(text=html)
    fields: dict[str, Any] = {}

    for name, selector in request.css_selectors.items():
        try:
            values = sel.css(selector).getall()
            fields[name] = values
        except Exception as exc:
            logger.warning("CSS selector '%s' failed: %s", name, exc)
            fields[name] = []

    for name, selector in request.xpath_selectors.items():
        try:
            values = sel.xpath(selector).getall()
            fields[name] = values
        except Exception as exc:
            logger.warning("XPath selector '%s' failed: %s", name, exc)
            fields[name] = []

    return fields


async def execute(request: OctopusRequest) -> OctopusResult:
    """
    Execute ARM-1 static scrape.

    Uses httpx for fast retrieval and parsel for CSS/XPath extraction.

    Args:
        request: The OctopusRequest containing URL and selectors.

    Returns:
        An OctopusResult with HTML, extracted fields, and metadata.
    """
    start = datetime.now(UTC)
    try:
        if not settings.scraper_tls_verify:
            verify = False
        else:
            import ssl

            import certifi

            verify = ssl.create_default_context(cafile=certifi.where())

        async with httpx.AsyncClient(
            timeout=request.timeout_seconds,
            follow_redirects=True,
            verify=verify,
        ) as client:
            resp = await client.get(
                request.url,
                headers={
                    "User-Agent": settings.scraper_http_user_agent,
                    "Accept-Language": (settings.scraper_http_accept_language),
                },
            )
            html = resp.text
            status = resp.status_code
            headers = dict(resp.headers)
    except Exception as exc:
        logger.exception("Static fetch failed for %s", request.url)
        return OctopusResult(
            arm=request.arm.value,
            url=request.url,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            success=False,
            duration_ms=int((datetime.now(UTC) - start).total_seconds() * 1000),
            fetched_at=start.isoformat(),
            error_code="FETCH_ERROR",
            error_message=str(exc),
        )

    extracted = _extract_fields(html, request)
    metadata = _extract_metadata(html) if request.extract_metadata else {}
    links: list[str] = []
    if request.extract_links:
        sel = Selector(text=html)
        links = sel.css("a::attr(href)").getall()

    duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
    return OctopusResult(
        arm=request.arm.value,
        url=request.url,
        tenant_id=request.tenant_id,
        job_id=request.job_id,
        success=True,
        duration_ms=duration_ms,
        fetched_at=start.isoformat(),
        html=html,
        status_code=status,
        response_headers=headers,
        extracted_fields=extracted,
        discovered_links=links,
        page_metadata=metadata,
    )
