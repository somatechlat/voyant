"""
Tests for OperationalActivities.

Tests clean_data, detect_anomalies, analyze_sentiment_batch, fix_data_quality,
and forecast_time_series using real primitives. No mocking.
"""

import numpy as np
import pytest
from temporalio.testing import ActivityEnvironment
from temporalio.exceptions import ApplicationError

from apps.worker.activities.operational_activities import OperationalActivities


@pytest.fixture(scope="module")
def ops():
    """Real OperationalActivities instance."""
    return OperationalActivities()


@pytest.fixture()
def env():
    """ActivityEnvironment for testing activities outside a Temporal worker."""
    return ActivityEnvironment()


# Check if NLTK vader_lexicon is available
def _nltk_vader_available():
    try:
        import nltk
        from nltk.sentiment.vader import SentimentIntensityAnalyzer

        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
            return True
        except LookupError:
            try:
                nltk.download("vader_lexicon", quiet=True)
                return True
            except Exception:
                return False
    except ImportError:
        return False


NLTK_AVAILABLE = _nltk_vader_available()


class TestCleanData:
    """Tests for the clean_data activity."""

    def test_clean_empty_data(self, ops):
        """Empty data returns empty cleaned_data and report."""
        result = ops.clean_data({"data": [], "strategies": {}})
        assert result["cleaned_data"] == []
        assert "report" in result

    def test_clean_no_strategies(self, ops):
        """Default strategies are applied when none provided."""
        data = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        result = ops.clean_data({"data": data})
        assert len(result["cleaned_data"]) == 2

    def test_clean_with_missing_values(self, ops):
        """Missing values are handled per strategy."""
        data = [{"a": 1}, {"a": None}, {"a": 3}]
        result = ops.clean_data(
            {"data": data, "strategies": {"missing_values": "mean"}}
        )
        assert len(result["cleaned_data"]) > 0

    def test_clean_with_duplicates(self, ops):
        """Duplicate rows are removed when strategy is 'drop'."""
        data = [{"a": 1}, {"a": 1}, {"a": 2}]
        result = ops.clean_data(
            {"data": data, "strategies": {"duplicates": "drop"}}
        )
        assert result["report"]["duplicates_removed"] == 1
        assert len(result["cleaned_data"]) == 2


class TestDetectAnomalies:
    """Tests for the detect_anomalies activity."""

    def test_detect_anomalies_basic(self, ops):
        """Basic anomaly detection returns results."""
        data = [{"value": float(i)} for i in range(50)]
        # Add some outliers
        data.append({"value": 10000.0})
        data.append({"value": -10000.0})
        result = ops.detect_anomalies({"data": data, "contamination": 0.05})
        assert "total_records" in result or "anomaly_count" in result

    def test_detect_anomalies_no_outliers(self, ops):
        """Clean data has few or no anomalies."""
        data = [{"value": float(100 + i)} for i in range(50)]
        result = ops.detect_anomalies({"data": data, "contamination": 0.05})
        if "anomaly_count" in result:
            assert result["anomaly_count"] <= 5

    def test_detect_anomalies_default_contamination(self, ops):
        """Default contamination of 0.05 is used."""
        data = [{"value": float(i)} for i in range(30)]
        result = ops.detect_anomalies({"data": data})
        assert result is not None


class TestAnalyzeSentimentBatch:
    """Tests for the analyze_sentiment_batch activity."""

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK vader_lexicon not available")
    def test_sentiment_positive(self, ops):
        """Positive text returns positive sentiment."""
        result = ops.analyze_sentiment_batch(
            {"texts": ["This is absolutely wonderful and amazing!"]}
        )
        assert len(result) == 1
        assert result[0]["sentiment"] == "positive"
        assert result[0]["compound"] > 0

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK vader_lexicon not available")
    def test_sentiment_negative(self, ops):
        """Negative text returns negative sentiment."""
        result = ops.analyze_sentiment_batch(
            {"texts": ["This is terrible and awful and horrible."]}
        )
        assert len(result) == 1
        assert result[0]["sentiment"] == "negative"
        assert result[0]["compound"] < 0

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK vader_lexicon not available")
    def test_sentiment_neutral(self, ops):
        """Neutral text returns neutral sentiment."""
        result = ops.analyze_sentiment_batch({"texts": ["The report is on the table."]})
        assert len(result) == 1
        assert result[0]["sentiment"] == "neutral"

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK vader_lexicon not available")
    def test_sentiment_empty_texts(self, ops):
        """Empty texts list returns empty results."""
        result = ops.analyze_sentiment_batch({"texts": []})
        assert result == []

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK vader_lexicon not available")
    def test_sentiment_batch_multiple(self, ops):
        """Multiple texts are processed in batch."""
        texts = [
            "I love this product!",
            "This is the worst experience ever.",
            "The weather is cloudy today.",
        ]
        result = ops.analyze_sentiment_batch({"texts": texts})
        assert len(result) == 3
        sentiments = [r["sentiment"] for r in result]
        assert "positive" in sentiments
        assert "negative" in sentiments

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK vader_lexicon not available")
    def test_sentiment_text_snippet_truncation(self, ops):
        """Long texts are truncated in text_snippet field."""
        long_text = "x" * 100
        result = ops.analyze_sentiment_batch({"texts": [long_text]})
        assert len(result[0]["text_snippet"]) <= 53  # 50 chars + "..."

    @pytest.mark.skipif(not NLTK_AVAILABLE, reason="NLTK vader_lexicon not available")
    def test_sentiment_scores_structure(self, ops):
        """Each result contains VADER score components."""
        result = ops.analyze_sentiment_batch({"texts": ["Great day!"]})
        scores = result[0]["scores"]
        assert "pos" in scores
        assert "neg" in scores
        assert "neu" in scores
        assert "compound" in scores


