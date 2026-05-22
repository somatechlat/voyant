"""
ARM-2: Dynamic scraping with Playwright + playwright-stealth.

JavaScript rendering, browser actions, scrolling, and structured
extraction for modern web applications.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from playwright.async_api import async_playwright

from apps.core.config import get_settings
from apps.scraper.octopus.schemas import BrowserAction, OctopusRequest, OctopusResult
from apps.scraper.parsing.html_parser import HTMLParser

logger = logging.getLogger(__name__)
settings = get_settings()

try:
    from playwright_stealth import stealth_async  # type: ignore[import-not-found]
except Exception:
    stealth_async = None  # type: ignore[misc]
    logger.warning("playwright-stealth not installed")


async def _perform_actions(page, actions: List[BrowserAction]) -> None:
    """Execute a sequence of browser actions on a Playwright page."""
    for action in actions:
        atype = action.type
        selector = action.selector
        value = action.value
        timeout = action.timeout_ms

        if atype == "click" and selector:
            await page.click(selector, timeout=timeout)
        elif atype == "fill" and selector:
            await page.fill(selector, value or "", timeout=timeout)
        elif atype == "scroll":
            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )
            await page.wait_for_timeout(1000)
        elif atype == "wait":
            await page.wait_for_timeout(timeout)
        elif atype == "screenshot" and action.path:
            await page.screenshot(path=action.path, timeout=timeout)
        elif atype == "hover" and selector:
            await page.hover(selector, timeout=timeout)
        elif atype == "select" and selector:
            await page.select_option(
                selector, value or "", timeout=timeout
            )
        elif atype == "keyboard" and value:
            await page.keyboard.press(value)
        else:
            logger.warning(
                "Unknown or incomplete action: %s", action.model_dump()
            )


async def execute(request: OctopusRequest) -> OctopusResult:
    """
    Execute ARM-2 dynamic scrape.

    Launches a stealth-patched Chromium browser, renders JavaScript,
    performs optional actions, and extracts structured data.

    Args:
        request: The OctopusRequest with browser configuration.

    Returns:
        An OctopusResult with rendered HTML and extracted fields.
    """
    start = datetime.now(timezone.utc)
    html = ""
    status = 0

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=settings.scraper_playwright_user_agent,
                locale=settings.scraper_playwright_locale,
            )
            page = await context.new_page()

            if stealth_async is not None:
                await stealth_async(page)
            else:
                logger.warning(
                    "playwright-stealth unavailable; skipping stealth"
                )

            if request.block_resources:

                async def _route_handler(route, req):
                    try:
                        if req.resource_type in ("image", "media", "font"):
                            await route.abort()
                        else:
                            await route.continue_()
                    except Exception:
                        try:
                            await route.continue_()
                        except Exception:
                            pass

                await page.route("**/*", _route_handler)

            response = await page.goto(
                request.url,
                wait_until=request.wait_until,  # type: ignore[arg-type]
                timeout=request.timeout_seconds * 1000,
            )
            status = response.status if response else 0

            if request.wait_for:
                await page.wait_for_selector(
                    request.wait_for,
                    timeout=request.timeout_seconds * 1000,
                )

            if request.scroll:
                await page.evaluate(
                    "window.scrollTo(0, document.body.scrollHeight)"
                )
                await page.wait_for_timeout(1000)

            if request.settle_ms and request.settle_ms > 0:
                await page.wait_for_timeout(request.settle_ms)

            if request.actions:
                await _perform_actions(page, request.actions)

            html = await page.content()
            await browser.close()
    except Exception as exc:
        logger.exception("Dynamic fetch failed for %s", request.url)
        return OctopusResult(
            arm=request.arm.value,
            url=request.url,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            success=False,
            duration_ms=int(
                (datetime.now(timezone.utc) - start).total_seconds() * 1000
            ),
            fetched_at=start.isoformat(),
            error_code="DYNAMIC_ERROR",
            error_message=str(exc),
        )

    parser = HTMLParser()
    extracted: Dict[str, Any] = {}
    if request.css_selectors or request.xpath_selectors:
        selectors: Dict[str, Any] = {}
        selectors.update(request.css_selectors)
        selectors.update(request.xpath_selectors)
        extracted = parser.extract(html, selectors)

    metadata: Dict[str, Any] = {}
    if request.extract_metadata:
        from apps.scraper.octopus.arms.arm_static import _extract_metadata

        metadata = _extract_metadata(html)

    links: List[str] = []
    if request.extract_links:
        links = parser.get_all_links(html)

    duration_ms = int(
        (datetime.now(timezone.utc) - start).total_seconds() * 1000
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
