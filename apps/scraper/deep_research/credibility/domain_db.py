"""
Static domain credibility database.

Scores are derived from academic and industry heuristics for source reliability.
No LLM is used — all scores are deterministic constants or rule-based lookups.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier definitions (higher = more credible)
# ---------------------------------------------------------------------------

TIER_ACADEMIC = 0.95
TIER_GOVERNMENT = 0.90
TIER_MAJOR_NEWS = 0.80
TIER_ESTABLISHED_MEDIA = 0.65
TIER_SPECIALIST_BLOG = 0.50
TIER_GENERIC_BLOG = 0.30
TIER_FORUM = 0.20
TIER_UNKNOWN = 0.40
TIER_LOW_QUALITY = 0.10

# Domains mapped to explicit scores.
# This list is intentionally conservative and can be extended via Django ORM
# in future iterations without changing the deterministic fallback rules.
_EXPLICIT_SCORES: Dict[str, float] = {
    # Academic
    "arxiv.org": TIER_ACADEMIC,
    "pubmed.ncbi.nlm.nih.gov": TIER_ACADEMIC,
    "ncbi.nlm.nih.gov": TIER_ACADEMIC,
    "doi.org": TIER_ACADEMIC,
    "jstor.org": TIER_ACADEMIC,
    "ieee.org": TIER_ACADEMIC,
    "acm.org": TIER_ACADEMIC,
    "springer.com": TIER_ACADEMIC,
    "nature.com": TIER_ACADEMIC,
    "science.org": TIER_ACADEMIC,
    "cell.com": TIER_ACADEMIC,
    "plos.org": TIER_ACADEMIC,
    "biorxiv.org": TIER_ACADEMIC,
    "medrxiv.org": TIER_ACADEMIC,
    "ssrn.com": TIER_ACADEMIC,
    # Government / IGO
    "who.int": TIER_GOVERNMENT,
    "cdc.gov": TIER_GOVERNMENT,
    "fda.gov": TIER_GOVERNMENT,
    "europa.eu": TIER_GOVERNMENT,
    "un.org": TIER_GOVERNMENT,
    "worldbank.org": TIER_GOVERNMENT,
    "imf.org": TIER_GOVERNMENT,
    "oecd.org": TIER_GOVERNMENT,
    "gov.uk": TIER_GOVERNMENT,
    "gob.ec": TIER_GOVERNMENT,
    "gob.mx": TIER_GOVERNMENT,
    "gob.ar": TIER_GOVERNMENT,
    "gov.au": TIER_GOVERNMENT,
    "gov.br": TIER_GOVERNMENT,
    "data.gov": TIER_GOVERNMENT,
    # Major news
    "reuters.com": TIER_MAJOR_NEWS,
    "apnews.com": TIER_MAJOR_NEWS,
    "bloomberg.com": TIER_MAJOR_NEWS,
    "ft.com": TIER_MAJOR_NEWS,
    "wsj.com": TIER_MAJOR_NEWS,
    "nytimes.com": TIER_MAJOR_NEWS,
    "washingtonpost.com": TIER_MAJOR_NEWS,
    "theguardian.com": TIER_MAJOR_NEWS,
    "bbc.com": TIER_MAJOR_NEWS,
    "bbc.co.uk": TIER_MAJOR_NEWS,
    "economist.com": TIER_MAJOR_NEWS,
    "npr.org": TIER_MAJOR_NEWS,
    "aljazeera.com": TIER_MAJOR_NEWS,
    # Established tech / business
    "techcrunch.com": TIER_ESTABLISHED_MEDIA,
    "wired.com": TIER_ESTABLISHED_MEDIA,
    "theverge.com": TIER_ESTABLISHED_MEDIA,
    "arstechnica.com": TIER_ESTABLISHED_MEDIA,
    "zdnet.com": TIER_ESTABLISHED_MEDIA,
    "forbes.com": TIER_ESTABLISHED_MEDIA,
    "fastcompany.com": TIER_ESTABLISHED_MEDIA,
    # Low-quality / content-farm indicators
    "hubpages.com": TIER_LOW_QUALITY,
    "ezinearticles.com": TIER_LOW_QUALITY,
    "answers.yahoo.com": TIER_FORUM,
    "quora.com": TIER_FORUM,
    "reddit.com": TIER_FORUM,
}

# TLD-based heuristics for domains not in the explicit list.
_TLD_SCORES: Dict[str, float] = {
    ".edu": TIER_ACADEMIC,
    ".ac.uk": TIER_ACADEMIC,
    ".ac.jp": TIER_ACADEMIC,
    ".gov": TIER_GOVERNMENT,
    ".gob": TIER_GOVERNMENT,
    ".go.id": TIER_GOVERNMENT,
    ".go.jp": TIER_GOVERNMENT,
    ".go.kr": TIER_GOVERNMENT,
    ".mil": TIER_GOVERNMENT,
    ".int": TIER_GOVERNMENT,
}


class DomainCredibilityDB:
    """
    Deterministic domain credibility scorer.

    Resolves a URL to a credibility score in the range [0.0, 1.0] using a
    static lookup table, TLD heuristics, and subdomain normalization.
    """

    def __init__(
        self,
        explicit_scores: Optional[Dict[str, float]] = None,
        tld_scores: Optional[Dict[str, float]] = None,
    ) -> None:
        self._explicit = explicit_scores or _EXPLICIT_SCORES.copy()
        self._tld = tld_scores or _TLD_SCORES.copy()

    @staticmethod
    def _normalize_domain(url: str) -> str:
        """Extract and lower-case the registered domain from a URL."""
        try:
            parsed = urlparse(url if "//" in url else f"http://{url}")
            netloc = parsed.netloc.lower()
            if netloc.startswith("www."):
                netloc = netloc[4:]
            return netloc
        except Exception:
            return url.lower().strip("/")

    def score(self, url: str) -> float:
        """Return the credibility score for *url*."""
        domain = self._normalize_domain(url)

        # Exact match
        if domain in self._explicit:
            return self._explicit[domain]

        # Parent domain match (e.g. "news.bbc.co.uk" -> "bbc.co.uk")
        parts = domain.split(".")
        for i in range(len(parts) - 1):
            parent = ".".join(parts[i:])
            if parent in self._explicit:
                return self._explicit[parent]

        # TLD heuristic
        for tld, score in self._tld.items():
            if domain.endswith(tld):
                return score

        return TIER_UNKNOWN

    def bulk_score(self, urls: list[str]) -> Dict[str, float]:
        """Score many URLs at once."""
        return {url: self.score(url) for url in urls}


# Global singleton
_db_instance: Optional[DomainCredibilityDB] = None


def get_domain_credibility_db() -> DomainCredibilityDB:
    """Return the singleton domain credibility database."""
    global _db_instance
    if _db_instance is None:
        _db_instance = DomainCredibilityDB()
    return _db_instance
