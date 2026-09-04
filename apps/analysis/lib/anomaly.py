"""
Anomaly detection for time series and tabular data.

Reference: docs/CANONICAL_ROADMAP.md - P6 Advanced Analytics
"""

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class AnomalyMethod(StrEnum):

    ZSCORE = "zscore"  # Standard z-score
    IQR = "iqr"  # Interquartile range
    MAD = "mad"  # Median Absolute Deviation
    ISOLATION_FOREST = "iforest"  # ML-based (implemented in ml_primitives.py)


@dataclass
class Anomaly:

    index: int
    value: float
    score: float  # How anomalous (higher = more anomalous)
    method: str
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "value": self.value,
            "score": round(self.score, 4),
            "method": self.method,
            "threshold": self.threshold,
        }


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""

    anomalies: list[Anomaly]
    stats: dict[str, float]
    method: str
    threshold: float
    total_points: int

    @property
    def anomaly_count(self) -> int:
        return len(self.anomalies)

    @property
    def anomaly_rate(self) -> float:
        if self.total_points == 0:
            return 0.0
        return len(self.anomalies) / self.total_points

    def to_dict(self) -> dict[str, Any]:
        return {
            "anomaly_count": self.anomaly_count,
            "anomaly_rate": round(self.anomaly_rate, 4),
            "method": self.method,
            "threshold": self.threshold,
            "total_points": self.total_points,
            "stats": {k: round(v, 4) for k, v in self.stats.items()},
            "anomalies": [a.to_dict() for a in self.anomalies],
        }


# =============================================================================
# Detectors
# =============================================================================


class AnomalyDetector(ABC):
    """Base class for anomaly detectors."""

    def __init__(self, threshold: float = 3.0):
        self.threshold = threshold

    @abstractmethod
    def detect(self, values: list[float]) -> AnomalyResult:
        """Detect anomalies in a list of values."""
        pass

    @property
    @abstractmethod
    def method_name(self) -> str:
        pass


class ZScoreDetector(AnomalyDetector):
    """
    Z-score based anomaly detection.

    Detects values that deviate more than `threshold` standard deviations
    from the mean. Simple but sensitive to outliers in the data itself.
    """

    @property
    def method_name(self) -> str:
        return "zscore"

    def detect(self, values: list[float]) -> AnomalyResult:
        if len(values) < 3:
            return AnomalyResult(
                anomalies=[],
                stats={},
                method=self.method_name,
                threshold=self.threshold,
                total_points=len(values),
            )

        # Calculate mean and std
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        std = math.sqrt(variance) if variance > 0 else 1.0

        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std) if std > 0 else 0
            if z_score > self.threshold:
                anomalies.append(
                    Anomaly(
                        index=i,
                        value=value,
                        score=z_score,
                        method=self.method_name,
                        threshold=self.threshold,
                    )
                )

        return AnomalyResult(
            anomalies=anomalies,
            stats={"mean": mean, "std": std},
            method=self.method_name,
            threshold=self.threshold,
            total_points=n,
        )


class IQRDetector(AnomalyDetector):
    """
    Interquartile Range (IQR) based anomaly detection.

    Resistant to outliers, unlike z-score.
    Detects values outside [Q1 - threshold*IQR, Q3 + threshold*IQR].
    """

    def __init__(self, threshold: float = 1.5):
        super().__init__(threshold)

    @property
    def method_name(self) -> str:
        return "iqr"

    def detect(self, values: list[float]) -> AnomalyResult:
        if len(values) < 4:
            return AnomalyResult(
                anomalies=[],
                stats={},
                method=self.method_name,
                threshold=self.threshold,
                total_points=len(values),
            )

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        q1_idx = n // 4
        q3_idx = (3 * n) // 4
        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]
        iqr = q3 - q1

        lower_bound = q1 - self.threshold * iqr
        upper_bound = q3 + self.threshold * iqr

        anomalies = []
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                # Calculate distance from nearest bound
                distance = max(lower_bound - value, value - upper_bound)
                score = distance / iqr if iqr > 0 else 0

                anomalies.append(
                    Anomaly(
                        index=i,
                        value=value,
                        score=score,
                        method=self.method_name,
                        threshold=self.threshold,
                    )
                )

        return AnomalyResult(
            anomalies=anomalies,
            stats={
                "q1": q1,
                "q3": q3,
                "iqr": iqr,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
            },
            method=self.method_name,
            threshold=self.threshold,
            total_points=len(values),
        )


