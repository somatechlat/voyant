"""
Tests for Anomaly Detection Service.
"""
import pytest
import pandas as pd
import numpy as np

from voyant.services.analysis.anomaly_detection import AnomalyDetector, SKLEARN_AVAILABLE
from voyant.core.errors import AnalysisError

@pytest.fixture
def detector():
    return AnomalyDetector()

@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_detects_outliers(detector):
    """Test simple outlier detection with synthetic data."""
    # 100 normal points
    normal = pd.DataFrame({
        "value": np.random.normal(100, 5, 100),
        "id": range(100)
    })
    # 5 outliers
    outliers = pd.DataFrame({
        "value": np.random.normal(200, 5, 5), # Far away
        "id": range(100, 105)
    })
    
    df = pd.concat([normal, outliers])
    
    result = detector.analyze(df, {})
    
    assert result["status"] == "success"
    assert result["anomaly_count"] >= 5 # Should catch at least the obvious ones
    
    # Check if outliers are in top anomalies
    top_ids = [r["id"] for r in result["top_anomalies"]]
    for outlying_id in range(100, 105):
        assert outlying_id in top_ids

@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_insufficient_data(detector):
    """Test handling of too few rows."""
    df = pd.DataFrame({"value": [1, 2, 3]})
    result = detector.analyze(df, {})
    assert result["status"] == "skipped"
    assert result["reason"] == "insufficient_data"

def test_empty_data(detector):
    """Test handling of empty input."""
    result = detector.analyze([], {})
    # Depending on implementation details, empty list -> empty dataframe
    assert result["status"] == "skipped"
    assert result["reason"] == "empty_data"

@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_input_conversion(detector):
    """Test input passed as list of dicts."""
    data = [{"val": 10}, {"val": 12}, {"val": 1000}, *[{"val": 10} for _ in range(20)]]
    result = detector.analyze(data, {})
    assert result["status"] == "success"
    # 1000 should be anomalous
    assert result["anomaly_count"] > 0
