"""
Voyant Scraper - Scrapy Client

High-performance web crawling using Scrapy for large-scale scraping.
"""
from typing import Optional, List, Dict, Any, Callable
import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.http import Request, Response
from scrapy.utils.project import get_project_settings


class VoyantSpider(scrapy.Spider):
    """
    Base Scrapy spider for Voyant scraping jobs.
    """
    name = "voyant_spider"
    
    def __init__(self, urls: List[str], callback: Optional[Callable] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = urls
        self.results = []
        self._callback = callback
    
    def parse(self, response: Response):
        """Parse response and extract content."""
        result = {
            "url": response.url,
            "status": response.status,
            "html": response.text,
            "headers": dict(response.headers),
        }
        self.results.append(result)
        
        if self._callback:
            self._callback(result)
        
        yield result


class ScrapyClient:
    """
    Scrapy-based high-performance web crawler.
    
    Best for:
    - Large-scale crawling
    - Sitemaps
    - Following links/pagination
    - Respecting robots.txt
    """
    
    def __init__(
        self, 
        concurrent_requests: int = 16,
        download_delay: float = 0.5,
        obey_robots: bool = True
    ):
        self.concurrent_requests = concurrent_requests
        self.download_delay = download_delay
        self.obey_robots = obey_robots
        self.results: List[Dict[str, Any]] = []
    
    def fetch(self, url: str) -> str:
        """
        Fetch a single URL.
        
        Args:
            url: URL to fetch
            
        Returns:
            Page HTML content
        """
        results = self.crawl([url])
        if results:
            return results[0].get("html", "")
        return ""
    
    def crawl(
        self, 
        urls: List[str],
        follow_links: bool = False,
        max_depth: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Crawl multiple URLs.
        
        Args:
            urls: List of URLs to crawl
            follow_links: Whether to follow links on pages
            max_depth: Maximum crawl depth
            
        Returns:
            List of results with url, status, html
        """
        results = []
        
        def collect_result(result):
            results.append(result)
        
        settings = {
            'CONCURRENT_REQUESTS': self.concurrent_requests,
            'DOWNLOAD_DELAY': self.download_delay,
            'ROBOTSTXT_OBEY': self.obey_robots,
            'DEPTH_LIMIT': max_depth,
            'LOG_LEVEL': 'WARNING',
        }
        
        process = CrawlerProcess(settings)
        spider = VoyantSpider(urls=urls, callback=collect_result)
        process.crawl(spider)
        process.start()
        
        return results
    
    def crawl_sitemap(self, sitemap_url: str) -> List[Dict[str, Any]]:
        """
        Crawl all URLs from a sitemap.
        
        Args:
            sitemap_url: URL of the sitemap.xml
            
        Returns:
            List of results
        """
        # Parse sitemap and extract URLs
        import requests
        from bs4 import BeautifulSoup
        
        response = requests.get(sitemap_url)
        soup = BeautifulSoup(response.text, 'lxml-xml')
        
        urls = [loc.text for loc in soup.find_all('loc')]
        return self.crawl(urls)
