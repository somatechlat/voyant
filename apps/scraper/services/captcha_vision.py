"""
CAPTCHA Vision LLM Solver — Tier 3 of the 4-tier hybrid chain.

Uses a vision-capable LLM to solve image-based CAPTCHAs and hCaptcha
image-grid challenges by screenshotting the challenge, sending the image
to the LLM, and parsing its textual answer.

SRS: SCR-F-020c — Vision LLM CAPTCHA solving (>70% text, image grids).
"""

from __future__ import annotations

import asyncio
import base64
import logging
import re
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default prompts
_TEXT_CAPTCHA_PROMPT = (
    "What text or characters are shown in this CAPTCHA image? "
    "Answer with only the characters, no explanation."
)

_HCAPTCHA_GRID_PROMPT_TEMPLATE = (
    "In this image grid, which numbered tiles (1-9 from left to right, "
    "top to bottom) contain {instruction}? List only the numbers separated "
    "by commas. Example: 2, 5, 7"
)


class VisionCaptchaSolver:
    """Tier 3 — Solve image CAPTCHAs and hCaptcha grids via vision LLM.

    Uses any OpenAI-compatible API that supports vision (image input).
    Falls back through configured providers.

    Usage::

        solver = VisionCaptchaSolver()
        # Text CAPTCHA
        answer = await solver.solve_image_captcha(image_bytes)
        # hCaptcha grid
        tiles = await solver.solve_hcaptcha_grid(page_url, site_key, instruction)
    """

    def __init__(
        self,
        provider_slug: str | None = None,
        api_base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        self._provider_slug = provider_slug
        self._api_base_url = api_base_url
        self._api_key = api_key
        self._model = model

    # ── Configuration resolution ─────────────────────────────────

    def _resolve_config(self) -> dict[str, str]:
        """Resolve LLM config from explicit params, DB, or env settings.

        Returns dict with api_base_url, api_key, model.
        """
        # 1) Use explicitly set values
        if self._api_base_url and self._api_key and self._model:
            return {
                "api_base_url": self._api_base_url,
                "api_key": self._api_key,
                "model": self._model,
            }

        # 2) Try to resolve from DB (ActiveLLMConfig or LLMProvider by slug)
        try:
            from apps.llm_providers.models import ActiveLLMConfig, LLMProvider

            # Try ActiveLLMConfig for scraper purpose
            active_config = (
                ActiveLLMConfig.objects.filter(purpose="scraper")
                .select_related("provider", "model")
                .first()
            )
            if active_config and active_config.provider and active_config.model:
                return {
                    "api_base_url": active_config.provider.api_base_url,
                    "api_key": active_config.provider.api_key,
                    "model": active_config.model.name,
                }

            # Try by slug
            slug = self._provider_slug or "groq"
            provider = LLMProvider.objects.filter(slug=slug, status="active").first()
            if provider:
                vision_model = (
                    provider.models.filter(status="active", supports_vision=True)  # type: ignore[attr-defined]
                    .order_by("-is_default", "name")
                    .first()
                )
                if vision_model:
                    return {
                        "api_base_url": provider.api_base_url,
                        "api_key": provider.api_key,
                        "model": vision_model.name,
                    }
        except Exception as exc:
            logger.debug("[Tier3] Could not resolve LLM config from DB: %s", exc)

        # 3) Fall back to global env settings
        try:
            from apps.core.config import get_settings

            settings = get_settings()
            return {
                "api_base_url": settings.llm_api_url,
                "api_key": settings.llm_api_key,
                "model": settings.llm_model,
            }
        except Exception as exc:
            logger.warning(
                "[Tier3] Could not resolve LLM config from settings: %s", exc
            )
            return {"api_base_url": "", "api_key": "", "model": ""}

    # ── LLM call ─────────────────────────────────────────────────

    async def _call_vision_llm(
        self,
        image_b64: str,
        prompt: str,
        *,
        mime_type: str = "image/png",
    ) -> str:
        """Send an image to the vision LLM and return the text response."""
        config = self._resolve_config()
        api_base = config["api_base_url"].rstrip("/")
        api_key = config["api_key"]
        model = config["model"]

        if not api_base or not api_key:
            raise RuntimeError(
                "No LLM provider configured for vision CAPTCHA solving. "
                "Set VOYANT_LLM_API_KEY or configure an LLM provider with vision support."
            )

        # Build OpenAI-compatible chat completion with image
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_b64}",
                            },
                        },
                    ],
                }
            ],
            "temperature": 0.0,
            "max_tokens": 256,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{api_base}/chat/completions",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        # Extract content from response
        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            return str(content).strip()

        return ""

    # ── Text CAPTCHA solver ──────────────────────────────────────

    async def solve_image_captcha(
        self,
        image_bytes: bytes,
        *,
        prompt: str | None = None,
        mime_type: str = "image/png",
    ) -> dict[str, Any] | None:
        """Solve a text/image CAPTCHA using the vision LLM.

        Args:
            image_bytes: Raw image bytes (PNG, JPEG, GIF).
            prompt: Optional custom prompt override.
            mime_type: MIME type of the image.

        Returns:
            Dict with ``token`` (the extracted text) and ``latency_ms``,
            or ``None`` if the LLM couldn't extract a usable answer.
        """
        t0 = time.monotonic()

        try:
            image_b64 = base64.b64encode(image_bytes).decode("ascii")
            effective_prompt = prompt or _TEXT_CAPTCHA_PROMPT

            response_text = await self._call_vision_llm(
                image_b64,
                effective_prompt,
                mime_type=mime_type,
            )

            # Parse: extract alphanumeric characters from the response
            answer = re.sub(r"[^a-zA-Z0-9]", "", response_text).strip()

            latency_ms = (time.monotonic() - t0) * 1000

            if answer:
                logger.info(
                    "[Tier3] Vision LLM solved image CAPTCHA: '%s' (%.0fms)",
                    answer,
                    latency_ms,
                )
                return {"token": answer, "latency_ms": latency_ms}

            logger.warning(
                "[Tier3] Vision LLM returned no usable answer: '%s'", response_text
            )
            return None

        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            logger.warning(
                "[Tier3] Vision CAPTCHA solve failed after %.0fms: %s",
                latency_ms,
                exc,
            )
            return None

    # ── hCaptcha grid solver ─────────────────────────────────────

    async def solve_hcaptcha_grid(
        self,
        page_url: str,
        site_key: str,
        instruction: str,
    ) -> dict[str, Any] | None:
        """Solve an hCaptcha image-grid challenge using the vision LLM.

        1. Opens the page, clicks the hCaptcha checkbox
        2. Screenshots the challenge overlay
        3. Sends to the vision LLM with the instruction
        4. Parses the LLM's tile-number response
        5. Clicks matching tiles and verifies

        Returns dict with ``token`` and ``latency_ms`` on success, or ``None``.
        """
        t0 = time.monotonic()

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error(
                "playwright not installed — Tier 3 hCaptcha solver unavailable"
            )
            return None

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()

                try:
                    # 1) Navigate to page
                    await page.goto(page_url, wait_until="domcontentloaded")
                    await asyncio.sleep(2.0)

                    # 2) Find and click hCaptcha checkbox
                    hcaptcha_frame = None
                    for frame in page.frames:
                        if "hcaptcha.com" in (frame.url or ""):
                            hcaptcha_frame = frame
                            break

                    if hcaptcha_frame is None:
                        logger.warning(
                            "[Tier3] hCaptcha iframe not found on %s", page_url
                        )
                        return None

                    checkbox = hcaptcha_frame.locator("#checkbox")
                    await checkbox.click(timeout=5000)
                    await asyncio.sleep(2.0)

                    # 3) Screenshot the challenge
                    # The challenge is in a separate iframe
                    challenge_frame = None
                    for frame in page.frames:
                        if (
                            "hcaptcha.com" in (frame.url or "")
                            and frame != hcaptcha_frame
                        ):
                            challenge_frame = frame
                            break

                    if challenge_frame is None:
                        # Sometimes it's the same frame
                        challenge_frame = hcaptcha_frame

                    # Take a screenshot of the challenge area
                    challenge_element = challenge_frame.locator(
                        ".challenge-container, .task-image, #challenge"
                    )
                    try:
                        screenshot_bytes = await challenge_element.screenshot(
                            timeout=5000
                        )
                    except Exception:
                        # Fallback: screenshot the whole page
                        screenshot_bytes = await page.screenshot()

                    # 4) Send to vision LLM
                    image_b64 = base64.b64encode(screenshot_bytes).decode("ascii")
                    prompt = _HCAPTCHA_GRID_PROMPT_TEMPLATE.format(
                        instruction=instruction
                    )

                    response_text = await self._call_vision_llm(image_b64, prompt)

                    # 5) Parse tile numbers from LLM response
                    tile_numbers = self._parse_tile_numbers(response_text)

                    if not tile_numbers:
                        logger.warning(
                            "[Tier3] Could not parse tile numbers from: '%s'",
                            response_text,
                        )
                        return None

                    logger.info("[Tier3] Vision LLM identified tiles: %s", tile_numbers)

                    # 6) Click matching tiles
                    tiles = challenge_frame.locator(".task-image, .image-wrapper")
                    tile_count = await tiles.count()

                    for num in tile_numbers:
                        idx = num - 1  # Convert to 0-based
                        if 0 <= idx < tile_count:
                            await tiles.nth(idx).click()
                            await asyncio.sleep(0.3)

                    # 7) Click submit/verify
                    try:
                        submit = challenge_frame.locator(
                            'button[type="submit"], .button-submit, #solve'
                        )
                        await submit.click(timeout=3000)
                    except Exception:
                        pass

                    await asyncio.sleep(2.0)

                    # 8) Check for token
                    token = await page.evaluate(
                        'document.querySelector("[name=h-captcha-response]")?.value || '
                        'document.querySelector("[data-hcaptcha-response]")?.getAttribute("data-hcaptcha-response") || ""'
                    )

                    if token and len(token) > 20:
                        latency_ms = (time.monotonic() - t0) * 1000
                        logger.info(
                            "[Tier3] hCaptcha solved via vision LLM (%.0fms)",
                            latency_ms,
                        )
                        return {"token": token, "latency_ms": latency_ms}

                    return None

                finally:
                    await browser.close()

        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            logger.warning(
                "[Tier3] hCaptcha grid solve failed after %.0fms: %s",
                latency_ms,
                exc,
            )
            return None

    # ── Parsing helpers ──────────────────────────────────────────

    @staticmethod
    def _parse_tile_numbers(response: str) -> list[int]:
        """Extract tile numbers (1-9) from the LLM response text.

        Handles formats like: "1, 3, 5" / "1 3 5" / "Tiles: 2, 4, 7"
        """
        numbers = []
        for match in re.finditer(r"\b([1-9])\b", response):
            num = int(match.group(1))
            if num not in numbers:
                numbers.append(num)
        return sorted(numbers)
