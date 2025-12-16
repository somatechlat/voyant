"""
Forecasting Engine

Basic time series forecasting methods implemented natively in Python.
Supports:
- Naive forecast
- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Linear trend extrapolation
- Seasonal decomposition (extensible for Prophet)

Note: Prophet implementation is in forecast_primitives.py
"""
Usage:
    from voyant.core.forecasting import (
        forecast, Forecaster,
        MovingAverageForecaster, ExponentialSmoothingForecaster
    )
    
    # Simple forecast
    predictions = forecast(values, periods=7, method="ema")
    
    # With dates
    result = forecast(values, dates, periods=30, method="linear")
"""
from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class ForecastMethod(str, Enum):
    """Available forecasting methods."""
    NAIVE = "naive"              # Last value repeated
    SMA = "sma"                  # Simple Moving Average
    EMA = "ema"                  # Exponential Moving Average
    LINEAR = "linear"            # Linear regression trend
    HOLT = "holt"                # Holt's linear trend (not implemented yet)


@dataclass
class ForecastPoint:
    """A single forecast point."""
    period: int              # Periods ahead (1 = next)
    value: float
    lower_bound: float       # Lower confidence interval
    upper_bound: float       # Upper confidence interval
    date: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "period": self.period,
            "value": round(self.value, 4),
            "lower_bound": round(self.lower_bound, 4),
            "upper_bound": round(self.upper_bound, 4),
        }
        if self.date:
            result["date"] = self.date
        return result


@dataclass
class ForecastResult:
    """Result of a forecast."""
    predictions: List[ForecastPoint]
    method: str
    periods: int
    confidence_level: float  # e.g., 0.95 for 95%
    stats: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "method": self.method,
            "periods": self.periods,
            "confidence_level": self.confidence_level,
            "stats": {k: round(v, 4) for k, v in self.stats.items()},
            "predictions": [p.to_dict() for p in self.predictions],
        }


# =============================================================================
# Forecasters
# =============================================================================

class Forecaster(ABC):
    """Base class for forecasters."""
    
    def __init__(self, confidence_level: float = 0.95):
        self.confidence_level = confidence_level
    
    @abstractmethod
    def forecast(
        self,
        values: List[float],
        periods: int,
        dates: Optional[List[str]] = None,
    ) -> ForecastResult:
        """Generate forecast for future periods."""
        pass
    
    @property
    @abstractmethod
    def method_name(self) -> str:
        pass
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / (n - 1)
        return math.sqrt(variance)
    
    def _get_z_score(self, confidence: float = 0.95) -> float:
        """Get z-score for confidence interval."""
        # Approximate z-scores for common confidence levels
        z_scores = {
            0.90: 1.645,
            0.95: 1.96,
            0.99: 2.576,
        }
        return z_scores.get(confidence, 1.96)


class NaiveForecaster(Forecaster):
    """
    Naive forecaster - repeats last value.
    
    Good baseline for comparison.
    """
    
    @property
    def method_name(self) -> str:
        return "naive"
    
    def forecast(
        self,
        values: List[float],
        periods: int,
        dates: Optional[List[str]] = None,
    ) -> ForecastResult:
        if not values:
            return ForecastResult(
                predictions=[],
                method=self.method_name,
                periods=periods,
                confidence_level=self.confidence_level,
                stats={},
            )
        
        last_value = values[-1]
        std = self._calculate_std(values)
        z = self._get_z_score(self.confidence_level)
        
        predictions = []
        for i in range(1, periods + 1):
            # Uncertainty grows with horizon
            margin = z * std * math.sqrt(i)
            
            predictions.append(ForecastPoint(
                period=i,
                value=last_value,
                lower_bound=last_value - margin,
                upper_bound=last_value + margin,
            ))
        
        return ForecastResult(
            predictions=predictions,
            method=self.method_name,
            periods=periods,
            confidence_level=self.confidence_level,
            stats={"last_value": last_value, "std": std},
        )


class MovingAverageForecaster(Forecaster):
    """
    Simple Moving Average (SMA) forecaster.
    
    Uses average of last `window` values as forecast.
    """
    
    def __init__(self, window: int = 7, confidence_level: float = 0.95):
        super().__init__(confidence_level)
        self.window = window
    
    @property
    def method_name(self) -> str:
        return "sma"
    
    def forecast(
        self,
        values: List[float],
        periods: int,
        dates: Optional[List[str]] = None,
    ) -> ForecastResult:
        if len(values) < 2:
            return ForecastResult(
                predictions=[],
                method=self.method_name,
                periods=periods,
                confidence_level=self.confidence_level,
                stats={},
            )
        
        # Use last `window` values
        window_values = values[-self.window:] if len(values) >= self.window else values
        forecast_value = sum(window_values) / len(window_values)
        
        std = self._calculate_std(values)
        z = self._get_z_score(self.confidence_level)
        
        predictions = []
        for i in range(1, periods + 1):
            margin = z * std * math.sqrt(i)
            
            predictions.append(ForecastPoint(
                period=i,
                value=forecast_value,
                lower_bound=forecast_value - margin,
                upper_bound=forecast_value + margin,
            ))
        
        return ForecastResult(
            predictions=predictions,
            method=self.method_name,
            periods=periods,
            confidence_level=self.confidence_level,
            stats={"window": self.window, "forecast_value": forecast_value, "std": std},
        )


class ExponentialSmoothingForecaster(Forecaster):
    """
    Simple Exponential Smoothing (SES) forecaster.
    
    Weights recent observations more heavily using alpha parameter.
    """
    
    def __init__(self, alpha: float = 0.3, confidence_level: float = 0.95):
        super().__init__(confidence_level)
        self.alpha = min(max(alpha, 0.01), 0.99)  # Clamp to valid range
    
    @property
    def method_name(self) -> str:
        return "ema"
    
    def forecast(
        self,
        values: List[float],
        periods: int,
        dates: Optional[List[str]] = None,
    ) -> ForecastResult:
        if len(values) < 2:
            return ForecastResult(
                predictions=[],
                method=self.method_name,
                periods=periods,
                confidence_level=self.confidence_level,
                stats={},
            )
        
        # Calculate exponential moving average
        ema = values[0]
        for value in values[1:]:
            ema = self.alpha * value + (1 - self.alpha) * ema
        
        std = self._calculate_std(values)
        z = self._get_z_score(self.confidence_level)
        
        predictions = []
        for i in range(1, periods + 1):
            margin = z * std * math.sqrt(i)
            
            predictions.append(ForecastPoint(
                period=i,
                value=ema,
                lower_bound=ema - margin,
                upper_bound=ema + margin,
            ))
        
        return ForecastResult(
            predictions=predictions,
            method=self.method_name,
            periods=periods,
            confidence_level=self.confidence_level,
            stats={"alpha": self.alpha, "final_ema": ema, "std": std},
        )


class LinearTrendForecaster(Forecaster):
    """
    Linear regression trend forecaster.
    
    Fits a line to historical data and extrapolates.
    """
    
    @property
    def method_name(self) -> str:
        return "linear"
    
    def forecast(
        self,
        values: List[float],
        periods: int,
        dates: Optional[List[str]] = None,
    ) -> ForecastResult:
        if len(values) < 3:
            return ForecastResult(
                predictions=[],
                method=self.method_name,
                periods=periods,
                confidence_level=self.confidence_level,
                stats={},
            )
        
        # Simple linear regression
        n = len(values)
        x = list(range(n))
        
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        # Calculate slope and intercept
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean
        
        # Calculate residual std for confidence intervals
        residuals = [values[i] - (slope * i + intercept) for i in range(n)]
        residual_std = self._calculate_std(residuals)
        z = self._get_z_score(self.confidence_level)
        
        predictions = []
        for i in range(1, periods + 1):
            future_x = n - 1 + i
            predicted = slope * future_x + intercept
            
            # Uncertainty grows with extrapolation distance
            margin = z * residual_std * math.sqrt(1 + i / n)
            
            predictions.append(ForecastPoint(
                period=i,
                value=predicted,
                lower_bound=predicted - margin,
                upper_bound=predicted + margin,
            ))
        
        return ForecastResult(
            predictions=predictions,
            method=self.method_name,
            periods=periods,
            confidence_level=self.confidence_level,
            stats={
                "slope": slope,
                "intercept": intercept,
                "residual_std": residual_std,
                "trend": "increasing" if slope > 0 else "decreasing" if slope < 0 else "flat",
            },
        )


# =============================================================================
# Main API
# =============================================================================

_FORECASTERS = {
    "naive": NaiveForecaster,
    "sma": MovingAverageForecaster,
    "ema": ExponentialSmoothingForecaster,
    "linear": LinearTrendForecaster,
}


def forecast(
    values: List[float],
    periods: int = 7,
    method: str = "ema",
    confidence_level: float = 0.95,
    dates: Optional[List[str]] = None,
    **kwargs,
) -> ForecastResult:
    """
    Generate forecast for future periods.
    
    Args:
        values: Historical values
        periods: Number of periods to forecast
        method: Forecasting method ("naive", "sma", "ema", "linear")
        confidence_level: Confidence interval level (0.9, 0.95, 0.99)
        dates: Optional date strings for labeling predictions
        **kwargs: Additional method-specific parameters
    
    Returns:
        ForecastResult with predictions and statistics
    """
    if method not in _FORECASTERS:
        raise ValueError(f"Unknown method: {method}. Available: {list(_FORECASTERS.keys())}")
    
    forecaster_cls = _FORECASTERS[method]
    forecaster = forecaster_cls(confidence_level=confidence_level, **kwargs)
    
    return forecaster.forecast(values, periods, dates)


def get_available_methods() -> List[str]:
    """Get list of available forecasting methods."""
    return list(_FORECASTERS.keys())


# =============================================================================
# Trend Analysis Helpers
# =============================================================================

def detect_trend(values: List[float]) -> Dict[str, Any]:
    """
    Detect trend direction and strength.
    
    Returns:
        {"direction": "up"|"down"|"flat", "slope": float, "strength": float}
    """
    if len(values) < 3:
        return {"direction": "flat", "slope": 0, "strength": 0}
    
    forecaster = LinearTrendForecaster()
    result = forecaster.forecast(values, periods=1)
    
    slope = result.stats.get("slope", 0)
    std = result.stats.get("residual_std", 1)
    
    # Calculate trend strength (R-squared proxy)
    n = len(values)
    mean = sum(values) / n
    ss_tot = sum((v - mean) ** 2 for v in values)
    ss_res = std ** 2 * (n - 2) if n > 2 else 0
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
    
    # Direction
    if abs(slope) < 0.001:
        direction = "flat"
    elif slope > 0:
        direction = "up"
    else:
        direction = "down"
    
    return {
        "direction": direction,
        "slope": round(slope, 4),
        "strength": round(max(0, min(1, r_squared)), 4),
    }
