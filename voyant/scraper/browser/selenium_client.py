"""
Voyant Scraper - Selenium Client

Classic browser automation using Selenium for legacy sites and form filling.
"""
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class SeleniumClient:
    """
    Selenium-based browser automation client.
    
    Best for:
    - Legacy websites
    - Complex form filling
    - Sites with older JavaScript
    """
    
    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self._driver: Optional[webdriver.Chrome] = None
    
    def _get_driver(self) -> webdriver.Chrome:
        """Get or create WebDriver instance."""
        if self._driver is None:
            options = Options()
            if self.headless:
                options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            if self.proxy:
                options.add_argument(f"--proxy-server={self.proxy}")
            
            self._driver = webdriver.Chrome(options=options)
        return self._driver
    
    def fetch(
        self, 
        url: str, 
        wait_for: Optional[str] = None,
        timeout: int = 30
    ) -> str:
        """
        Fetch a page.
        
        Args:
            url: URL to fetch
            wait_for: Optional CSS selector to wait for
            timeout: Timeout in seconds
            
        Returns:
            Page HTML content
        """
        driver = self._get_driver()
        driver.get(url)
        
        if wait_for:
            WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
            )
        
        return driver.page_source
    
    def fetch_with_actions(
        self,
        url: str,
        actions: List[Dict[str, Any]],
        wait_for: Optional[str] = None
    ) -> str:
        """
        Fetch a page and perform actions.
        
        Args:
            url: URL to fetch
            actions: List of actions to perform
            wait_for: Optional selector to wait for
            
        Returns:
            Page HTML content after actions
        """
        driver = self._get_driver()
        driver.get(url)
        
        if wait_for:
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, wait_for))
            )
        
        for action in actions:
            action_type = action.get("type")
            selector = action.get("selector")
            
            if action_type == "click":
                element = driver.find_element(By.CSS_SELECTOR, selector)
                element.click()
            elif action_type == "fill":
                element = driver.find_element(By.CSS_SELECTOR, selector)
                element.clear()
                element.send_keys(action.get("value", ""))
            elif action_type == "scroll":
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            elif action_type == "wait":
                import time
                time.sleep(action.get("timeout", 1) / 1000)
        
        return driver.page_source
    
    def close(self):
        """Close WebDriver instance."""
        if self._driver:
            self._driver.quit()
            self._driver = None
