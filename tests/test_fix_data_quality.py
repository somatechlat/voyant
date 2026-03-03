"""
Tests for Data Quality Fixing Activity.

Tests fix_data_quality() directly against real OperationalActivities.
No mocking. All logic runs in-process with real pandas/numpy.
"""

import numpy as np
import pandas as pd
import pytest

from apps.worker.activities.operational_activities import OperationalActivities


@pytest.fixture(scope="module")
def ops():
    """Real OperationalActivities instance — no mocking."""
    return OperationalActivities()


class TestFixDataQuality:

    def test_empty_data(self, ops):
        """Empty dataset returns zero-row report with 0.0 quality scores."""
        params = {"data": [], "numeric_columns": [], "categorical_columns": []}
        result = ops.fix_data_quality(params)
        assert result["cleaned_data"] == []
        assert result["quality_report"]["original_rows"] == 0
        assert result["quality_report"]["cleaned_rows"] == 0
        assert result["quality_report"]["quality_score_before"] == 0.0
        assert result["quality_report"]["quality_score_after"] == 0.0

    def test_no_missing_values(self, ops):
        """Dataset with no missing values keeps quality_score at 1.0."""
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
        result = ops.fix_data_quality(params)
        assert result["quality_report"]["missing_value_fixes"] == 0
        assert result["quality_report"]["quality_score_before"] == 1.0
        assert result["quality_report"]["quality_score_after"] == 1.0

    def test_missing_value_imputation_median(self, ops):
        """Median imputation fills None numeric values with column median."""
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
        result = ops.fix_data_quality(params)
        assert result["quality_report"]["missing_value_fixes"] == 2
        df = pd.DataFrame(result["cleaned_data"])
        assert df["revenue"].isnull().sum() == 0
        # median of [100, 150, 200] = 150
        assert all(val == 150.0 for val in df[df.index.isin([1, 3])]["revenue"].values)
        assert (
            result["quality_report"]["quality_score_after"]
            > result["quality_report"]["quality_score_before"]
        )

    def test_missing_value_imputation_mean(self, ops):
        """Mean imputation fills None values with column mean."""
        data = [{"value": 100}, {"value": None}, {"value": 200}, {"value": None}, {"value": 300}]
        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "imputation_strategy": "mean",
        }
        result = ops.fix_data_quality(params)
        df = pd.DataFrame(result["cleaned_data"])
        imputed_values = df[df.index.isin([1, 3])]["value"].values
        # mean of [100, 200, 300] = 200
        assert all(v == 200.0 for v in imputed_values)

    def test_missing_value_imputation_mode(self, ops):
        """Mode imputation fills None categorical values with column mode."""
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
        result = ops.fix_data_quality(params)
        df = pd.DataFrame(result["cleaned_data"])
        assert df["category"].isnull().sum() == 0
        imputed_values = df[df.index.isin([1, 3])]["category"].values
        assert all(v == "A" for v in imputed_values)

    def test_outlier_detection_and_capping(self, ops):
        """Outlier capping contains extreme values within statistical bounds."""
        data = [
            {"value": 100}, {"value": 110}, {"value": 105},
            {"value": 1000},   # outlier
            {"value": 95}, {"value": -500},  # outlier
            {"value": 108},
        ]
        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "outlier_strategy": "cap",
            "outlier_threshold": 2.0,
        }
        result = ops.fix_data_quality(params)
        assert result["quality_report"]["outliers_treated"] > 0
        df = pd.DataFrame(result["cleaned_data"])
        mean_v, std_v = df["value"].mean(), df["value"].std()
        assert df["value"].max() < mean_v + (3 * std_v)
        assert df["value"].min() > mean_v - (3 * std_v)

    def test_outlier_removal_strategy(self, ops):
        """Outlier rows are removed, reducing total row count."""
        data = [
            {"value": 100}, {"value": 110}, {"value": 105},
            {"value": 1000},  # outlier
            {"value": 95}, {"value": -500},  # outlier
            {"value": 108},
        ]
        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "outlier_strategy": "remove",
            "outlier_threshold": 2.0,
        }
        result = ops.fix_data_quality(params)
        assert result["quality_report"]["original_rows"] == 7
        assert result["quality_report"]["cleaned_rows"] < 7
        assert result["quality_report"]["outliers_treated"] > 0

    def test_winsorization_strategy(self, ops):
        """Winsorization clips extreme percentiles."""
        data = [{"value": v} for v in range(1, 101)]
        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "outlier_strategy": "winsorize",
            "outlier_threshold": 3.0,
        }
        result = ops.fix_data_quality(params)
        df = pd.DataFrame(result["cleaned_data"])
        assert df["value"].min() >= 5
        assert df["value"].max() <= 95

    def test_combined_missing_and_outliers(self, ops):
        """Both missing value imputation and outlier treatment run together."""
        data = [
            {"value": 100, "category": "A"},
            {"value": None, "category": "B"},
            {"value": 1000, "category": "A"},  # outlier
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
        result = ops.fix_data_quality(params)
        assert result["quality_report"]["missing_value_fixes"] > 0
        df = pd.DataFrame(result["cleaned_data"])
        assert df.isnull().sum().sum() == 0
        assert result["quality_report"]["quality_score_after"] == 1.0

    def test_quality_score_calculation(self, ops):
        """Quality score reflects proportion of non-null cells before and after."""
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
        result = ops.fix_data_quality(params)
        # 6/10 non-null = 0.6
        assert abs(result["quality_report"]["quality_score_before"] - 0.6) < 0.01
        assert result["quality_report"]["quality_score_after"] == 1.0
        assert abs(result["quality_report"]["improvement"] - 0.4) < 0.01

    def test_nonexistent_columns_ignored(self, ops):
        """Columns not present in data are silently skipped."""
        data = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        params = {
            "data": data,
            "numeric_columns": ["a", "b", "nonexistent_col"],
            "categorical_columns": ["also_nonexistent"],
            "imputation_strategy": "mean",
        }
        result = ops.fix_data_quality(params)
        assert result["quality_report"]["original_rows"] == 2
        assert result["quality_report"]["cleaned_rows"] == 2

    def test_constant_column_outlier_handling(self, ops):
        """Constant-value columns do not crash outlier detection."""
        data = [{"constant": 100, "variable": i} for i in range(10)]
        params = {
            "data": data,
            "numeric_columns": ["constant", "variable"],
            "categorical_columns": [],
            "outlier_strategy": "cap",
        }
        result = ops.fix_data_quality(params)
        assert result["quality_report"]["original_rows"] == 10

    def test_large_dataset_performance(self, ops):
        """10,000-row dataset completes without timeout and shows quality improvement."""
        np.random.seed(42)
        data = [
            {
                "revenue": np.random.normal(1000, 200) if np.random.random() > 0.1 else None,
                "category": (
                    np.random.choice(["A", "B", "C"]) if np.random.random() > 0.05 else None
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
        result = ops.fix_data_quality(params)
        assert result["quality_report"]["original_rows"] == 10000
        assert (
            result["quality_report"]["quality_score_after"]
            >= result["quality_report"]["quality_score_before"]
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