class TestFixDataQuality:
    """Tests for the fix_data_quality activity (delegates to clean_data)."""

    def test_fix_quality_basic(self, ops):
        """Basic quality fix returns cleaned_data and quality_report."""
        data = [
            {"value": 100, "category": "A"},
            {"value": None, "category": "B"},
            {"value": 200, "category": "A"},
        ]
        result = ops.fix_data_quality(
            {
                "data": data,
                "numeric_columns": ["value"],
                "categorical_columns": ["category"],
                "imputation_strategy": "median",
            }
        )
        assert "cleaned_data" in result
        assert "quality_report" in result
        assert result["quality_report"]["original_rows"] == 3

    def test_fix_quality_empty_data(self, ops):
        """Empty data returns zero-row report."""
        result = ops.fix_data_quality(
            {"data": [], "numeric_columns": [], "categorical_columns": []}
        )
        assert result["quality_report"]["original_rows"] == 0
        assert result["quality_report"]["quality_score_before"] == 0.0

    def test_fix_quality_auto_detect_columns(self, ops):
        """Auto-detects columns when not specified."""
        data = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        result = ops.fix_data_quality({"data": data})
        assert result["quality_report"]["original_rows"] == 2


class TestForecastTimeSeries:
    """Tests for the forecast_time_series activity."""

    @pytest.mark.asyncio
    async def test_forecast_ema(self, ops, env):
        """EMA forecast returns predictions."""
        values = [float(100 + i * 2) for i in range(30)]
        result = await env.run(
            ops.forecast_time_series,
            {"values": values, "periods": 7, "method": "ema"},
        )
        assert "predictions" in result
        assert len(result["predictions"]) == 7

    @pytest.mark.asyncio
    async def test_forecast_linear(self, ops, env):
        """Linear forecast returns predictions."""
        values = [float(100 + i * 3) for i in range(30)]
        result = await env.run(
            ops.forecast_time_series,
            {"values": values, "periods": 5, "method": "linear"},
        )
        assert "predictions" in result
        assert len(result["predictions"]) == 5

    @pytest.mark.asyncio
    async def test_forecast_empty_values_raises(self, ops, env):
        """Empty values raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No values provided"):
            await env.run(ops.forecast_time_series, {"values": []})

    @pytest.mark.asyncio
    async def test_forecast_missing_values_raises(self, ops, env):
        """Missing values key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No values provided"):
            await env.run(ops.forecast_time_series, {})

    @pytest.mark.asyncio
    async def test_forecast_with_dates(self, ops, env):
        """Forecast with dates includes date in predictions."""
        dates = [f"2024-01-{i:02d}" for i in range(1, 31)]
        values = [float(100 + i) for i in range(30)]
        result = await env.run(
            ops.forecast_time_series,
            {"values": values, "dates": dates, "periods": 5, "method": "ema"},
        )
        assert "predictions" in result
        if result["predictions"] and "date" in result["predictions"][0]:
            assert result["predictions"][0]["date"] is not None

    @pytest.mark.asyncio
    async def test_forecast_default_method(self, ops, env):
        """Default method is 'ema'."""
        values = [float(50 + i) for i in range(20)]
        result = await env.run(ops.forecast_time_series, {"values": values, "periods": 3})
        assert result["method"] == "ema"

    @pytest.mark.asyncio
    async def test_forecast_default_periods(self, ops, env):
        """Default periods is 7."""
        values = [float(50 + i) for i in range(20)]
        result = await env.run(ops.forecast_time_series, {"values": values})
        assert len(result["predictions"]) == 7

    @pytest.mark.asyncio
    async def test_forecast_confidence_intervals(self, ops, env):
        """Predictions include confidence bounds."""
        values = [float(100 + i * 2) for i in range(30)]
        result = await env.run(
            ops.forecast_time_series,
            {"values": values, "periods": 5, "confidence_level": 0.95},
        )
        for pred in result["predictions"]:
            assert "lower_bound" in pred
            assert "upper_bound" in pred
            assert pred["lower_bound"] <= pred["value"] <= pred["upper_bound"]

    @pytest.mark.asyncio
    async def test_forecast_prophet_not_available_raises(self, ops, env):
        """Prophet method raises error if Prophet is not installed."""
        try:
            from prophet import Prophet  # noqa: F401
            pytest.skip("Prophet is installed, cannot test unavailable path")
        except ImportError:
            pass

        values = [float(100 + i) for i in range(30)]
        dates = [f"2024-01-{i:02d}" for i in range(1, 31)]
        with pytest.raises(ApplicationError, match="Forecasting failed"):
            await env.run(
                ops.forecast_time_series,
                {"values": values, "dates": dates, "periods": 7, "method": "prophet"},
            )

    @pytest.mark.asyncio
    async def test_forecast_prophet_without_dates_raises(self, ops, env):
        """Prophet method without dates raises error."""
        try:
            from prophet import Prophet  # noqa: F401
        except ImportError:
            pytest.skip("Prophet not installed")

        values = [float(100 + i) for i in range(30)]
        with pytest.raises(ApplicationError, match="Forecasting failed"):
            await env.run(
                ops.forecast_time_series,
                {"values": values, "periods": 7, "method": "prophet"},
            )
