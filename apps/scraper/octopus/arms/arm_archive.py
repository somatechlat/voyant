"""
ARM-8: Interactive deep archive with Playwright.

Programmatically clicks through UI elements and downloads matching
files for deep archival scraping.
"""

from __future__ import annotations

import json as _json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import httpx
from playwright.async_api import async_playwright

from apps.scraper.octopus.schemas import OctopusRequest, OctopusResult
from apps.scraper.security import validate_url

logger = logging.getLogger(__name__)


async def _download_file(target_url: str, dest: Path) -> bool:
    """Download a file to a local path with SSRF validation."""
    try:
        validate_url(target_url)
    except Exception as exc:
        logger.warning("Download URL blocked: %s - %s", target_url, exc)
        return False
    try:
        async with httpx.AsyncClient(
            verify=False, timeout=60.0
        ) as client:
            resp = await client.get(target_url)
            if resp.status_code == 200:
                dest.write_bytes(resp.content)
                return True
    except Exception as exc:
        logger.error("Failed to download %s: %s", target_url, exc)
    return False


async def execute(request: OctopusRequest) -> OctopusResult:
    files that match the configured patterns.

    Args:
        request: The OctopusRequest with archive parameters.

    Returns:
        An OctopusResult with the archive manifest and file list.
    """
    start = datetime.now(UTC)
    try:
        validate_url(request.url)
    except Exception as exc:
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
            error_code="SSRF_BLOCKED",
            error_message=str(exc),
        )

    out_dir = Path(request.target_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files_dir = out_dir / "files"
    files_dir.mkdir(exist_ok=True)

    interaction_states: dict[str, str] = {}
    files_downloaded: list[dict[str, Any]] = []
    html = ""
    status = 0

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                ignore_https_errors=True
            )
            page = await context.new_page()
            page.on("popup", lambda popup: None)

            response = await page.goto(
                request.url,
                wait_until="networkidle",
                timeout=request.timeout_ms,
            )
            status = response.status if response else 0
            html = await page.content()
            interaction_states["baseline"] = html

            for selector in request.interaction_selectors:
                try:
                    element = await page.wait_for_selector(
                        selector, timeout=10000
                    )
                    if element:
                        await element.click()
                        await page.wait_for_timeout(
                            request.wait_settle_ms
                        )
                        interaction_states[selector] = (
                            await page.content()
                        )
                except Exception as exc:
                    logger.warning(
                        "Interaction failed for %s: %s", selector, exc
                    )

            if request.download_patterns:
                links = await page.query_selector_all("a")
                for link in links:
                    href = await link.get_attribute("href")
                    if not href:
                        continue
                    matched = any(
                        pattern.lower() in href.lower()
                        for pattern in request.download_patterns
                    )
                    if matched:
                        full_url = urljoin(page.url, href)
                        safe_name = (
                            f"artifact_{len(files_downloaded)}.download"
                        )
                        if "archivo=" in href.lower():
                            safe_name = href.split("=")[-1].split(
                                "&"
                            )[0][:50]
                        elif href.split("?")[0].endswith(".pdf"):
                            safe_name = (
                                f"artifact_{len(files_downloaded)}.pdf"
                            )
                        dest = files_dir / safe_name
                        success = await _download_file(full_url, dest)
                        files_downloaded.append(
                            {
                                "url": full_url,
                                "filename": safe_name,
                                "saved": success,
                                "path": str(dest) if success else None,
                            }
                        )
                    elif "javascript" in href.lower() and "'" in href:
                        extracted = href.split("'")[1]
                        matched_js = any(
                            pattern.lower() in extracted.lower()
                            for pattern in request.download_patterns
                        )
                        if matched_js:
                            full_url = urljoin(page.url, extracted)
                            safe_name = f"js_artifact_{len(files_downloaded)}.download"
                            if "archivo=" in extracted.lower():
                                safe_name = extracted.split("=")[-1].split(
                                    "&"
                                )[0][:50]
                            dest = files_dir / safe_name
                            success = await _download_file(
                                full_url, dest
                            )
                            files_downloaded.append(
                                {
                                    "url": full_url,
                                    "filename": safe_name,
                                    "saved": success,
                                    "path": str(dest)
                                    if success
                                    else None,
                                }
                            )

            await browser.close()

        manifest = {
            "source_url": request.url,
            "target_dir": request.target_dir,
            "interaction_states": list(interaction_states.keys()),
            "files_downloaded": files_downloaded,
        }
        manifest_path = out_dir / "deep_archive_manifest.json"
        manifest_path.write_text(
            _json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    except Exception as exc:
        logger.exception("Deep archive failed for %s", request.url)
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
            error_code="ARCHIVE_ERROR",
            error_message=str(exc),
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
        html=html,
        status_code=status,
        archive_manifest=manifest,
        files_downloaded=files_downloaded,
        interaction_states=interaction_states,
    )
