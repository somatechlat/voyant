"""
Tests for Advanced Analytics Modules.

This module contains comprehensive unit and integration tests for Voyant's
advanced analytics functionalities, including:
- Anomaly Detection (using Z-score, IQR, MAD methods)
- Time Series Forecasting (linear, EMA, confidence intervals)
- Data Segmentation (profiling, comparison, drift detection)
- Text Embeddings (TF-IDF, cosine similarity, dimensionality reduction)

These tests ensure the correctness and reliability of the analytical core components.
Reference: docs/CANONICAL_ROADMAP.md - P6 Advanced Analytics
"""

from typing import Any, Dict, List

import pytest

# Anomaly Detection
from apps.core.lib.anomaly import (
    detect_anomalies,
)
from apps.core.lib.anomaly import (
    get_available_methods as get_anomaly_methods,
)

# Embeddings
from apps.core.lib.embeddings import (
    cosine_similarity,
    embed_texts,
    find_similar,
    get_available_models,
    reduce_dimensions,
)

# Forecasting
from apps.core.lib.forecasting import (
    detect_trend,
    forecast,
)

# Segmentation
from apps.core.lib.segmentation import (
    compare_segments,
    detect_segment_drift,
    profile_segments,
)

# =============================================================================
# Anomaly Detection Tests
# =============================================================================


class TestAnomalyDetection:
    """
    Tests for the anomaly detection functionalities within the analytics module.

    These tests verify that various anomaly detection methods (Z-score, IQR, MAD)
    correctly identify outliers in datasets and handle cases with no anomalies.
    """

    def test_detect_outlier_zscore(self):
        """
        Verifies that the Z-score method correctly detects a single outlier in a dataset.
        """
        values = [10, 12, 11, 13, 12, 100, 11, 12]  # 100 is the clear outlier.
        result = detect_anomalies(values, method="zscore", threshold=2.0)

        assert result.anomaly_count == 1
        assert result.anomalies[0].value == 100

    def test_detect_outlier_iqr(self):
        """
        Verifies that the IQR (Interquartile Range) method correctly detects outliers.
        """
        values = [10, 12, 11, 13, 12, 100, 11, 12]
        result = detect_anomalies(values, method="iqr", threshold=1.5)

        assert result.anomaly_count >= 1
        assert any(a.value == 100 for a in result.anomalies)

    def test_detect_outlier_mad(self):
        """
        Verifies that the MAD (Median Absolute Deviation) method correctly detects outliers.
        This method is generally more robust to extreme outliers than Z-score or IQR.
        """
        values = [10, 12, 11, 13, 12, 100, 11, 12]
        result = detect_anomalies(values, method="mad")

        assert result.anomaly_count == 1
        assert result.anomalies[0].value == 100

    def test_no_outliers(self):
        """
        Ensures that `detect_anomalies` returns no anomalies when the dataset is clean.
        """
        values = [10, 11, 10, 11, 10, 11, 10, 11]
        result = detect_anomalies(values, method="mad")

        assert result.anomaly_count == 0

    def test_available_methods(self):
        """
        Checks that `get_anomaly_methods` returns a list of all supported anomaly detection techniques.
        """
        methods = get_anomaly_methods()
        assert "zscore" in methods
        assert "iqr" in methods
        assert "mad" in methods


# =============================================================================
# Forecasting Tests
# =============================================================================


class TestForecasting:
    """
    Tests for the time series forecasting functionalities.

    These tests cover various forecasting methods and ensure that predictions
    are reasonable, include confidence intervals, and trend detection works correctly.
    """

    def test_linear_trend_forecast(self):
        """
        Verifies that the linear trend forecasting method produces accurate predictions.
        """
        values = [10, 11, 12, 13, 14]
        result = forecast(values, periods=3, method="linear")

        assert result.method == "linear"
        assert len(result.predictions) == 3
        # Should predict values around 15, 16, 17 with some tolerance.
        assert result.predictions[0].value == pytest.approx(15, rel=0.1)
        assert result.predictions[1].value == pytest.approx(16, rel=0.1)

    def test_ema_forecast(self):
        """
        Verifies that the Exponential Moving Average (EMA) forecasting method works.
        """
        values = [10, 12, 14, 13, 15]
        result = forecast(values, periods=5, method="ema")

        assert result.method == "ema"
        assert len(result.predictions) == 5

    def test_confidence_intervals(self):
        """
        Ensures that forecasting results include confidence intervals and they are
        correctly bounded around the prediction.
        """
        values = [10, 11, 12, 13, 14]
        result = forecast(values, periods=3, method="linear")

        for pred in result.predictions:
            assert pred.lower_bound < pred.value
            assert pred.upper_bound > pred.value

    def test_detect_trend_increasing(self):
        """
        Verifies that the trend detection accurately identifies an increasing trend.
        """
        values = [10, 12, 14, 16, 18]
        trend = detect_trend(values)

        assert trend["direction"] == "up"
        assert trend["slope"] > 0

    def test_detect_trend_decreasing(self):
        """
        Verifies that the trend detection accurately identifies a decreasing trend.
        """
        values = [20, 18, 16, 14, 12]
        trend = detect_trend(values)

        assert trend["direction"] == "down"
        assert trend["slope"] < 0


# =============================================================================
# Segmentation Tests
# =============================================================================


