"""
Source scoring agent.

Combines domain credibility (from the static DB) with content freshness
heuristics to produce a unified [0, 1] source score.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional

from apps.scraper.deep_research.credibility.domain_db import (
    DomainCredibilityDB,
    get_domain_credibility_db,
)

logger = logging.getLogger(__name__)

# Regex patterns that match common date strings in HTML/text.
_DATE_PATTERNS = [
    re.compile(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})"),  # 2024-01-15
    re.compile(r"(\d{1,2})[-/](\d{1,2})[-/](\d{4})"),  # 01/15/2024
    re.compile(
        r"(January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+"
        r"(\d{1,2}),?\s+(\d{4})",
        re.IGNORECASE,
    ),
]

_MONTH_MAP = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


class SourceScorer:
    """
    Scores web sources by credibility and freshness.

    The unified score is a weighted product:
        score = credibility * (0.6 + 0.4 * freshness)
    where freshness decays linearly with age (max 5 years).
    """

    def __init__(self, db: Optional[DomainCredibilityDB] = None) -> None:
        self._db = db or get_domain_credibility_db()

    @staticmethod
    def _extract_years(text: str) -> List[int]:
        """Extract plausible publication years from text."""
        years: List[int] = []
        for pat in _DATE_PATTERNS:
            for match in pat.finditer(text):
                groups = match.groups()
                # Try to locate the year group (the 4-digit number).
                year_str = next((g for g in groups if len(str(g)) == 4), None)
                if year_str:
                    try:
                        y = int(year_str)
                        if 1990 <= y <= datetime.now(timezone.utc).year + 1:
                            years.append(y)
                    except ValueError:
                        continue
        return years

    def freshness_score(self, text: str, fetched_at: Optional[str] = None) -> float:
        """
        Compute a freshness score in [0, 1].

        1.0  = published today
        0.0  = older than 5 years
        """
        now = datetime.now(timezone.utc)

        # Use fetched_at as a fallback anchor.
        anchor = now
        if fetched_at:
            try:
                anchor = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
            except Exception:
                pass

        years = self._extract_years(text)
        if not years:
            # No date found — assume moderately fresh.
            return 0.5

        most_recent = max(years)
        try:
            pub_date = datetime(most_recent, 6, 15, tzinfo=timezone.utc)
        except ValueError:
            return 0.5

        age_days = (anchor - pub_date).days
        max_days = 5 * 365  # 5 years
        if age_days <= 0:
            return 1.0
        if age_days >= max_days:
            return 0.0
        return 1.0 - (age_days / max_days)

    def score_source(
        self,
        url: str,
        text: str = "",
        fetched_at: Optional[str] = None,
    ) -> Dict[str, float]:
        """
        Return a dict with 'credibility', 'freshness', and 'total' scores.

        Args:
            url: The source URL.
            text: Extracted text content (for freshness analysis).
            fetched_at: ISO timestamp when the page was fetched.

        Returns:
            {"credibility": float, "freshness": float, "total": float}
        """
        credibility = self._db.score(url)
        freshness = self.freshness_score(text, fetched_at)
        total = credibility * (0.6 + 0.4 * freshness)

        return {
            "credibility": round(credibility, 4),
            "freshness": round(freshness, 4),
            "total": round(total, 4),
        }

    def filter_sources(
        self,
        url_texts: Dict[str, str],
        min_score: float = 0.15,
        fetched_at: Optional[str] = None,
    ) -> Dict[str, Dict[str, float]]:
        """
        Score many sources and return only those above *min_score*.

        Args:
            url_texts: Mapping of URL -> extracted text.
            min_score: Minimum total score to retain.
            fetched_at: Shared fetch timestamp.

        Returns:
            Mapping of URL -> score dict for passing sources.
        """
        results: Dict[str, Dict[str, float]] = {}
        for url, text in url_texts.items():
            scores = self.score_source(url, text, fetched_at)
            if scores["total"] >= min_score:
                results[url] = scores
        return results
