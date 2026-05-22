"""
Deep Research Module v2 for Voyant v3.1.0.

Deterministic, multi-source deep research pipeline orchestrated by Temporal.
Zero LLM usage — all algorithms are deterministic and reproducible.

Modules:
    schemas          — Pydantic data models for the research pipeline.
    workflow         — Temporal workflow orchestrating the full pipeline.
    activities       — Temporal activities for research steps.
    agents           — Deterministic research agents (query, score, extract, etc.).
    sources          — Search engine clients (SearXNG, Brave, Google CSE).
    credibility      — Domain credibility database and scoring.
"""

from apps.scraper.deep_research.schemas import (
    Citation,
    EvidenceChunk,
    Finding,
    ResearchConfig,
    ResearchReport,
    ResearchResult,
)

__all__ = [
    "ResearchConfig",
    "ResearchResult",
    "Citation",
    "Finding",
    "EvidenceChunk",
    "ResearchReport",
]
