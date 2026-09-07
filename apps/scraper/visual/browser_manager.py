"""
Playwright Browser Manager — server-side browser control for visual scraping.

Manages headless Chromium instances per session. Captures screenshots,
extracts DOM tree, handles clicks, scrolls, navigation, and element detection.
Replaces Octoparse's embedded browser with a server-side WebSocket architecture.
"""

from __future__ import annotations

import asyncio
import base64
import logging
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)


@dataclass
class ElementInfo:
    """Detected element on the page."""

    tag: str
    text: str
    selector: str
    xpath: str
    x: float
    y: float
    width: float
    height: float
    attributes: dict[str, str] = field(default_factory=dict)
    is_clickable: bool = False
    is_input: bool = False
    is_link: bool = False


@dataclass
class PageState:
    """Current state of the browser page."""

    url: str
    title: str
    screenshot: str  # base64 PNG
    viewport_width: int
    viewport_height: int
    scroll_y: int
    page_height: int
    elements: list[ElementInfo] = field(default_factory=list)


class BrowserSession:
    """Manages a single Playwright browser session."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._playwright = None

    async def start(self, viewport_width: int = 1280, viewport_height: int = 800) -> None:
        """Start a new browser session."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        self._context = await self._browser.new_context(
            viewport={"width": viewport_width, "height": viewport_height},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="en-US",
        )
        self._page = await self._context.new_page()
        logger.info("Browser session %s started (%dx%d)", self.session_id, viewport_width, viewport_height)

    async def stop(self) -> None:
        """Stop the browser session and clean up."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser session %s stopped", self.session_id)

    @property
    def page(self) -> Page:
        if not self._page:
            raise RuntimeError("Browser session not started")
        return self._page

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> PageState:
        """Navigate to a URL and capture the page state."""
        await self.page.goto(url, wait_until=wait_until, timeout=30000)
        await self.page.wait_for_load_state("networkidle", timeout=10000)
        return await self._capture_state()

    async def screenshot(self) -> PageState:
        """Capture current page state without navigation."""
        return await self._capture_state()

    async def click(self, x: float, y: float) -> PageState:
        """Click at coordinates and capture resulting state."""
        await self.page.mouse.click(x, y)
        await asyncio.sleep(0.5)
        return await self._capture_state()

    async def click_element(self, selector: str) -> PageState:
        """Click an element by selector and capture resulting state."""
        try:
            await self.page.click(selector, timeout=5000)
            await asyncio.sleep(0.5)
        except Exception as exc:
            logger.warning("Click failed for %s: %s", selector, exc)
        return await self._capture_state()

    async def scroll(self, direction: str = "down", amount: int = 500) -> PageState:
        """Scroll the page and capture state."""
        if direction == "down":
            await self.page.evaluate(f"window.scrollBy(0, {amount})")
        elif direction == "up":
            await self.page.evaluate(f"window.scrollBy(0, -{amount})")
        await asyncio.sleep(0.3)
        return await self._capture_state()

    async def scroll_to(self, x: float, y: float) -> PageState:
        """Scroll to specific coordinates."""
        await self.page.evaluate(f"window.scrollTo({x}, {y})")
        await asyncio.sleep(0.3)
        return await self._capture_state()

    async def hover(self, x: float, y: float) -> list[ElementInfo]:
        """Hover at coordinates and return element under cursor."""
        element = await self._get_element_at(x, y)
        return [element] if element else []

    async def enter_text(self, selector: str, text: str) -> PageState:
        """Type text into an input field."""
        try:
            await self.page.fill(selector, text, timeout=5000)
        except Exception:
            await self.page.type(selector, text, delay=50)
        return await self._capture_state()

    async def extract_data(self, selectors: dict[str, str]) -> dict[str, Any]:
        """Extract data from the page using CSS selectors."""
        results: dict[str, Any] = {}
        for name, selector in selectors.items():
            try:
                elements = await self.page.query_selector_all(selector)
                if len(elements) == 1:
                    results[name] = await elements[0].inner_text()
                elif len(elements) > 1:
                    results[name] = [await el.inner_text() for el in elements]
                else:
                    results[name] = None
            except Exception as exc:
                results[name] = f"Error: {exc}"
        return results

    async def get_page_html(self) -> str:
        """Get the full page HTML."""
        return await self.page.content()

    async def evaluate(self, expression: str) -> Any:
        """Evaluate JavaScript on the page."""
        return await self.page.evaluate(expression)

    # ── Private helpers ─────────────────────────────────────────────────────

    async def _capture_state(self) -> PageState:
        """Capture a complete snapshot of the current page."""
        # Screenshot
        screenshot_bytes = await self.page.screenshot(type="png", full_page=False)
        screenshot_b64 = base64.b64encode(screenshot_bytes).decode("ascii")

        # Page info
        url = self.page.url
        title = await self.page.title()

        # Viewport and scroll
        viewport = self.page.viewport_size or {"width": 1280, "height": 800}
        scroll_info = await self.page.evaluate("""() => ({
            scrollY: window.scrollY,
            pageHeight: document.documentElement.scrollHeight
        })""")

        # Detect interactive elements
        elements = await self._detect_elements()

        return PageState(
            url=url,
            title=title,
            screenshot=screenshot_b64,
            viewport_width=viewport["width"],
            viewport_height=viewport["height"],
            scroll_y=scroll_info["scrollY"],
            page_height=scroll_info["pageHeight"],
            elements=elements,
        )

    async def _detect_elements(self) -> list[ElementInfo]:
        """Detect all interactive elements on the page."""
        return await self.page.evaluate("""() => {
            const elements = [];
            const interactiveSelectors = 'a, button, input, select, textarea, [onclick], [role="button"], [role="link"], [tabindex]';
            const allElements = document.querySelectorAll(interactiveSelectors);

            for (const el of allElements) {
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) continue;
                if (rect.bottom < 0 || rect.top > window.innerHeight) continue;

                // Generate CSS selector
                let selector = el.tagName.toLowerCase();
                if (el.id) selector = '#' + CSS.escape(el.id);
                else if (el.className && typeof el.className === 'string') {
                    const classes = el.className.trim().split(/\\s+/).filter(c => c.length > 0).slice(0, 3);
                    if (classes.length > 0) selector += '.' + classes.map(c => CSS.escape(c)).join('.');
                }

                // Generate XPath
                let xpath = '';
                let current = el;
                while (current && current !== document.body) {
                    let part = current.tagName.toLowerCase();
                    const parent = current.parentElement;
                    if (parent) {
                        const siblings = Array.from(parent.children).filter(c => c.tagName === current.tagName);
                        if (siblings.length > 1) {
                            const index = siblings.indexOf(current) + 1;
                            part += '[' + index + ']';
                        }
                    }
                    xpath = '/' + part + (xpath ? xpath : '');
                    current = current.parentElement;
                }
                xpath = '/' + xpath;

                // Attributes
                const attrs = {};
                for (const attr of el.attributes) {
                    if (['class', 'id', 'style'].includes(attr.name)) continue;
                    attrs[attr.name] = attr.value.slice(0, 200);
                }

                elements.push({
                    tag: el.tagName.toLowerCase(),
                    text: (el.innerText || '').slice(0, 200).trim(),
                    selector: selector,
                    xpath: xpath,
                    x: Math.round(rect.left + window.scrollX),
                    y: Math.round(rect.top + window.scrollY),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    attributes: attrs,
                    is_clickable: ['A', 'BUTTON'].includes(el.tagName) || el.hasAttribute('onclick') || el.getAttribute('role') === 'button',
                    is_input: ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName),
                    is_link: el.tagName === 'A',
                });
            }
            return elements;
        }""")

    async def _get_element_at(self, x: float, y: float) -> ElementInfo | None:
        """Get the element at specific page coordinates."""
        result = await self.page.evaluate(f"""() => {{
            const el = document.elementFromPoint({x}, {y});
            if (!el) return null;

            const rect = el.getBoundingClientRect();
            let selector = el.tagName.toLowerCase();
            if (el.id) selector = '#' + CSS.escape(el.id);
            else if (el.className && typeof el.className === 'string') {{
                const classes = el.className.trim().split(/\\s+/).slice(0, 3);
                if (classes.length > 0) selector += '.' + classes.join('.');
            }}

            return {{
                tag: el.tagName.toLowerCase(),
                text: (el.innerText || '').slice(0, 200).trim(),
                selector: selector,
                xpath: '',
                x: Math.round(rect.left + window.scrollX),
                y: Math.round(rect.top + window.scrollY),
                width: Math.round(rect.width),
                height: Math.round(rect.height),
                attributes: {{}},
                is_clickable: ['A', 'BUTTON'].includes(el.tagName),
                is_input: ['INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName),
                is_link: el.tagName === 'A',
            }};
        }}""")
        return ElementInfo(**result) if result else None


class BrowserManager:
    """Manages multiple browser sessions."""

    def __init__(self):
        self._sessions: dict[str, BrowserSession] = {}

    async def create_session(self, session_id: str) -> BrowserSession:
        """Create a new browser session."""
        if session_id in self._sessions:
            await self._sessions[session_id].stop()
        session = BrowserSession(session_id)
        await session.start()
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> BrowserSession | None:
        """Get an existing browser session."""
        return self._sessions.get(session_id)

    async def close_session(self, session_id: str) -> None:
        """Close and remove a browser session."""
        session = self._sessions.pop(session_id, None)
        if session:
            await session.stop()

    async def close_all(self) -> None:
        """Close all browser sessions."""
        for session_id in list(self._sessions.keys()):
            await self.close_session(session_id)


# Singleton
_browser_manager: BrowserManager | None = None


def get_browser_manager() -> BrowserManager:
    """Get the singleton browser manager."""
    global _browser_manager
    if _browser_manager is None:
        _browser_manager = BrowserManager()
    return _browser_manager
