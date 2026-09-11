"""
Scraper anti-bot services.

Provides CAPTCHA solving, proxy rotation, and browser fingerprint
randomization for bypassing anti-bot protections.

The CAPTCHA solver supports a 4-tier hybrid chain:
  Tier 1 — Behavioral Simulation (reCAPTCHA v3)
  Tier 2 — Audio Bypass / Whisper STT (reCAPTCHA v2)
  Tier 3 — Vision LLM (image CAPTCHAs, hCaptcha grids)
  Tier 4 — Human Solving Farm (2Captcha/AntiCaptcha/CapSolver)
"""

from apps.scraper.services.captcha_audio import AudioCaptchaSolver
from apps.scraper.services.captcha_behavioral import BehavioralCaptchaSolver
from apps.scraper.services.captcha_hybrid import HybridCaptchaSolver
from apps.scraper.services.captcha_solver import (
    AntiCaptchaSolver,
    CapSolverSolver,
    CaptchaProviderError,
    CaptchaSolveError,
    CaptchaSolver,
    MultiProviderCaptchaSolver,
    TwoCaptchaSolver,
)
from apps.scraper.services.captcha_vision import VisionCaptchaSolver
from apps.scraper.services.fingerprint import (
    BrowserFingerprint,
    apply_to_context,
    apply_to_page,
    fingerprint_to_headers,
    generate_fingerprint,
)
from apps.scraper.services.proxy_manager import (
    BrightDataIntegration,
    OxylabsIntegration,
    ProxyEntry,
    ProxyManager,
    ProxyStats,
    SmartProxyIntegration,
)

__all__ = [
    # CAPTCHA solving — human farm (Tier 4)
    "CaptchaSolver",
    "TwoCaptchaSolver",
    "AntiCaptchaSolver",
    "CapSolverSolver",
    "MultiProviderCaptchaSolver",
    "CaptchaSolveError",
    "CaptchaProviderError",
    # CAPTCHA solving — AI-native (Tiers 1-3)
    "BehavioralCaptchaSolver",
    "AudioCaptchaSolver",
    "VisionCaptchaSolver",
    # CAPTCHA solving — hybrid chain (all tiers)
    "HybridCaptchaSolver",
    # Proxy management
    "ProxyManager",
    "ProxyEntry",
    "ProxyStats",
    "BrightDataIntegration",
    "SmartProxyIntegration",
    "OxylabsIntegration",
    # Browser fingerprinting
    "BrowserFingerprint",
    "generate_fingerprint",
    "apply_to_page",
    "apply_to_context",
    "fingerprint_to_headers",
]
