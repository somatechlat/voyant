"""
Tests for Advanced Analytics Modules

Tests for anomaly detection, forecasting, segmentation, and embeddings.
Reference: docs/CANONICAL_ROADMAP.md - P6 Advanced Analytics
"""
import pytest
import math

# Anomaly Detection
from voyant.core.anomaly import (
    detect_anomalies,
    ZScoreDetector,
    IQRDetector,
    MADDetector,
    get_available_methods as get_anomaly_methods,
)

# Forecasting
from voyant.core.forecasting import (
    forecast,
    NaiveForecaster,
    MovingAverageForecaster,
    ExponentialSmoothingForecaster,
    LinearTrendForecaster,
    detect_trend,
    get_available_methods as get_forecast_methods,
)

# Segmentation
from voyant.core.segmentation import (
    profile_segments,
    compare_segments,
    detect_segment_drift,
    SegmentProfiler,
)

# Embeddings
from voyant.core.embeddings import (
    embed_texts,
    cosine_similarity,
    euclidean_distance,
    calculate_similarity,
    find_similar,
    reduce_dimensions,
    get_available_models,
)


# =============================================================================
# Anomaly Detection Tests
# =============================================================================

class TestAnomalyDetection:
    """Test anomaly detection."""

    def test_detect_outlier_zscore(self):
        """Should detect outliers with z-score."""
        values = [10, 12, 11, 13, 12, 100, 11, 12]  # 100 is outlier
        result = detect_anomalies(values, method="zscore", threshold=2.0)
        
        assert result.anomaly_count == 1
        assert result.anomalies[0].value == 100

    def test_detect_outlier_iqr(self):
        """Should detect outliers with IQR."""
        values = [10, 12, 11, 13, 12, 100, 11, 12]
        result = detect_anomalies(values, method="iqr", threshold=1.5)
        
        assert result.anomaly_count >= 1
        assert any(a.value == 100 for a in result.anomalies)

    def test_detect_outlier_mad(self):
        """Should detect outliers with MAD (most robust)."""
        values = [10, 12, 11, 13, 12, 100, 11, 12]
        result = detect_anomalies(values, method="mad")
        
        assert result.anomaly_count == 1
        assert result.anomalies[0].value == 100

    def test_no_outliers(self):
        """Should return empty when no outliers."""
        values = [10, 11, 10, 11, 10, 11, 10, 11]
        result = detect_anomalies(values, method="mad")
        
        assert result.anomaly_count == 0

    def test_available_methods(self):
        """Should list available methods."""
        methods = get_anomaly_methods()
        assert "zscore" in methods
        assert "iqr" in methods
        assert "mad" in methods


# =============================================================================
# Forecasting Tests
# =============================================================================

class TestForecasting:
    """Test time series forecasting."""

    def test_linear_trend_forecast(self):
        """Should forecast linear trend."""
        values = [10, 11, 12, 13, 14]
        result = forecast(values, periods=3, method="linear")
        
        assert result.method == "linear"
        assert len(result.predictions) == 3
        # Should predict ~15, 16, 17
        assert result.predictions[0].value == pytest.approx(15, rel=0.1)
        assert result.predictions[1].value == pytest.approx(16, rel=0.1)

    def test_ema_forecast(self):
        """Should forecast with EMA."""
        values = [10, 12, 14, 13, 15]
        result = forecast(values, periods=5, method="ema")
        
        assert result.method == "ema"
        assert len(result.predictions) == 5

    def test_confidence_intervals(self):
        """Should include confidence intervals."""
        values = [10, 11, 12, 13, 14]
        result = forecast(values, periods=3, method="linear")
        
        for pred in result.predictions:
            assert pred.lower_bound < pred.value
            assert pred.upper_bound > pred.value

    def test_detect_trend_increasing(self):
        """Should detect increasing trend."""
        values = [10, 12, 14, 16, 18]
        trend = detect_trend(values)
        
        assert trend["direction"] == "up"
        assert trend["slope"] > 0

    def test_detect_trend_decreasing(self):
        """Should detect decreasing trend."""
        values = [20, 18, 16, 14, 12]
        trend = detect_trend(values)
        
        assert trend["direction"] == "down"
        assert trend["slope"] < 0


