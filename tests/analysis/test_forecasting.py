"""
Tests for Time Series Forecasting Service.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from voyant.services.analysis.forecasting import TimeForecaster, SKLEARN_AVAILABLE

@pytest.fixture
def forecaster():
    return TimeForecaster()

@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_linear_trend_forecast(forecaster):
    """Test forecasting a simple perfect linear trend."""
    # Create 100 days of data: y = 2x
    dates = pd.date_range(start="2023-01-01", periods=100, freq="D")
    values = [i * 2 for i in range(100)]
    
    df = pd.DataFrame({"date": dates, "value": values})
    
    # Forecast next 10 days
    result = forecaster.analyze(df, {"horizon": 10})
    
    assert result["status"] == "success"
    assert len(result["forecast"]) == 10
    
    # Check predictions roughly follow trend
    # Last value was 198, next should be 200, 202...
    forecast_values = [r["forecast"] for r in result["forecast"]]
    first_pred = forecast_values[0]
    last_pred = forecast_values[-1]
    
    # Allow small floating point variance, but logic is deterministic
    assert 199 < first_pred < 201
    assert 217 < last_pred < 219

@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
def test_missing_values_handling(forecaster):
    """Test resilience to missing dates/values."""
    dates = pd.date_range(start="2023-01-01", periods=20, freq="D")
    values = np.arange(20.0)
    
    df = pd.DataFrame({"date": dates, "value": values})
    # Remove some rows to create gaps
    df = df.drop([5, 6, 7]) 
    
    result = forecaster.analyze(df, {"horizon": 5})
    assert result["status"] == "success"
    # Should automatically resample and fill, producing a forecast
    assert len(result["forecast"]) == 5

def test_empty_data(forecaster):
    result = forecaster.analyze([], {})
    assert result["status"] == "skipped"
    assert result["reason"] == "empty_data"

def test_unsupported_data_type(forecaster):
    with pytest.raises(Exception): # AnalysisError
        forecaster.analyze("string_data", {})
