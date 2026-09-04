"""
Pydantic schemas for the Deep Research v2 pipeline.

All models use Pydantic v2 ConfigDict for strict validation and serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResearchConfig(BaseModel):
    """Input configuration for a DeepResearchWorkflowV2 run."""

    query: str = Field(..., description="Primary research query.")
    breadth: int = Field(default=3, ge=1, le=10, description="Number of parallel sub-queries.")
    depth: int = Field(default=2, ge=1, le=5, description="Recursive depth levels.")
    tenant_id: str = Field(..., description="Tenant isolation identifier.")
    realm: str = Field(default="default", description="Security / data realm.")
    user_id: str = Field(default="", description="Initiating user identifier.")
    max_urls_per_query: int = Field(
        default=5, ge=1, le=20, description="Max URLs to fetch per sub-query."
    )
    min_source_score: float = Field(
        default=0.15, ge=0.0, le=1.0, description="Minimum source credibility to retain."
    )
    dedup_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Jaccard threshold for near-duplicate removal."
    )
    require_cross_validation: bool = Field(
        default=True, description="Require >=2 sources to accept a claim."
    )

    model_config = ConfigDict(extra="forbid")


class Citation(BaseModel):
    """A single bibliographic citation for a source."""

    url: str
    title: str = ""
    domain: str = ""
    accessed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    credibility_score: float = 0.0
    freshness_score: float = 0.0

    model_config = ConfigDict(extra="forbid")


class EvidenceChunk(BaseModel):
    """A snippet of text extracted from a source with relevance metadata."""

    text: str
    source_url: str
    source_title: str = ""
    relevance_score: float = 0.0
    extracted_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    model_config = ConfigDict(extra="forbid")


class Finding(BaseModel):
    """A structured finding synthesized from one or more evidence chunks."""

    claim: str
    evidence_chunks: list[EvidenceChunk] = Field(default_factory=list)
    supporting_sources: list[str] = Field(default_factory=list)
    confidence_score: float = 0.0
    cross_validated: bool = False

    model_config = ConfigDict(extra="forbid")


class ResearchReport(BaseModel):
    """Final Markdown research report with metadata."""

    markdown: str = ""
    executive_summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    confidence_score: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    query: str = ""
    breadth: int = 0
    depth: int = 0
    urls_processed: int = 0
    sources_deduplicated: int = 0
    artifact_hash: str | None = None

    model_config = ConfigDict(extra="forbid")


class ResearchResult(BaseModel):
    """High-level result returned by the DeepResearchWorkflowV2."""

    status: str = "pending"  # pending | success | failed | partial
    job_id: str = ""
    config: ResearchConfig | None = None
    report: ResearchReport | None = None
    error: str | None = None
    artifacts: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")


class SearchResultItem(BaseModel):
    """Normalized item returned by any search backend."""

    url: str
    title: str = ""
    snippet: str = ""
    engine: str = ""
    rank: int = 0

    model_config = ConfigDict(extra="forbid")


class FetchedContent(BaseModel):
    """Content fetched from a URL after extraction and scoring."""

    url: str
    html: str = ""
    text: str = ""
    title: str = ""
    domain: str = ""
    source_score: float = 0.0
    freshness_score: float = 0.0
    fetched_at: str = ""
    error: str | None = None

    model_config = ConfigDict(extra="forbid")


class SynthesisOutput(BaseModel):
    """Intermediate output produced by the synthesizer agent."""

    findings: list[Finding] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    follow_up_queries: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")
