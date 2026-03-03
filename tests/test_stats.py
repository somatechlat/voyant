"""
Tests for StatisticalEngine.

Tests pure Python logic (validation, error handling) against real data.
R-dependent tests (normality, ANOVA) live in tests/integration/
where a real Rserve connection is available.
"""

import pandas as pd
import pytest

from apps.analysis.lib.stats import StatisticalEngine
from apps.core.lib.errors import ValidationError


def test_t_test_validation_three_groups():
    """t-test requires exactly 2 groups — 3 groups must raise ValidationError."""
    stats = StatisticalEngine()
    df = pd.DataFrame({"val": [1, 2, 3], "group": ["A", "B", "C"]})

    with pytest.raises(ValidationError):
        stats.t_test(df, "group", "val")


def test_t_test_validation_empty_dataframe():
    """t-test on empty dataframe must raise ValidationError."""
    stats = StatisticalEngine()
    df = pd.DataFrame({"val": [], "group": []})

    with pytest.raises((ValidationError, ValueError)):
        stats.t_test(df, "group", "val")


def test_statistical_engine_instantiates():
    """StatisticalEngine must construct without R connection (R is optional)."""
    engine = StatisticalEngine()
    assert engine is not None
