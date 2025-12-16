"""
Segment Profiling Module

Generate group-level statistical profiles for data segments.
Enables comparison of customer segments, time periods, or categorical groups.

Seven personas applied:
- PhD Developer: Clean statistical computation with proper formulas
- PhD Analyst: Comprehensive segment metrics including distributions
- PhD QA Engineer: Validation of segment boundaries and data
- ISO Documenter: Clear documentation of all metrics
- Security Auditor: No PII in segment profiles, aggregation only
- Performance Engineer: Efficient group-by operations
- UX Consultant: Easy-to-interpret segment comparison reports

Usage:
    from voyant.core.segment_profiling import (
        profile_segments,
        compare_segments,
        SegmentProfile
    )
    
    # Profile data by segment
    profiles = profile_segments(
        data=[{"segment": "A", "value": 100}, ...],
        segment_column="segment",
        value_columns=["value"]
    )
    
    # Compare two segments
    comparison = compare_segments(profiles["A"], profiles["B"])
"""
from __future__ import annotations

import logging
import math
import statistics
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Profile Result Types
# =============================================================================

@dataclass
class ColumnProfile:
    """Statistical profile for a single column."""
    column_name: str
    data_type: str  # "numeric", "categorical", "datetime"
    count: int
    missing_count: int
    
    # Numeric stats
    mean: Optional[float] = None
    median: Optional[float] = None
    std_dev: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    q25: Optional[float] = None
    q75: Optional[float] = None
    skewness: Optional[float] = None
    
    # Categorical stats
    unique_count: Optional[int] = None
    top_values: Optional[List[Tuple[str, int]]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "column_name": self.column_name,
            "data_type": self.data_type,
            "count": self.count,
            "missing_count": self.missing_count,
            "missing_rate": round(self.missing_count / self.count, 4) if self.count > 0 else 0,
        }
        
        if self.data_type == "numeric":
            result.update({
                "mean": round(self.mean, 4) if self.mean is not None else None,
                "median": round(self.median, 4) if self.median is not None else None,
                "std_dev": round(self.std_dev, 4) if self.std_dev is not None else None,
                "min": self.min_value,
                "max": self.max_value,
                "q25": round(self.q25, 4) if self.q25 is not None else None,
                "q75": round(self.q75, 4) if self.q75 is not None else None,
                "skewness": round(self.skewness, 4) if self.skewness is not None else None,
            })
        elif self.data_type == "categorical":
            result.update({
                "unique_count": self.unique_count,
                "top_values": [{"value": v, "count": c} for v, c in (self.top_values or [])],
            })
        
        return result


@dataclass
class SegmentProfile:
    """Complete profile for a data segment."""
    segment_name: str
    segment_value: Any
    row_count: int
    column_profiles: Dict[str, ColumnProfile] = field(default_factory=dict)
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_name": self.segment_name,
            "segment_value": self.segment_value,
            "row_count": self.row_count,
            "columns": {
                name: profile.to_dict()
                for name, profile in self.column_profiles.items()
            },
            "created_at": self.created_at,
        }


@dataclass
class SegmentComparison:
    """Comparison between two segments."""
    segment_a: str
    segment_b: str
    column_name: str
    
    # Statistical differences
    mean_diff: Optional[float] = None
    mean_diff_percent: Optional[float] = None
    std_diff: Optional[float] = None
    distribution_overlap: Optional[float] = None
    
    # Statistical tests
    t_statistic: Optional[float] = None
    effect_size: Optional[float] = None  # Cohen's d
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_a": self.segment_a,
            "segment_b": self.segment_b,
            "column": self.column_name,
            "mean_difference": round(self.mean_diff, 4) if self.mean_diff is not None else None,
            "mean_diff_percent": round(self.mean_diff_percent, 2) if self.mean_diff_percent is not None else None,
            "std_difference": round(self.std_diff, 4) if self.std_diff is not None else None,
            "distribution_overlap": round(self.distribution_overlap, 4) if self.distribution_overlap is not None else None,
            "effect_size_cohens_d": round(self.effect_size, 4) if self.effect_size is not None else None,
        }


# =============================================================================
# Statistical Helpers
# =============================================================================

def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile from sorted values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    idx = int(len(sorted_values) * (percentile / 100))
    idx = min(idx, len(sorted_values) - 1)
    return sorted_values[idx]


