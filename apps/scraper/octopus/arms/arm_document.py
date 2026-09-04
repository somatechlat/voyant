"""
ARM-6: Document parsing with pdfplumber and unstructured.

Extracts text, metadata, and tables from PDF and Office documents.
"""

from __future__ import annotations

import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx

from apps.core.config import get_settings
from apps.scraper.octopus.schemas import OctopusRequest, OctopusResult
from apps.scraper.parsing.pdf_parser import PDFParser
from apps.scraper.security import validate_url

logger = logging.getLogger(__name__)
settings = get_settings()


async def _download_to_temp(url: str, suffix: str) -> str:
    """Download a remote file to a temporary file."""
    validate_url(url)
    async with httpx.AsyncClient(
        timeout=settings.scraper_default_timeout_seconds,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(resp.content)
            return f.name


async def execute(request: OctopusRequest) -> OctopusResult:
    """
    start = datetime.now(UTC)
    file_path = request.url
    is_remote = file_path.startswith(("http://", "https://"))

    try:
        if is_remote:
            file_path = await _download_to_temp(file_path, ".pdf")
        else:
            if not Path(file_path).exists():
                raise FileNotFoundError(f"Document not found: {file_path}")
    except Exception as exc:
        logger.exception("Document fetch failed for %s", request.url)
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
            error_code="DOCUMENT_FETCH_ERROR",
            error_message=str(exc),
        )

    try:
        parser = PDFParser()
        pdf_result = parser.parse(
            file_path, extract_tables=request.extract_tables
        )

        text = pdf_result.get("text", "")
        metadata = pdf_result.get("metadata", {})
        tables = pdf_result.get("tables", [])

        # Unstructured extraction for additional structure
        try:
            from unstructured.partition.auto import partition  # type: ignore[reportMissingImports]

            elements = partition(filename=file_path)
            unstructured_text = "\n\n".join(str(el) for el in elements)
            if len(unstructured_text) > len(text):
                text = unstructured_text
        except Exception as exc:
            logger.warning("Unstructured extraction failed: %s", exc)

    except Exception as exc:
        logger.exception("Document parsing failed for %s", request.url)
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
            error_code="DOCUMENT_PARSE_ERROR",
            error_message=str(exc),
        )
    finally:
        if is_remote:
            try:
                Path(file_path).unlink(missing_ok=True)
            except Exception:
                pass

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
        document_text=text,
        document_tables=tables,
        document_metadata=metadata,
    )
