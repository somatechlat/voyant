"""
Browser Fingerprint Randomizer — Anti-detection fingerprint generation.

Generates realistic, randomized browser fingerprints and applies them
to Playwright pages at context-creation time.  Covers user-agent,
viewport, WebGL, canvas noise, AudioContext, navigator properties,
and screen characteristics.

SRS: SCR-F-024 — Fingerprint randomization for anti-bot evasion.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ===================================================================
# Realistic data pools for fingerprint generation
# ===================================================================

# Chrome versions (stable channel, recent)
_CHROME_VERSIONS = [
    (124, 0, 6367, 118),
    (123, 0, 6312, 109),
    (122, 0, 6261, 121),
    (121, 0, 6167, 175),
    (120, 0, 6099, 208),
    (119, 0, 6045, 198),
    (118, 0, 5993, 112),
]

_FIREFOX_VERSIONS = [126, 125, 124, 123, 122, 121, 120]

_SAFARI_VERSIONS = [
    (17, 5, 1),
    (17, 4, 0),
    (17, 3, 1),
    (17, 2, 0),
    (16, 6, 1),
]

_WINDOWS_VERSIONS = ["10.0", "10.0", "10.0", "11.0"]  # weighted
_MAC_VERSIONS = [
    "10_15_7",
    "13_0_0",
    "13_1_0",
    "14_0_0",
    "14_1_0",
    "14_2_0",
    "14_3_1",
]
_LINUX_PLATFORMS = ["Linux x86_64", "Linux x86_64"]

# Common desktop resolutions
_DESKTOP_VIEWPORTS = [
    (1920, 1080),
    (1920, 1080),  # weighted
    (2560, 1440),
    (1366, 768),
    (1536, 864),
    (1440, 900),
    (1280, 720),
    (1680, 1050),
    (2560, 1600),
    (3840, 2160),
]

# WebGL vendor/renderer combos (Intel, NVIDIA, AMD)
_WEBGL_CONFIGS = [
    ("Intel Inc.", "Intel Iris OpenGL Engine"),
    ("Intel Inc.", "Intel(R) UHD Graphics 630"),
    ("Intel Inc.", "Intel(R) Iris(R) Xe Graphics"),
    ("Intel Inc.", "Intel(R) HD Graphics 630"),
    ("NVIDIA Corporation", "NVIDIA GeForce GTX 1060 6GB/PCIe/SSE2"),
    ("NVIDIA Corporation", "NVIDIA GeForce GTX 1080/PCIe/SSE2"),
    ("NVIDIA Corporation", "NVIDIA GeForce RTX 3060/PCIe/SSE2"),
    ("NVIDIA Corporation", "NVIDIA GeForce RTX 3070/PCIe/SSE2"),
    ("NVIDIA Corporation", "NVIDIA GeForce RTX 4070/PCIe/SSE2"),
    ("ATI Technologies Inc.", "AMD Radeon RX 580"),
    ("ATI Technologies Inc.", "AMD Radeon RX 6700 XT"),
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630, OpenGL 4.5)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1060 6GB, OpenGL 4.5)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070, OpenGL 4.5)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580, OpenGL 4.5)"),
]

# Navigator language lists
_LANGUAGES = [
    ["en-US", "en"],
    ["en-US", "en", "es"],
    ["en-US", "en-GB", "en"],
    ["en-US"],
    ["en-GB", "en-US", "en"],
    ["es-ES", "es", "en-US", "en"],
    ["fr-FR", "fr", "en-US", "en"],
    ["de-DE", "de", "en-US", "en"],
    ["ja-JP", "ja", "en-US", "en"],
    ["zh-CN", "zh", "en-US", "en"],
]

# Hardware concurrency (number of logical CPU cores)
_HARDWARE_CONCURRENCY = [2, 4, 4, 8, 8, 8, 12, 16, 16]

# Device memory in GB
_DEVICE_MEMORY = [4, 8, 8, 8, 16, 16, 16, 32, 32]

# Screen properties
_COLOR_DEPTHS = [24, 24, 24, 30, 32]
_PIXEL_RATIOS = [1.0, 1.0, 1.25, 1.5, 2.0, 2.0]

# Platform strings
_PLATFORMS = [
    "Win32",
    "Win32",
    "Win32",
    "MacIntel",
    "MacIntel",
    "Linux x86_64",
]


# ===================================================================
# Fingerprint dataclass
# ===================================================================


@dataclass
class BrowserFingerprint:
    """A randomized browser fingerprint profile.

    Call ``generate_fingerprint()`` to create a new random fingerprint
    or use the ``random()`` classmethod for convenience.

    Apply to a Playwright page with ``apply_to_page(page)``.
    """

    # User-Agent
    user_agent: str = ""

    # Viewport
    viewport_width: int = 1920
    viewport_height: int = 1080

    # WebGL
    webgl_vendor: str = "Intel Inc."
    webgl_renderer: str = "Intel Iris OpenGL Engine"

    # Navigator
    platform: str = "Win32"
    languages: list[str] = field(default_factory=lambda: ["en-US", "en"])
    hardware_concurrency: int = 8
    device_memory: int = 8

    # Screen
    color_depth: int = 24
    pixel_depth: int = 24
    device_pixel_ratio: float = 1.0

    # Canvas noise seed (deterministic per fingerprint)
    canvas_noise_seed: float = 0.0

    # Audio context noise
    audio_noise_seed: float = 0.0

    # ----------------------------------------------------------------
    # Generation
    # ----------------------------------------------------------------

    def generate_fingerprint(self) -> dict[str, Any]:
        """Generate a fully randomized fingerprint and populate all fields.

        Returns:
            A dict of all fingerprint properties, ready for JSON serialization
            or storage in ``ScrapeFingerprint``.
        """
        self._randomize_all()
        return self.to_dict()

    @classmethod
    def random(cls) -> BrowserFingerprint:
        """Create a fully randomized fingerprint instance."""
        fp = cls()
        fp._randomize_all()
        return fp

    # ----------------------------------------------------------------
    # Serialization
    # ----------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "user_agent": self.user_agent,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "webgl_vendor": self.webgl_vendor,
            "webgl_renderer": self.webgl_renderer,
            "platform": self.platform,
            "languages": self.languages,
            "hardware_concurrency": self.hardware_concurrency,
            "device_memory": self.device_memory,
            "color_depth": self.color_depth,
            "pixel_depth": self.pixel_depth,
            "device_pixel_ratio": self.device_pixel_ratio,
            "canvas_noise_seed": self.canvas_noise_seed,
            "audio_noise_seed": self.audio_noise_seed,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BrowserFingerprint:
        """Reconstruct from a dict (e.g., from DB or JSON)."""
        return cls(
            user_agent=data.get("user_agent", ""),
            viewport_width=int(data.get("viewport_width", 1920)),
            viewport_height=int(data.get("viewport_height", 1080)),
            webgl_vendor=data.get("webgl_vendor", "Intel Inc."),
            webgl_renderer=data.get("webgl_renderer", "Intel Iris OpenGL Engine"),
            platform=data.get("platform", "Win32"),
            languages=data.get("languages", ["en-US", "en"]),
            hardware_concurrency=int(data.get("hardware_concurrency", 8)),
            device_memory=int(data.get("device_memory", 8)),
            color_depth=int(data.get("color_depth", 24)),
            pixel_depth=int(data.get("pixel_depth", 24)),
            device_pixel_ratio=float(data.get("device_pixel_ratio", 1.0)),
            canvas_noise_seed=float(data.get("canvas_noise_seed", 0.0)),
            audio_noise_seed=float(data.get("audio_noise_seed", 0.0)),
        )

    # ----------------------------------------------------------------
    # Playwright integration
    # ----------------------------------------------------------------

    async def apply_to_page(self, page: Any) -> None:
        """Apply this fingerprint to a Playwright Page via JavaScript injection.

        Overrides navigator, screen, WebGL, canvas, and AudioContext
        properties to match this fingerprint.  Must be called *before*
        navigation to the target URL.

        Args:
            page: A Playwright ``Page`` instance.
        """
        js_overrides = self._build_js_overrides()
        await page.add_init_script(js_overrides)
        logger.debug(
            "Applied fingerprint to page (UA=%s, viewport=%dx%d, WebGL=%s)",
            self.user_agent[:80],
            self.viewport_width,
            self.viewport_height,
            self.webgl_renderer[:50],
        )

    # ----------------------------------------------------------------
    # Internal randomization
    # ----------------------------------------------------------------

    def _randomize_all(self) -> None:
        """Randomize every field."""
        self._randomize_user_agent()
        self._randomize_viewport()
        self._randomize_webgl()
        self._randomize_navigator()
        self._randomize_screen()
        self.canvas_noise_seed = random.uniform(0, 1_000_000)
        self.audio_noise_seed = random.uniform(0, 1_000_000)

    def _randomize_user_agent(self) -> None:
        """Pick a random platform and build a matching user agent."""
        self.platform = random.choice(_PLATFORMS)

        if self.platform == "Win32":
            ver = random.choice(_CHROME_VERSIONS)
            win_ver = random.choice(_WINDOWS_VERSIONS)
            self.user_agent = (
                f"Mozilla/5.0 (Windows NT {win_ver}; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{ver[0]}.0.0.0 Safari/537.36"
            )
        elif self.platform == "MacIntel":
            ver = random.choice(_CHROME_VERSIONS)
            mac_ver = random.choice(_MAC_VERSIONS)
            self.user_agent = (
                f"Mozilla/5.0 (Macintosh; Intel Mac OS X {mac_ver}) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{ver[0]}.0.0.0 Safari/537.36"
            )
        else:  # Linux
            ver = random.choice(_CHROME_VERSIONS)
            self.user_agent = (
                f"Mozilla/5.0 (X11; Linux x86_64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{ver[0]}.0.0.0 Safari/537.36"
            )

    def _randomize_viewport(self) -> None:
        vp = random.choice(_DESKTOP_VIEWPORTS)
        self.viewport_width = vp[0]
        self.viewport_height = vp[1]

    def _randomize_webgl(self) -> None:
        cfg = random.choice(_WEBGL_CONFIGS)
        self.webgl_vendor = cfg[0]
        self.webgl_renderer = cfg[1]

    def _randomize_navigator(self) -> None:
        self.languages = random.choice(_LANGUAGES)
        self.hardware_concurrency = random.choice(_HARDWARE_CONCURRENCY)
        self.device_memory = random.choice(_DEVICE_MEMORY)

    def _randomize_screen(self) -> None:
        self.color_depth = random.choice(_COLOR_DEPTHS)
        self.pixel_depth = self.color_depth
        self.device_pixel_ratio = random.choice(_PIXEL_RATIOS)

    # ----------------------------------------------------------------
    # JavaScript override builder
    # ----------------------------------------------------------------

    def _build_js_overrides(self) -> str:
        """Build a JavaScript snippet that overrides browser APIs."""
        # Escape strings for safe JS embedding
        ua = _js_escape(self.user_agent)
        vendor = _js_escape(self.webgl_vendor)
        renderer = _js_escape(self.webgl_renderer)
        platform = _js_escape(self.platform)
        langs = self.languages
        hc = self.hardware_concurrency
        dm = self.device_memory
        vw = self.viewport_width
        vh = self.viewport_height
        cd = self.color_depth
        pd = self.pixel_depth
        dpr = self.device_pixel_ratio
        canvas_seed = self.canvas_noise_seed
        audio_seed = self.audio_noise_seed

        return f"""
