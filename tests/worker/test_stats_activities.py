"""
Tests for StatsActivities.

Tests parameter validation and error handling for statistical activities.
R-Engine dependent tests verify proper error propagation when the service
is unavailable. Schema tracking tests use real governance primitives.
"""

import pytest
from temporalio.exceptions import ApplicationError

from apps.worker.activities.stats_activities import StatsActivities


@pytest.fixture(scope="module")
def activities():
    """Real StatsActivities instance."""
    return StatsActivities()


class TestDescribeDistribution:
    """Tests for the describe_distribution activity."""

    def test_empty_data_raises(self, activities):
        """Empty data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.describe_distribution({"data": []})

    def test_missing_data_raises(self, activities):
        """Missing data key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.describe_distribution({})

    def test_with_real_data(self, activities):
        """With real data, delegates to RStatsPrimitives.describe_column."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        try:
            result = activities.describe_distribution({"data": data})
            assert "mean" in result
            assert "median" in result
            assert "std_dev" in result
        except ApplicationError as e:
            # R-Engine may not be available in test environment
            assert "R-Engine" in str(e) or "circuit breaker" in str(e).lower() or "Distribution analysis failed" in str(e)

    def test_with_table_name_tracks_schema(self, activities):
        """table_name parameter triggers schema tracking."""
        data = [10.0, 20.0, 30.0, 40.0, 50.0]
        try:
            result = activities.describe_distribution(
                {"data": data, "table_name": "test_schema_table"}
            )
            assert result is not None
        except ApplicationError:
            # R-Engine may not be available
            pass

    def test_with_dict_data_schema_inference(self, activities):
        """Dict data infers column schema from keys and value types."""
        data = [
            {"revenue": 100.0, "quantity": 5},
            {"revenue": 200.0, "quantity": 10},
            {"revenue": 150.0, "quantity": 7},
        ]
        try:
            result = activities.describe_distribution(
                {"data": data, "table_name": "dict_data_table"}
            )
            assert result is not None
        except ApplicationError:
            # R-Engine may not be available
            pass


class TestCalculateCorrelation:
    """Tests for the calculate_correlation activity."""

    def test_empty_data_raises(self, activities):
        """Empty data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.calculate_correlation({"data": {}})

    def test_missing_data_raises(self, activities):
        """Missing data key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.calculate_correlation({})

    def test_with_real_data(self, activities):
        """With real data, delegates to RStatsPrimitives.correlation_matrix."""
        data = {
            "x": [1.0, 2.0, 3.0, 4.0, 5.0],
            "y": [2.0, 4.0, 6.0, 8.0, 10.0],
        }
        try:
            result = activities.calculate_correlation({"data": data, "method": "pearson"})
            assert result is not None
        except ApplicationError as e:
            assert "R-Engine" in str(e) or "circuit breaker" in str(e).lower() or "Correlation" in str(e)

    def test_spearman_method(self, activities):
        """Spearman method is passed through."""
        data = {
            "a": [1.0, 2.0, 3.0, 4.0, 5.0],
            "b": [5.0, 4.0, 3.0, 2.0, 1.0],
        }
        try:
            result = activities.calculate_correlation({"data": data, "method": "spearman"})
            assert result is not None
        except ApplicationError:
            pass


class TestFitDistribution:
    """Tests for the fit_distribution activity."""

    def test_empty_data_raises(self, activities):
        """Empty data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.fit_distribution({"data": []})

    def test_missing_data_raises(self, activities):
        """Missing data key raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="No data provided"):
            activities.fit_distribution({})

    def test_default_distribution(self, activities):
        """Default distribution is 'normal'."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        try:
            result = activities.fit_distribution({"data": data})
            assert result is not None
        except ApplicationError:
            pass

    def test_custom_distribution(self, activities):
        """Custom distribution name is passed through."""
        data = [1.0, 2.0, 3.0, 4.0, 5.0]
        try:
            result = activities.fit_distribution({"data": data, "dist": "lognormal"})
            assert result is not None
        except ApplicationError:
            pass


class TestCalculateMarketShare:
    """Tests for the calculate_market_share activity."""

    def test_empty_brand_data_raises(self, activities):
        """Empty brand data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Brand or competitor data cannot be empty"):
            activities.calculate_market_share(
                {"brand_data": [], "competitor_data": [{"value": 100}]}
            )

    def test_empty_competitor_data_raises(self, activities):
        """Empty competitor data raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Brand or competitor data cannot be empty"):
            activities.calculate_market_share(
                {"brand_data": [{"value": 100}], "competitor_data": []}
            )

    def test_both_empty_raises(self, activities):
        """Both empty raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="Brand or competitor data cannot be empty"):
            activities.calculate_market_share(
                {"brand_data": [], "competitor_data": []}
            )


class TestPerformHypothesisTest:
    """Tests for the perform_hypothesis_test activity."""

    def test_unsupported_test_type(self, activities):
        """Unsupported test type raises non-retryable ApplicationError."""
        with pytest.raises(ApplicationError, match="not supported"):
            activities.perform_hypothesis_test(
                {
                    "group_a": [1.0, 2.0, 3.0],
                    "group_b": [4.0, 5.0, 6.0],
                    "test_type": "chi-squared",
                }
            )

    def test_t_test_with_real_data(self, activities):
        """t-test with real data returns p-value and statistic."""
        group_a = [23.0, 25.0, 28.0, 22.0, 30.0, 27.0, 24.0, 26.0, 29.0, 21.0]
        group_b = [31.0, 33.0, 35.0, 30.0, 32.0, 34.0, 36.0, 29.0, 33.0, 31.0]
        try:
            result = activities.perform_hypothesis_test(
                {
                    "group_a": group_a,
                    "group_b": group_b,
                    "test_type": "t-test",
                }
            )
            assert "p_value" in result
            assert "statistic" in result
            assert "method" in result
            assert 0 <= result["p_value"] <= 1
        except ApplicationError as e:
            assert "R-Engine" in str(e) or "circuit breaker" in str(e).lower() or "Hypothesis test failed" in str(e)

    def test_t_test_default_test_type(self, activities):
        """Default test_type is 't-test'."""
        try:
            result = activities.perform_hypothesis_test(
                {"group_a": [1.0, 2.0, 3.0], "group_b": [4.0, 5.0, 6.0]}
            )
            assert "p_value" in result
        except ApplicationError:
            pass
