"""
ARM-4: Large-scale site crawling with Scrapy.

Supports depth control, robots.txt compliance, link following,
and sitemap parsing.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from apps.scraper.browser.scrapy_client import ScrapyClient
from apps.scraper.octopus.schemas import CrawledPage, OctopusRequest, OctopusResult
from apps.scraper.security import validate_url

logger = logging.getLogger(__name__)


def _run_scrapy_crawl(request: OctopusRequest) -> list[dict[str, Any]]:
    """
    Synchronously run a Scrapy crawl.

    Must be executed in a thread because ``CrawlerProcess.start()``
    blocks the calling thread.
    """
    urls = [request.url]
    if request.start_urls:
        for u in request.start_urls:
            try:
                validate_url(u)
                urls.append(u)
            except Exception:
                logger.warning("Invalid start URL skipped: %s", u)

    client = ScrapyClient(
        concurrent_requests=request.concurrent_requests,
        download_delay=request.download_delay,
        obey_robots=request.obey_robots,
    )

    # Patch missing timeout attribute used by crawl_sitemap
    setattr(client, "timeout", request.timeout_seconds)  # type: ignore[attr-defined]

    if request.sitemap_url:
        try:
            validate_url(request.sitemap_url)
            return client.crawl_sitemap(request.sitemap_url)
        except Exception as exc:
            logger.error("Sitemap crawl failed: %s", exc)
            return []

    return client.crawl(
        urls=urls,
        follow_links=request.follow_links,
        max_depth=request.max_depth,
    )


async def execute(request: OctopusRequest) -> OctopusResult:
    """
    Execute ARM-4 crawl.

    Runs Scrapy in a background thread to avoid blocking the
    asyncio event loop.

    Args:
        request: The OctopusRequest with crawl parameters.

    Returns:
        An OctopusResult with all crawled pages.
    """
    start = datetime.now(UTC)

    try:
        results = await asyncio.to_thread(_run_scrapy_crawl, request)
    except Exception as exc:
        logger.exception("Crawl failed for %s", request.url)
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
            error_code="CRAWL_ERROR",
            error_message=str(exc),
        )

    crawled_pages: list[CrawledPage] = []
    for item in results:
        crawled_pages.append(
            CrawledPage(
                url=item.get("url", ""),
                status=item.get("status", 0),
                html=item.get("html", ""),
                extracted_fields={},
            )
        )

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
        crawled_pages=crawled_pages,
        total_pages=len(crawled_pages),
    )
