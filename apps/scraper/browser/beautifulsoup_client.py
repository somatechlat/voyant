"""
Voyant Scraper - BeautifulSoup Client for Static HTML Parsing.

This module provides a client that leverages `requests` for fetching web pages
and `BeautifulSoup` for parsing HTML content. It is designed for efficient,
lightweight scraping of static HTML pages where JavaScript rendering is not
required. The client includes features such as user-agent rotation and SSL
verification to enhance scraping robustness.
"""

from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


class BeautifulSoupClient:
    """
    A client for fetching and parsing static HTML web pages using BeautifulSoup.

    This client is optimized for situations where:
    - The target web pages primarily serve static HTML content.
    - Advanced browser interactions (like JavaScript execution, form submission) are not needed.
    - Fast and lightweight content extraction is the primary goal.
    """

    def __init__(
        self, timeout: int = 30, verify_ssl: bool = True, rotate_user_agent: bool = True
    ):
        """
        Initializes the BeautifulSoupClient.

        Args:
            timeout (int): The maximum number of seconds to wait for a server response.
            verify_ssl (bool): Whether to verify SSL certificates for HTTPS requests.
            rotate_user_agent (bool): If True, a random user agent will be used for each request.
        """
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
        """
        Constructs the HTTP request headers, including an optional rotated User-Agent.

        Returns:
            Dict[str, str]: A dictionary of HTTP headers.
        """
        headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        if self._ua:
            headers["User-Agent"] = self._ua.random
        else:
            # Default User-Agent if rotation is disabled or fails.
            headers["User-Agent"] = "Mozilla/5.0 (compatible; VoyantBot/1.0)"
        return headers

    def fetch(self, url: str) -> str:
        """
        Fetches the HTML content of a given URL.

        Args:
            url (str): The URL of the web page to fetch.

        Returns:
            str: The HTML content of the page as a string.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails (e.g., network error, bad status code).
        """
        response = self._session.get(
            url,
            headers=self._get_headers(),
            timeout=self.timeout,
            verify=self.verify_ssl,
        )
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        return response.text

    def fetch_and_parse(self, url: str, parser: str = "lxml") -> BeautifulSoup:
        """
        Fetches the HTML content from a URL and parses it into a BeautifulSoup object.

        Args:
            url (str): The URL of the web page to fetch and parse.
            parser (str, optional): The BeautifulSoup parser to use (e.g., "lxml", "html.parser").
                                    Defaults to "lxml" for performance.

        Returns:
            BeautifulSoup: A BeautifulSoup object representing the parsed HTML tree.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
            Exception: Any exception raised by BeautifulSoup during parsing.
        """
        html = self.fetch(url)
        return BeautifulSoup(html, parser)

    def extract_text(self, url: str) -> str:
        """
        Fetches a web page and extracts all visible text content,
        excluding script, style, navigation, footer, and header elements.

        Args:
            url (str): The URL of the web page from which to extract text.

        Returns:
            str: The clean, plain text content of the page.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
            Exception: Any exception raised during HTML parsing or element decomposition.
        """
        soup = self.fetch_and_parse(url)
        # Remove common non-content elements to get cleaner text.
        for element in soup(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        return soup.get_text(separator="\n", strip=True)

    def extract_links(self, url: str) -> List[str]:
        """
        Fetches a web page and extracts all absolute URLs from its `<a>` tags.

        Args:
            url (str): The URL of the web page from which to extract links.

        Returns:
            List[str]: A list of absolute URLs found on the page.

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
            Exception: Any exception raised during HTML parsing.
        """
        soup = self.fetch_and_parse(url)
        links = []

        for a in soup.find_all("a", href=True):
            href = a["href"]
            absolute_url = urljoin(url, href)
            links.append(absolute_url)

        return links

    def extract_by_selector(
        self, url: str, selector: str, attribute: Optional[str] = None
    ) -> List[str]:
        """
        Fetches a web page and extracts content based on a CSS selector.

        Args:
            url (str): The URL of the web page to fetch.
            selector (str): The CSS selector to use for finding elements.
            attribute (str, optional): The attribute to extract from the selected elements.
                                       If None, the element's text content is extracted.

        Returns:
            List[str]: A list of extracted values (either attribute values or text content).

        Raises:
            requests.exceptions.RequestException: If the HTTP request fails.
            Exception: Any exception raised during HTML parsing or selector execution.
        """
        soup = self.fetch_and_parse(url)
        elements = soup.select(selector)

        if attribute:
            return [el.get(attribute, "") for el in elements]
        return [el.get_text(strip=True) for el in elements]
