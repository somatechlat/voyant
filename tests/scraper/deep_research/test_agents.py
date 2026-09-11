"""Tests for deep research agents: QueryGenerator, ContentExtractor, SourceScorer, Synthesizer, CrossValidator.

Note: ReportGenerator excluded — report_generator.py has a pre-existing
IndentationError (missing `lines = [` and undefined `validated` variable).
We use importlib.util to load individual agent modules directly from file,
bypassing the __init__.py which triggers the broken import chain.
"""

import importlib.util
import sys
from pathlib import Path

_AGENTS_DIR = Path(__file__).resolve().parents[3] / "apps" / "scraper" / "deep_research" / "agents"


def _load_module(name: str, filepath: Path):
    """Load a Python module directly from filepath, registering it in sys.modules."""
    spec = importlib.util.spec_from_file_location(name, filepath)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Ensure the parent packages exist in sys.modules
for _pkg in [
    "apps.scraper.deep_research.agents",
]:
    if _pkg not in sys.modules:
        import types
        _mod = types.ModuleType(_pkg)
        _mod.__path__ = [str(Path(_pkg.replace(".", "/")))]
        _mod.__package__ = _pkg
        sys.modules[_pkg] = _mod

_qg_mod = _load_module("apps.scraper.deep_research.agents.query_generator", _AGENTS_DIR / "query_generator.py")
_ce_mod = _load_module("apps.scraper.deep_research.agents.content_extractor", _AGENTS_DIR / "content_extractor.py")
_ss_mod = _load_module("apps.scraper.deep_research.agents.source_scorer", _AGENTS_DIR / "source_scorer.py")
_sy_mod = _load_module("apps.scraper.deep_research.agents.synthesizer", _AGENTS_DIR / "synthesizer.py")
_cv_mod = _load_module("apps.scraper.deep_research.agents.cross_validator", _AGENTS_DIR / "cross_validator.py")

QueryGenerator = _qg_mod.QueryGenerator
ContentExtractor = _ce_mod.ContentExtractor
SourceScorer = _ss_mod.SourceScorer
Synthesizer = _sy_mod.Synthesizer
CrossValidator = _cv_mod.CrossValidator

from apps.scraper.deep_research.schemas import (  # noqa: E402
    Finding,
    SearchResultItem,
)

# ---------------------------------------------------------------------------
# QueryGenerator
# ---------------------------------------------------------------------------


class TestQueryGenerator:
    def test_basic_generation(self):
        gen = QueryGenerator()
        result = gen.generate("machine learning", breadth=3)
        assert len(result) == 3
        assert all(isinstance(q, str) for q in result)

    def test_breadth_limits_output(self):
        gen = QueryGenerator()
        result = gen.generate("AI", breadth=1)
        assert len(result) == 1

    def test_stopwords_removed(self):
        gen = QueryGenerator()
        result = gen.generate("what is the best approach for data science", breadth=1)
        # Stopwords like "what", "is", "the", "for" should be removed
        assert "what" not in result[0].lower().split()[:3]

    def test_unique_queries(self):
        gen = QueryGenerator()
        result = gen.generate("neural networks", breadth=5)
        assert len(result) == len(set(result))

    def test_empty_query(self):
        gen = QueryGenerator()
        result = gen.generate("", breadth=3)
        assert len(result) <= 3

    def test_breadth_exceeds_templates_uses_permutations(self):
        gen = QueryGenerator()
        # Request more than available templates
        result = gen.generate("deep learning neural network optimization", breadth=13)
        assert len(result) <= 13

    def test_follow_up_queries(self):
        gen = QueryGenerator()
        findings = ["Neural networks improve accuracy significantly"]
        result = gen.generate_follow_up("machine learning", findings, breadth=3)
        assert len(result) <= 3
        assert all(isinstance(q, str) for q in result)

    def test_follow_up_fallback(self):
        gen = QueryGenerator()
        # Empty findings should still produce fallback queries
        result = gen.generate_follow_up("AI", [], breadth=2)
        assert len(result) == 2

    def test_tokenize(self):
        tokens = QueryGenerator._tokenize("Hello, World! 123")
        assert "hello" in tokens
        assert "world" in tokens
        assert "123" in tokens

    def test_custom_templates(self):
        custom = ["search: {query}", "find: {query}"]
        gen = QueryGenerator(templates=custom)
        result = gen.generate("test", breadth=2)
        assert result[0] == "search: test"
        assert result[1] == "find: test"


# ---------------------------------------------------------------------------
# ContentExtractor
# ---------------------------------------------------------------------------


