"""Tests for apps.analysis.lib.cleaning_primitives."""

import pytest

from apps.analysis.lib.cleaning_primitives import DataCleaningPrimitives


@pytest.fixture
def cleaner():
    return DataCleaningPrimitives()


# ---------------------------------------------------------------------------
# clean_dataset — empty input
# ---------------------------------------------------------------------------


class TestCleanDatasetEmpty:
    def test_empty_data(self, cleaner):
        result = cleaner.clean_dataset([])
        assert result["cleaned_data"] == []
        assert result["report"]["final_row_count"] == 0


# ---------------------------------------------------------------------------
# Duplicates
# ---------------------------------------------------------------------------


class TestDuplicateRemoval:
    def test_drops_duplicates(self, cleaner):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        result = cleaner.clean_dataset(data, strategies={"duplicates": "drop"})
        assert result["report"]["duplicates_removed"] == 1
        assert result["report"]["final_row_count"] == 2

    def test_keeps_duplicates_by_default(self, cleaner):
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Alice", "age": 30},
        ]
        result = cleaner.clean_dataset(data)
        # Default strategy is "keep" for duplicates — duplicates_removed key may not be present
        assert result["report"]["final_row_count"] == 2


# ---------------------------------------------------------------------------
# Missing values
# ---------------------------------------------------------------------------


class TestMissingValues:
    def test_drop_missing(self, cleaner):
        data = [
            {"name": "Alice", "age": 30},
            {"name": None, "age": 25},
            {"name": "Bob", "age": None},
        ]
        result = cleaner.clean_dataset(data, strategies={"missing_values": "drop"})
        assert result["report"]["missing_values_after"] == 0

    def test_mean_imputation(self, cleaner):
        data = [
            {"score": 10.0},
            {"score": 20.0},
            {"score": None},
        ]
        result = cleaner.clean_dataset(data, strategies={"missing_values": "mean"})
        cleaned = result["cleaned_data"]
        assert result["report"]["missing_values_after"] == 0
        # The None should be filled with mean of 10 and 20 = 15
        scores = [r["score"] for r in cleaned]
        assert 15.0 in scores

    def test_median_imputation(self, cleaner):
        data = [
            {"score": 10.0},
            {"score": 20.0},
            {"score": 30.0},
            {"score": None},
        ]
        result = cleaner.clean_dataset(data, strategies={"missing_values": "median"})
        assert result["report"]["missing_values_after"] == 0

    def test_mode_imputation(self, cleaner):
        data = [
            {"category": "A"},
            {"category": "A"},
            {"category": "B"},
            {"category": None},
        ]
        result = cleaner.clean_dataset(data, strategies={"missing_values": "mode"})
        assert result["report"]["missing_values_after"] == 0


# ---------------------------------------------------------------------------
# String normalization
# ---------------------------------------------------------------------------


class TestStringNormalization:
    def test_normalizes_strings(self, cleaner):
        data = [
            {"name": "  Alice  "},
            {"name": "BOB"},
        ]
        result = cleaner.clean_dataset(data, strategies={"normalize_strings": True})
        cleaned = result["cleaned_data"]
        names = [r["name"] for r in cleaned]
        assert "alice" in names
        assert "bob" in names

    def test_no_normalization_by_default(self, cleaner):
        data = [{"name": "  Alice  "}]
        result = cleaner.clean_dataset(data)
        assert result["cleaned_data"][0]["name"] == "  Alice  "


# ---------------------------------------------------------------------------
# Outliers
# ---------------------------------------------------------------------------


class TestOutlierHandling:
    def test_cap_outliers(self, cleaner):
        data = [{"val": i} for i in range(100)] + [{"val": 10000}]
        result = cleaner.clean_dataset(
            data,
            strategies={"outliers": "cap", "outlier_threshold": 3.0},
        )
        assert result["report"]["outliers_treated"] >= 1

    def test_remove_outliers(self, cleaner):
        data = [{"val": i} for i in range(100)] + [{"val": 10000}]
        result = cleaner.clean_dataset(
            data,
            strategies={"outliers": "remove", "outlier_threshold": 3.0},
        )
        assert result["report"]["outliers_treated"] >= 1
        assert result["report"]["final_row_count"] < len(data)

    def test_winsorize_outliers(self, cleaner):
        data = [{"val": i} for i in range(100)] + [{"val": 10000}]
        result = cleaner.clean_dataset(
            data,
            strategies={"outliers": "winsorize"},
        )
        assert result["report"]["outliers_treated"] >= 1

    def test_no_outlier_treatment_by_default(self, cleaner):
        data = [{"val": i} for i in range(100)] + [{"val": 10000}]
        result = cleaner.clean_dataset(data)
        assert result["report"]["outliers_treated"] == 0


# ---------------------------------------------------------------------------
# Report structure
# ---------------------------------------------------------------------------


class TestReportStructure:
    def test_report_has_all_keys(self, cleaner):
        data = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        result = cleaner.clean_dataset(data, strategies={"duplicates": "drop"})
        report = result["report"]
        assert "duplicates_removed" in report
        assert "missing_values_before" in report
        assert "missing_values_after" in report
        assert "outliers_treated" in report
        assert "final_row_count" in report
        assert "removed_rows" in report
