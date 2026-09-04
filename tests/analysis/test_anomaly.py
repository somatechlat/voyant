"""Tests for apps.analysis.lib.anomaly — anomaly detection module."""

import pytest

from apps.analysis.lib.anomaly import (
    Anomaly,
    AnomalyDetector,
    AnomalyMethod,
    AnomalyResult,
    IQRDetector,
    MADDetector,
    ZScoreDetector,
    detect_anomalies,
    detect_column_anomalies,
    get_available_methods,
)


# ---------------------------------------------------------------------------
# Anomaly dataclass
# ---------------------------------------------------------------------------


class TestAnomalyDataclass:
    def test_to_dict(self):
        a = Anomaly(index=5, value=100.0, score=3.5, method="zscore", threshold=3.0)
        d = a.to_dict()
        assert d["index"] == 5
        assert d["value"] == 100.0
        assert d["score"] == 3.5
        assert d["method"] == "zscore"


# ---------------------------------------------------------------------------
# AnomalyResult
# ---------------------------------------------------------------------------


class TestAnomalyResult:
    def test_anomaly_count(self):
        result = AnomalyResult(
            anomalies=[Anomaly(0, 100, 5.0, "zscore", 3.0)],
            stats={}, method="zscore", threshold=3.0, total_points=10,
        )
        assert result.anomaly_count == 1

    def test_anomaly_rate(self):
        result = AnomalyResult(
            anomalies=[Anomaly(0, 100, 5.0, "zscore", 3.0)] * 5,
            stats={}, method="zscore", threshold=3.0, total_points=100,
        )
        assert result.anomaly_rate == 0.05

    def test_anomaly_rate_zero_points(self):
        result = AnomalyResult(
            anomalies=[], stats={}, method="zscore", threshold=3.0, total_points=0,
        )
        assert result.anomaly_rate == 0.0

    def test_to_dict(self):
        result = AnomalyResult(
            anomalies=[], stats={"mean": 10.0}, method="zscore", threshold=3.0, total_points=5,
        )
        d = result.to_dict()
        assert "anomaly_count" in d
        assert "anomaly_rate" in d
        assert "stats" in d


# ---------------------------------------------------------------------------
# ZScoreDetector
# ---------------------------------------------------------------------------


class TestZScoreDetector:
    def test_detects_obvious_outlier(self):
        values = [10.0] * 20 + [1000.0]
        detector = ZScoreDetector(threshold=3.0)
        result = detector.detect(values)
        assert result.anomaly_count >= 1
        assert any(a.value == 1000.0 for a in result.anomalies)

    def test_no_anomalies_in_uniform_data(self):
        values = [5.0] * 20
        detector = ZScoreDetector(threshold=3.0)
        result = detector.detect(values)
        assert result.anomaly_count == 0

    def test_too_few_points(self):
        result = ZScoreDetector().detect([1.0, 2.0])
        assert result.anomaly_count == 0

    def test_method_name(self):
        assert ZScoreDetector().method_name == "zscore"

    def test_stats_contain_mean_and_std(self):
        result = ZScoreDetector().detect([1.0, 2.0, 3.0, 4.0, 5.0])
        assert "mean" in result.stats
        assert "std" in result.stats


# ---------------------------------------------------------------------------
# IQRDetector
# ---------------------------------------------------------------------------


class TestIQRDetector:
    def test_detects_outlier(self):
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 100.0]
        detector = IQRDetector(threshold=1.5)
        result = detector.detect(values)
        assert result.anomaly_count >= 1

    def test_no_outliers_in_normal_range(self):
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        detector = IQRDetector(threshold=1.5)
        result = detector.detect(values)
        assert result.anomaly_count == 0

    def test_too_few_points(self):
        result = IQRDetector().detect([1.0, 2.0, 3.0])
        assert result.anomaly_count == 0

    def test_method_name(self):
        assert IQRDetector().method_name == "iqr"

    def test_stats_contain_bounds(self):
        result = IQRDetector().detect([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        assert "q1" in result.stats
        assert "q3" in result.stats
        assert "iqr" in result.stats
        assert "lower_bound" in result.stats
        assert "upper_bound" in result.stats


# ---------------------------------------------------------------------------
# MADDetector
# ---------------------------------------------------------------------------


class TestMADDetector:
    def test_detects_outlier(self):
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 1000.0]
        detector = MADDetector(threshold=3.5)
        result = detector.detect(values)
        assert result.anomaly_count >= 1

    def test_no_outliers_in_uniform(self):
        values = [5.0] * 20
        detector = MADDetector(threshold=3.5)
        result = detector.detect(values)
        assert result.anomaly_count == 0

    def test_too_few_points(self):
        result = MADDetector().detect([1.0, 2.0])
        assert result.anomaly_count == 0

    def test_method_name(self):
        assert MADDetector().method_name == "mad"

    def test_stats_contain_median_and_mad(self):
        result = MADDetector().detect([1.0, 2.0, 3.0, 4.0, 5.0])
        assert "median" in result.stats
        assert "mad" in result.stats


# ---------------------------------------------------------------------------
# detect_anomalies (main API)
# ---------------------------------------------------------------------------


class TestDetectAnomalies:
    def test_zscore_method(self):
        values = [10.0] * 20 + [1000.0]
        result = detect_anomalies(values, method="zscore")
        assert result.method == "zscore"
        assert result.anomaly_count >= 1

    def test_iqr_method(self):
        values = [10.0, 11.0, 12.0, 13.0, 14.0, 100.0]
        result = detect_anomalies(values, method="iqr")
        assert result.method == "iqr"

    def test_mad_method(self):
        values = [10.0] * 20 + [1000.0]
        result = detect_anomalies(values, method="mad")
        assert result.method == "mad"

    def test_custom_threshold(self):
        values = [10.0] * 20 + [50.0]
        result = detect_anomalies(values, method="zscore", threshold=2.0)
        assert result.threshold == 2.0

    def test_unknown_method_raises(self):
        with pytest.raises(ValueError, match="Unknown method"):
            detect_anomalies([1.0, 2.0], method="nonexistent")


# ---------------------------------------------------------------------------
# get_available_methods
# ---------------------------------------------------------------------------


class TestGetAvailableMethods:
    def test_returns_list(self):
        methods = get_available_methods()
        assert "zscore" in methods
        assert "iqr" in methods
        assert "mad" in methods


# ---------------------------------------------------------------------------
# detect_column_anomalies
# ---------------------------------------------------------------------------


class TestDetectColumnAnomalies:
    def test_basic_column_detection(self):
        data = [{"val": 10}] * 20 + [{"val": 1000}]
        results = detect_column_anomalies(data, columns=["val"], method="zscore")
        assert "val" in results
        assert results["val"].anomaly_count >= 1

    def test_auto_detect_numeric_columns(self):
        data = [{"name": "a", "score": 10}] * 20 + [{"name": "b", "score": 1000}]
        results = detect_column_anomalies(data, method="zscore")
        assert "score" in results
        assert "name" not in results  # Not numeric

    def test_empty_data(self):
        results = detect_column_anomalies([])
        assert results == {}

    def test_non_numeric_values_skipped(self):
        data = [{"text": "hello"}, {"text": "world"}]
        results = detect_column_anomalies(data)
        assert results == {}
