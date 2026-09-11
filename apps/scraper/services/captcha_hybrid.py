"""
Hybrid CAPTCHA Solver — Tier 4 chain orchestrator.

Chains all four solving tiers with intelligent routing based on CAPTCHA
type.  Tries AI-native methods first (zero or near-zero cost), then
falls back to commercial human-solving farms for guaranteed coverage.

SRS: SCR-F-020, SCR-F-021, SCR-F-022 — >90% hybrid solve rate.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


class HybridCaptchaSolver:
    """4-tier hybrid CAPTCHA solver with intelligent fallback chain.

    Tier 1: Behavioral Simulation (reCAPTCHA v3) — free, <1s
    Tier 2: Audio Bypass / Whisper STT (reCAPTCHA v2) — free, 2-3s
    Tier 3: Vision LLM (image CAPTCHAs, hCaptcha grids) — ~$0.01, 3-5s
    Tier 4: Human Farm (2Captcha/AntiCaptcha/CapSolver) — $1-3/1K, 10-60s

    Usage::

        solver = HybridCaptchaSolver()
        result = await solver.solve(
            site_key="6Le...",
            page_url="https://example.com",
            captcha_type="recaptcha_v2",
        )
        # result: {token, method_used, latency_ms, tier}
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._behavioral = None
        self._audio = None
        self._vision = None
        self._human_farm = None

    # ── Lazy tier initialization ─────────────────────────────────

    def _get_behavioral_solver(self) -> Any:
        """Tier 1: Behavioral simulation (Playwright-based)."""
        if self._behavioral is None:
            try:
                from apps.scraper.services.captcha_behavioral import (
                    BehavioralCaptchaSolver,
                )

                self._behavioral = BehavioralCaptchaSolver()
                logger.debug("[Hybrid] Tier 1 (behavioral) initialized")
            except Exception as exc:
                logger.warning("[Hybrid] Tier 1 init failed: %s", exc)
        return self._behavioral

    def _get_audio_solver(self) -> Any:
        """Tier 2: Audio bypass with Whisper STT."""
        if self._audio is None:
            try:
                from apps.scraper.services.captcha_audio import AudioCaptchaSolver

                whisper_model = (
                    getattr(self._settings, "captcha_whisper_model", "base") or "base"
                )
                self._audio = AudioCaptchaSolver(whisper_model_size=whisper_model)
                logger.debug("[Hybrid] Tier 2 (audio/whisper) initialized")
            except Exception as exc:
                logger.warning("[Hybrid] Tier 2 init failed: %s", exc)
        return self._audio

    def _get_vision_solver(self) -> Any:
        """Tier 3: Vision LLM solver."""
        if self._vision is None:
            try:
                from apps.scraper.services.captcha_vision import VisionCaptchaSolver

                provider_slug = (
                    getattr(self._settings, "captcha_vision_llm_provider", "groq")
                    or "groq"
                )
                self._vision = VisionCaptchaSolver(provider_slug=provider_slug)
                logger.debug("[Hybrid] Tier 3 (vision LLM) initialized")
            except Exception as exc:
                logger.warning("[Hybrid] Tier 3 init failed: %s", exc)
        return self._vision

    def _get_human_farm_solver(self) -> Any:
        """Tier 4: Commercial human-solving farm (MultiProviderCaptchaSolver)."""
        if self._human_farm is None:
            try:
                from apps.scraper.services.captcha_solver import (
                    MultiProviderCaptchaSolver,
                )

                self._human_farm = MultiProviderCaptchaSolver.from_settings()
                logger.debug("[Hybrid] Tier 4 (human farm) initialized")
            except Exception as exc:
                logger.warning("[Hybrid] Tier 4 init failed: %s", exc)
        return self._human_farm

    @property
    def ai_enabled(self) -> bool:
        """Check if AI-native tiers are enabled via config."""
        return getattr(self._settings, "captcha_ai_enabled", True) is not False

    # ── Main entry point ─────────────────────────────────────────

    async def solve(
        self,
        site_key: str,
        page_url: str,
        captcha_type: str = "recaptcha_v2",
    ) -> dict[str, Any]:
        """Solve a CAPTCHA using the tiered chain.

        Args:
            site_key: The CAPTCHA site key.
            page_url: The page URL where the CAPTCHA appears.
            captcha_type: One of 'recaptcha_v2', 'recaptcha_v3', 'hcaptcha', 'turnstile'.

        Returns:
            Dict with keys: token, method_used, latency_ms, tier

        Raises:
            CaptchaSolveError: If all tiers fail.
        """
        from apps.scraper.services.captcha_solver import CaptchaSolveError

        t0 = time.monotonic()
        errors: list[str] = []

        # Route to the appropriate chain based on CAPTCHA type
        if captcha_type == "recaptcha_v3":
            chain = self._build_recaptcha_v3_chain(site_key, page_url)
        elif captcha_type == "recaptcha_v2":
            chain = self._build_recaptcha_v2_chain(site_key, page_url)
        elif captcha_type == "hcaptcha":
            chain = self._build_hcaptcha_chain(site_key, page_url)
        else:
            # turnstile or unknown — go straight to human farm
            chain = self._build_fallback_chain(site_key, page_url, captcha_type)

        # Execute chain
        for tier_name, solver_fn in chain:
            try:
                result = await solver_fn()
                if result is not None:
                    total_latency = (time.monotonic() - t0) * 1000
                    token = (
                        result if isinstance(result, str) else result.get("token", "")
                    )
                    tier_latency = (
                        result.get("latency_ms", total_latency)
                        if isinstance(result, dict)
                        else total_latency
                    )

                    log_entry = {
                        "token": token,
                        "method_used": tier_name,
                        "latency_ms": round(tier_latency, 1),
                        "tier": tier_name,
                    }

                    logger.info(
                        "[Hybrid] Solved %s via %s (tier_latency=%.0fms, total=%.0fms)",
                        captcha_type,
                        tier_name,
                        tier_latency,
                        total_latency,
                    )
                    return log_entry

            except Exception as exc:
                err_msg = f"[{tier_name}] {exc}"
                logger.warning("[Hybrid] %s failed: %s", tier_name, exc)
                errors.append(err_msg)

        total_latency = (time.monotonic() - t0) * 1000
        raise CaptchaSolveError(
            f"All tiers exhausted for {captcha_type} ({total_latency:.0f}ms): "
            + "; ".join(errors)
        )

    # ── Chain builders ───────────────────────────────────────────

    def _build_recaptcha_v3_chain(
        self,
        site_key: str,
        page_url: str,
    ) -> list[tuple[str, Any]]:
        """reCAPTCHA v3: behavioral → human farm."""
        chain: list[tuple[str, Any]] = []

        if self.ai_enabled:
            solver = self._get_behavioral_solver()
            if solver:
                chain.append(
                    (
                        "tier1_behavioral",
                        lambda s=solver: s.solve_recaptcha_v3(site_key, page_url),
                    )
                )

        farm = self._get_human_farm_solver()
        if farm:
            chain.append(
                (
                    "tier4_human_farm",
                    lambda s=farm: s.solve_recaptcha_v3(site_key, page_url),
                )
            )

        return chain

    def _build_recaptcha_v2_chain(
        self,
        site_key: str,
        page_url: str,
    ) -> list[tuple[str, Any]]:
        """reCAPTCHA v2: audio bypass → human farm."""
        chain: list[tuple[str, Any]] = []

        if self.ai_enabled:
            solver = self._get_audio_solver()
            if solver:
                chain.append(
                    (
                        "tier2_audio_bypass",
                        lambda s=solver: s.solve_recaptcha_v2(page_url, site_key),
                    )
                )

        farm = self._get_human_farm_solver()
        if farm:
            chain.append(
                (
                    "tier4_human_farm",
                    lambda s=farm: s.solve_recaptcha_v2(site_key, page_url),
                )
            )

        return chain

    def _build_hcaptcha_chain(
        self,
        site_key: str,
        page_url: str,
    ) -> list[tuple[str, Any]]:
        """hCaptcha: vision LLM → human farm."""
        chain: list[tuple[str, Any]] = []

        if self.ai_enabled:
            solver = self._get_vision_solver()
            if solver:
                chain.append(
                    (
                        "tier3_vision_llm",
                        lambda s=solver: s.solve_hcaptcha_grid(
                            page_url, site_key, "the required object"
                        ),
                    )
                )

        farm = self._get_human_farm_solver()
        if farm:
            chain.append(
                (
                    "tier4_human_farm",
                    lambda s=farm: s.solve_hcaptcha(site_key, page_url),
                )
            )

        return chain

    def _build_fallback_chain(
        self,
        site_key: str,
        page_url: str,
        captcha_type: str,
    ) -> list[tuple[str, Any]]:
        """Turnstile / unknown: human farm directly."""
        chain: list[tuple[str, Any]] = []

        farm = self._get_human_farm_solver()
        if farm:
            method_name = f"solve_{captcha_type}"
            method = getattr(farm, method_name, None)
            if method:
                chain.append(
                    ("tier4_human_farm", lambda m=method: m(site_key, page_url))
                )
            else:
                # Default to turnstile if method not found
                chain.append(
                    (
                        "tier4_human_farm",
                        lambda s=farm: s.solve_turnstile(site_key, page_url),
                    )
                )

        return chain

    # ── Convenience: direct access to individual tiers ───────────

    async def solve_with_vision(
        self,
        image_bytes: bytes,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Direct access to Tier 3 vision for solving a standalone image CAPTCHA."""
        solver = self._get_vision_solver()
        if solver:
            return await solver.solve_image_captcha(image_bytes, **kwargs)
        return None
