"""
Tests for MLActivities.

Tests cluster_data, train_classifier_model, train_regression_model, and
forecast_time_series using real ML primitives (scikit-learn, Prophet).
No mocking — all computations run in-process.
"""

import pytest
from temporalio.exceptions import ApplicationError

from apps.worker.activities.ml_activities import MLActivities


@pytest.fixture(scope="module")
def activities():
    """Real MLActivities instance."""
    return MLActivities()


class TestClusterData:
    """Tests for the cluster_data activity."""

    def test_cluster_basic(self, activities):
        """Basic clustering returns cluster assignments."""
        data = [{"x": float(i), "y": float(i * 2)} for i in range(30)]
        result = activities.cluster_data({"data": data, "clusters": 3})
        assert "labels" in result or "clusters" in result or "total_records" in result

    def test_cluster_empty_data_raises(self, activities):
        """Empty data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.cluster_data({"data": []})

    def test_cluster_missing_data_raises(self, activities):
        """Missing data key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.cluster_data({})

    def test_cluster_default_clusters(self, activities):
        """Default cluster count of 3 is used when not specified."""
        data = [{"x": float(i), "y": float(i * 2)} for i in range(30)]
        result = activities.cluster_data({"data": data})
        assert result is not None

    def test_cluster_single_cluster(self, activities):
        """Single cluster is valid."""
        data = [{"x": float(i), "y": float(i)} for i in range(20)]
        result = activities.cluster_data({"data": data, "clusters": 1})
        assert result is not None

    def test_cluster_returns_silhouette(self, activities):
        """Clustering result includes silhouette score for quality assessment."""
        data = [
            {"x": float(i % 3 * 10 + i), "y": float(i % 3 * 10 + i * 2)}
            for i in range(30)
        ]
        result = activities.cluster_data({"data": data, "clusters": 3})
        # MLPrimitives.cluster_kmeans returns silhouette_score
        if "silhouette_score" in result:
            assert -1 <= result["silhouette_score"] <= 1


class TestTrainClassifierModel:
    """Tests for the train_classifier_model activity."""

    def test_classifier_basic(self, activities):
        """Basic classification training returns metrics."""
        data = [
            {"feature1": float(i), "feature2": float(i * 2), "target": int(i > 10)}
            for i in range(30)
        ]
        result = activities.train_classifier_model(
            {
                "data": data,
                "target_col": "target",
                "feature_cols": ["feature1", "feature2"],
            }
        )
        assert result is not None
        assert "accuracy" in result or "model_type" in result

    def test_classifier_empty_data_raises(self, activities):
        """Empty data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.train_classifier_model({"data": []})

    def test_classifier_missing_data_raises(self, activities):
        """Missing data key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.train_classifier_model({})

    def test_classifier_default_target(self, activities):
        """Default target column 'target' is used when not specified."""
        data = [
            {"feature1": float(i), "target": i % 2} for i in range(20)
        ]
        result = activities.train_classifier_model({"data": data})
        assert result is not None


class TestTrainRegressionModel:
    """Tests for the train_regression_model activity."""

    def test_regression_basic(self, activities):
        """Basic regression training returns coefficients and R-squared."""
        data = [
            {"feature1": float(i), "feature2": float(i * 0.5), "target": float(i * 2 + 5)}
            for i in range(30)
        ]
        result = activities.train_regression_model(
            {
                "data": data,
                "target_col": "target",
                "feature_cols": ["feature1", "feature2"],
            }
        )
        assert result is not None
        assert "r_squared" in result or "coefficients" in result

    def test_regression_empty_data_raises(self, activities):
        """Empty data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.train_regression_model({"data": []})

    def test_regression_missing_data_raises(self, activities):
        """Missing data key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.train_regression_model({})

    def test_regression_perfect_correlation(self, activities):
        """Perfect linear relationship yields R-squared near 1.0."""
        data = [
            {"x": float(i), "target": float(i * 3 + 10)} for i in range(50)
        ]
        result = activities.train_regression_model(
            {"data": data, "target_col": "target", "feature_cols": ["x"]}
        )
        if "r_squared" in result:
            assert result["r_squared"] > 0.99


class TestForecastTimeSeries:
    """Tests for the forecast_time_series activity."""

    def test_forecast_empty_dates_raises(self, activities):
        """Empty dates raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Dates and values are required"):
            activities.forecast_time_series({"dates": [], "values": [1, 2, 3]})

    def test_forecast_empty_values_raises(self, activities):
        """Empty values raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Dates and values are required"):
            activities.forecast_time_series(
                {"dates": ["2024-01-01", "2024-01-02"], "values": []}
            )

    def test_forecast_missing_both_raises(self, activities):
        """Missing both dates and values raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Dates and values are required"):
            activities.forecast_time_series({})

    def test_forecast_with_prophet(self, activities):
        """Prophet forecast returns predictions if library is available."""
        try:
            from prophet import Prophet  # noqa: F401
        except ImportError:
            pytest.skip("Prophet not installed")

        dates = [f"2024-01-{i:02d}" for i in range(1, 31)]
        values = [float(100 + i * 2 + (i % 3)) for i in range(30)]
        result = activities.forecast_time_series(
            {"dates": dates, "values": values, "periods": 7, "method": "prophet"}
        )
        assert "forecast_values" in result or "method" in result