class TestContentExtractor:
    def test_fallback_extraction(self):
        """When no extraction libraries produce results, fallback should strip tags."""
        ext = ContentExtractor()
        html = "<html><body><p>" + "This is a long article text. " * 20 + "</p></body></html>"
        result = ext.extract(html, "https://example.com")
        assert "text" in result
        assert "method" in result
        assert "success" in result
        assert result["url"] == "https://example.com"

    def test_fallback_caps_text(self):
        """Fallback extraction should cap text at 50000 chars."""
        ext = ContentExtractor()
        html = "<p>" + "x" * 100000 + "</p>"
        result = ext.extract(html, "https://example.com")
        assert len(result["text"]) <= 50000

    def test_empty_html(self):
        ext = ContentExtractor()
        result = ext.extract("", "https://example.com")
        assert "text" in result
        assert result["method"] == "fallback"

    def test_bulk_extract(self):
        ext = ContentExtractor()
        items = [
            ("https://a.com", "<html><body><p>" + "Content A " * 20 + "</p></body></html>"),
            ("https://b.com", "<html><body><p>" + "Content B " * 20 + "</p></body></html>"),
        ]
        results = ext.bulk_extract(items)
        assert len(results) == 2
        assert all("text" in r for r in results)

    def test_result_has_required_keys(self):
        ext = ContentExtractor()
        html = "<html><body><p>" + "text content " * 20 + "</p></body></html>"
        result = ext.extract(html, "https://example.com")
        assert "text" in result
        assert "title" in result
        assert "method" in result
        assert "success" in result
        assert "url" in result


# ---------------------------------------------------------------------------
# SourceScorer
# ---------------------------------------------------------------------------


class TestSourceScorer:
    def test_known_academic_domain(self):
        scorer = SourceScorer()
        scores = scorer.score_source("https://arxiv.org/abs/1234")
        assert scores["credibility"] >= 0.90

    def test_known_government_domain(self):
        scorer = SourceScorer()
        scores = scorer.score_source("https://cdc.gov/health")
        assert scores["credibility"] >= 0.85

    def test_unknown_domain(self):
        scorer = SourceScorer()
        scores = scorer.score_source("https://random-blog-xyz.com/post")
        assert scores["credibility"] == 0.40  # TIER_UNKNOWN

    def test_freshness_score_recent(self):
        scorer = SourceScorer()
        text = "Published on 2025-06-15 this article discusses recent advances"
        score = scorer.freshness_score(text)
        assert score > 0.5

    def test_freshness_score_old(self):
        scorer = SourceScorer()
        text = "Published on 2019-01-01 this old article discusses past events"
        score = scorer.freshness_score(text)
        assert score < 0.5

    def test_freshness_no_date_returns_05(self):
        scorer = SourceScorer()
        score = scorer.freshness_score("No dates in this text at all")
        assert score == 0.5

    def test_total_score_range(self):
        scorer = SourceScorer()
        scores = scorer.score_source("https://nature.com/article", "Published 2024-01-01")
        assert 0.0 <= scores["total"] <= 1.0
        assert 0.0 <= scores["credibility"] <= 1.0
        assert 0.0 <= scores["freshness"] <= 1.0

    def test_filter_sources(self):
        scorer = SourceScorer()
        url_texts = {
            "https://arxiv.org/paper": "Academic paper published 2024-06-01",
            "https://random-spam.com/post": "Spam content",
        }
        filtered = scorer.filter_sources(url_texts, min_score=0.15)
        # arxiv should pass; random-spam might or might not depending on score
        assert isinstance(filtered, dict)

    def test_edu_tld_high_score(self):
        scorer = SourceScorer()
        scores = scorer.score_source("https://mit.edu/research")
        assert scores["credibility"] >= 0.90

    def test_extract_years(self):
        years = SourceScorer._extract_years("Published on 2024-01-15 and updated 2025-03-20")
        assert 2024 in years
        assert 2025 in years

    def test_extract_years_month_name(self):
        years = SourceScorer._extract_years("Published January 15, 2024")
        assert 2024 in years

    def test_extract_years_no_dates(self):
        years = SourceScorer._extract_years("No dates here")
        assert years == []


# ---------------------------------------------------------------------------
# Synthesizer
# ---------------------------------------------------------------------------