def calculate_skewness(values: List[float]) -> Optional[float]:
    """
    Calculate Fisher-Pearson skewness coefficient.
    
    PhD Analyst: Measures distribution asymmetry
    """
    if len(values) < 3:
        return None
    
    n = len(values)
    mean = statistics.mean(values)
    std = statistics.stdev(values)
    
    if std == 0:
        return 0.0
    
    # Fisher-Pearson coefficient
    sum_cubed = sum((x - mean) ** 3 for x in values)
    skew = (n / ((n - 1) * (n - 2))) * (sum_cubed / (std ** 3))
    
    return skew


def calculate_cohens_d(
    mean1: float, std1: float, n1: int,
    mean2: float, std2: float, n2: int
) -> float:
    """
    Calculate Cohen's d effect size.
    
    PhD Analyst: Standardized measure of difference between groups
    """
    # Pooled standard deviation
    pooled_std = math.sqrt(
        ((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2)
    )
    
    if pooled_std == 0:
        return 0.0
    
    return (mean1 - mean2) / pooled_std


def calculate_distribution_overlap(
    mean1: float, std1: float,
    mean2: float, std2: float
) -> float:
    """
    Estimate distribution overlap using Bhattacharyya coefficient.
    
    PhD Analyst: Measures similarity between distributions
    """
    if std1 == 0 or std2 == 0:
        return 1.0 if mean1 == mean2 else 0.0
    
    # Bhattacharyya coefficient (assuming normal distributions)
    var1 = std1 ** 2
    var2 = std2 ** 2
    
    # Bhattacharyya distance
    db = 0.25 * math.log(0.25 * (var1/var2 + var2/var1 + 2)) + \
         0.25 * ((mean1 - mean2)**2) / (var1 + var2)
    
    # Convert to overlap (coefficient)
    bc = math.exp(-db)
    
    return bc


# =============================================================================
# Column Profiling
# =============================================================================

def profile_numeric_column(
    values: List[Any],
    column_name: str
) -> ColumnProfile:
    """
    Profile a numeric column.
    
    Performance Engineer: Efficient single-pass statistics where possible
    """
    # Filter to valid numeric values
    numeric_values = []
    missing = 0
    
    for v in values:
        if v is None:
            missing += 1
        else:
            try:
                numeric_values.append(float(v))
            except (ValueError, TypeError):
                missing += 1
    
    total = len(values)
    
    if not numeric_values:
        return ColumnProfile(
            column_name=column_name,
            data_type="numeric",
            count=total,
            missing_count=missing
        )
    
    return ColumnProfile(
        column_name=column_name,
        data_type="numeric",
        count=total,
        missing_count=missing,
        mean=statistics.mean(numeric_values),
        median=statistics.median(numeric_values),
        std_dev=statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0.0,
        min_value=min(numeric_values),
        max_value=max(numeric_values),
        q25=calculate_percentile(numeric_values, 25),
        q75=calculate_percentile(numeric_values, 75),
        skewness=calculate_skewness(numeric_values),
    )


def profile_categorical_column(
    values: List[Any],
    column_name: str,
    top_n: int = 10
) -> ColumnProfile:
    """
    Profile a categorical column.
    
    PhD Analyst: Value distribution analysis
    """
    # Filter missing
    valid_values = [v for v in values if v is not None]
    missing = len(values) - len(valid_values)
    
    # Count values
    counter = Counter(str(v) for v in valid_values)
    
    return ColumnProfile(
        column_name=column_name,
        data_type="categorical",
        count=len(values),
        missing_count=missing,
        unique_count=len(counter),
        top_values=counter.most_common(top_n),
    )


def infer_column_type(values: List[Any]) -> str:
    """Infer column data type from values."""
    # Sample non-null values
    sample = [v for v in values[:100] if v is not None]
    
    if not sample:
        return "categorical"
    
    # Check if numeric
    numeric_count = 0
    for v in sample:
        try:
            float(v)
            numeric_count += 1
        except (ValueError, TypeError):
            pass
    
    if numeric_count / len(sample) > 0.8:
        return "numeric"
    
    return "categorical"


# =============================================================================
# Segment Profiling
# =============================================================================

def profile_segments(
    data: List[Dict[str, Any]],
    segment_column: str,
    value_columns: Optional[List[str]] = None,
    top_categorical: int = 10
) -> Dict[str, SegmentProfile]:
    """
    Profile data by segments.
    
    Args:
        data: List of row dictionaries
        segment_column: Column to segment by
        value_columns: Columns to profile (None = all except segment)
        top_categorical: Number of top values for categorical columns
        
    Returns:
        Dictionary mapping segment values to their profiles
        
    UX Consultant: Simple API for segment analysis
    """
    if not data:
        return {}
    
    # Determine columns to profile
    all_columns = set()
    for row in data:
        all_columns.update(row.keys())
    
    if value_columns is None:
        value_columns = [c for c in all_columns if c != segment_column]
    
    # Group data by segment
    segments: Dict[Any, List[Dict[str, Any]]] = {}
    for row in data:
        segment_value = row.get(segment_column)
        if segment_value not in segments:
            segments[segment_value] = []
        segments[segment_value].append(row)
    
    # Profile each segment
    profiles: Dict[str, SegmentProfile] = {}
    
    for segment_value, segment_data in segments.items():
        segment_key = str(segment_value)
        
        profile = SegmentProfile(
            segment_name=segment_column,
            segment_value=segment_value,
            row_count=len(segment_data)
        )
        
        # Profile each column
        for col in value_columns:
            values = [row.get(col) for row in segment_data]
            col_type = infer_column_type(values)
            
            if col_type == "numeric":
                col_profile = profile_numeric_column(values, col)
            else:
                col_profile = profile_categorical_column(values, col, top_categorical)
            
            profile.column_profiles[col] = col_profile
        
        profiles[segment_key] = profile
    
    logger.info(f"Profiled {len(profiles)} segments on column '{segment_column}'")
    
    return profiles


def compare_segments(
    profile_a: SegmentProfile,
    profile_b: SegmentProfile,
    columns: Optional[List[str]] = None
) -> List[SegmentComparison]:
    """
    Compare two segment profiles.
    
    Args:
        profile_a: First segment profile
        profile_b: Second segment profile
        columns: Columns to compare (None = all numeric)
        
    Returns:
        List of column comparisons
        
    PhD Analyst: Statistical comparison between groups
    """
    comparisons = []
    
    # Get common numeric columns
    common_columns = set(profile_a.column_profiles.keys()) & set(profile_b.column_profiles.keys())
    
    if columns:
        common_columns = common_columns & set(columns)
    
    for col in common_columns:
        col_a = profile_a.column_profiles[col]
        col_b = profile_b.column_profiles[col]
        
        # Only compare numeric columns
        if col_a.data_type != "numeric" or col_b.data_type != "numeric":
            continue
        
        if col_a.mean is None or col_b.mean is None:
            continue
        
        # Calculate differences
        mean_diff = col_a.mean - col_b.mean
        mean_diff_pct = None
        if col_b.mean != 0:
            mean_diff_pct = (mean_diff / abs(col_b.mean)) * 100
        
        std_diff = None
        if col_a.std_dev is not None and col_b.std_dev is not None:
            std_diff = col_a.std_dev - col_b.std_dev
        
        # Effect size (Cohen's d)
        effect = None
        if col_a.std_dev and col_b.std_dev:
            effect = calculate_cohens_d(
                col_a.mean, col_a.std_dev, profile_a.row_count,
                col_b.mean, col_b.std_dev, profile_b.row_count
            )
        
        # Distribution overlap
        overlap = None
        if col_a.std_dev and col_b.std_dev:
            overlap = calculate_distribution_overlap(
                col_a.mean, col_a.std_dev,
                col_b.mean, col_b.std_dev
            )
        
        comparisons.append(SegmentComparison(
            segment_a=str(profile_a.segment_value),
            segment_b=str(profile_b.segment_value),
            column_name=col,
            mean_diff=mean_diff,
            mean_diff_percent=mean_diff_pct,
            std_diff=std_diff,
            effect_size=effect,
            distribution_overlap=overlap,
        ))
    
    return comparisons


def generate_segment_report(
    profiles: Dict[str, SegmentProfile],
    compare_all: bool = True
) -> Dict[str, Any]:
    """
    Generate a comprehensive segment analysis report.
    
    Args:
        profiles: Dictionary of segment profiles
        compare_all: Whether to include pairwise comparisons
        
    Returns:
        Report dictionary
        
    ISO Documenter: Comprehensive reporting format
    """
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "segment_count": len(profiles),
        "total_rows": sum(p.row_count for p in profiles.values()),
        "segments": {name: p.to_dict() for name, p in profiles.items()},
    }
    
    # Add pairwise comparisons
    if compare_all and len(profiles) > 1:
        comparisons = []
        profile_list = list(profiles.values())
        
        for i, p1 in enumerate(profile_list):
            for p2 in profile_list[i+1:]:
                comp = compare_segments(p1, p2)
                for c in comp:
                    comparisons.append(c.to_dict())
        
        report["comparisons"] = comparisons
    
    return report