class TestSegmentation:
    """
    Tests for data segmentation functionalities.

    These tests ensure that segment profiling, comparison, and drift detection
    work as expected on sample datasets.
    """

    @pytest.fixture
    def sample_data(self) -> List[Dict[str, Any]]:
        """Provides sample data for segmentation tests."""
        return [
            {"region": "US", "sales": 100, "quantity": 10},
            {"region": "US", "sales": 120, "quantity": 12},
            {"region": "EU", "sales": 80, "quantity": 8},
            {"region": "EU", "sales": 90, "quantity": 9},
            {"region": "APAC", "sales": 150, "quantity": 15},
        ]

    def test_profile_by_region(self, sample_data: List[Dict[str, Any]]):
        """
        Verifies that `profile_segments` correctly profiles data based on a specified column.
        """
        result = profile_segments(sample_data, "region")

        assert result.segment_column == "region"
        assert result.total_rows == 5
        assert len(result.segments) == 3  # US, EU, APAC

    def test_segment_stats(self, sample_data: List[Dict[str, Any]]):
        """
        Ensures that per-segment statistics are calculated correctly.
        """
        result = profile_segments(sample_data, "region")

        us_segment = next(s for s in result.segments if s.segment_value == "US")
        assert us_segment.row_count == 2
        assert "sales" in us_segment.numeric_stats
        assert us_segment.numeric_stats["sales"]["mean"] == 110

    def test_compare_segments(self, sample_data: List[Dict[str, Any]]):
        """
        Verifies that `compare_segments` can accurately compare two distinct segments.
        """
        comparison = compare_segments(sample_data, "region", "US", "EU")

        assert comparison.segment_a == "US"
        assert comparison.segment_b == "EU"
        assert "sales" in comparison.numeric_differences

    def test_segment_drift_detection(self, sample_data: List[Dict[str, Any]]):
        """
        Tests the detection of drift in segment proportions between two datasets.
        """
        old_data = sample_data
        new_data = [
            {"region": "US", "sales": 100},
            {"region": "US", "sales": 100},
            {"region": "US", "sales": 100},
            {"region": "EU", "sales": 80},
        ]

        drift = detect_segment_drift(old_data, new_data, "region")
        assert "drifts" in drift


# =============================================================================
# Embedding Tests
# =============================================================================


class TestEmbeddings:
    """
    Tests for text embedding extraction and similarity calculations.

    These tests ensure that text embedding models (e.g., TF-IDF) work,
    similarity metrics (cosine) are correct, and dimensionality reduction functions operate as expected.
    """

    def test_embed_texts_tfidf(self):
        """
        Verifies that TF-IDF embedding correctly processes texts and produces embeddings of the specified dimensions.
        """
        texts = ["hello world", "goodbye world", "hello again"]
        result = embed_texts(texts, model="tfidf", dimensions=32)

        assert result.count == 3
        assert result.dimensions == 32
        assert len(result.embeddings) == 3
        assert len(result.embeddings[0]) == 32

    def test_cosine_similarity(self):
        """
        Tests the cosine similarity calculation for identical and orthogonal vectors.
        """
        a = [1, 0, 0]
        b = [1, 0, 0]
        sim = cosine_similarity(a, b)
        assert sim == pytest.approx(
            1.0
        )  # Identical vectors should have a similarity of 1.0.

        c = [0, 1, 0]
        sim2 = cosine_similarity(a, c)
        assert sim2 == pytest.approx(
            0.0
        )  # Orthogonal vectors should have a similarity of 0.0.

    def test_similar_texts_have_higher_similarity(self):
        """
        Ensures that semantically similar texts result in higher cosine similarity scores
        after embedding.
        """
        texts = ["the quick brown fox", "the fast brown fox", "pizza delivery"]
        result = embed_texts(texts, model="tfidf", dimensions=64)

        sim_01 = cosine_similarity(result.embeddings[0], result.embeddings[1])
        sim_02 = cosine_similarity(result.embeddings[0], result.embeddings[2])

        assert (
            sim_01 > sim_02
        )  # Expect "quick brown fox" to be more similar to "fast brown fox" than "pizza delivery".

    def test_find_similar(self):
        """
        Tests the functionality to find embeddings most similar to a query embedding.
        """
        texts = ["apple fruit", "banana fruit", "car vehicle", "truck vehicle"]
        result = embed_texts(texts, model="tfidf", dimensions=32)

        # Query with the embedding of the first text ("apple fruit").
        similar = find_similar(result.embeddings[0], result.embeddings, top_k=2)

        assert len(similar) == 2
        assert similar[0][0] == 0  # The text itself should be the most similar.
        assert similar[0][1] == pytest.approx(1.0, rel=0.01)

    def test_reduce_dimensions(self):
        """
        Verifies that dimensionality reduction for embeddings works correctly.
        """
        embeddings = [
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.3, 0.4, 0.5],
            [0.3, 0.4, 0.5, 0.6],
        ]
        reduced = reduce_dimensions(embeddings, target_dims=2)

        assert len(reduced) == 3
        assert len(reduced[0]) == 2

    def test_available_models(self):
        """
        Checks that `get_available_models` returns a list of supported embedding models.
        """
        models = get_available_models()
        assert "simple" in models
        assert "tfidf" in models
