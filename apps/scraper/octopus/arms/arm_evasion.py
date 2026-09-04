"""
ARM-3: Evasion scraping with curl-cffi or camoufox.

Bypasses anti-bot measures via TLS fingerprint impersonation
(curl-cffi) or stealth browser automation (camoufox).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from apps.core.config import get_settings
from apps.scraper.octopus.schemas import OctopusRequest, OctopusResult
from apps.scraper.parsing.html_parser import HTMLParser

logger = logging.getLogger(__name__)
settings = get_settings()


async def _execute_curl_cffi(request: OctopusRequest) -> OctopusResult:
    """Execute evasion scrape using curl-cffi."""
    start = datetime.now(UTC)
    try:
        from curl_cffi.requests import AsyncSession  # type: ignore[import-not-found]

        proxies = None
        if request.proxy_url:
            proxies = {
                "http": request.proxy_url,
                "https": request.proxy_url,
            }

        async with AsyncSession() as session:
            resp = await session.get(
                request.url,
                impersonate=request.impersonate,
                proxies=proxies,
                timeout=request.timeout_seconds,
                headers={
                    "User-Agent": settings.scraper_http_user_agent,
                    "Accept-Language": (
                        settings.scraper_http_accept_language
                    ),
                },
            )
            html = resp.text
            status = resp.status_code
            headers = dict(resp.headers)
    except Exception as exc:
        logger.exception("curl-cffi fetch failed for %s", request.url)
        return OctopusResult(
            arm=request.arm.value,
            url=request.url,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            success=False,
            duration_ms=int(
                (datetime.now(UTC) - start).total_seconds() * 1000
            ),
            fetched_at=start.isoformat(),
            error_code="EVASION_CURL_ERROR",
            error_message=str(exc),
        )

    parser = HTMLParser()
    extracted: dict[str, Any] = {}
    if request.css_selectors or request.xpath_selectors:
        selectors: dict[str, Any] = {}
        selectors.update(request.css_selectors)
        selectors.update(request.xpath_selectors)
        extracted = parser.extract(html, selectors)

    metadata: dict[str, Any] = {}
    if request.extract_metadata:
        from apps.scraper.octopus.arms.arm_static import _extract_metadata

        metadata = _extract_metadata(html)

    links: list[str] = []
    if request.extract_links:
        links = parser.get_all_links(html)

    duration_ms = int(
        (datetime.now(UTC) - start).total_seconds() * 1000
    )
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


async def _execute_camoufox(request: OctopusRequest) -> OctopusResult:
    """Execute evasion scrape using Camoufox stealth browser."""
    start = datetime.now(UTC)
    html = ""
    status = 0

    try:
        from camoufox.async_api import AsyncCamoufox  # type: ignore[import-not-found]

        kwargs: dict[str, Any] = {"headless": True}
        if request.proxy_url:
            kwargs["proxy"] = {"server": request.proxy_url}

        async with AsyncCamoufox(**kwargs) as browser:
            page = await browser.new_page()
            response = await page.goto(
                request.url,
                wait_until="domcontentloaded",
                timeout=request.timeout_seconds * 1000,
            )
            html = await page.content()
            status = response.status if response else 0
            await page.close()
    except Exception as exc:
        logger.exception("Camoufox fetch failed for %s", request.url)
        return OctopusResult(
            arm=request.arm.value,
            url=request.url,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            success=False,
            duration_ms=int(
                (datetime.now(UTC) - start).total_seconds() * 1000
            ),
            fetched_at=start.isoformat(),
            error_code="EVASION_CAMOUFOX_ERROR",
            error_message=str(exc),
        )

    parser = HTMLParser()
    extracted: dict[str, Any] = {}
    if request.css_selectors or request.xpath_selectors:
        selectors: dict[str, Any] = {}
        selectors.update(request.css_selectors)
        selectors.update(request.xpath_selectors)
        extracted = parser.extract(html, selectors)

    metadata: dict[str, Any] = {}
    if request.extract_metadata:
        from apps.scraper.octopus.arms.arm_static import _extract_metadata

        metadata = _extract_metadata(html)

    links: list[str] = []
    if request.extract_links:
        links = parser.get_all_links(html)

    duration_ms = int(
        (datetime.now(UTC) - start).total_seconds() * 1000
    )
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
        extracted_fields=extracted,
        discovered_links=links,
        page_metadata=metadata,
    )


async def execute(request: OctopusRequest) -> OctopusResult:
    """
    Execute ARM-3 evasion scrape.

    Dispatches to curl-cffi or Camoufox based on
    ``request.evasion_mode``.

    Args:
        request: The OctopusRequest with evasion configuration.

    Returns:
        An OctopusResult with the fetched HTML and extractions.
    """
    if request.evasion_mode == "camoufox":
        return await _execute_camoufox(request)
    return await _execute_curl_cffi(request)
