"""
Content extraction agent.

Wraps trafilatura, readability-lxml, newspaper3k, and crawl4ai in a
priority-based fallback chain. All extraction is deterministic.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Optional dependency availability flags.
_TRAFILATURA_AVAILABLE = False
_READABILITY_AVAILABLE = False
_NEWSPAPER_AVAILABLE = False
_CRAWL4AI_AVAILABLE = False

trafilatura: Any = None  # type: ignore[no-redef]
try:
    import trafilatura as _trafilatura_mod  # type: ignore[import-not-found]

    trafilatura = _trafilatura_mod
    _TRAFILATURA_AVAILABLE = True
except ImportError:
    pass

Document: Any = None  # type: ignore[no-redef]
try:
    from readability import Document as _Document_cls  # type: ignore[import-not-found]

    Document = _Document_cls
    _READABILITY_AVAILABLE = True
except ImportError:
    pass

newspaper: Any = None  # type: ignore[no-redef]
try:
    import newspaper as _newspaper_mod  # type: ignore[import-not-found]

    newspaper = _newspaper_mod
    _NEWSPAPER_AVAILABLE = True
except ImportError:
    pass

try:
    import importlib.util

    _CRAWL4AI_AVAILABLE = importlib.util.find_spec("crawl4ai") is not None
except ImportError:
    pass


class ContentExtractor:
    """
    Extracts article text and metadata from HTML using a prioritized
    fallback chain of extraction libraries.
    """

    def __init__(self) -> None:
        self._methods = [
            ("trafilatura", self._extract_trafilatura),
            ("readability", self._extract_readability),
            ("newspaper", self._extract_newspaper),
            ("crawl4ai", self._extract_crawl4ai),
        ]

    # ------------------------------------------------------------------
    # Individual extractors
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_trafilatura(html: str, url: str) -> dict[str, Any] | None:
        if not _TRAFILATURA_AVAILABLE:
            return None
        try:
            text = trafilatura.extract(html, url=url, include_comments=False)
            if text and len(text.strip()) > 100:
                return {"text": text.strip(), "title": "", "method": "trafilatura"}
        except Exception:
            logger.debug("trafilatura extraction failed for %s", url, exc_info=True)
        return None

    @staticmethod
    def _extract_readability(html: str, url: str) -> dict[str, Any] | None:
        if not _READABILITY_AVAILABLE:
            return None
        try:
            doc = Document(html)
            text = doc.summary()
            import re

            text = re.sub(r"<[^>]+>", "", text)
            text = re.sub(r"\s+", " ", text).strip()
            if len(text) > 100:
                return {
                    "text": text,
                    "title": doc.title() or "",
                    "method": "readability",
                }
        except Exception:
            logger.debug("readability extraction failed for %s", url, exc_info=True)
        return None

    @staticmethod
    def _extract_newspaper(html: str, url: str) -> dict[str, Any] | None:
        if not _NEWSPAPER_AVAILABLE:
            return None
        try:
            article = newspaper.Article(url)
            article.set_html(html)
            article.parse()
            text = article.text or ""
            if len(text.strip()) > 100:
                return {
                    "text": text.strip(),
                    "title": article.title or "",
                    "method": "newspaper",
                }
        except Exception:
            logger.debug("newspaper extraction failed for %s", url, exc_info=True)
        return None

    @staticmethod
    def _extract_crawl4ai(html: str, url: str) -> dict[str, Any] | None:
        if not _CRAWL4AI_AVAILABLE:
            return None
        try:
            from crawl4ai import WebCrawler  # type: ignore[import-not-found]

            crawler = WebCrawler()
            result = crawler.run(url=url)
            text = getattr(result, "markdown", "") or getattr(result, "text", "")
            if text and len(text.strip()) > 100:
                return {
                    "text": text.strip(),
                    "title": getattr(result, "title", "") or "",
                    "method": "crawl4ai",
                }
        except Exception:
            logger.debug("crawl4ai extraction failed for %s", url, exc_info=True)
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(self, html: str, url: str) -> dict[str, Any]:
        """
        Extract content from *html* originating from *url*.

        Returns a dict with keys:
            text (str), title (str), method (str), success (bool)
        """
        for name, method in self._methods:
            result = method(html, url)
            if result:
                result["success"] = True
                result["url"] = url
                logger.debug(f"[ContentExtractor] used {name} for {url}")
                return result

        # Ultimate fallback: strip tags and return raw text.
        import re

        raw = re.sub(r"<[^>]+>", " ", html)
        raw = re.sub(r"\s+", " ", raw).strip()
        return {
            "text": raw[:50000],  # Hard cap to avoid memory bloat.
            "title": "",
            "method": "fallback",
            "success": len(raw) > 50,
            "url": url,
        }

    def bulk_extract(self, items: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """
        Extract content from multiple (url, html) pairs.

        Args:
            items: List of (url, html) tuples.

        Returns:
            List of extraction result dicts.
        """
        return [self.extract(html, url) for url, html in items]
