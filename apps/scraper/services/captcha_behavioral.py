"""
CAPTCHA Behavioral Simulation Solver — Tier 1 of the 4-tier hybrid chain.

Simulates realistic human browser interactions (mouse movement via Bézier
curves, scrolling, keyboard events, page dwell time) to pass reCAPTCHA v3
score-based challenges without any external API call.

SRS: SCR-F-020a — Behavioral signals for reCAPTCHA v3 (score >= 0.7, 70% target).
"""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any

logger = logging.getLogger(__name__)


class BehavioralCaptchaSolver:
    """Tier 1 — Solve reCAPTCHA v3 by simulating human behavior in Playwright.

    Usage::

        solver = BehavioralCaptchaSolver()
        result = await solver.solve_recaptcha_v3(
            site_key="6Le...",
            page_url="https://example.com",
        )
        if result is not None:
            print(result)  # g-recaptcha-response token
    """

    # ── Helpers ───────────────────────────────────────────────────

    @staticmethod
    def _bezier_curve(
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        steps: int = 30,
    ) -> list[tuple[float, float]]:
        """Return *steps* points along a cubic Bézier curve from *p0* to *p3*.

        Control points *p1* and *p2* shape the curve so that mouse
        movement looks natural rather than linear.
        """
        points: list[tuple[float, float]] = []
        for i in range(steps + 1):
            t = i / steps
            u = 1.0 - t
            x = (
                u**3 * p0[0]
                + 3 * u**2 * t * p1[0]
                + 3 * u * t**2 * p2[0]
                + t**3 * p3[0]
            )
            y = (
                u**3 * p0[1]
                + 3 * u**2 * t * p1[1]
                + 3 * u * t**2 * p2[1]
                + t**3 * p3[1]
            )
            points.append((x, y))
        return points

    @staticmethod
    def _random_human_delay(min_ms: int = 50, max_ms: int = 150) -> float:
        """Return a random delay in seconds, modelling human reaction time.

        Uses a truncated normal distribution so that most delays cluster
        around the midpoint with occasional outliers — just like real
        human input timing.
        """
        mid = (min_ms + max_ms) / 2
        std = (max_ms - min_ms) / 6
        delay_ms = random.gauss(mid, std)
        delay_ms = max(min_ms, min(max_ms, delay_ms))
        return delay_ms / 1000.0

    # ── Mouse simulation ─────────────────────────────────────────

    async def _simulate_mouse_movements(
        self,
        page: Any,
        viewport: dict[str, int],
    ) -> None:
        """Generate 3-6 Bézier-curve mouse movements across the viewport."""
        vw = viewport.get("width", 1280)
        vh = viewport.get("height", 720)
        num_movements = random.randint(3, 6)

        current = (random.uniform(100, vw - 100), random.uniform(100, vh - 100))

        for _ in range(num_movements):
            target = (random.uniform(50, vw - 50), random.uniform(50, vh - 50))
            # Random control points to create a curved path
            ctrl1 = (
                current[0] + random.uniform(-200, 200),
                current[1] + random.uniform(-200, 200),
            )
            ctrl2 = (
                target[0] + random.uniform(-200, 200),
                target[1] + random.uniform(-200, 200),
            )

            steps = random.randint(20, 50)
            curve = self._bezier_curve(current, ctrl1, ctrl2, target, steps)

            for x, y in curve:
                await page.mouse.move(x, y)
                await asyncio.sleep(self._random_human_delay(5, 25))

            current = target

    # ── Scroll simulation ────────────────────────────────────────

    async def _simulate_scrolls(self, page: Any) -> None:
        """Simulate 2-4 natural scroll events (down and partial up)."""
        num_scrolls = random.randint(2, 4)
        for _ in range(num_scrolls):
            delta_y = random.randint(100, 400)
            await page.mouse.wheel(0, delta_y)
            await asyncio.sleep(self._random_human_delay(300, 800))

        # Occasional scroll back up
        if random.random() < 0.4:
            await page.mouse.wheel(0, -random.randint(50, 150))
            await asyncio.sleep(self._random_human_delay(200, 500))

    # ── Keyboard simulation ──────────────────────────────────────

    async def _simulate_keyboard(self, page: Any) -> None:
        """Simulate a few benign keyboard events (Tab, arrow keys)."""
        keys = ["Tab", "Tab", "ArrowDown", "ArrowUp", "Tab"]
        num_presses = random.randint(1, 3)
        for key in random.sample(keys, min(num_presses, len(keys))):
            await page.keyboard.press(key)
            await asyncio.sleep(self._random_human_delay(80, 200))

    # ── Main solve method ────────────────────────────────────────

    async def solve_recaptcha_v3(
        self,
        site_key: str,
        page_url: str,
        *,
        action: str = "verify",
    ) -> dict[str, Any] | None:
        """Attempt to solve a reCAPTCHA v3 challenge via behavioral simulation.

        Returns a dict with ``token`` and ``latency_ms`` on success, or
        ``None`` if the score was too low (challenge appeared) — in that
        case the caller should escalate to the next tier.
        """
        t0 = time.monotonic()

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error(
                "playwright not installed — Tier 1 behavioral solver unavailable"
            )
            return None

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(headless=True)
                context = await browser.new_context()
                page = await context.new_page()
                viewport = page.viewport_size or {"width": 1280, "height": 720}

                # 1) Navigate to page
                await page.goto(page_url, wait_until="domcontentloaded")

                # 2) Page dwell time (3-7 seconds)
                dwell = random.uniform(3.0, 7.0)
                await asyncio.sleep(dwell)

                # 3) Simulate mouse movements
                await self._simulate_mouse_movements(page, viewport)  # type: ignore[reportArgumentType]

                # 4) Simulate scrolling
                await self._simulate_scrolls(page)

                # 5) Simulate keyboard events
                await self._simulate_keyboard(page)

                # 6) Click the reCAPTCHA checkbox
                recaptcha_frame = None
                for frame in page.frames:
                    if "google.com/recaptcha" in (frame.url or ""):
                        recaptcha_frame = frame
                        break

                if recaptcha_frame is None:
                    logger.warning("[Tier1] reCAPTCHA iframe not found on %s", page_url)
                    await browser.close()
                    return None

                # Click the checkbox inside the reCAPTCHA iframe
                checkbox = recaptcha_frame.locator("#recaptcha-anchor")
                try:
                    await checkbox.click(timeout=5000)
                except Exception as exc:
                    logger.warning(
                        "[Tier1] Could not click reCAPTCHA checkbox: %s", exc
                    )
                    await browser.close()
                    return None

                # 7) Wait and check result
                await asyncio.sleep(2.0)

                # Check if the checkbox is checked (aria-checked="true")
                try:
                    is_checked = await checkbox.get_attribute("aria-checked")
                except Exception:
                    is_checked = None

                if is_checked == "true":
                    # 8) Extract g-recaptcha-response token
                    token = await page.evaluate(
                        "document.getElementById('g-recaptcha-response')?.value || "
                        "document.querySelector('[name=\"g-recaptcha-response\"]')?.value || ''"
                    )
                    latency_ms = (time.monotonic() - t0) * 1000

                    await browser.close()

                    if token:
                        logger.info(
                            "[Tier1] reCAPTCHA v3 solved via behavioral simulation "
                            "(latency=%.0fms)",
                            latency_ms,
                        )
                        return {"token": token, "latency_ms": latency_ms}

                # 9) Challenge appeared or checkbox not checked — escalate
                logger.info(
                    "[Tier1] Behavioral simulation did not pass (challenge or low score), "
                    "escalating to next tier"
                )
                await browser.close()
                return None

        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            logger.warning(
                "[Tier1] Behavioral solver failed after %.0fms: %s",
                latency_ms,
                exc,
            )
            return None
