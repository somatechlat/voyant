"""
Voyant Scraper - Playwright Client for Dynamic Web Automation.

This module provides a client for browser automation using Playwright,
specifically designed for scraping JavaScript-heavy websites and Single Page
Applications (SPAs). It allows for page fetching, performing browser actions
(like clicks, fills, scrolls), and extracting HTML content after dynamic rendering.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from playwright.async_api import Browser, async_playwright

logger = logging.getLogger(__name__)


class PlaywrightClient:
    """
    An asynchronous client for browser automation and dynamic web scraping using Playwright.

    This client is best suited for:
    - Websites that rely heavily on JavaScript for content rendering.
    - Single Page Applications (SPAs) where content loads dynamically.
    - Scenarios requiring browser interactions (clicks, form fills, scrolling).
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        """
        Initializes the PlaywrightClient.

        Args:
            headless (bool): If True, the browser runs in headless mode (without a UI).
            proxy (Optional[str]): A proxy server URL (e.g., "http://localhost:8080") for network requests.
        """
        self.headless = headless
        self.proxy = proxy
        self._browser: Optional[Browser] = None
        self._playwright_instance = None  # To manage playwright context lifecycle

    async def _get_browser(self) -> Browser:
        """
        Lazily gets or creates a Playwright browser instance.

        Returns:
            playwright.async_api.Browser: The Playwright browser instance.
        """
        if self._browser is None:
            self._playwright_instance = await async_playwright().start()
            launch_options = {
                "headless": self.headless,
            }
            if self.proxy:
                launch_options["proxy"] = {"server": self.proxy}

            self._browser = await self._playwright_instance.chromium.launch(**launch_options)
        return self._browser

    async def fetch_async(
        self, url: str, wait_until: str = "networkidle", timeout: int = 30000
    ) -> str:
        """
        Fetches the HTML content of a URL asynchronously, waiting for dynamic content to load.

        Args:
            url (str): The URL of the web page to fetch.
            wait_until (str): Condition to wait for after navigation ('domcontentloaded', 'load', 'networkidle').
                              Defaults to 'networkidle'.
            timeout (int): Maximum time in milliseconds to wait for navigation. Defaults to 30000 (30 seconds).

        Returns:
            str: The HTML content of the page after rendering.

        Raises:
            playwright.async_api.TimeoutError: If the navigation or wait condition times out.
            playwright.async_api.Error: For other Playwright-related errors.
        """
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until=wait_until, timeout=timeout)
            html = await page.content()
            return html
        finally:
            await page.close()

    def fetch(self, url: str, **kwargs) -> str:
        """
        Synchronous wrapper for `fetch_async`.

        Args:
            url (str): The URL of the web page to fetch.
            **kwargs: Additional keyword arguments to pass to `fetch_async` (e.g., `wait_until`, `timeout`).

        Returns:
            str: The HTML content of the page.
        """
        return asyncio.run(self.fetch_async(url, **kwargs))

    async def fetch_with_actions(
        self, url: str, actions: List[Dict[str, Any]], wait_until: str = "networkidle"
    ) -> str:
        """
        Fetches a page and performs a sequence of browser actions.

        This allows for interacting with dynamic elements, filling forms, or
        scrolling before extracting the final HTML content.

        Args:
            url (str): The URL of the web page to fetch.
            actions (List[Dict[str, Any]]): A list of dictionaries, each describing an action:
                - `{"type": "click", "selector": "#btn_id"}`
                - `{"type": "fill", "selector": "#input_id", "value": "text"}`
                - `{"type": "scroll"}` (scrolls to bottom)
                - `{"type": "wait", "timeout": 1000}` (waits for 1 second)
                - `{"type": "screenshot", "path": "path/to/save.png"}`
            wait_until (str): Condition to wait for after navigation and actions.

        Returns:
            str: The HTML content of the page after all actions have been performed.

        Raises:
            playwright.async_api.Error: For various Playwright-related errors during navigation or actions.
        """
        browser = await self._get_browser()
        page = await browser.new_page()

        try:
            await page.goto(url, wait_until=wait_until)

            for action in actions:
                action_type = action.get("type")
                selector = action.get("selector")

                if action_type == "click" and selector:
                    await page.click(selector)
                elif action_type == "fill" and selector:
                    await page.fill(selector, action.get("value", ""))
                elif action_type == "scroll":
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                elif action_type == "wait":
                    await asyncio.sleep(action.get("timeout", 1000) / 1000)  # Playwright wait_for_timeout is deprecated
                elif action_type == "screenshot" and action.get("path"):
                    await page.screenshot(path=action.get("path"))
                else:
                    logger.warning(f"Unknown or malformed action type: {action_type}")

            html = await page.content()
            return html
        finally:
            await page.close()

    async def close(self):
        """
        Closes the underlying Playwright browser instance.

        This should be called to release browser resources when the client is no longer needed.
        """
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright_instance:
            await self._playwright_instance.stop()
            self._playwright_instance = None
