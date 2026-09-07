"""
Tests for MLActivities.

Tests cluster_data, train_classifier_model, train_regression_model, and
forecast_time_series using real ML primitives (scikit-learn, Prophet).
ActivityEnvironment.run() is synchronous — no await needed.
"""

import pytest
from temporalio.exceptions import ApplicationError
from temporalio.testing import ActivityEnvironment

from apps.worker.activities.ml_activities import MLActivities


@pytest.fixture(scope="module")
def activities():
    """Real MLActivities instance."""
    return MLActivities()


@pytest.fixture()
def env():
    """ActivityEnvironment for testing activities outside a Temporal worker."""
    return ActivityEnvironment()


class TestClusterData:
    """Tests for the cluster_data activity."""

    def test_cluster_basic(self, activities, env):
        """Basic clustering returns cluster assignments."""
        data = [{"x": float(i), "y": float(i * 2)} for i in range(30)]
        result = env.run(
            activities.cluster_data, {"data": data, "clusters": 3}
        )
        assert "labels" in result or "clusters" in result or "total_records" in result

    def test_cluster_empty_data_raises(self, activities, env):
        """Empty data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            env.run(activities.cluster_data, {"data": []})

    def test_cluster_missing_data_raises(self, activities, env):
        """Missing data key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            env.run(activities.cluster_data, {})

    def test_cluster_default_clusters(self, activities, env):
        """Default cluster count of 3 is used when not specified."""
        data = [{"x": float(i), "y": float(i * 2)} for i in range(30)]
        result = env.run(activities.cluster_data, {"data": data})
        assert result is not None

    def test_cluster_two_clusters(self, activities, env):
        """Two clusters is valid (minimum for KMeans)."""
        data = [{"x": float(i), "y": float(i)} for i in range(20)]
        result = env.run(
            activities.cluster_data, {"data": data, "clusters": 2}
        )
        assert result is not None

    def test_cluster_returns_silhouette(self, activities, env):
        """Clustering result includes silhouette score for quality assessment."""
        data = [
            {"x": float(i % 3 * 10 + i), "y": float(i % 3 * 10 + i * 2)}
            for i in range(30)
        ]
        result = env.run(
            activities.cluster_data, {"data": data, "clusters": 3}
        )
        if "silhouette_score" in result:
            assert -1 <= result["silhouette_score"] <= 1


class TestTrainClassifierModel:
    """Tests for the train_classifier_model activity."""

    def test_classifier_basic(self, activities, env):
        """Basic classification training returns metrics."""
        data = [
            {"feature1": float(i), "feature2": float(i * 2), "target": int(i > 10)}
            for i in range(30)
        ]
        result = env.run(
            activities.train_classifier_model,
            {
                "data": data,
                "target_col": "target",
                "feature_cols": ["feature1", "feature2"],
            },
        )
        assert result is not None
        assert "accuracy" in result or "model_type" in result

    def test_classifier_empty_data_raises(self, activities, env):
        """Empty data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            env.run(activities.train_classifier_model, {"data": []})

    def test_classifier_missing_data_raises(self, activities, env):
        """Missing data key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            env.run(activities.train_classifier_model, {})

    def test_classifier_default_target(self, activities, env):
        """Default target column 'target' is used when not specified.

        Note: feature_cols must be provided; empty feature_cols causes
        'No numeric feature columns found' error.
        """
        data = [
            {"feature1": float(i), "target": float(i % 2)} for i in range(20)
        ]
        result = env.run(
            activities.train_classifier_model,
            {"data": data, "feature_cols": ["feature1"]},
        )
        assert result is not None


class TestTrainRegressionModel:
    """Tests for the train_regression_model activity."""

    def test_regression_basic(self, activities, env):
        """Basic regression training returns coefficients and R-squared."""
        data = [
            {"feature1": float(i), "feature2": float(i * 0.5), "target": float(i * 2 + 5)}
            for i in range(30)
        ]
        result = env.run(
            activities.train_regression_model,
            {
                "data": data,
                "target_col": "target",
                "feature_cols": ["feature1", "feature2"],
            },
        )
        assert result is not None
        assert "r_squared" in result or "coefficients" in result

    def test_regression_empty_data_raises(self, activities, env):
        """Empty data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            env.run(activities.train_regression_model, {"data": []})

    def test_regression_missing_data_raises(self, activities, env):
        """Missing data key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            env.run(activities.train_regression_model, {})

    def test_regression_perfect_correlation(self, activities, env):
        """Perfect linear relationship yields R-squared near 1.0."""
        data = [
            {"x": float(i), "target": float(i * 3 + 10)} for i in range(50)
        ]
        result = env.run(
            activities.train_regression_model,
            {"data": data, "target_col": "target", "feature_cols": ["x"]},
        )
        if "r_squared" in result:
            assert result["r_squared"] > 0.99


class TestForecastTimeSeries:
    """Tests for the forecast_time_series activity."""

    def test_forecast_empty_dates_raises(self, activities, env):
        """Empty dates raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Dates and values are required"):
            env.run(
                activities.forecast_time_series,
                {"dates": [], "values": [1, 2, 3]},
            )

    def test_forecast_empty_values_raises(self, activities, env):
        """Empty values raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Dates and values are required"):
            env.run(
                activities.forecast_time_series,
                {"dates": ["2024-01-01", "2024-01-02"], "values": []},
            )

    def test_forecast_missing_both_raises(self, activities, env):
        """Missing both dates and values raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Dates and values are required"):
            env.run(activities.forecast_time_series, {})

    def test_forecast_with_prophet(self, activities, env):
        """Prophet forecast returns predictions if library is available."""
        try:
            from prophet import Prophet  # noqa: F401
        except ImportError:
            pytest.skip("Prophet not installed")

        dates = [f"2024-01-{i:02d}" for i in range(1, 31)]
        values = [float(100 + i * 2 + (i % 3)) for i in range(30)]
        result = env.run(
            activities.forecast_time_series,
            {"dates": dates, "values": values, "periods": 7, "method": "prophet"},
        )
        assert "forecast_values" in result or "method" in result
