"""
WebSocket Consumer for visual scraping — connects frontend to Playwright browser.

Protocol:
  Client → Server: {"action": "navigate", "url": "https://..."}
  Client → Server: {"action": "click", "x": 100, "y": 200}
  Client → Server: {"action": "scroll", "direction": "down", "amount": 500}
  Client → Server: {"action": "screenshot"}
  Client → Server: {"action": "extract", "selectors": {"name": ".selector"}}
  Client → Server: {"action": "hover", "x": 100, "y": 200}
  Client → Server: {"action": "enter_text", "selector": "input.search", "text": "query"}
  Client → Server: {"action": "detect"}  — auto-detect lists/tables/pagination

  Server → Client: {"type": "page_state", "data": {...}}
  Server → Client: {"type": "elements", "data": [...]}
  Server → Client: {"type": "extracted", "data": {...}}
  Server → Client: {"type": "detected", "data": {...}}
  Server → Client: {"type": "error", "message": "..."}
"""

from __future__ import annotations

import logging
from dataclasses import asdict

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from apps.scraper.visual.auto_detect import AutoDetectEngine
from apps.scraper.visual.browser_manager import BrowserManager, get_browser_manager

logger = logging.getLogger(__name__)


class ScraperConsumer(AsyncJsonWebsocketConsumer):
    """WebSocket consumer for visual scraping sessions."""

    session_id: str = ""
    browser_manager: BrowserManager | None = None

    async def connect(self) -> None:
        """Handle WebSocket connection."""
        self.session_id = self.scope.get("session", {}).get("session_key", "default")
        self.browser_manager = get_browser_manager()

        await self.accept()
        await self.send_json({"type": "connected", "session_id": self.session_id})
        logger.info("Scraper WebSocket connected: %s", self.session_id)

    async def disconnect(self, close_code: int) -> None:  # type: ignore[reportIncompatibleMethodOverride]
        """Handle WebSocket disconnection."""
        if self.browser_manager:
            await self.browser_manager.close_session(self.session_id)
        logger.info(
            "Scraper WebSocket disconnected: %s (code=%d)", self.session_id, close_code
        )

    async def receive_json(self, content: dict) -> None:  # type: ignore[reportIncompatibleMethodOverride]
        """Handle incoming messages from the client."""
        action = content.get("action", "")
        try:
            handler = getattr(self, f"_action_{action}", None)
            if handler:
                await handler(content)
            else:
                await self._send_error(f"Unknown action: {action}")
        except Exception as exc:
            logger.exception("Action %s failed", action)
            await self._send_error(str(exc))

    # ── Action handlers ─────────────────────────────────────────────────────

    async def _action_start(self, content: dict) -> None:
        """Start a new browser session."""
        await self.browser_manager.create_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        await self.send_json({"type": "session_started", "session_id": self.session_id})

    async def _action_navigate(self, content: dict) -> None:
        """Navigate to a URL."""
        url = content.get("url", "")
        if not url:
            await self._send_error("URL is required")
            return

        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            session = await self.browser_manager.create_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]

        state = await session.navigate(url)
        await self._send_page_state(state)

        # Auto-detect after navigation
        detected = await self._run_auto_detect(session)
        await self.send_json({"type": "detected", "data": detected})

    async def _action_screenshot(self, content: dict) -> None:
        """Capture current page state."""
        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        state = await session.screenshot()
        await self._send_page_state(state)

    async def _action_click(self, content: dict) -> None:
        """Click at coordinates."""
        x = content.get("x", 0)
        y = content.get("y", 0)

        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        state = await session.click(x, y)
        await self._send_page_state(state)

    async def _action_click_element(self, content: dict) -> None:
        """Click an element by selector."""
        selector = content.get("selector", "")

        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        state = await session.click_element(selector)
        await self._send_page_state(state)

    async def _action_scroll(self, content: dict) -> None:
        """Scroll the page."""
        direction = content.get("direction", "down")
        amount = content.get("amount", 500)

        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        state = await session.scroll(direction, amount)
        await self._send_page_state(state)

    async def _action_hover(self, content: dict) -> None:
        """Hover at coordinates and return element info."""
        x = content.get("x", 0)
        y = content.get("y", 0)

        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        elements = await session.hover(x, y)
        await self.send_json(
            {
                "type": "hover",
                "data": [asdict(e) for e in elements],
            }
        )

    async def _action_enter_text(self, content: dict) -> None:
        """Type text into a field."""
        selector = content.get("selector", "")
        text = content.get("text", "")

        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        state = await session.enter_text(selector, text)
        await self._send_page_state(state)

    async def _action_extract(self, content: dict) -> None:
        """Extract data using selectors."""
        selectors = content.get("selectors", {})

        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        data = await session.extract_data(selectors)
        await self.send_json({"type": "extracted", "data": data})

    async def _action_detect(self, content: dict) -> None:
        """Run auto-detect on the current page."""
        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        detected = await self._run_auto_detect(session)
        await self.send_json({"type": "detected", "data": detected})

    async def _action_back(self, content: dict) -> None:
        """Navigate back."""
        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        await session.page.go_back()
        state = await session.screenshot()
        await self._send_page_state(state)

    async def _action_forward(self, content: dict) -> None:
        """Navigate forward."""
        session = self.browser_manager.get_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        if not session:
            await self._send_error("No active session")
            return

        await session.page.go_forward()
        state = await session.screenshot()
        await self._send_page_state(state)

    async def _action_close(self, content: dict) -> None:
        """Close the browser session."""
        await self.browser_manager.close_session(self.session_id)  # type: ignore[reportOptionalMemberAccess]
        await self.send_json({"type": "session_closed"})

    # ── Helpers ─────────────────────────────────────────────────────────────

    async def _send_page_state(self, state) -> None:
        """Send a page state snapshot to the client."""
        await self.send_json(
            {
                "type": "page_state",
                "data": {
                    "url": state.url,
                    "title": state.title,
                    "screenshot": state.screenshot,
                    "viewport_width": state.viewport_width,
                    "viewport_height": state.viewport_height,
                    "scroll_y": state.scroll_y,
                    "page_height": state.page_height,
                    "elements": [asdict(e) for e in state.elements],
                },
            }
        )

    async def _send_error(self, message: str) -> None:
        """Send an error message to the client."""
        await self.send_json({"type": "error", "message": message})

    async def _run_auto_detect(self, session) -> dict:
        """Run auto-detect analysis on the current page."""
        engine = AutoDetectEngine()
        html = await session.get_page_html()
        url = session.page.url
        return engine.detect(html, url)
