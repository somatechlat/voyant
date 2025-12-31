"""
Voyant Scraper - BeautifulSoup Client

Simple HTML parsing using BeautifulSoup and requests for static pages.
"""
from typing import Optional, Dict, Any, List
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


class BeautifulSoupClient:
    """
    BeautifulSoup-based HTML parser.
    
    Best for:
    - Static HTML pages
    - Simple content extraction
    - Fast lightweight scraping
    """
    
    def __init__(
        self, 
        timeout: int = 30,
        verify_ssl: bool = True,
        rotate_user_agent: bool = True
    ):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.rotate_user_agent = rotate_user_agent
        self._session = requests.Session()
        
        if rotate_user_agent:
            try:
                self._ua = UserAgent()
            except Exception:
                self._ua = None
        else:
            self._ua = None
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional UA rotation."""
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        if self._ua:
            headers["User-Agent"] = self._ua.random
        else:
            headers["User-Agent"] = "Mozilla/5.0 (compatible; VoyantBot/1.0)"
        return headers
    
    def fetch(self, url: str) -> str:
        """
        Fetch a page.
        
        Args:
            url: URL to fetch
            
        Returns:
            Page HTML content
        """
        response = self._session.get(
            url,
            headers=self._get_headers(),
            timeout=self.timeout,
            verify=self.verify_ssl
        )
        response.raise_for_status()
        return response.text
    
    def fetch_and_parse(self, url: str, parser: str = "lxml") -> BeautifulSoup:
        """
        Fetch and parse a page.
        
        Args:
            url: URL to fetch
            parser: Parser to use (lxml, html.parser, html5lib)
            
        Returns:
            BeautifulSoup object
        """
        html = self.fetch(url)
        return BeautifulSoup(html, parser)
    
    def extract_text(self, url: str) -> str:
        """
        Extract all text from a page.
        
        Args:
            url: URL to fetch
            
        Returns:
            Plain text content
        """
        soup = self.fetch_and_parse(url)
        # Remove script and style elements
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        return soup.get_text(separator="\n", strip=True)
    
    def extract_links(self, url: str) -> List[str]:
        """
        Extract all links from a page.
        
        Args:
            url: URL to fetch
            
        Returns:
            List of absolute URLs
        """
        from urllib.parse import urljoin
        
        soup = self.fetch_and_parse(url)
        links = []
        
        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute_url = urljoin(url, href)
            links.append(absolute_url)
        
        return links
    
    def extract_by_selector(
        self, 
        url: str, 
        selector: str, 
        attribute: Optional[str] = None
    ) -> List[str]:
        """
        Extract content by CSS selector.
        
        Args:
            url: URL to fetch
            selector: CSS selector
            attribute: Optional attribute to extract (default: text)
            
        Returns:
            List of extracted values
        """
        soup = self.fetch_and_parse(url)
        elements = soup.select(selector)
        
        if attribute:
            return [el.get(attribute, "") for el in elements]
        return [el.get_text(strip=True) for el in elements]
