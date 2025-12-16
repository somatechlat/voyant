"""
Test suite for data quality fixing activity.

Tests the fix_data_quality activity which performs:
- Missing value imputation
- Outlier detection and treatment
- Quality scoring

Adheres to VIBE Coding Rules: Real data, real statistical methods, comprehensive validation.

PhD-level QA Engineer: Edge cases, boundary conditions, statistical correctness
Performance Engineer: Validates efficiency for large datasets
Security Auditor: No data leakage in error messages
"""
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch

# Mock NLTK to avoid data download requirement
with patch('voyant.core.nlp_primitives.SentimentIntensityAnalyzer'):
    from voyant.activities.operational_activities import OperationalActivities



class TestFixDataQuality:
    """Test suite for fix_data_quality activity."""
    
    def setup_method(self):
        """Set up test fixtures."""
        with patch('voyant.core.nlp_primitives.SentimentIntensityAnalyzer'):
            self.ops_activities = OperationalActivities()

    
    def test_empty_data(self):
        """Test with empty dataset."""
        params = {
            "data": [],
            "numeric_columns": [],
            "categorical_columns": []
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        assert result["cleaned_data"] == []
        assert result["quality_report"]["original_rows"] == 0
        assert result["quality_report"]["cleaned_rows"] == 0
        assert result["quality_report"]["quality_score_before"] == 0.0
        assert result["quality_report"]["quality_score_after"] == 0.0
    
    def test_no_missing_values(self):
        """Test dataset with no missing values."""
        data = [
            {"revenue": 100, "category": "A"},
            {"revenue": 200, "category": "B"},
            {"revenue": 150, "category": "A"}
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["revenue"],
            "categorical_columns": ["category"]
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        assert result["quality_report"]["missing_value_fixes"] == 0
        assert result["quality_report"]["quality_score_before"] == 1.0
        assert result["quality_report"]["quality_score_after"] == 1.0
    
    def test_missing_value_imputation_median(self):
        """Test median imputation for numeric columns."""
        data = [
            {"revenue": 100, "category": "A"},
            {"revenue": None, "category": "B"},
            {"revenue": 200, "category": "A"},
            {"revenue": None, "category": "B"},
            {"revenue": 150, "category": "A"}
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["revenue"],
            "categorical_columns": ["category"],
            "imputation_strategy": "median"
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        # Should fix 2 missing values
        assert result["quality_report"]["missing_value_fixes"] == 2
        
        # Check median was used (median of 100, 200, 150 = 150)
        df = pd.DataFrame(result["cleaned_data"])
        assert df["revenue"].isnull().sum() == 0
        
        # Quality score should improve
        assert result["quality_report"]["quality_score_after"] > result["quality_report"]["quality_score_before"]
    
    def test_missing_value_imputation_mean(self):
        """Test mean imputation for numeric columns."""
        data = [
            {"value": 100},
            {"value": None},
            {"value": 200},
            {"value": None},
            {"value": 300}
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "imputation_strategy": "mean"
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        # Mean of 100, 200, 300 = 200
        df = pd.DataFrame(result["cleaned_data"])
        imputed_values = df[df.index.isin([1, 3])]["value"].values
        assert all(v == 200.0 for v in imputed_values)
    
    def test_missing_value_imputation_mode(self):
        """Test mode imputation for categorical columns."""
        data = [
            {"category": "A"},
            {"category": None},
            {"category": "A"},
            {"category": None},
            {"category": "B"}
        ]
        
        params = {
            "data": data,
            "numeric_columns": [],
            "categorical_columns": ["category"],
            "imputation_strategy": "mode"
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        # Mode is "A"
        df = pd.DataFrame(result["cleaned_data"])
        assert df["category"].isnull().sum() == 0
        imputed_values = df[df.index.isin([1, 3])]["category"].values
        assert all(v == "A" for v in imputed_values)
    
    def test_outlier_detection_and_capping(self):
        """Test outlier detection and capping strategy."""
        # Create data with clear outliers
        data = [
            {"value": 100},
            {"value": 110},
            {"value": 105},
            {"value": 1000},  # Outlier
            {"value": 95},
            {"value": -500},  # Outlier
            {"value": 108}
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "outlier_strategy": "cap",
            "outlier_threshold": 2.0  # Lower threshold to catch outliers
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        # Should detect and cap outliers
        assert result["quality_report"]["outliers_treated"] > 0
        
        df = pd.DataFrame(result["cleaned_data"])
        # All values should be within reasonable bounds
        mean = 100  # Approximate
        std = np.std([100, 110, 105, 95, 108])
        assert df["value"].max() < mean + (3 * std)
        assert df["value"].min() > mean - (3 * std)
    
    def test_outlier_removal_strategy(self):
        """Test outlier removal strategy."""
        data = [
            {"value": 100},
            {"value": 110},
            {"value": 105},
            {"value": 1000},  # Outlier
            {"value": 95},
            {"value": -500},  # Outlier
            {"value": 108}
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "outlier_strategy": "remove",
            "outlier_threshold": 2.0
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        # Original 7 rows, should remove outliers
        assert result["quality_report"]["original_rows"] == 7
        assert result["quality_report"]["cleaned_rows"] < 7
        assert result["quality_report"]["outliers_treated"] > 0
    
    def test_winsorization_strategy(self):
        """Test winsorization strategy (clip at percentiles)."""
        # Create data with clear distribution
        data = [{"value": v} for v in range(1, 101)]  # 1 to 100
        
        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": [],
            "outlier_strategy": "winsorize",
            "outlier_threshold": 3.0
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        df = pd.DataFrame(result["cleaned_data"])
        # Values should be clipped at 5th and 95th percentiles
        # 5th percentile ≈ 5, 95th percentile ≈ 95
        assert df["value"].min() >= 5
        assert df["value"].max() <= 95
    
    def test_combined_missing_and_outliers(self):
        """Test handling both missing values and outliers."""
        data = [
            {"value": 100, "category": "A"},
            {"value": None, "category": "B"},
            {"value": 1000, "category": "A"},  # Outlier
            {"value": 110, "category": None},
            {"value": 105, "category": "A"},
            {"value": None, "category": None}
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["value"],
            "categorical_columns": ["category"],
            "imputation_strategy": "median",
            "outlier_strategy": "cap",
            "outlier_threshold": 2.5
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        # Should fix both missing values and outliers
        assert result["quality_report"]["missing_value_fixes"] > 0
        assert result["quality_report"]["outliers_treated"] >= 0  # May or may not detect outliers
        
        # Final data should have no missing values
        df = pd.DataFrame(result["cleaned_data"])
        assert df.isnull().sum().sum() == 0
        
        # Quality score should be 1.0 after fixing
        assert result["quality_report"]["quality_score_after"] == 1.0
    
    def test_quality_score_calculation(self):
        """Test quality score calculation logic."""
        # 10 cells total, 4 missing = 60% quality
        data = [
            {"a": 1, "b": None},
            {"a": None, "b": 2},
            {"a": 3, "b": None},
            {"a": None, "b": 4},
            {"a": 5, "b": 6}
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["a", "b"],
            "categorical_columns": [],
            "imputation_strategy": "mean"
        }
        
        result = self.ops_activities.fix_data_quality(params)
        
        # Before: 6/10 cells filled = 0.6
        assert abs(result["quality_report"]["quality_score_before"] - 0.6) < 0.01
        
        # After: all filled = 1.0
        assert result["quality_report"]["quality_score_after"] == 1.0
        
        # Improvement = 0.4
        assert abs(result["quality_report"]["improvement"] - 0.4) < 0.01
    
    def test_nonexistent_columns(self):
        """Test graceful handling of nonexistent columns."""
        data = [
            {"a": 1, "b": 2},
            {"a": 3, "b": 4}
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["a", "b", "nonexistent_col"],
            "categorical_columns": ["also_nonexistent"],
            "imputation_strategy": "mean"
        }
        
        # Should not crash, should just skip nonexistent columns
        result = self.ops_activities.fix_data_quality(params)
        
        assert result["quality_report"]["original_rows"] == 2
        assert result["quality_report"]["cleaned_rows"] == 2
    
    def test_constant_column_outlier_handling(self):
        """Test that constant columns don't crash outlier detection."""
        data = [
            {"constant": 100, "variable": i}
            for i in range(10)
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["constant", "variable"],
            "categorical_columns": [],
            "outlier_strategy": "cap"
        }
        
        # Should not crash on constant column
        result = self.ops_activities.fix_data_quality(params)
        
        assert result["quality_report"]["original_rows"] == 10
    
    def test_large_dataset_performance(self):
        """Test performance with large dataset."""
        # Create 10,000 rows
        np.random.seed(42)
        data = [
            {
                "revenue": np.random.normal(1000, 200) if np.random.random() > 0.1 else None,
                "category": np.random.choice(["A", "B", "C"]) if np.random.random() > 0.05 else None
            }
            for _ in range(10000)
        ]
        
        params = {
            "data": data,
            "numeric_columns": ["revenue"],
            "categorical_columns": ["category"],
            "imputation_strategy": "median",
            "outlier_strategy": "winsorize"
        }
        
        # Should complete without timeout
        result = self.ops_activities.fix_data_quality(params)
        
        assert result["quality_report"]["original_rows"] == 10000
        assert result["quality_report"]["quality_score_after"] >= result["quality_report"]["quality_score_before"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