# =============================================================================
# Segmentation Tests
# =============================================================================

class TestSegmentation:
    """Test segment profiling."""

    @pytest.fixture
    def sample_data(self):
        return [
            {"region": "US", "sales": 100, "quantity": 10},
            {"region": "US", "sales": 120, "quantity": 12},
            {"region": "EU", "sales": 80, "quantity": 8},
            {"region": "EU", "sales": 90, "quantity": 9},
            {"region": "APAC", "sales": 150, "quantity": 15},
        ]

    def test_profile_by_region(self, sample_data):
        """Should profile data by region."""
        result = profile_segments(sample_data, "region")
        
        assert result.segment_column == "region"
        assert result.total_rows == 5
        assert len(result.segments) == 3

    def test_segment_stats(self, sample_data):
        """Should calculate per-segment stats."""
        result = profile_segments(sample_data, "region")
        
        us_segment = next(s for s in result.segments if s.segment_value == "US")
        assert us_segment.row_count == 2
        assert "sales" in us_segment.numeric_stats
        assert us_segment.numeric_stats["sales"]["mean"] == 110

    def test_compare_segments(self, sample_data):
        """Should compare two segments."""
        comparison = compare_segments(sample_data, "region", "US", "EU")
        
        assert comparison.segment_a == "US"
        assert comparison.segment_b == "EU"
        assert "sales" in comparison.numeric_differences

    def test_segment_drift_detection(self, sample_data):
        """Should detect drift in segment proportions."""
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
    """Test embedding extraction."""

    def test_embed_texts_tfidf(self):
        """Should embed texts with TF-IDF."""
        texts = ["hello world", "goodbye world", "hello again"]
        result = embed_texts(texts, model="tfidf", dimensions=32)
        
        assert result.count == 3
        assert result.dimensions == 32
        assert len(result.embeddings) == 3
        assert len(result.embeddings[0]) == 32

    def test_cosine_similarity(self):
        """Should calculate cosine similarity."""
        a = [1, 0, 0]
        b = [1, 0, 0]
        sim = cosine_similarity(a, b)
        assert sim == pytest.approx(1.0)  # Identical vectors
        
        c = [0, 1, 0]
        sim2 = cosine_similarity(a, c)
        assert sim2 == pytest.approx(0.0)  # Orthogonal

    def test_similar_texts_have_higher_similarity(self):
        """Similar texts should have higher similarity."""
        texts = ["the quick brown fox", "the fast brown fox", "pizza delivery"]
        result = embed_texts(texts, model="tfidf", dimensions=64)
        
        sim_01 = cosine_similarity(result.embeddings[0], result.embeddings[1])
        sim_02 = cosine_similarity(result.embeddings[0], result.embeddings[2])
        
        assert sim_01 > sim_02  # "quick brown fox" more similar to "fast brown fox"

    def test_find_similar(self):
        """Should find similar embeddings."""
        texts = ["apple fruit", "banana fruit", "car vehicle", "truck vehicle"]
        result = embed_texts(texts, model="tfidf", dimensions=32)
        
        # Query with first embedding (apple)
        similar = find_similar(result.embeddings[0], result.embeddings, top_k=2)
        
        assert len(similar) == 2
        assert similar[0][0] == 0  # Self is most similar
        assert similar[0][1] == pytest.approx(1.0, rel=0.01)

    def test_reduce_dimensions(self):
        """Should reduce embedding dimensions."""
        embeddings = [
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.3, 0.4, 0.5],
            [0.3, 0.4, 0.5, 0.6],
        ]
        reduced = reduce_dimensions(embeddings, target_dims=2)
        
        assert len(reduced) == 3
        assert len(reduced[0]) == 2

    def test_available_models(self):
        """Should list available models."""
        models = get_available_models()
        assert "simple" in models
        assert "tfidf" in models
