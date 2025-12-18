"""
Tests for Data Quality Rules Engine.
"""
import pytest
import pandas as pd
import numpy as np

from voyant.core.quality_rules import (
    NullCheck, RangeCheck, UniqueCheck, QualityEngine, ValidationResult
)

@pytest.fixture
def clean_df():
    return pd.DataFrame({
        "id": [1, 2, 3, 4, 5],
        "score": [10.0, 20.0, 30.0, 40.0, 50.0],
        "category": ["A", "B", "C", "A", "B"]
    })

@pytest.fixture
def dirty_df():
    return pd.DataFrame({
        "id": [1, 2, 2, 4, 5], # Duplicate ID 2
        "score": [10.0, None, 150.0, -10.0, 50.0], # Null, Out of range (suppose 0-100)
        "category": ["A", None, "C", "A", "B"]
    })

def test_null_check(clean_df, dirty_df):
    # Should pass
    rule = NullCheck("score", max_null_pct=0.0)
    assert rule.check(clean_df).passed
    
    # Should fail (1/5 = 20% > 0%)
    assert not rule.check(dirty_df).passed
    
    # Should pass with higher threshold
    rule_lax = NullCheck("score", max_null_pct=0.25)
    assert rule_lax.check(dirty_df).passed

def test_range_check(clean_df, dirty_df):
    rule = RangeCheck("score", min_val=0, max_val=100)
    
    # Clean check
    assert rule.check(clean_df).passed
    
    # Dirty check: 150.0 > 100, -10.0 < 0
    res = rule.check(dirty_df)
    assert not res.passed
    # 2 failures (150 and -10). None is ignored by check.
    assert res.details["failures"] == 2

def test_unique_check(clean_df, dirty_df):
    rule = UniqueCheck("id")
    
    assert rule.check(clean_df).passed
    
    res = rule.check(dirty_df)
    assert not res.passed
    assert res.details["duplicates"] == 1 # one duplicate set (value 2 appear twice)

def test_quality_engine(clean_df, dirty_df):
    rules = [
        UniqueCheck("id"),
        NullCheck("score"),
        RangeCheck("score", 0, 100)
    ]
    engine = QualityEngine(rules)
    
    # Clean run
    report_clean = engine.validate(clean_df)
    assert report_clean["is_valid"]
    assert report_clean["passed"] == 3
    
    # Dirty run
    report_dirty = engine.validate(dirty_df)
    assert not report_dirty["is_valid"]
    assert report_dirty["failed"] == 3 # All 3 fail
    assert len(report_dirty["results"]) == 3

def test_missing_column(clean_df):
    rule = NullCheck("non_existent")
    res = rule.check(clean_df)
    assert not res.passed
    assert "error" in res.details