(() => {{
  // --- User-Agent ---
  Object.defineProperty(navigator, 'userAgent', {{
    get: () => '{ua}',
    configurable: true,
  }});

  // --- Platform ---
  Object.defineProperty(navigator, 'platform', {{
    get: () => '{platform}',
    configurable: true,
  }});

  // --- Languages ---
  Object.defineProperty(navigator, 'languages', {{
    get: () => {langs!r},
    configurable: true,
  }});
  Object.defineProperty(navigator, 'language', {{
    get: () => '{langs[0]}',
    configurable: true,
  }});

  // --- Hardware Concurrency ---
  Object.defineProperty(navigator, 'hardwareConcurrency', {{
    get: () => {hc},
    configurable: true,
  }});

  // --- Device Memory ---
  Object.defineProperty(navigator, 'deviceMemory', {{
    get: () => {dm},
    configurable: true,
  }});

  // --- Screen ---
  if (window.screen) {{
    Object.defineProperty(screen, 'colorDepth', {{ get: () => {cd}, configurable: true }});
    Object.defineProperty(screen, 'pixelDepth', {{ get: () => {pd}, configurable: true }});
    Object.defineProperty(screen, 'width', {{ get: () => {vw}, configurable: true }});
    Object.defineProperty(screen, 'height', {{ get: () => {vh}, configurable: true }});
    Object.defineProperty(screen, 'availWidth', {{ get: () => {vw}, configurable: true }});
    Object.defineProperty(screen, 'availHeight', {{ get: () => {vh - 40}, configurable: true }});
  }}
  Object.defineProperty(window, 'devicePixelRatio', {{ get: () => {dpr}, configurable: true }});

  // --- WebGL ---
  const _origGetParam = WebGLRenderingContext.prototype.getParameter;
  WebGLRenderingContext.prototype.getParameter = function(param) {{
    const ext = this.getExtension('WEBGL_debug_renderer_info');
    if (ext) {{
      if (param === ext.UNMASKED_VENDOR_WEBGL) return '{vendor}';
      if (param === ext.UNMASKED_RENDERER_WEBGL) return '{renderer}';
    }}
    return _origGetParam.call(this, param);
  }};

  const _origGetParam2 = WebGL2RenderingContext.prototype.getParameter;
  WebGL2RenderingContext.prototype.getParameter = function(param) {{
    const ext = this.getExtension('WEBGL_debug_renderer_info');
    if (ext) {{
      if (param === ext.UNMASKED_VENDOR_WEBGL) return '{vendor}';
      if (param === ext.UNMASKED_RENDERER_WEBGL) return '{renderer}';
    }}
    return _origGetParam2.call(this, param);
  }};

  // --- Canvas Noise ---
  // Inject subtle per-fingerprint noise into toDataURL and getImageData
  const _canvasSeed = {canvas_seed};
  function _canvasNoise(ctx) {{
    const orig = ctx.getImageData;
    ctx.getImageData = function(x, y, w, h) {{
      const data = orig.call(this, x, y, w, h);
      // Apply deterministic noise to a few random pixels
      const rng = _canvasSeed + w * h;
      for (let i = 0; i < Math.min(data.data.length, 32); i += 4) {{
        const idx = Math.floor((rng * (i + 1)) % data.data.length);
        data.data[idx] = data.data[idx] ^ 1;
      }}
      return data;
    }};
  }}
  try {{
    const origGetCtx = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function(type, attrs) {{
      const ctx = origGetCtx.call(this, type, attrs);
      if (ctx && (type === '2d' || type === '2d')) {{
        _canvasNoise(ctx);
      }}
      return ctx;
    }};
  }} catch(e) {{}}

  // --- AudioContext Noise ---
  try {{
    const _audioSeed = {audio_seed};
    const origCreateOsc = (window.AudioContext || window.webkitAudioContext).prototype.createOscillator;
    if (origCreateOsc) {{
      (window.AudioContext || window.webkitAudioContext).prototype.createOscillator = function() {{
        const osc = origCreateOsc.call(this);
        const origStart = osc.start.bind(osc);
        osc.start = function(when) {{
          origStart(when);
          // Add subtle frequency perturbation
          try {{
            osc.frequency.setValueAtTime(
              osc.frequency.value + (_audioSeed % 0.001),
              this.currentTime
            );
          }} catch(e) {{}}
        }};
        return osc;
      }};
    }}
  }} catch(e) {{}}
}})();
"""


def _js_escape(s: str) -> str:
    """Escape a string for safe embedding in a JS single-quoted literal."""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")


# ===================================================================
# Convenience factory
# ===================================================================


def generate_fingerprint() -> dict[str, Any]:
    """Module-level convenience: generate a random fingerprint as a dict.

    Used by the API endpoint ``POST /scraper/fingerprints/generate``.
    """
    fp = BrowserFingerprint.random()
    return fp.to_dict()


async def apply_to_page(
    page: Any, fingerprint: BrowserFingerprint | None = None
) -> BrowserFingerprint:
    """Apply a fingerprint to a Playwright Page.

    If no fingerprint is provided, a random one is generated.
    Returns the applied fingerprint for logging/tracking.
    """
    if fingerprint is None:
        fingerprint = BrowserFingerprint.random()
    await fingerprint.apply_to_page(page)
    return fingerprint


async def apply_to_context(
    context: Any, fingerprint: BrowserFingerprint | None = None
) -> BrowserFingerprint:
    """Apply a fingerprint to a Playwright BrowserContext.

    Sets viewport and user-agent at the context level, then injects
    JS overrides via ``add_init_script``.

    If no fingerprint is provided, a random one is generated.
    Returns the applied fingerprint.
    """
    if fingerprint is None:
        fingerprint = BrowserFingerprint.random()

    js_overrides = fingerprint._build_js_overrides()
    await context.add_init_script(js_overrides)

    logger.debug(
        "Applied fingerprint to browser context (UA=%s, viewport=%dx%d)",
        fingerprint.user_agent[:80],
        fingerprint.viewport_width,
        fingerprint.viewport_height,
    )
    return fingerprint


def fingerprint_to_headers(fingerprint: BrowserFingerprint) -> dict[str, str]:
    """Extract HTTP headers from a fingerprint for use with httpx / curl-cffi.

    Returns a dict suitable for passing as ``headers=`` to HTTP clients.
    """
    return {
        "User-Agent": fingerprint.user_agent,
        "Accept-Language": (
            fingerprint.languages[0] if fingerprint.languages else "en-US,en;q=0.9"
        ),
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": f'"{fingerprint.platform}"',
    }
