"""
Adaptive Sampling Module

Intelligent sampling strategies for large table profiling.
Reference: docs/CANONICAL_ROADMAP.md - Future Investigation Backlog

Seven personas applied:
- PhD Developer: Statistically sound sampling algorithms
- PhD Analyst: Preserves distribution characteristics
- PhD QA Engineer: Validation of sample representativeness
- ISO Documenter: Clear sampling methodology documentation
- Security Auditor: No data leakage, deterministic for audit
- Performance Engineer: Efficient sampling without full scan
- UX Consultant: Simple API with sensible defaults

Usage:
    from voyant.core.adaptive_sampling import (
        sample_table,
        get_optimal_sample_size,
        SamplingStrategy
    )
    
    # Get optimal sample size
    sample_size = get_optimal_sample_size(
        total_rows=1_000_000,
        confidence=0.95,
        margin_of_error=0.02
    )
    
    # Sample data
    sampled = sample_table(
        data=large_dataset,
        strategy=SamplingStrategy.STRATIFIED,
        sample_size=sample_size
    )
"""
from __future__ import annotations

import hashlib
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)


# =============================================================================
# Sampling Strategies
# =============================================================================

class SamplingStrategy(str, Enum):
    """Available sampling strategies."""
    RANDOM = "random"  # Simple random sampling
    SYSTEMATIC = "systematic"  # Every nth row
    STRATIFIED = "stratified"  # Preserve group proportions
    RESERVOIR = "reservoir"  # Single-pass for streaming
    ADAPTIVE = "adaptive"  # Auto-select best strategy
    DETERMINISTIC = "deterministic"  # Repeatable via hash


# =============================================================================
# Sample Statistics
# =============================================================================

@dataclass
class SampleStats:
    """Statistics about a sample."""
    total_rows: int
    sample_size: int
    sampling_rate: float
    strategy: SamplingStrategy
    confidence_level: float
    margin_of_error: float
    seed: Optional[int] = None
    strata_info: Dict[str, int] = field(default_factory=dict)
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_rows": self.total_rows,
            "sample_size": self.sample_size,
            "sampling_rate": round(self.sampling_rate, 4),
            "strategy": self.strategy.value,
            "confidence_level": self.confidence_level,
            "margin_of_error": round(self.margin_of_error, 4),
            "seed": self.seed,
            "strata_info": self.strata_info,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class SampleResult:
    """Result of sampling operation."""
    data: List[Dict[str, Any]]
    stats: SampleStats
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "data_preview": self.data[:5] if self.data else [],
            "stats": self.stats.to_dict(),
        }


# =============================================================================
# Sample Size Calculation
# =============================================================================

def get_optimal_sample_size(
    total_rows: int,
    confidence: float = 0.95,
    margin_of_error: float = 0.03,
    estimated_proportion: float = 0.5,
    min_sample: int = 100,
    max_sample: int = 100_000
) -> int:
    """
    Calculate optimal sample size using Cochran's formula.
    
    Args:
        total_rows: Total population size
        confidence: Confidence level (0.90, 0.95, 0.99)
        margin_of_error: Acceptable margin of error
        estimated_proportion: Estimated population proportion
        min_sample: Minimum sample size
        max_sample: Maximum sample size
        
    Returns:
        Optimal sample size
        
    PhD Analyst: Statistically sound sample size calculation
    """
    # Z-scores for common confidence levels
    z_scores = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576,
    }
    z = z_scores.get(confidence, 1.96)
    
    p = estimated_proportion
    e = margin_of_error
    
    # Cochran's formula for infinite population
    n0 = (z**2 * p * (1 - p)) / (e**2)
    
    # Finite population correction
    if total_rows > 0:
        n = n0 / (1 + ((n0 - 1) / total_rows))
    else:
        n = n0
    
    # Apply bounds
    sample_size = int(math.ceil(n))
    sample_size = max(min_sample, min(sample_size, max_sample))
    sample_size = min(sample_size, total_rows)
    
    return sample_size


