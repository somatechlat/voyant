"""
ARM-5: API interception via Playwright network monitoring.

Captures XHR/Fetch JSON responses to reverse-engineer hidden APIs.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

from playwright.async_api import async_playwright

from apps.core.config import get_settings
from apps.scraper.octopus.schemas import OctopusRequest, OctopusResult

logger = logging.getLogger(__name__)
settings = get_settings()


async def execute(request: OctopusRequest) -> OctopusResult:
    """
    Execute ARM-5 API interception.

    Navigates with Playwright and collects JSON network responses
    matching the configured filters.

    Args:
        request: The OctopusRequest with interception rules.

    Returns:
        An OctopusResult with captured JSON payloads and page HTML.
    """
    start = datetime.now(timezone.utc)
    captured_json: List[Dict[str, Any]] = []
    capture_tasks: Set[asyncio.Task] = set()
    capturing_enabled = True

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=settings.scraper_playwright_user_agent,
                locale=settings.scraper_playwright_locale,
            )
            page = await context.new_page()

            async def _maybe_capture(response) -> None:
                try:
                    if not request.capture_json:
                        return
                    if len(captured_json) >= request.capture_max_items:
                        return
                    req = response.request
                    if req.resource_type not in ("xhr", "fetch"):
                        return
                    if response.status < 200 or response.status >= 300:
                        return
                    resp_url = str(response.url)
                    if request.capture_url_contains and not any(
                        s in resp_url for s in request.capture_url_contains
                    ):
                        return
                    ct = (response.headers or {}).get("content-type", "")
                    if "json" not in ct.lower():
                        return
                    body = await response.text()
                    if body is None or len(body) > request.capture_max_bytes:
                        return
                    parsed = json.loads(body)
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

            def _on_response(response) -> None:
                if not capturing_enabled:
                    return
                try:
                    task = asyncio.create_task(_maybe_capture(response))
                    capture_tasks.add(task)
                    task.add_done_callback(
                        lambda t: capture_tasks.discard(t)
                    )
                except RuntimeError:
                    return

            page.on("response", _on_response)

            response = await page.goto(
                request.url,
                wait_until=request.wait_until,
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

            html = await page.content()

            capturing_enabled = False
            if capture_tasks:
                await asyncio.gather(
                    *list(capture_tasks), return_exceptions=True
                )

            await browser.close()
    except Exception as exc:
        logger.exception("API intercept failed for %s", request.url)
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
            error_code="API_INTERCEPT_ERROR",
            error_message=str(exc),
        )

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
        captured_json=captured_json,
    )
