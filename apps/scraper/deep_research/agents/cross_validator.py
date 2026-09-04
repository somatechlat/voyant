"""
Cross-validation agent.

Verifies that claims are supported by at least two independent sources
using deterministic n-gram overlap and source-diversity heuristics.
"""

from __future__ import annotations

import re

from apps.scraper.deep_research.schemas import Finding


class CrossValidator:
    """
    Cross-validates findings against a multi-source corpus.

    A claim is considered *validated* when:
      1. At least 2 unique domains provide supporting n-gram overlap.
      2. The overlap ratio exceeds a configurable threshold.
    """

    def __init__(self, ngram_size: int = 4, overlap_threshold: float = 0.15) -> None:
        self._n = ngram_size
        self._threshold = overlap_threshold

    @staticmethod
    def _domain(url: str) -> str:
        """Extract normalized domain from URL."""
        from urllib.parse import urlparse

        netloc = urlparse(url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc

    def _ngrams(self, text: str) -> set[str]:
        """Return character n-grams for the text."""
        cleaned = re.sub(r"\s+", " ", text.lower().strip())
        if len(cleaned) < self._n:
            return set()
        return {cleaned[i : i + self._n] for i in range(len(cleaned) - self._n + 1)}

    def _overlap(self, text_a: str, text_b: str) -> float:
        """Compute Jaccard overlap of character n-grams."""
        ng_a = self._ngrams(text_a)
        ng_b = self._ngrams(text_b)
        if not ng_a or not ng_b:
            return 0.0
        intersection = ng_a & ng_b
        union = ng_a | ng_b
        return len(intersection) / len(union)

    def validate(
        self,
        findings: list[Finding],
        url_texts: dict[str, str],
    ) -> list[Finding]:
        """
        Validate findings against the full source corpus.

        Args:
            findings: Previously synthesized findings.
            url_texts: Mapping of URL -> extracted text for all fetched pages.

        Returns:
            Updated findings with cross_validated and confidence_score set.
        """
        validated: list[Finding] = []

        for finding in findings:
            claim = finding.claim
            claim_ngrams = self._ngrams(claim)
            if not claim_ngrams:
                validated.append(finding)
                continue

            supporting_domains: set[str] = set()
            total_overlap = 0.0
            matches = 0

            for url, text in url_texts.items():
                if url in finding.supporting_sources:
                    continue  # Skip sources already counted in synthesis.
                overlap = self._overlap(claim, text)
                if overlap >= self._threshold:
                    domain = self._domain(url)
                    supporting_domains.add(domain)
                    total_overlap += overlap
                    matches += 1

            # Combine with original supporting sources.
            all_domains = supporting_domains | {
                self._domain(u) for u in finding.supporting_sources
            }

            cross_validated = len(all_domains) >= 2
            confidence = min(
                1.0,
                len(all_domains) * 0.25 + (total_overlap / max(matches, 1)) * 0.5,
            )

            validated.append(
                Finding(
                    claim=finding.claim,
                    evidence_chunks=finding.evidence_chunks,
                    supporting_sources=list(
                        set(finding.supporting_sources) | set(url_texts.keys())
                    )[:20],
                    confidence_score=round(confidence, 4),
                    cross_validated=cross_validated,
                )
            )

        return validated

    def validate_single(
        self,
        claim: str,
        url_texts: dict[str, str],
    ) -> tuple[bool, float, list[str]]:
        """
        Validate a single claim string.

        Returns:
            (is_validated, confidence_score, list_of_supporting_urls)
        """
        supporting: list[str] = []
        domains: set[str] = set()
        total_overlap = 0.0
        matches = 0

        for url, text in url_texts.items():
            overlap = self._overlap(claim, text)
            if overlap >= self._threshold:
                domain = self._domain(url)
                if domain not in domains:
                    domains.add(domain)
                    supporting.append(url)
                total_overlap += overlap
                matches += 1

        validated = len(domains) >= 2
        confidence = min(
            1.0,
            len(domains) * 0.25 + (total_overlap / max(matches, 1)) * 0.5,
        )
        return validated, round(confidence, 4), supporting
