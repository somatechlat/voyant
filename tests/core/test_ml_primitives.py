"""
Tests for MLPrimitives Core Component.
Verifies real scikit-learn integration without mocking internal logic.
"""
import pytest
import pandas as pd
import numpy as np
from voyant.core.ml_primitives import MLPrimitives, SKLEARN_AVAILABLE
from voyant.core.errors import AnalysisError

@pytest.fixture
def ml():
    return MLPrimitives()

@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
class TestMLPrimitives:
    
    def test_detect_anomalies_basics(self, ml):
        """Test basic anomaly detection with clear outliers."""
        # 20 points around 10, 2 points around 1000
        normal = [{"val": 10 + np.random.normal()} for _ in range(20)]
        outliers = [{"val": 1000}, {"val": 1001}]
        data = normal + outliers
        
        result = ml.detect_anomalies(data, contamination=0.1)
        
        assert result["total_records"] == 22
        assert result["anomaly_count"] > 0
        # The outliers should be in the anomalies list
        anomalies = result["anomalies"]
        # Check values
        outlier_vals = [r["val"] for r in anomalies]
        assert 1000 in outlier_vals or 1001 in outlier_vals

    def test_detect_anomalies_empty(self, ml):
        """Test error handling for empty data."""
        with pytest.raises(AnalysisError, match="No data provided"):
            ml.detect_anomalies([])

    def test_detect_anomalies_no_numeric(self, ml):
        """Test error handling for non-numeric data."""
        data = [{"col": "a"}, {"col": "b"}]
        with pytest.raises(AnalysisError, match="No numeric data"):
            ml.detect_anomalies(data)

    def test_cluster_kmeans(self, ml):
        """Test K-Means clustering."""
        # Two distinct blobs
        blob1 = [{"x": 0, "y": 0}, {"x": 1, "y": 1}, {"x": 0, "y": 1}]
        blob2 = [{"x": 10, "y": 10}, {"x": 11, "y": 11}, {"x": 10, "y": 11}]
        data = blob1 + blob2
        
        result = ml.cluster_kmeans(data, n_clusters=2)
        
        assert len(result["clusters"]) == 6
        assert len(result["centroids"]) == 2
        assert result["silhouette_score"] > 0.5 # Should be well separated

    def test_train_regression(self, ml):
        """Test Linear Regression training."""
        # y = 2x + 1
        data = [{"x": i, "y": 2*i + 1} for i in range(10)]
        
        result = ml.train_regression(data, target_col="y", feature_cols=["x"])
        
        assert result["model_type"] == "linear_regression"
        assert result["r2_score"] > 0.99 # Should be perfect
        assert abs(result["coefficients"][0] - 2.0) < 0.001
        assert abs(result["intercept"] - 1.0) < 0.001

    def test_train_classifier(self, ml):
        """Test RandoForest Classifier."""
        # Simple separation x > 5 -> 1 else 0
        data = [{"x": i, "target": 1 if i > 5 else 0} for i in range(10)]
        
        result = ml.train_classifier(data, target_col="target", feature_cols=["x"])
        
        assert result["model_type"] == "RandomForestClassifier"
        # Since it's a small dataset and RF can overfit/fit perfectly
        assert result["accuracy"] >= 0.8
        assert "x" in result["feature_importance"]
