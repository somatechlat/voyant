"""
ARM-7a: OCR extraction with Tesseract.

Extracts text and bounding-box blocks from images.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from apps.core.config import get_settings
from apps.scraper.octopus.schemas import OctopusRequest, OctopusResult
from apps.scraper.parsing.ocr_processor import OCRProcessor
from apps.scraper.security import validate_url

logger = logging.getLogger(__name__)
settings = get_settings()


async def _fetch_image(url: str) -> bytes:
    """Fetch image bytes from a remote URL."""
    validate_url(url)
    async with httpx.AsyncClient(timeout=settings.scraper_default_timeout_seconds) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


async def execute(request: OctopusRequest) -> OctopusResult:
    """
    Execute ARM-7a OCR.

    Fetches the image and extracts text with Tesseract, filtering
    by the requested confidence threshold.

    Args:
        request: The OctopusRequest pointing to an image.

    Returns:
        An OctopusResult with OCR text and word blocks.
    """
    start = datetime.now(UTC)

    try:
        if request.url.startswith(("http://", "https://")):
            image_bytes = await _fetch_image(request.url)
        else:
            with open(request.url, "rb") as f:
                image_bytes = f.read()
    except Exception as exc:
        logger.exception("Image fetch failed for %s", request.url)
        return OctopusResult(
            arm=request.arm.value,
            url=request.url,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            success=False,
            duration_ms=int((datetime.now(UTC) - start).total_seconds() * 1000),
            fetched_at=start.isoformat(),
            error_code="OCR_FETCH_ERROR",
            error_message=str(exc),
        )

    try:
        processor = OCRProcessor(language=request.language)
        result = processor.extract_structured(image_bytes)
    except Exception as exc:
        logger.exception("OCR processing failed for %s", request.url)
        return OctopusResult(
            arm=request.arm.value,
            url=request.url,
            tenant_id=request.tenant_id,
            job_id=request.job_id,
            success=False,
            duration_ms=int((datetime.now(UTC) - start).total_seconds() * 1000),
            fetched_at=start.isoformat(),
            error_code="OCR_PROCESS_ERROR",
            error_message=str(exc),
        )

    words = result.get("words", [])
    full_text = result.get("full_text", "")
    filtered_blocks: list[dict[str, Any]] = []
    for word in words:
        conf = word.get("confidence", 0)
        if conf >= request.ocr_confidence_threshold:
            filtered_blocks.append(word)

    duration_ms = int((datetime.now(UTC) - start).total_seconds() * 1000)
    return OctopusResult(
        arm=request.arm.value,
        url=request.url,
        tenant_id=request.tenant_id,
        job_id=request.job_id,
        success=True,
        duration_ms=duration_ms,
        fetched_at=start.isoformat(),
        ocr_text=full_text,
        ocr_blocks=filtered_blocks,
    )
