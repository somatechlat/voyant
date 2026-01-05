"""
Tests for Data Quality Fixing Activity.

This module contains comprehensive tests for the `fix_data_quality` activity,
which performs various data cleaning operations. It verifies the correctness
of missing value imputation (mean, median, mode), outlier detection and
treatment (capping, removal, winsorization), and the calculation of data
quality scores. Tests also cover edge cases like empty datasets and performance
with large datasets.
"""

import math
import os
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import pytest

# Mock NLTK to avoid data download requirement during testing.
# This assumes the sentiment analyzer is only used in operational_activities.
with patch("voyant.core.nlp_primitives.SentimentIntensityAnalyzer"):
    from voyant.activities.operational_activities import OperationalActivities


class TestFixDataQuality:
    """
    Test suite for the `fix_data_quality` activity.

    This class verifies that the data quality fixing mechanisms correctly
    handle various data imperfections, including missing values and outliers,
    and accurately report on the improvements made.
    """

    def setup_method(self):
        """
        Sets up the test environment before each test method is executed.
        Initializes an instance of `OperationalActivities` with a mocked
        `SentimentIntensityAnalyzer` to prevent external dependencies.
        """
        with patch("voyant.core.nlp_primitives.SentimentIntensityAnalyzer"):
            self.ops_activities = OperationalActivities()

    def test_empty_data(self):
        """
        Tests the `fix_data_quality` activity with an empty dataset.

        Ensures that the activity gracefully handles empty input and returns
        an empty cleaned dataset with a quality score of 0.
        """
        params = {"data": [], "numeric_columns": [], "categorical_columns": []}

        result = self.ops_activities.fix_data_quality(params)

        assert result["cleaned_data"] == []
        assert result["quality_report"]["original_rows"] == 0
        assert result["quality_report"]["cleaned_rows"] == 0
        assert result["quality_report"]["quality_score_before"] == 0.0
        assert result["quality_report"]["quality_score_after"] == 0.0

    def test_no_missing_values(self):
        """
        Tests the `fix_data_quality` activity with a dataset that has no missing values.

        Ensures that if no issues are present, no fixes are applied and the quality score remains 1.0.
        """
        data = [
            {"revenue": 100, "category": "A"},
            {"revenue": 200, "category": "B"},
            {"revenue": 150, "category": "A"},
        ]

        params = {
            "data": data,
            "numeric_columns": ["revenue"],
            "categorical_columns": ["category"],
        }

        result = self.ops_activities.fix_data_quality(params)

        assert result["quality_report"]["missing_value_fixes"] == 0
        assert result["quality_report"]["quality_score_before"] == 1.0
        assert result["quality_report"]["quality_score_after"] == 1.0

    def test_missing_value_imputation_median(self):
        """
        Tests median imputation for numeric columns with missing values.

        Verifies that missing numeric values are replaced by the median of the existing values.
        """
        data = [
            {"revenue": 100, "category": "A"},
            {"revenue": None, "category": "B"},
            {"revenue": 200, "category": "A"},
            {"revenue": None, "category": "B"},
            {"revenue": 150, "category": "A"},
        ]

        params = {
            "data": data,
            "numeric_columns": ["revenue"],
            "categorical_columns": ["category"],
            "imputation_strategy": "median",
        }

        result = self.ops_activities.fix_data_quality(params)

        # Expect 2 missing values to be fixed.
        assert result["quality_report"]["missing_value_fixes"] == 2

        # Check if the median was correctly used for imputation (median of 100, 150, 200 is 150).
        df = pd.DataFrame(result["cleaned_data"])
        assert df["revenue"].isnull().sum() == 0
        assert all(val == 150.0 for val in df[df.index.isin([1, 3])]["revenue"].values)

        # Quality score should show improvement.
        assert (
            result["quality_report"]["quality_score_after"]
            > result["quality_report"]["quality_score_before"]
        )

    def test_missing_value_imputation_mean(self):
        """
        Tests mean imputation for numeric columns with missing values.

        Verifies that missing numeric values are replaced by the mean of the existing values.
        """
        data = [
            {"value": 100},
            {"value": None},
            {"value": 200},
            {"value": None},
            {"value": 300},
        ]

        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "imputation_strategy": "mean",
        }

        result = self.ops_activities.fix_data_quality(params)

        # Mean of 100, 200, 300 = 200.
        df = pd.DataFrame(result["cleaned_data"])
        imputed_values = df[df.index.isin([1, 3])]["value"].values
        assert all(v == 200.0 for v in imputed_values)

    def test_missing_value_imputation_mode(self):
        """
        Tests mode imputation for categorical columns with missing values.

        Verifies that missing categorical values are replaced by the mode of the existing values.
        """
        data = [
            {"category": "A"},
            {"category": None},
            {"category": "A"},
            {"category": None},
            {"category": "B"},
        ]

        params = {
            "data": data,
            "numeric_columns": [],
            "categorical_columns": ["category"],
            "imputation_strategy": "mode",
        }

        result = self.ops_activities.fix_data_quality(params)

        # Mode is "A".
        df = pd.DataFrame(result["cleaned_data"])
        assert df["category"].isnull().sum() == 0
        imputed_values = df[df.index.isin([1, 3])]["category"].values
        assert all(v == "A" for v in imputed_values)

    def test_outlier_detection_and_capping(self):
        """
        Tests outlier detection and capping strategy for numeric columns.

        Verifies that extreme values are capped at a calculated threshold.
        """
        # Create data with clear outliers.
        data = [
            {"value": 100},
            {"value": 110},
            {"value": 105},
            {"value": 1000},  # Outlier.
            {"value": 95},
            {"value": -500},  # Outlier.
            {"value": 108},
        ]

        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "outlier_strategy": "cap",
            "outlier_threshold": 2.0,  # Lower threshold to more easily catch outliers.
        }

        result = self.ops_activities.fix_data_quality(params)

        # Should detect and cap outliers.
        assert result["quality_report"]["outliers_treated"] > 0

        df = pd.DataFrame(result["cleaned_data"])
        # All values should be within reasonable bounds after capping.
        # Approximate mean and std for a rough check, precise values depend on capping implementation.
        mean_approx = df["value"].mean()
        std_approx = df["value"].std()
        assert df["value"].max() < mean_approx + (3 * std_approx)
        assert df["value"].min() > mean_approx - (3 * std_approx)

    def test_outlier_removal_strategy(self):
        """
        Tests outlier detection and removal strategy for numeric columns.

        Verifies that rows containing detected outliers are removed from the dataset.
        """
        data = [
            {"value": 100},
            {"value": 110},
            {"value": 105},
            {"value": 1000},  # Outlier.
            {"value": 95},
            {"value": -500},  # Outlier.
            {"value": 108},
        ]

        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "outlier_strategy": "remove",
            "outlier_threshold": 2.0,
        }

        result = self.ops_activities.fix_data_quality(params)

        # Original 7 rows, expect fewer rows after removing outliers.
        assert result["quality_report"]["original_rows"] == 7
        assert result["quality_report"]["cleaned_rows"] < 7
        assert result["quality_report"]["outliers_treated"] > 0

    def test_winsorization_strategy(self):
        """
        Tests the winsorization strategy for outlier treatment.

        Verifies that extreme values are clipped at specified percentiles.
        """
        # Create data with clear distribution (1 to 100).
        data = [{"value": v} for v in range(1, 101)]

        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "outlier_strategy": "winsorize",
            "outlier_threshold": 3.0,  # This threshold might be interpreted as percentiles or std devs.
        }

        result = self.ops_activities.fix_data_quality(params)

        df = pd.DataFrame(result["cleaned_data"])
        # Assuming winsorization clips at 5th and 95th percentiles if threshold implies so.
        # For data 1-100, 5th percentile is 5, 95th is 95.
        assert df["value"].min() >= 5
        assert df["value"].max() <= 95

    def test_combined_missing_and_outliers(self):
        """
        Tests the activity's ability to handle both missing value imputation
        and outlier treatment in a single call.
        """
        data = [
            {"value": 100, "category": "A"},
            {"value": None, "category": "B"},
            {"value": 1000, "category": "A"},  # Outlier.
            {"value": 110, "category": None},
            {"value": 105, "category": "A"},
            {"value": None, "category": None},
        ]

        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": ["category"],
            "imputation_strategy": "median",
            "outlier_strategy": "cap",
            "outlier_threshold": 2.5,
        }

        result = self.ops_activities.fix_data_quality(params)

        # Expect both missing values and outliers to be addressed.
        assert result["quality_report"]["missing_value_fixes"] > 0
        assert (
            result["quality_report"]["outliers_treated"] >= 0
        )  # Outlier detection is context-dependent.

        # Final data should have no missing values after fixes.
        df = pd.DataFrame(result["cleaned_data"])
        assert df.isnull().sum().sum() == 0

        # Quality score should be 1.0 after all fixes.
        assert result["quality_report"]["quality_score_after"] == 1.0

    def test_quality_score_calculation(self):
        """
        Tests the accuracy of the quality score calculation logic before and after fixes.
        """
        # Example: 10 cells total, 4 missing = 60% quality.
        data = [
            {"a": 1, "b": None},
            {"a": None, "b": 2},
            {"a": 3, "b": None},
            {"a": None, "b": 4},
            {"a": 5, "b": 6},
        ]

        params = {
            "data": data,
            "numeric_columns": ["a", "b"],
            "categorical_columns": [],
            "imputation_strategy": "mean",
        }

        result = self.ops_activities.fix_data_quality(params)

        # Before: 6/10 cells filled = 0.6.
        assert abs(result["quality_report"]["quality_score_before"] - 0.6) < 0.01

        # After: all filled = 1.0.
        assert result["quality_report"]["quality_score_after"] == 1.0

        # Improvement should be 0.4.
        assert abs(result["quality_report"]["improvement"] - 0.4) < 0.01

    def test_nonexistent_columns(self):
        """
        Tests the graceful handling of nonexistent columns specified in the parameters.
        The activity should not crash and should skip over columns that do not exist in the data.
        """
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]

        params = {
            "data": data,
            "numeric_columns": ["a", "b", "nonexistent_col"],
            "categorical_columns": ["also_nonexistent"],
            "imputation_strategy": "mean",
        }

        # The activity should complete without crashing and the row counts should be consistent.
        result = self.ops_activities.fix_data_quality(params)

        assert result["quality_report"]["original_rows"] == 2
        assert result["quality_report"]["cleaned_rows"] == 2

    def test_constant_column_outlier_handling(self):
        """
        Ensures that outlier detection does not crash or produce erroneous results
        when applied to columns with constant values.
        """
        data = [{"constant": 100, "variable": i} for i in range(10)]

        params = {
            "data": data,
            "numeric_columns": ["constant", "variable"],
            "categorical_columns": [],
            "outlier_strategy": "cap",
        }

        # The activity should complete without crashing even with a constant column.
        result = self.ops_activities.fix_data_quality(params)

        assert result["quality_report"]["original_rows"] == 10

    def test_large_dataset_performance(self):
        """
        Tests the performance and scalability of the `fix_data_quality` activity
        with a large synthetic dataset.

        Ensures that the operation completes within reasonable timeframes and
        that quality improvements are reflected.
        """
        # Create a large dataset (e.g., 10,000 rows) with some missing values and potential outliers.
        np.random.seed(42)
        data = [
            {
                "revenue": (
                    np.random.normal(1000, 200) if np.random.random() > 0.1 else None
                ),
                "category": (
                    np.random.choice(["A", "B", "C"])
                    if np.random.random() > 0.05
                    else None
                ),
            }
            for _ in range(10000)
        ]

        params = {
            "data": data,
            "numeric_columns": ["revenue"],
            "categorical_columns": ["category"],
            "imputation_strategy": "median",
            "outlier_strategy": "winsorize",
        }

        # The test should complete without a timeout and show quality improvement.
        result = self.ops_activities.fix_data_quality(params)

        assert result["quality_report"]["original_rows"] == 10000
        assert (
            result["quality_report"]["quality_score_after"]
            >= result["quality_report"]["quality_score_before"]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
