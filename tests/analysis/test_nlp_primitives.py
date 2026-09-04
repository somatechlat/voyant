"""Tests for apps.analysis.lib.nlp_primitives."""

import pytest

from apps.analysis.lib.nlp_primitives import NLPPrimitives, NLTK_AVAILABLE


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
    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not installed")
    def test_positive_sentiment(self, nlp):
        results = nlp.analyze_sentiment(["I love this product, it's amazing!"])
        assert len(results) == 1
        assert results[0]["sentiment"] == "positive"
        assert results[0]["compound"] > 0

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not installed")
    def test_negative_sentiment(self, nlp):
        results = nlp.analyze_sentiment(["This is terrible and awful."])
        assert len(results) == 1
        assert results[0]["sentiment"] == "negative"
        assert results[0]["compound"] < 0

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not installed")
    def test_neutral_sentiment(self, nlp):
        results = nlp.analyze_sentiment(["The book is on the table."])
        assert len(results) == 1
        assert results[0]["sentiment"] == "neutral"

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not installed")
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

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not installed")
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

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not installed")
    def test_long_text_truncated_snippet(self, nlp):
        long_text = "This is a wonderful experience. " * 10
        results = nlp.analyze_sentiment([long_text])
        assert len(results[0]["text_snippet"]) <= 53  # 50 + "..."

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not installed")
    def test_sia_lazy_initialized(self, nlp):
        assert nlp._sia is None
        nlp.analyze_sentiment(["test"])
        assert nlp._sia is not None

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not installed")
    def test_empty_list(self, nlp):
        results = nlp.analyze_sentiment([])
        assert results == []

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK not installed")
    def test_compound_range(self, nlp):
        results = nlp.analyze_sentiment(["Absolutely fantastic!", "Completely dreadful!"])
        for r in results:
            assert -1.0 <= r["compound"] <= 1.0