class MADDetector(AnomalyDetector):
    """
    Median Absolute Deviation (MAD) based anomaly detection.

    Uses median instead of mean.
    Modified z-score = 0.6745 * (x - median) / MAD
    """

    def __init__(self, threshold: float = 3.5):
        super().__init__(threshold)

    @property
    def method_name(self) -> str:
        return "mad"

    def detect(self, values: list[float]) -> AnomalyResult:
        if len(values) < 3:
            return AnomalyResult(
                anomalies=[],
                stats={},
                method=self.method_name,
                threshold=self.threshold,
                total_points=len(values),
            )

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        median = sorted_vals[n // 2]

        # Calculate MAD
        absolute_deviations = [abs(x - median) for x in values]
        sorted_deviations = sorted(absolute_deviations)
        mad = sorted_deviations[n // 2]

        # Avoid division by zero
        if mad == 0:
            mad = 1.0

        # Scaling factor for normal distribution
        k = 0.6745

        anomalies = []
        for i, value in enumerate(values):
            modified_z = k * abs(value - median) / mad
            if modified_z > self.threshold:
                anomalies.append(
                    Anomaly(
                        index=i,
                        value=value,
                        score=modified_z,
                        method=self.method_name,
                        threshold=self.threshold,
                    )
                )

        return AnomalyResult(
            anomalies=anomalies,
            stats={"median": median, "mad": mad},
            method=self.method_name,
            threshold=self.threshold,
            total_points=len(values),
        )


# =============================================================================
# Main API
# =============================================================================

_DETECTORS = {
    "zscore": ZScoreDetector,
    "iqr": IQRDetector,
    "mad": MADDetector,
}


def detect_anomalies(
    values: list[float],
    method: str = "mad",
    threshold: float | None = None,
) -> AnomalyResult:
    """
    Detect anomalies in a list of values.

    Args:
        values: List of numeric values
        method: Detection method ("zscore", "iqr", "mad")
        threshold: Detection threshold (method-specific default if None)

    Returns:
        AnomalyResult with detected anomalies and statistics
    """
    if method not in _DETECTORS:
        raise ValueError(
            f"Unknown method: {method}. Available: {list(_DETECTORS.keys())}"
        )

    detector_cls = _DETECTORS[method]

    if threshold is not None:
        detector = detector_cls(threshold=threshold)
    else:
        detector = detector_cls()

    return detector.detect(values)


def get_available_methods() -> list[str]:
    """Get list of available detection methods."""
    return list(_DETECTORS.keys())


# =============================================================================
# Column-level Anomaly Detection
# =============================================================================


def detect_column_anomalies(
    data: list[dict[str, Any]],
    columns: list[str] | None = None,
    method: str = "mad",
    threshold: float | None = None,
) -> dict[str, AnomalyResult]:
    """
    Detect anomalies in specific columns of tabular data.

    Args:
        data: List of row dicts
        columns: Columns to check (None = all numeric)
        method: Detection method
        threshold: Detection threshold

    Returns:
        Dict mapping column name to AnomalyResult
    """
    if not data:
        return {}

    # Determine columns to check
    if columns is None:
        # Find numeric columns
        columns = []
        sample = data[0]
        for key, value in sample.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                columns.append(key)

    results = {}
    for column in columns:
        values = []
        for row in data:
            val = row.get(column)
            if val is not None and isinstance(val, (int, float)):
                values.append(float(val))

        if values:
            results[column] = detect_anomalies(
                values, method=method, threshold=threshold
            )

    return results
