"""
Canonical service exports for Voyant analytics.

This package intentionally exposes a single implementation path and avoids
duplicate analytics logic.
"""

from voyant.services.analysis.anomaly_detection import AnomalyDetector
from voyant.services.analysis.forecasting import TimeForecaster

__all__ = ["TimeForecaster", "AnomalyDetector"]