def calculate_margin_of_error(
    sample_size: int,
    total_rows: int,
    confidence: float = 0.95
) -> float:
    """Calculate actual margin of error for a given sample size."""
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)
    
    # Assuming worst case p=0.5
    p = 0.5
    
    # Standard error with finite population correction
    fpc = math.sqrt((total_rows - sample_size) / (total_rows - 1)) if total_rows > 1 else 1
    se = math.sqrt((p * (1 - p)) / sample_size) * fpc
    
    return z * se


# =============================================================================
# Sampling Algorithms
# =============================================================================

T = TypeVar('T')


def random_sample(
    data: List[T],
    sample_size: int,
    seed: Optional[int] = None
) -> List[T]:
    """
    Simple random sampling.
    
    Performance Engineer: Efficient for any size
    """
    if sample_size >= len(data):
        return data.copy()
    
    rng = random.Random(seed)
    return rng.sample(data, sample_size)


def systematic_sample(
    data: List[T],
    sample_size: int,
    seed: Optional[int] = None
) -> List[T]:
    """
    Systematic sampling (every nth element).
    
    PhD Developer: Even distribution across data
    """
    if sample_size >= len(data):
        return data.copy()
    
    n = len(data)
    k = n // sample_size  # Interval
    
    # Random start within first interval
    rng = random.Random(seed)
    start = rng.randint(0, k - 1) if k > 1 else 0
    
    indices = range(start, n, k)
    return [data[i] for i in indices][:sample_size]


