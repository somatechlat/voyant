"""
Canonical service exports for Voyant analytics.

This package intentionally exposes a single implementation path and avoids
duplicate analytics logic.
"""

from apps.services.analysis.anomaly_detection import AnomalyDetector
from apps.services.analysis.forecasting import TimeForecaster

__all__ = ["TimeForecaster", "AnomalyDetector"]
