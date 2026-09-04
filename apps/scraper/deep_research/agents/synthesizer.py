"""
Synthesizer agent.

Structures extracted text into findings with evidence chunks and source
attribution using deterministic TF-IDF-style keyword overlap and sentence
salience scoring. Zero LLM usage.
"""

from __future__ import annotations

import math
import re
from collections import Counter

from apps.scraper.deep_research.schemas import (
    Citation,
    EvidenceChunk,
    Finding,
    SearchResultItem,
    SynthesisOutput,
)


class Synthesizer:
    """
    Synthesizes fetched content into structured findings.

    Algorithm:
      1. Tokenize all sentences across all sources.
      2. Compute inverse document frequency (IDF) over the corpus.
      3. Score each sentence by keyword density + uniqueness.
      4. Cluster top-scoring sentences into findings by keyword overlap.
      5. Emit Finding objects with EvidenceChunk attribution.
    """

    def __init__(self, max_sentences_per_source: int = 30) -> None:
        self._max_sentences = max_sentences_per_source

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Lower-case alphanumeric tokenization."""
        return re.findall(r"[a-z0-9áéíóúñü]+", text.lower())

    @staticmethod
    def _sentences(text: str) -> list[str]:
        """Naive sentence splitter."""
        text = re.sub(r"\s+", " ", text)
        # Split on sentence terminators followed by space and capital.
        parts = re.split(r'(?<=[.!?])\s+(?=[A-Z"\'])', text)
        return [s.strip() for s in parts if len(s.strip()) > 20]

    def _compute_idf(self, docs: list[list[str]]) -> dict[str, float]:
        """Compute IDF over tokenized documents."""
        n = len(docs)
        idf: dict[str, float] = {}
        for doc in docs:
            seen: set[str] = set()
            for token in doc:
                if token not in seen:
                    seen.add(token)
                    idf[token] = idf.get(token, 0.0) + 1.0
        for token, df in idf.items():
            idf[token] = math.log((1.0 + n) / (1.0 + df)) + 1.0
        return idf

    def _score_sentences(
        self,
        sentences: list[tuple[str, str]],  # (sentence, source_url)
        idf: dict[str, float],
    ) -> list[tuple[float, str, str]]:
        """Return list of (score, sentence, source_url) sorted descending."""
        scored: list[tuple[float, str, str]] = []
        for sent, src in sentences:
            tokens = self._tokenize(sent)
            if not tokens:
                continue
            tf = Counter(tokens)
            score = sum(idf.get(t, 0.0) * tf[t] for t in tf) / len(tokens)
            # Penalize very short sentences.
            if len(tokens) < 5:
                score *= 0.5
            scored.append((score, sent, src))
        scored.sort(key=lambda x: x[0], reverse=True)
        return scored

    def _cluster_findings(
        self,
        scored: list[tuple[float, str, str]],
        top_n: int = 15,
    ) -> list[Finding]:
        """
        Cluster top sentences into findings by Jaccard token overlap.
        """
        top = scored[:top_n]
        findings: list[Finding] = []
        used: set[int] = set()

        for idx, (score, sent, src) in enumerate(top):
            if idx in used:
                continue
            tokens = set(self._tokenize(sent))
            cluster_sents = [(score, sent, src)]
            used.add(idx)

            for jdx in range(idx + 1, len(top)):
                if jdx in used:
                    continue
                other_tokens = set(self._tokenize(top[jdx][1]))
                if not other_tokens:
                    continue
                intersection = tokens & other_tokens
                union = tokens | other_tokens
                jaccard = len(intersection) / len(union) if union else 0.0
                if jaccard > 0.25:
                    cluster_sents.append(top[jdx])
                    used.add(jdx)
                    tokens |= other_tokens

            # Build Finding from cluster.
            evidence = [
                EvidenceChunk(
                    text=s,
                    source_url=src,
                    relevance_score=round(sc, 4),
                )
                for sc, s, src in cluster_sents
            ]
            sources = list({src for _, _, src in cluster_sents})
            claim = cluster_sents[0][1]  # Highest-scoring sentence as claim.
            findings.append(
                Finding(
                    claim=claim,
                    evidence_chunks=evidence,
                    supporting_sources=sources,
                    confidence_score=round(min(1.0, len(sources) * 0.3 + 0.2), 4),
                )
            )

        return findings

    def synthesize(
        self,
        url_texts: dict[str, str],
        search_results: dict[str, SearchResultItem],
    ) -> SynthesisOutput:
        """
        Synthesize text from multiple sources into structured findings.

        Args:
            url_texts: Mapping of URL -> extracted text.
            search_results: Mapping of URL -> original SearchResultItem.

        Returns:
            SynthesisOutput with findings, citations, and follow-up queries.
        """
        # 1. Gather sentences per source.
        all_sentences: list[tuple[str, str]] = []
        docs: list[list[str]] = []

        for url, text in url_texts.items():
            sents = self._sentences(text)[: self._max_sentences]
            for s in sents:
                all_sentences.append((s, url))
            docs.append(self._tokenize(text))

        if not all_sentences:
            return SynthesisOutput()

        # 2. Compute IDF and score sentences.
        idf = self._compute_idf(docs)
        scored = self._score_sentences(all_sentences, idf)

        # 3. Cluster into findings.
        findings = self._cluster_findings(scored)

        # 4. Build citations.
        citations: list[Citation] = []
        seen_domains: set[str] = set()
        for url, item in search_results.items():
            if url in url_texts:
                from urllib.parse import urlparse

                domain = urlparse(url).netloc.lower()
                if domain not in seen_domains:
                    seen_domains.add(domain)
                    citations.append(
                        Citation(
                            url=url,
                            title=item.title,
                            domain=domain,
                        )
                    )

        # 5. Generate follow-up queries from finding keywords.
        follow_up_queries: list[str] = []
        if findings:
            base_claims = [f.claim for f in findings[:3]]
            keywords: set[str] = set()
            for claim in base_claims:
                keywords.update(self._tokenize(claim))
            # Remove common words.
            common = {
                "the",
                "and",
                "for",
                "are",
                "but",
                "not",
                "you",
                "all",
                "can",
                "had",
                "her",
                "was",
                "one",
                "our",
                "out",
                "day",
                "get",
                "has",
                "him",
                "his",
                "how",
                "its",
                "may",
                "new",
                "now",
                "old",
                "see",
                "two",
                "who",
                "boy",
                "did",
                "she",
                "use",
                "her",
                "way",
                "many",
                "oil",
                "sit",
                "set",
                "run",
                "eat",
                "far",
                "sea",
                "eye",
                "ago",
                "off",
                "too",
                "any",
                "say",
                "man",
                "try",
                "ask",
                "end",
                "why",
                "let",
                "put",
                "say",
                "she",
                "try",
                "way",
                "own",
                "say",
                "too",
                "old",
                "tell",
                "very",
                "when",
                "much",
                "would",
                "there",
                "their",
                "what",
                "said",
                "each",
                "which",
                "will",
                "about",
                "could",
                "other",
                "after",
                "first",
                "never",
                "these",
                "think",
                "where",
                "being",
                "every",
                "great",
                "might",
                "shall",
                "still",
                "those",
                "while",
                "this",
                "that",
                "with",
                "have",
                "from",
                "they",
                "know",
                "want",
                "been",
                "good",
                "much",
                "some",
                "time",
                "very",
                "when",
                "come",
                "here",
                "just",
                "like",
                "long",
                "make",
                "many",
                "over",
                "such",
                "take",
                "than",
                "them",
                "well",
                "were",
            }
            novel = sorted(keywords - common)[:5]
            if novel:
                follow_up_queries.append(" ".join(novel))

        return SynthesisOutput(
            findings=findings,
            citations=citations,
            follow_up_queries=follow_up_queries,
        )
