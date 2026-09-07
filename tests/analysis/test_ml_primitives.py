"""Tests for apps.analysis.lib.ml_primitives."""

import pytest

from apps.analysis.lib.ml_primitives import SKLEARN_AVAILABLE, MLPrimitives
from apps.core.lib.errors import AnalysisError


@pytest.fixture
def ml():
    return MLPrimitives()


# ---------------------------------------------------------------------------
# Dependency check
# ---------------------------------------------------------------------------


class TestDependencyCheck:
    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_check_deps_passes(self, ml):
        ml._check_deps()  # Should not raise


# ---------------------------------------------------------------------------
# detect_anomalies (Isolation Forest)
# ---------------------------------------------------------------------------


class TestDetectAnomalies:
    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_basic_anomaly_detection(self, ml):
        data = [{"val": float(i)} for i in range(100)] + [{"val": 10000.0}]
        result = ml.detect_anomalies(data, contamination=0.05)
        assert result["total_records"] == 101
        assert result["anomaly_count"] >= 1

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_no_anomalies_in_normal_data(self, ml):
        data = [{"val": float(i)} for i in range(100)]
        result = ml.detect_anomalies(data, contamination=0.01)
        assert result["total_records"] == 100

    def test_empty_data_raises(self, ml):
        with pytest.raises(AnalysisError):
            ml.detect_anomalies([])

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_no_numeric_data_raises(self, ml):
        data = [{"name": "Alice"}, {"name": "Bob"}]
        with pytest.raises(AnalysisError):
            ml.detect_anomalies(data)

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_result_structure(self, ml):
        data = [{"val": float(i)} for i in range(50)]
        result = ml.detect_anomalies(data)
        assert "total_records" in result
        assert "anomaly_count" in result
        assert "anomaly_indices" in result
        assert "anomalies" in result


# ---------------------------------------------------------------------------
# cluster_kmeans
# ---------------------------------------------------------------------------


class TestClusterKMeans:
    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_basic_clustering(self, ml):
        data = [{"x": float(i), "y": float(i * 2)} for i in range(30)]
        result = ml.cluster_kmeans(data, n_clusters=3)
        assert len(result["clusters"]) == 30
        assert len(result["centroids"]) == 3
        assert "silhouette_score" in result

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_two_clusters(self, ml):
        data = [{"x": float(i)} for i in range(20)]
        result = ml.cluster_kmeans(data, n_clusters=2)
        assert len(result["centroids"]) == 2
        assert set(result["clusters"]).issubset({0, 1})

    def test_empty_data_raises(self, ml):
        with pytest.raises(AnalysisError):
            ml.cluster_kmeans([])

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_labeled_data_returned(self, ml):
        data = [{"x": float(i), "y": float(i)} for i in range(10)]
        result = ml.cluster_kmeans(data, n_clusters=2)
        assert "labeled_data" in result
        assert "cluster" in result["labeled_data"][0]


# ---------------------------------------------------------------------------
# train_classifier
# ---------------------------------------------------------------------------


class TestTrainClassifier:
    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_basic_classification(self, ml):
        data = [
            {"feature1": 1.0, "feature2": 2.0, "target": "A"},
            {"feature1": 2.0, "feature2": 3.0, "target": "A"},
            {"feature1": 10.0, "feature2": 11.0, "target": "B"},
            {"feature1": 11.0, "feature2": 12.0, "target": "B"},
        ] * 10
        result = ml.train_classifier(data, target_col="target", feature_cols=["feature1", "feature2"])
        assert result["model_type"] == "RandomForestClassifier"
        assert 0.0 <= result["accuracy"] <= 1.0
        assert "feature_importance" in result

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_numeric_target(self, ml):
        data = [{"f1": float(i), "f2": float(i * 2), "t": i % 2} for i in range(40)]
        result = ml.train_classifier(data, target_col="t", feature_cols=["f1", "f2"])
        assert result["classes"] == "numeric"

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_missing_target_raises(self, ml):
        data = [{"f1": 1.0}]
        with pytest.raises(Exception):
            ml.train_classifier(data, target_col="nonexistent", feature_cols=["f1"])


# ---------------------------------------------------------------------------
# train_regression
# ---------------------------------------------------------------------------


class TestTrainRegression:
    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_basic_regression(self, ml):
        data = [{"x": float(i), "y": float(i * 2 + 1)} for i in range(50)]
        result = ml.train_regression(data, target_col="y", feature_cols=["x"])
        assert result["model_type"] == "linear_regression"
        assert result["r2_score"] > 0.9  # Should be a near-perfect fit
        assert "coefficients" in result
        assert "intercept" in result
        assert "rmse" in result

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_multiple_features(self, ml):
        data = [{"a": float(i), "b": float(i * 2), "y": float(i * 3)} for i in range(50)]
        result = ml.train_regression(data, target_col="y", feature_cols=["a", "b"])
        assert len(result["coefficients"]) == 2
        assert len(result["features"]) == 2

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_missing_columns_raises(self, ml):
        data = [{"x": 1.0}]
        with pytest.raises(AnalysisError):
            ml.train_regression(data, target_col="missing", feature_cols=["x"])

    @pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not installed")
    def test_feature_importance(self, ml):
        data = [{"x": float(i), "y": float(i * 2)} for i in range(50)]
        result = ml.train_regression(data, target_col="y", feature_cols=["x"])
        assert "feature_importance" in result
        assert "x" in result["feature_importance"]
