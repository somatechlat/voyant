"""Tests for apps.analysis.lib.nlp_primitives."""

import pytest

from apps.analysis.lib.nlp_primitives import NLPPrimitives, NLTK_AVAILABLE

# Check if VADER data is actually available (not just NLTK installed)
_VADER_AVAILABLE = False
if NLTK_AVAILABLE:
    try:
        import nltk
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
            _VADER_AVAILABLE = True
        except LookupError:
            # Try downloading
            nltk.download("vader_lexicon", quiet=True)
            # Verify download succeeded
            nltk.data.find("sentiment/vader_lexicon.zip")
            _VADER_AVAILABLE = True
    except Exception:
        pass

_skip_no_vader = pytest.mark.skipif(
    not _VADER_AVAILABLE, reason="NLTK VADER lexicon not available"
)


@pytest.fixture
def nlp():
    return NLPPrimitives()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestNLPPrimitivesInit:
    def test_sia_initially_none(self, nlp):
        assert nlp._sia is None


# ---------------------------------------------------------------------------
# analyze_sentiment
# ---------------------------------------------------------------------------


class TestAnalyzeSentiment:
    @_skip_no_vader
    def test_positive_sentiment(self, nlp):
        results = nlp.analyze_sentiment(["I love this product, it's amazing!"])
        assert len(results) == 1
        assert results[0]["sentiment"] == "positive"
        assert results[0]["compound"] > 0

    @_skip_no_vader
    def test_negative_sentiment(self, nlp):
        results = nlp.analyze_sentiment(["This is terrible and awful."])
        assert len(results) == 1
        assert results[0]["sentiment"] == "negative"
        assert results[0]["compound"] < 0

    @_skip_no_vader
    def test_neutral_sentiment(self, nlp):
        results = nlp.analyze_sentiment(["The book is on the table."])
        assert len(results) == 1
        assert results[0]["sentiment"] == "neutral"

    @_skip_no_vader
    def test_multiple_texts(self, nlp):
        texts = [
            "I love this!",
            "This is horrible.",
            "It is a table.",
        ]
        results = nlp.analyze_sentiment(texts)
        assert len(results) == 3
        sentiments = [r["sentiment"] for r in results]
        assert "positive" in sentiments
        assert "negative" in sentiments

    @_skip_no_vader
    def test_result_structure(self, nlp):
        results = nlp.analyze_sentiment(["Great day!"])
        r = results[0]
        assert "text_snippet" in r
        assert "scores" in r
        assert "compound" in r
        assert "sentiment" in r
        assert "neg" in r["scores"]
        assert "neu" in r["scores"]
        assert "pos" in r["scores"]

    @_skip_no_vader
    def test_long_text_truncated_snippet(self, nlp):
        long_text = "This is a wonderful experience. " * 10
        results = nlp.analyze_sentiment([long_text])
        assert len(results[0]["text_snippet"]) <= 53  # 50 + "..."

    @_skip_no_vader
    def test_sia_lazy_initialized(self, nlp):
        assert nlp._sia is None
        nlp.analyze_sentiment(["test"])
        assert nlp._sia is not None

    @_skip_no_vader
    def test_empty_list(self, nlp):
        results = nlp.analyze_sentiment([])
        assert results == []

    @_skip_no_vader
    def test_compound_range(self, nlp):
        results = nlp.analyze_sentiment(["Absolutely fantastic!", "Completely dreadful!"])
        for r in results:
            assert -1.0 <= r["compound"] <= 1.0
