"""
CAPTCHA Audio Bypass Solver — Tier 2 of the 4-tier hybrid chain.

Solves reCAPTCHA v2 by switching to the audio challenge, downloading
the MP3, transcribing it with Whisper (faster-whisper preferred, falls
back to openai-whisper), and submitting the transcript.

SRS: SCR-F-020b — Audio CAPTCHA bypass via speech-to-text (>90% target).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def _get_whisper_model(model_size: str = "base") -> Any:
    """Load a Whisper model, preferring faster-whisper then falling back.

    Returns (model, backend_name) tuple.
    """
    # Try faster-whisper first (CTranslate2 — faster, lower memory)
    try:
        from faster_whisper import WhisperModel  # type: ignore[import-untyped]

        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("[Tier2] Loaded faster-whisper model '%s'", model_size)
        return model, "faster-whisper"
    except ImportError:
        pass

    # Fallback to openai-whisper
    try:
        import whisper  # type: ignore[import-untyped]

        model = whisper.load_model(model_size)
        logger.info("[Tier2] Loaded openai-whisper model '%s'", model_size)
        return model, "openai-whisper"
    except ImportError:
        pass

    raise ImportError(
        "No Whisper package found. Install 'faster-whisper' or 'openai-whisper':\n"
        "  pip install faster-whisper   # preferred\n"
        "  pip install openai-whisper   # fallback"
    )


def _transcribe_faster_whisper(model: Any, audio_bytes: bytes) -> str:
    """Transcribe audio bytes using a faster-whisper model."""
    import os
    import tempfile

    # faster-whisper needs a file path
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        segments, info = model.transcribe(tmp_path, beam_size=5)
        text = "".join(seg.text for seg in segments).strip()
        return text
    finally:
        os.unlink(tmp_path)


def _transcribe_openai_whisper(model: Any, audio_bytes: bytes) -> str:
    """Transcribe audio bytes using openai-whisper."""
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        result = model.transcribe(tmp_path)
        return str(result.get("text", "")).strip()
    finally:
        os.unlink(tmp_path)


class AudioCaptchaSolver:
    """Tier 2 — Solve reCAPTCHA v2 via audio challenge + Whisper transcription.

    Usage::

        solver = AudioCaptchaSolver()
        result = await solver.solve_recaptcha_v2(
            page_url="https://example.com",
            site_key="6Le...",
        )
        if result is not None:
            print(result)  # g-recaptcha-response token
    """

    def __init__(self, whisper_model_size: str = "base") -> None:
        self._whisper_model_size = whisper_model_size
        self._model: Any = None
        self._backend: str | None = None

    def _ensure_model(self, model_size: str | None = None) -> None:
        """Lazy-load the Whisper model (only when actually needed)."""
        if self._model is not None and (
            model_size is None or model_size == self._whisper_model_size
        ):
            return
        size = model_size or self._whisper_model_size
        self._model, self._backend = _get_whisper_model(size)
        self._whisper_model_size = size

    def _transcribe(self, audio_bytes: bytes) -> str:
        """Transcribe audio bytes using the loaded model."""
        self._ensure_model()
        if self._backend == "faster-whisper":
            return _transcribe_faster_whisper(self._model, audio_bytes)
        return _transcribe_openai_whisper(self._model, audio_bytes)

    async def solve_recaptcha_v2(
        self,
        page_url: str,
        site_key: str,
        *,
        max_retries: int = 1,
    ) -> dict[str, Any] | None:
        """Attempt to solve reCAPTCHA v2 via audio challenge.

        Returns a dict with ``token`` and ``latency_ms`` on success, or
        ``None`` on failure.  Retries once with a different Whisper model
        size if the first attempt fails.
        """
        t0 = time.monotonic()

        try:
            import playwright.async_api  # noqa: F401
        except ImportError:
            logger.error("playwright not installed — Tier 2 audio solver unavailable")
            return None

        attempt = 0
        model_sizes_to_try = [self._whisper_model_size, "small"]

        while attempt <= max_retries:
            current_model = model_sizes_to_try[
                min(attempt, len(model_sizes_to_try) - 1)
            ]
            attempt += 1

            try:
                result = await self._attempt_solve(
                    page_url,
                    site_key,
                    current_model,
                    t0,
                )
                if result is not None:
                    return result
                logger.info(
                    "[Tier2] Attempt %d failed with model '%s', retrying...",
                    attempt,
                    current_model,
                )
            except Exception as exc:
                logger.warning(
                    "[Tier2] Attempt %d error with model '%s': %s",
                    attempt,
                    current_model,
                    exc,
                )

        latency_ms = (time.monotonic() - t0) * 1000
        logger.warning(
            "[Tier2] Audio solver exhausted all attempts (%.0fms)", latency_ms
        )
        return None

    async def _attempt_solve(
        self,
        page_url: str,
        site_key: str,
        model_size: str,
        t0: float,
    ) -> dict[str, Any] | None:
        """Single solve attempt: navigate → audio challenge → transcribe → submit."""

        try:
            from playwright.async_api import async_playwright  # noqa: F401
        except ImportError:
            return None

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # 1) Navigate to page
                await page.goto(page_url, wait_until="domcontentloaded")
                await asyncio.sleep(2.0)

                # 2) Find and click the reCAPTCHA iframe checkbox
                recaptcha_frame = None
                for frame in page.frames:
                    if "google.com/recaptcha" in (frame.url or ""):
                        recaptcha_frame = frame
                        break

                if recaptcha_frame is None:
                    logger.warning("[Tier2] reCAPTCHA iframe not found on %s", page_url)
                    return None

                checkbox = recaptcha_frame.locator("#recaptcha-anchor")
                await checkbox.click(timeout=5000)
                await asyncio.sleep(1.5)

                # Check if it passed directly (v2 sometimes does)
                try:
                    is_checked = await checkbox.get_attribute("aria-checked")
                    if is_checked == "true":
                        token = await page.evaluate(
                            "document.getElementById('g-recaptcha-response')?.value || ''"
                        )
                        if token:
                            latency_ms = (time.monotonic() - t0) * 1000
                            logger.info(
                                "[Tier2] reCAPTCHA passed without challenge (%.0fms)",
                                latency_ms,
                            )
                            return {"token": token, "latency_ms": latency_ms}
                except Exception:
                    pass

                # 3) A challenge appeared — find the challenge iframe
                challenge_frame = None
                for frame in page.frames:
                    if "bframe" in (frame.url or ""):
                        challenge_frame = frame
                        break

                if challenge_frame is None:
                    logger.warning("[Tier2] Challenge iframe not found")
                    return None

                # 3) Click the audio challenge button (headphones icon)
                audio_button = challenge_frame.locator("#recaptcha-audio-button")
                try:
                    await audio_button.click(timeout=5000)
                except Exception:
                    # Try alternative selector
                    audio_button = challenge_frame.locator(
                        'button[title="Get an audio challenge"]'
                    )
                    await audio_button.click(timeout=5000)

                await asyncio.sleep(1.5)

                # 4) Find the audio source and get the URL
                audio_source = challenge_frame.locator("#audio-source")
                audio_url = await audio_source.get_attribute("src")

                if not audio_url:
                    logger.warning("[Tier2] Audio source URL not found")
                    return None

                # Make URL absolute if needed
                if audio_url.startswith("/"):
                    from urllib.parse import urlparse

                    parsed = urlparse(page_url)
                    audio_url = f"{parsed.scheme}://{parsed.netloc}{audio_url}"

                # 5) Download the audio MP3
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.get(audio_url)
                    resp.raise_for_status()
                    audio_bytes = resp.content

                if len(audio_bytes) < 100:
                    logger.warning(
                        "[Tier2] Audio download too small (%d bytes)", len(audio_bytes)
                    )
                    return None

                # 6) Transcribe using Whisper
                transcript = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self._transcribe,
                    audio_bytes,
                )

                # Clean transcript — keep only alphanumeric and spaces
                transcript = re.sub(r"[^a-zA-Z0-9 ]", "", transcript).strip()

                if not transcript:
                    logger.warning("[Tier2] Transcription empty")
                    return None

                logger.info("[Tier2] Transcribed audio as: '%s'", transcript)

                # 7) Type the transcribed text into the answer field
                answer_input = challenge_frame.locator("#audio-response")
                await answer_input.fill("")
                await answer_input.type(transcript, delay=80)
                await asyncio.sleep(0.5)

                # 8) Click verify
                verify_button = challenge_frame.locator("#recaptcha-verify-button")
                await verify_button.click(timeout=5000)
                await asyncio.sleep(2.0)

                # 9) Check if solved — extract token
                token = await page.evaluate(
                    "document.getElementById('g-recaptcha-response')?.value || "
                    "document.querySelector('[name=\"g-recaptcha-response\"]')?.value || ''"
                )

                if token and len(token) > 20:
                    latency_ms = (time.monotonic() - t0) * 1000
                    logger.info(
                        "[Tier2] reCAPTCHA v2 solved via audio bypass (model=%s, latency=%.0fms)",
                        model_size,
                        latency_ms,
                    )
                    return {"token": token, "latency_ms": latency_ms}

                # Check for error message (wrong answer)
                try:
                    error_el = challenge_frame.locator(
                        ".rc-audiochallenge-error-message"
                    )
                    error_text = await error_el.text_content(timeout=1000)
                    if error_text:
                        logger.info("[Tier2] Audio challenge error: %s", error_text)
                except Exception:
                    pass

                return None

            finally:
                await browser.close()
