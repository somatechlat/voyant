"""
Voyant Scraper - Scrapy Client for High-Performance Web Crawling.

This module provides an integration with the Scrapy framework, enabling
large-scale, high-performance web scraping operations. It is designed for
scenarios requiring efficient traversal of websites, adherence to `robots.txt`
rules, and the ability to follow links for deeper data collection.
"""

import logging
from typing import Any, Callable, Dict, List, Optional

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Response

logger = logging.getLogger(__name__)


class VoyantSpider(scrapy.Spider):
    """
    A custom Scrapy spider designed for Voyant's web scraping jobs.

    This spider is configured to start scraping from a given list of URLs
    and collect the full HTML content and metadata of each response.
    It can optionally invoke a callback function for real-time result processing.
    """

    name = "voyant_spider"

    def __init__(
        self,
        urls: List[str],
        callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        *args,
        **kwargs,
    ):
        """
        Initializes the VoyantSpider.

        Args:
            urls (List[str]): A list of starting URLs for the spider to crawl.
            callback (Optional[Callable]): An optional callback function to process
                                           results as they are yielded by the parser.
            *args: Positional arguments passed to the base Scrapy spider.
            **kwargs: Keyword arguments passed to the base Scrapy spider.
        """
        super().__init__(*args, **kwargs)
        self.start_urls = urls
        self.results: List[Dict[str, Any]] = []  # Stores all collected results.
        self._callback = callback

    def parse(self, response: Response) -> Optional[Dict[str, Any]]:
        """
        Parses the HTTP response, extracts relevant content, and stores it.

        This method is the default callback used by Scrapy to process downloaded responses.
        It extracts the URL, status code, HTML content, and headers from the response.

        Args:
            response (scrapy.http.Response): The HTTP response object from the crawled page.

        Returns:
            Optional[Dict[str, Any]]: A dictionary containing the parsed data,
                                      or None if no data is extracted.
        """
        result = {
            "url": response.url,
            "status": response.status,
            "html": response.text,
            "headers": dict(response.headers),
        }
        self.results.append(result)

        if self._callback:
            self._callback(result)

        yield result  # Yield the result for Scrapy's internal processing pipeline.


class ScrapyClient:
    """
    A client for orchestrating web crawling operations using the Scrapy framework.

    This client provides methods for fetching single URLs, crawling lists of URLs,
    and crawling all links found within a sitemap. It allows for configuration
    of crawl behavior such as concurrency, download delay, and robots.txt adherence.
    """

    def __init__(
        self,
        concurrent_requests: int = 16,
        download_delay: float = 0.5,
        obey_robots: bool = True,
    ):
        """
        Initializes the ScrapyClient.

        Args:
            concurrent_requests (int): The maximum number of concurrent requests Scrapy will perform.
            download_delay (float): The average number of seconds that the downloads should be delayed.
            obey_robots (bool): If True, Scrapy will respect robots.txt rules.
        """
        self.concurrent_requests = concurrent_requests
        self.download_delay = download_delay
        self.obey_robots = obey_robots
        self.results: List[Dict[str, Any]] = []

    def fetch(self, url: str) -> str:
        """
        Fetches the HTML content of a single URL using the Scrapy engine.

        This method initiates a crawl for a single URL and returns its HTML content.

        Args:
            url (str): The URL to fetch.

        Returns:
            str: The HTML content of the page as a string, or an empty string if fetching fails.
        """
        results = self.crawl([url])
        if results:
            return results[0].get("html", "")
        return ""

    def crawl(
        self, urls: List[str], follow_links: bool = False, max_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Crawls a list of URLs and, optionally, follows links found on those pages.

        This method sets up and runs a Scrapy crawler process to fetch content
        from the specified URLs.

        Args:
            urls (List[str]): A list of URLs to begin crawling.
            follow_links (bool): If True, the crawler will follow links found on pages
                                  up to `max_depth`.
            max_depth (int): The maximum depth to follow links if `follow_links` is True.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                  represents the scraped data for a URL.
        """
        self.results = []  # Reset results for this crawl.

        def collect_result(result):
            """Callback to collect results from the spider."""
            self.results.append(result)

        settings = {
            "CONCURRENT_REQUESTS": self.concurrent_requests,
            "DOWNLOAD_DELAY": self.download_delay,
            "ROBOTSTXT_OBEY": self.obey_robots,
            "DEPTH_LIMIT": (
                max_depth if follow_links else 0
            ),  # 0 means no following links from start_urls
            "LOG_LEVEL": "WARNING",  # Suppress excessive Scrapy logging
        }

        process = CrawlerProcess(settings)
        spider = VoyantSpider(urls=urls, callback=collect_result)
        process.crawl(spider)
        process.start()  # This is blocking until the crawl finishes.

        return self.results

    def crawl_sitemap(self, sitemap_url: str) -> List[Dict[str, Any]]:
        """
        Crawls all URLs listed in a sitemap XML file.

        Args:
            sitemap_url (str): The URL to the sitemap.xml file.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries, where each dictionary
                                  represents the scraped data for a URL found in the sitemap.

        Raises:
            requests.exceptions.RequestException: If fetching the sitemap fails.
            Exception: If XML parsing of the sitemap fails.
        """
        # Parse sitemap and extract URLs
        # Note: This uses requests and BeautifulSoup directly, separate from Scrapy's core.
        import requests
        from bs4 import BeautifulSoup

        try:
            response = requests.get(sitemap_url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml-xml")
            urls = [loc.text for loc in soup.find_all("loc")]
            logger.info(f"Discovered {len(urls)} URLs from sitemap: {sitemap_url}.")
            return self.crawl(urls)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch sitemap from {sitemap_url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse sitemap from {sitemap_url}: {e}")
            raise