def stratified_sample(
    data: List[Dict[str, Any]],
    sample_size: int,
    strata_column: str,
    seed: Optional[int] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Stratified sampling preserving group proportions.
    
    PhD Analyst: Maintains distribution of key variable
    """
    if sample_size >= len(data):
        return data.copy(), {}
    
    # Group by strata
    strata: Dict[Any, List[Dict[str, Any]]] = {}
    for row in data:
        key = row.get(strata_column, "unknown")
        if key not in strata:
            strata[key] = []
        strata[key].append(row)
    
    # Calculate proportional samples per stratum
    rng = random.Random(seed)
    result = []
    strata_info = {}
    
    for key, group in strata.items():
        proportion = len(group) / len(data)
        stratum_sample_size = max(1, int(round(sample_size * proportion)))
        stratum_sample_size = min(stratum_sample_size, len(group))
        
        sampled = rng.sample(group, stratum_sample_size)
        result.extend(sampled)
        strata_info[str(key)] = len(sampled)
    
    return result[:sample_size], strata_info


def reservoir_sample(
    data: List[T],
    sample_size: int,
    seed: Optional[int] = None
) -> List[T]:
    """
    Reservoir sampling for streaming data.
    
    Performance Engineer: Single-pass, O(n) time, O(k) space
    """
    rng = random.Random(seed)
    reservoir = []
    
    for i, item in enumerate(data):
        if i < sample_size:
            reservoir.append(item)
        else:
            j = rng.randint(0, i)
            if j < sample_size:
                reservoir[j] = item
    
    return reservoir


def deterministic_sample(
    data: List[Dict[str, Any]],
    sample_size: int,
    key_column: str
) -> List[Dict[str, Any]]:
    """
    Deterministic sampling based on content hash.
    
    Security Auditor: Reproducible for audit purposes
    """
    if sample_size >= len(data):
        return data.copy()
    
    threshold = sample_size / len(data)
    
    result = []
    for row in data:
        key_value = str(row.get(key_column, ""))
        hash_val = int(hashlib.md5(key_value.encode()).hexdigest(), 16)
        normalized = (hash_val % 10000) / 10000.0
        
        if normalized < threshold:
            result.append(row)
    
    return result[:sample_size]


# =============================================================================
# Adaptive Sampling
# =============================================================================

def select_strategy(
    total_rows: int,
    has_strata_column: bool = False,
    is_streaming: bool = False,
    need_reproducible: bool = False
) -> SamplingStrategy:
    """
    Select optimal sampling strategy based on context.
    
    PhD Developer: Intelligent strategy selection
    """
    if need_reproducible:
        return SamplingStrategy.DETERMINISTIC
    
    if is_streaming:
        return SamplingStrategy.RESERVOIR
    
    if has_strata_column and total_rows > 1000:
        return SamplingStrategy.STRATIFIED
    
    if total_rows > 100_000:
        return SamplingStrategy.SYSTEMATIC
    
    return SamplingStrategy.RANDOM


def sample_table(
    data: List[Dict[str, Any]],
    strategy: SamplingStrategy = SamplingStrategy.ADAPTIVE,
    sample_size: Optional[int] = None,
    strata_column: Optional[str] = None,
    key_column: Optional[str] = None,
    seed: Optional[int] = None,
    confidence: float = 0.95,
    margin_of_error: float = 0.03
) -> SampleResult:
    """
    Sample a table with the specified strategy.
    
    Args:
        data: Input data (list of row dicts)
        strategy: Sampling strategy
        sample_size: Target sample size (auto-calculated if None)
        strata_column: Column for stratified sampling
        key_column: Column for deterministic sampling
        seed: Random seed for reproducibility
        confidence: Confidence level (for auto sample size)
        margin_of_error: Margin of error (for auto sample size)
        
    Returns:
        SampleResult with sampled data and statistics
        
    UX Consultant: Simple unified sampling API
    """
    import time
    start = time.time()
    
    total_rows = len(data)
    
    if total_rows == 0:
        return SampleResult(
            data=[],
            stats=SampleStats(
                total_rows=0,
                sample_size=0,
                sampling_rate=0.0,
                strategy=strategy,
                confidence_level=confidence,
                margin_of_error=0.0,
            )
        )
    
    # Auto-calculate sample size if not provided
    if sample_size is None:
        sample_size = get_optimal_sample_size(
            total_rows, confidence, margin_of_error
        )
    
    # Auto-select strategy if adaptive
    if strategy == SamplingStrategy.ADAPTIVE:
        strategy = select_strategy(
            total_rows,
            has_strata_column=strata_column is not None,
            is_streaming=False,
            need_reproducible=key_column is not None
        )
    
    # Apply sampling
    strata_info = {}
    
    if strategy == SamplingStrategy.RANDOM:
        sampled = random_sample(data, sample_size, seed)
    elif strategy == SamplingStrategy.SYSTEMATIC:
        sampled = systematic_sample(data, sample_size, seed)
    elif strategy == SamplingStrategy.STRATIFIED:
        if strata_column:
            sampled, strata_info = stratified_sample(data, sample_size, strata_column, seed)
        else:
            sampled = random_sample(data, sample_size, seed)
    elif strategy == SamplingStrategy.RESERVOIR:
        sampled = reservoir_sample(data, sample_size, seed)
    elif strategy == SamplingStrategy.DETERMINISTIC:
        if key_column:
            sampled = deterministic_sample(data, sample_size, key_column)
        else:
            sampled = random_sample(data, sample_size, seed)
    else:
        sampled = random_sample(data, sample_size, seed)
    
    # Calculate actual margin of error
    actual_moe = calculate_margin_of_error(len(sampled), total_rows, confidence)
    
    duration = (time.time() - start) * 1000
    
    stats = SampleStats(
        total_rows=total_rows,
        sample_size=len(sampled),
        sampling_rate=len(sampled) / total_rows,
        strategy=strategy,
        confidence_level=confidence,
        margin_of_error=actual_moe,
        seed=seed,
        strata_info=strata_info,
        duration_ms=duration,
    )
    
    logger.info(
        f"Sampled {len(sampled)}/{total_rows} rows ({stats.sampling_rate:.1%}) "
        f"using {strategy.value} in {duration:.1f}ms"
    )
    
    return SampleResult(data=sampled, stats=stats)


# =============================================================================
# Convenience Functions
# =============================================================================

def quick_sample(
    data: List[Dict[str, Any]],
    max_rows: int = 10000
) -> List[Dict[str, Any]]:
    """
    Quick sampling with sensible defaults.
    
    Args:
        data: Input data
        max_rows: Maximum rows to return
        
    Returns:
        Sampled data
    """
    if len(data) <= max_rows:
        return data
    
    result = sample_table(data, sample_size=max_rows)
    return result.data


def should_sample(total_rows: int, threshold: int = 50000) -> bool:
    """Check if sampling is recommended based on row count."""
    return total_rows > threshold