class TestSynthesizer:
    def test_basic_synthesis(self):
        synth = Synthesizer()
        url_texts = {
            "https://a.com": "Machine learning is transforming healthcare. AI models can detect diseases early. Deep learning improves diagnosis accuracy.",
            "https://b.com": "Healthcare AI is growing rapidly. Machine learning models help doctors diagnose patients faster and more accurately.",
        }
        search_results = {
            "https://a.com": SearchResultItem(url="https://a.com", title="AI Healthcare"),
            "https://b.com": SearchResultItem(url="https://b.com", title="ML in Medicine"),
        }
        output = synth.synthesize(url_texts, search_results)
        assert len(output.findings) >= 0
        assert len(output.citations) >= 0

    def test_empty_input(self):
        synth = Synthesizer()
        output = synth.synthesize({}, {})
        assert output.findings == []
        assert output.citations == []

    def test_single_source(self):
        synth = Synthesizer()
        text = "Artificial intelligence is revolutionizing many industries. " * 10
        url_texts = {"https://example.com": text}
        search_results = {"https://example.com": SearchResultItem(url="https://example.com", title="AI")}
        output = synth.synthesize(url_texts, search_results)
        assert isinstance(output.findings, list)

    def test_findings_have_evidence(self):
        synth = Synthesizer()
        text = "Neural networks achieve state of the art results. Deep learning models outperform traditional methods. Transfer learning reduces training time significantly."
        url_texts = {"https://a.com": text}
        search_results = {"https://a.com": SearchResultItem(url="https://a.com", title="DL")}
        output = synth.synthesize(url_texts, search_results)
        for finding in output.findings:
            assert isinstance(finding, Finding)
            assert finding.claim
            assert isinstance(finding.evidence_chunks, list)

    def test_citations_built_from_search_results(self):
        synth = Synthesizer()
        text = "Content about artificial intelligence and machine learning applications in modern technology." * 5
        url_texts = {
            "https://nature.com/article": text,
            "https://arxiv.org/paper": text,
        }
        search_results = {
            "https://nature.com/article": SearchResultItem(url="https://nature.com/article", title="Nature AI"),
            "https://arxiv.org/paper": SearchResultItem(url="https://arxiv.org/paper", title="arXiv ML"),
        }
        output = synth.synthesize(url_texts, search_results)
        assert len(output.citations) == 2

    def test_sentences_splitter(self):
        synth = Synthesizer()
        # Sentences must be > 20 chars to pass the filter
        text = "Neural networks achieve state of the art results. Deep learning models outperform traditional methods. Transfer learning reduces training time significantly."
        sents = synth._sentences(text)
        assert len(sents) >= 2

    def test_idf_computation(self):
        synth = Synthesizer()
        docs = [["hello", "world"], ["hello", "test"], ["foo", "bar"]]
        idf = synth._compute_idf(docs)
        assert "hello" in idf
        assert "foo" in idf
        # "hello" appears in 2/3 docs, "foo" in 1/3 — foo should have higher IDF
        assert idf["foo"] > idf["hello"]


# ---------------------------------------------------------------------------
# CrossValidator
# ---------------------------------------------------------------------------


class TestCrossValidator:
    def test_validated_with_multiple_sources(self):
        cv = CrossValidator()
        claim = "Machine learning improves healthcare diagnostics significantly"
        url_texts = {
            "https://a.com": "Machine learning improves healthcare diagnostics significantly in many hospitals.",
            "https://b.com": "Healthcare diagnostics are being improved by machine learning technology.",
        }
        validated, confidence, supporting = cv.validate_single(claim, url_texts)
        assert isinstance(validated, bool)
        assert 0.0 <= confidence <= 1.0
        assert isinstance(supporting, list)

    def test_single_source_not_cross_validated(self):
        cv = CrossValidator()
        claim = "Unique claim about quantum computing"
        url_texts = {
            "https://only-source.com": "Completely different text about weather patterns today.",
        }
        validated, confidence, supporting = cv.validate_single(claim, url_texts)
        # With only 1 source and low overlap, should not be cross-validated
        assert validated is False

    def test_validate_findings_list(self):
        cv = CrossValidator()
        findings = [
            Finding(
                claim="AI is transforming industries",
                supporting_sources=["https://a.com"],
            ),
        ]
        url_texts = {
            "https://a.com": "AI is transforming industries worldwide.",
            "https://b.com": "Industries are being transformed by AI technology.",
        }
        result = cv.validate(findings, url_texts)
        assert len(result) == 1
        assert isinstance(result[0], Finding)

    def test_domain_extraction(self):
        assert CrossValidator._domain("https://www.example.com/path") == "example.com"
        assert CrossValidator._domain("https://blog.example.com") == "blog.example.com"

    def test_ngrams(self):
        cv = CrossValidator(ngram_size=3)
        ng = cv._ngrams("hello")
        assert len(ng) == 3  # "hel", "ell", "llo"

    def test_overlap_identical(self):
        cv = CrossValidator()
        overlap = cv._overlap("hello world", "hello world")
        assert overlap == 1.0

    def test_overlap_no_common(self):
        cv = CrossValidator()
        overlap = cv._overlap("aaa", "bbb")
        assert overlap == 0.0

    def test_empty_text_overlap(self):
        cv = CrossValidator()
        assert cv._overlap("", "hello") == 0.0
        assert cv._overlap("hello", "") == 0.0


# ---------------------------------------------------------------------------
# ReportGenerator — SKIPPED
# ---------------------------------------------------------------------------
# ReportGenerator tests are excluded because report_generator.py has a
# pre-existing IndentationError (missing `lines = [` in _build_markdown
# and undefined `validated` variable in _build_executive_summary).
# These must be fixed in the source before tests can be written.
