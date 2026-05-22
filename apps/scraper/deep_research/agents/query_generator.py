"""
Deterministic query generator.

Expands a user query into *breadth* search-optimized sub-queries using
heuristic keyword extraction, stopword filtering, and query templates.
Zero LLM usage.
"""

from __future__ import annotations

import re
from typing import List, Set

# A conservative English + Spanish stopword list.
_STOPWORDS: Set[str] = {
    "a",
    "about",
    "above",
    "after",
    "again",
    "against",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "below",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "don",
    "down",
    "during",
    "each",
    "few",
    "for",
    "from",
    "further",
    "had",
    "has",
    "have",
    "having",
    "he",
    "her",
    "here",
    "hers",
    "herself",
    "him",
    "himself",
    "his",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "itself",
    "just",
    "me",
    "more",
    "most",
    "my",
    "myself",
    "no",
    "nor",
    "not",
    "now",
    "of",
    "off",
    "on",
    "once",
    "only",
    "or",
    "other",
    "our",
    "ours",
    "ourselves",
    "out",
    "over",
    "own",
    "same",
    "she",
    "should",
    "so",
    "some",
    "such",
    "than",
    "that",
    "the",
    "their",
    "theirs",
    "them",
    "themselves",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "to",
    "too",
    "under",
    "until",
    "up",
    "very",
    "was",
    "we",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "whom",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
    "yours",
    "yourself",
    "yourselves",
    "el",
    "la",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "y",
    "o",
    "pero",
    "por",
    "para",
    "con",
    "sin",
    "sobre",
    "entre",
    "desde",
    "hasta",
    "durante",
    "ante",
    "bajo",
    "segun",
    "mediante",
    "tras",
    "hacia",
    "excepto",
    "salvo",
    "como",
    "cuando",
    "donde",
    "que",
    "quien",
    "cual",
    "cuyo",
    "cuya",
    "lo",
    "le",
    "les",
    "se",
    "ya",
    "aun",
    "aunque",
    "si",
    "no",
    "tambien",
    "tampoco",
    "ni",
    "mas",
    "menos",
    "muy",
    "mucho",
    "muchos",
    "poco",
    "pocos",
    "todo",
    "todos",
    "cada",
    "otro",
    "otros",
    "alguno",
    "algunos",
    "ninguno",
    "ningunos",
    "tal",
    "tales",
    "mismo",
    "mismos",
    "tan",
    "tanto",
    "tal vez",
    "quizas",
    "acaso",
    "sea",
    "fuese",
    "hubiera",
    "habria",
    "sera",
    "era",
    "es",
    "son",
    "fue",
    "fueron",
    "esta",
    "estan",
    "estaba",
    "estaban",
    "estuvo",
    "estuvieron",
    "habia",
    "habian",
    "hay",
    "han",
    "ha",
    "he",
    "hemos",
    "habeis",
    "han",
    "tenia",
    "tenian",
    "tengo",
    "tiene",
    "tienen",
    "tuve",
    "tuvieron",
    "pude",
    "pudieron",
    "podria",
    "podrian",
    "debo",
    "debe",
    "deben",
    "debia",
    "debieron",
    "quiso",
    "quisieron",
    "sabe",
    "saben",
    "sabia",
    "sabian",
    "dice",
    "dicen",
    "dijo",
    "dijeron",
    "hace",
    "hacen",
    "hizo",
    "hicieron",
    "ve",
    "ven",
    "vio",
    "vieron",
    "va",
    "van",
    "fue",
    "iban",
    "voy",
    "vamos",
    "vais",
    "van",
    "soy",
    "eres",
    "es",
    "somos",
    "sois",
    "son",
    "estoy",
    "estas",
    "esta",
    "estamos",
    "estais",
    "estan",
}

# Query templates for breadth expansion.
_TEMPLATES: List[str] = [
    "{query}",
    '"{query}"',
    "{query} overview",
    "{query} latest research",
    "{query} statistics",
    "{query} case study",
    "{query} best practices",
    "{query} challenges",
    "{query} future trends",
    "{query} impact analysis",
    "site:gov {query}",
    "site:edu {query}",
    'filetype:pdf "{query}"',
]


class QueryGenerator:
    """
    Generates search-optimized sub-queries deterministically.

    The algorithm:
      1. Tokenizes the input query.
      2. Removes stopwords to find keywords.
      3. Selects templates based on the requested breadth.
      4. Returns unique sub-queries.
    """

    def __init__(self, templates: List[str] | None = None) -> None:
        self._templates = templates or _TEMPLATES.copy()

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Lower-case and split on non-alphanumeric characters."""
        return re.findall(r"[a-z0-9áéíóúñü]+", text.lower())

    def generate(
        self,
        query: str,
        breadth: int = 3,
    ) -> List[str]:
        """
        Generate *breadth* unique sub-queries from *query*.

        Args:
            query: The original research query.
            breadth: Number of sub-queries to produce.

        Returns:
            A list of unique search query strings.
        """
        tokens = self._tokenize(query)
        keywords = [t for t in tokens if t not in _STOPWORDS]
        core = " ".join(keywords) if keywords else query

        sub_queries: List[str] = []
        for template in self._templates[:breadth]:
            sub = template.format(query=core)
            if sub not in sub_queries:
                sub_queries.append(sub)

        # If templates exhausted, append simple keyword permutations.
        if len(sub_queries) < breadth and len(keywords) > 1:
            for i in range(len(keywords)):
                perm = " ".join(keywords[: i + 1])
                if perm not in sub_queries:
                    sub_queries.append(perm)
                if len(sub_queries) >= breadth:
                    break

        return sub_queries[:breadth]

    def generate_follow_up(
        self,
        query: str,
        findings: List[str],
        breadth: int = 3,
    ) -> List[str]:
        """
        Generate follow-up queries based on prior findings.

        Args:
            query: Original query.
            findings: List of claim strings from prior synthesis.
            breadth: Number of follow-up queries.

        Returns:
            New sub-queries targeting gaps in the findings.
        """
        follow_ups: List[str] = []
        base_keywords = set(self._tokenize(query))

        for finding in findings:
            finding_tokens = set(self._tokenize(finding))
            novel = finding_tokens - base_keywords
            if novel:
                novel_phrase = " ".join(sorted(novel)[:3])
                candidate = f"{query} {novel_phrase}"
                if candidate not in follow_ups:
                    follow_ups.append(candidate)
            if len(follow_ups) >= breadth:
                break

        # Fallback to generic deeper queries.
        if len(follow_ups) < breadth:
            fallbacks = [
                f"{query} detailed analysis",
                f"{query} recent developments",
                f"{query} expert review",
                f"{query} comparative study",
                f"{query} methodology",
            ]
            for fb in fallbacks:
                if fb not in follow_ups:
                    follow_ups.append(fb)
                if len(follow_ups) >= breadth:
                    break

        return follow_ups[:breadth]
