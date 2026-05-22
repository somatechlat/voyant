"""
ARM-7b: Audio/video transcription with OpenAI Whisper.

Transcribes media files into text, JSON, or SRT formats.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx

from apps.core.config import get_settings
from apps.scraper.octopus.schemas import OctopusRequest, OctopusResult
from apps.scraper.security import validate_url

logger = logging.getLogger(__name__)
settings = get_settings()


async def _fetch_media(url: str) -> str:
    """Download media to a temporary file and return its path."""
    validate_url(url)
    async with httpx.AsyncClient(
        timeout=settings.scraper_default_timeout_seconds
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        suffix = ".mp3"
        if "mp4" in ct:
            suffix = ".mp4"
        elif "wav" in ct:
            suffix = ".wav"
        elif "webm" in ct:
            suffix = ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(resp.content)
            return f.name


def _srt_time(seconds: float) -> str:
    """Convert seconds to SRT timestamp format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _format_transcription(result: Dict[str, Any], fmt: str) -> str:
    """Format a Whisper result into text, JSON, or SRT."""
    if fmt == "json":
        import json

        return json.dumps(result, ensure_ascii=False)
    if fmt == "srt":
        segments: List[Dict[str, Any]] = result.get("segments", [])
        lines: List[str] = []
        for i, seg in enumerate(segments, start=1):
            start_sec = seg.get("start", 0)
            end_sec = seg.get("end", 0)
            text_seg = seg.get("text", "").strip()
            lines.append(str(i))
            lines.append(
                f"{_srt_time(start_sec)} --> {_srt_time(end_sec)}"
            )
            lines.append(text_seg)
            lines.append("")
        return "\n".join(lines)
    return result.get("text", "")


async def execute(request: OctopusRequest) -> OctopusResult:
    """
    Execute ARM-7b transcription.

    Downloads the media file and transcribes it with the requested
    Whisper model and language.

    Args:
        request: The OctopusRequest pointing to a media file.

    Returns:
        An OctopusResult with transcription text and segments.
    """
    start = datetime.now(timezone.utc)
    temp_path = ""
    is_remote = request.url.startswith(("http://", "https://"))

    try:
        if is_remote:
            temp_path = await _fetch_media(request.url)
        else:
            temp_path = request.url
            if not Path(temp_path).exists():
                raise FileNotFoundError(
                    f"Media file not found: {temp_path}"
                )
    except Exception as exc:
        logger.exception("Media fetch failed for %s", request.url)
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
            error_code="TRANSCRIBE_FETCH_ERROR",
            error_message=str(exc),
        )

    try:
        import whisper

        model = whisper.load_model(request.whisper_model)
        result = model.transcribe(
            temp_path, language=request.language
        )
    except Exception as exc:
        logger.exception("Whisper transcription failed for %s", request.url)
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
            error_code="TRANSCRIBE_ERROR",
            error_message=str(exc),
        )
    finally:
        if is_remote and temp_path:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    transcription_text = _format_transcription(
        result, request.transcription_format
    )
    segments: List[Dict[str, Any]] = []
    raw_segments = result.get("segments", [])
    if isinstance(raw_segments, list):
        segments = raw_segments

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
        transcription=transcription_text,
        transcription_language=request.language,
        transcription_segments=segments,
    )
