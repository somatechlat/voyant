"""
Unit tests for Deep Research v2 Pydantic schemas.
"""

import pytest
from pydantic import ValidationError

from apps.scraper.deep_research.schemas import (
    Citation,
    FetchedContent,
    Finding,
    ResearchConfig,
    ResearchReport,
    ResearchResult,
    SearchResultItem,
    SynthesisOutput,
)


class TestResearchConfig:
    """Tests for the research configuration schema."""

    def test_minimal_config(self):
        cfg = ResearchConfig(query="test", tenant_id="t1")
        assert cfg.query == "test"
        assert cfg.breadth == 3
        assert cfg.depth == 2
        assert cfg.realm == "default"

    def test_custom_depth_and_breadth(self):
        cfg = ResearchConfig(query="q", tenant_id="t1", depth=4, breadth=5)
        assert cfg.depth == 4
        assert cfg.breadth == 5

    def test_depth_bounds(self):
        with pytest.raises(ValidationError):
            ResearchConfig(query="q", tenant_id="t1", depth=0)
        with pytest.raises(ValidationError):
            ResearchConfig(query="q", tenant_id="t1", depth=10)

    def test_breadth_bounds(self):
        with pytest.raises(ValidationError):
            ResearchConfig(query="q", tenant_id="t1", breadth=0)
        with pytest.raises(ValidationError):
            ResearchConfig(query="q", tenant_id="t1", breadth=15)

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            ResearchConfig(query="q", tenant_id="t1", injected="bad")


class TestCitation:
    """Tests for the Citation schema."""

    def test_creation(self):
        c = Citation(url="https://example.com", title="Example")
        assert c.url == "https://example.com"
        assert c.title == "Example"
        assert c.credibility_score == 0.0
        assert c.accessed_at != ""


class TestFinding:
    """Tests for the Finding schema."""

    def test_defaults(self):
        f = Finding(claim="Voyant is a data platform")
        assert f.claim == "Voyant is a data platform"
        assert f.evidence_chunks == []
        assert f.confidence_score == 0.0
        assert f.cross_validated is False


class TestResearchReport:
    """Tests for the ResearchReport schema."""

    def test_defaults(self):
        r = ResearchReport()
        assert r.markdown == ""
        assert r.findings == []
        assert r.citations == []
        assert r.urls_processed == 0


class TestResearchResult:
    """Tests for the ResearchResult schema."""

    def test_defaults(self):
        r = ResearchResult()
        assert r.status == "pending"
        assert r.job_id == ""
        assert r.artifacts == []


class TestSearchResultItem:
    """Tests for the SearchResultItem schema."""

    def test_creation(self):
        s = SearchResultItem(url="https://example.com", title="Ex")
        assert s.url == "https://example.com"
        assert s.rank == 0


class TestFetchedContent:
    """Tests for the FetchedContent schema."""

    def test_creation(self):
        fc = FetchedContent(url="https://example.com", text="hello")
        assert fc.url == "https://example.com"
        assert fc.text == "hello"


class TestSynthesisOutput:
    """Tests for the SynthesisOutput schema."""

    def test_defaults(self):
        so = SynthesisOutput()
        assert so.findings == []
        assert so.citations == []
        assert so.follow_up_queries == []
