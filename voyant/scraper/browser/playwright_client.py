"""
Voyant Scraper - Playwright Client

Modern browser automation using Playwright for JavaScript-heavy sites and SPAs.
"""
import asyncio
from typing import Optional, Dict, Any
from playwright.async_api import async_playwright, Browser, Page


class PlaywrightClient:
    """
    Playwright-based browser automation client.
    
    Best for:
    - JavaScript-heavy websites
    - Single Page Applications (SPAs)
    - Sites requiring modern browser features
    """
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self._browser: Optional[Browser] = None
    
    async def _get_browser(self) -> Browser:
        """Get or create browser instance."""
        if self._browser is None:
            playwright = await async_playwright().start()
            launch_options = {
                "headless": self.headless,
            }
            if self.proxy:
                launch_options["proxy"] = {"server": self.proxy}
            
            self._browser = await playwright.chromium.launch(**launch_options)
        return self._browser
    
    async def fetch_async(
        self, 
        url: str, 
        wait_until: str = "networkidle",
        timeout: int = 30000
    ) -> str:
        """
        Fetch a page asynchronously.
        
        Args:
            url: URL to fetch
            wait_until: domcontentloaded, load, networkidle
            timeout: Timeout in milliseconds
            
        Returns:
            Page HTML content
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
        """Synchronous wrapper for fetch_async."""
        return asyncio.run(self.fetch_async(url, **kwargs))
    
    async def fetch_with_actions(
        self,
        url: str,
        actions: list[Dict[str, Any]],
        wait_until: str = "networkidle"
    ) -> str:
        """
        Fetch a page and perform actions (click, fill, scroll, etc).
        
        Args:
            url: URL to fetch
            actions: List of actions to perform
                [{"type": "click", "selector": "#btn"}, ...]
            wait_until: Wait condition
            
        Returns:
            Page HTML content after actions
        """
        browser = await self._get_browser()
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until=wait_until)
            
            for action in actions:
                action_type = action.get("type")
                selector = action.get("selector")
                
                if action_type == "click":
                    await page.click(selector)
                elif action_type == "fill":
                    await page.fill(selector, action.get("value", ""))
                elif action_type == "scroll":
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                elif action_type == "wait":
                    await page.wait_for_timeout(action.get("timeout", 1000))
                elif action_type == "screenshot":
                    await page.screenshot(path=action.get("path", "screenshot.png"))
            
            html = await page.content()
            return html
        finally:
            await page.close()
    
    async def close(self):
        """Close browser instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
