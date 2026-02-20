"""
Voyant Scraper - Selenium Client for Browser Automation.

This module provides a client for web scraping and browser automation using
Selenium WebDriver. It is useful for interacting with complex websites,
performing form filling, or handling scenarios where
JavaScript execution and full browser simulation are required.
"""

from typing import Any, Dict, List, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class SeleniumClient:
    """
    A client for automating web browser interactions using Selenium WebDriver.

    This client simulates a full user browsing experience, making it suitable for:
    - Websites with complex JavaScript rendering.
    - Scenarios requiring interaction with forms, buttons, or dynamic elements.
    - Testing browser-based workflows.

    Performance Note: Selenium clients are generally more resource-intensive and
    slower than HTTP-based clients (e.g., requests, httpx) or even Playwright,
    as they launch and control a full browser instance.
    """

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        """
        Initializes the SeleniumClient.

        Args:
            headless (bool): If True, the browser runs in headless mode (without a UI).
            proxy (Optional[str]): A proxy server address (e.g., "http://proxy.internal:8080") for network requests.
        """
        self.headless = headless
        self.proxy = proxy
        self._driver: Optional[webdriver.Chrome] = None

    def _get_driver(self) -> webdriver.Chrome:
        """
        Lazily gets or creates a Selenium Chrome WebDriver instance.

        Returns:
            selenium.webdriver.Chrome: The Chrome WebDriver instance.
        """
        if self._driver is None:
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            # Recommended arguments for running Chrome in a containerized environment.
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")

            if self.proxy:
                options.add_argument(f"--proxy-server={self.proxy}")

            self._driver = webdriver.Chrome(options=options)
        return self._driver

    def fetch_page(
        self, url: str, wait_for: Optional[str] = None, timeout: int = 30
    ) -> str:
        """
        Fetches the HTML content of a given URL, optionally waiting for a specific element.

        Args:
            url (str): The URL of the web page to fetch.
            wait_for (Optional[str]): An optional CSS selector to wait for before
                                       returning the page source. This ensures dynamic
                                       content has loaded.
            timeout (int): The maximum number of seconds to wait for the element or page to load.

        Returns:
            str: The HTML content of the page after rendering.

        Raises:
            selenium.common.exceptions.TimeoutException: If the element specified by `wait_for` is not found within the timeout.
            selenium.common.exceptions.WebDriverException: For other WebDriver-related errors.
        """
        driver = self._get_driver()
        driver.get(url)

        if wait_for:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
            )

        return driver.page_source

    def perform_actions(
        self,
        url: str,
        actions: List[Dict[str, Any]],
        wait_for: Optional[str] = None,
        timeout: int = 30,
    ) -> str:
        """
        Fetches a page and performs a sequence of browser actions.

        This method allows for interacting with dynamic elements, filling forms,
        or scrolling before extracting the final HTML content.

        Args:
            url (str): The URL of the web page to fetch.
            actions (List[Dict[str, Any]]): A list of dictionaries, each describing an action:
                - `{"type": "click", "selector": "#btn_id"}`
                - `{"type": "fill", "selector": "#input_id", "value": "text"}`
                - `{"type": "scroll"}` (scrolls to bottom)
                - `{"type": "wait", "timeout": 1000}` (waits for 1 second)
            wait_for (Optional[str]): An optional CSS selector to wait for after
                                       initial page load and before performing actions.
            timeout (int): The maximum number of seconds to wait for elements or actions.

        Returns:
            str: The HTML content of the page after all actions have been performed.

        Raises:
            selenium.common.exceptions.WebDriverException: For various WebDriver-related errors.
        """
        driver = self._get_driver()
        driver.get(url)

        if wait_for:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
            )

        for action in actions:
            action_type = action.get("type")
            selector = action.get("selector")

            if action_type == "click" and selector:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                element.click()
            elif action_type == "fill" and selector:
                element = driver.find_element(By.CSS_SELECTOR, selector)
                element.clear()
                element.send_keys(action.get("value", ""))
            elif action_type == "scroll":
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            elif action_type == "wait":
                import time  # Importing here to avoid circular dependencies if time isn't used elsewhere.

                time.sleep(
                    action.get("timeout", 1000) / 1000
                )  # Timeout is in milliseconds, sleep in seconds.
            else:
                pass  # Log a warning for unknown action types if needed.

        return driver.page_source

    def close(self):
        """
        Closes the underlying Selenium WebDriver instance and releases browser resources.

        This should be called to clean up resources when the client is no longer needed.
        """
        if self._driver:
            self._driver.quit()
            self._driver = None
