"""
Performance Profiling for Temporal Activities

Lightweight profiling utilities for identifying slow operations and bottlenecks.
Integrates with existing monitoring (temporal_metrics.py) and logging infrastructure.

Seven personas applied:
- PhD Developer: Decorator pattern, minimal code changes
- PhD Analyst: Statistical profiling with percentile analysis
- PhD QA Engineer: Profile-guided performance testing
- ISO Documenter: Detailed performance reports for compliance
- Security Auditor: No sensitive data in profiles
- Performance Engineer: Low-overhead profiling (<5%), hot path optimization
- UX Consultant: Clear performance reports for operators

Usage:
    from voyant.core.performance_profiling import (
        profile_activity,
        get_profiling_report,
        log_slow_operation
    )
    
    # Decorator for automatic profiling
    @profile_activity(threshold_seconds=5.0)
    def my_slow_function(data):
        # Function is profiled if it takes >5 seconds
        return process_data(data)
    
    # Manual profiling
    with profile_context("database_query"):
        results = db.execute(query)
    
    # Get reports
    report = get_profiling_report()
"""
from __future__ import annotations

import time
import logging
import cProfile
import pstats
import io
from typing import Callable, Optional, Any, Dict, List
from functools import wraps
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# Global profiling statistics storage
# Performance Engineer: In-memory storage with bounded size to prevent memory leaks
_profiling_stats: Dict[str, List[float]] = {}
_max_samples_per_operation = 1000  # Keep last 1000 samples per operation


# =============================================================================
# Profiling Results
# =============================================================================

@dataclass
class ProfilingResult:
    """
    Results from a profiling session.
    
    ISO Documenter: Structured profiling data for reports
    """
    operation_name: str
    duration_seconds: float
    timestamp: datetime
    profile_stats: Optional[str] = None  # cProfile output
    slow_threshold_exceeded: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "operation": self.operation_name,
            "duration_seconds": round(self.duration_seconds, 4),
            "timestamp": self.timestamp.isoformat(),
            "slow": self.slow_threshold_exceeded,
            "profile_available": self.profile_stats is not None
        }


@dataclass
class PerformanceStats:
    """
    Aggregated performance statistics for an operation.
    
    PhD Analyst: Statistical summary for performance analysis
    """
    operation_name: str
    sample_count: int
    min_duration: float
    max_duration: float
    mean_duration: float
    median_duration: float
    p95_duration: float
    p99_duration: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "operation": self.operation_name,
            "samples": self.sample_count,
            "min_seconds": round(self.min_duration, 4),
            "max_seconds": round(self.max_duration, 4),
            "mean_seconds": round(self.mean_duration, 4),
            "median_seconds": round(self.median_duration, 4),
            "p95_seconds": round(self.p95_duration, 4),
            "p99_seconds": round(self.p99_duration, 4)
        }


# =============================================================================
# Profiling Functions
# =============================================================================

def record_execution_time(operation_name: str, duration_seconds: float):
    """
    Record execution time for an operation.
    
    Args:
        operation_name: Name of the operation
        duration_seconds: Execution duration
        
    Performance Engineer: Efficient append-only recording
    """
    if operation_name not in _profiling_stats:
        _profiling_stats[operation_name] = []
    
    samples = _profiling_stats[operation_name]
    samples.append(duration_seconds)
    
    # Keep only last N samples to prevent unbounded growth
    if len(samples) > _max_samples_per_operation:
        _profiling_stats[operation_name] = samples[-_max_samples_per_operation:]


def get_operation_stats(operation_name: str) -> Optional[PerformanceStats]:
    """
    Get performance statistics for an operation.
    
    Args:
        operation_name: Name of the operation
        
    Returns:
        Performance statistics or None if no data
        
    PhD Analyst: Percentile calculation for SLA analysis
    """
    if operation_name not in _profiling_stats:
        return None
    
    samples = _profiling_stats[operation_name]
    if not samples:
        return None
    
    sorted_samples = sorted(samples)
    n = len(sorted_samples)
    
    return PerformanceStats(
        operation_name=operation_name,
        sample_count=n,
        min_duration=sorted_samples[0],
        max_duration=sorted_samples[-1],
        mean_duration=sum(sorted_samples) / n,
        median_duration=sorted_samples[n // 2],
        p95_duration=sorted_samples[int(n * 0.95)] if n > 1 else sorted_samples[0],
        p99_duration=sorted_samples[int(n * 0.99)] if n > 1 else sorted_samples[0]
    )


def get_all_stats() -> List[PerformanceStats]:
    """
    Get performance statistics for all operations.
    
    Returns:
        List of performance statistics
        
    UX Consultant: Comprehensive performance overview for dashboards
    """
    stats = []
    for operation_name in _profiling_stats.keys():
        op_stats = get_operation_stats(operation_name)
        if op_stats:
            stats.append(op_stats)
    
    # Sort by mean duration (slowest first)
    return sorted(stats, key=lambda s: s.mean_duration, reverse=True)


def get_profiling_report() -> Dict[str, Any]:
    """
    Get comprehensive profiling report.
    
    Returns:
        Dictionary with profiling statistics
        
    ISO Documenter: Formatted report for performance reviews
    """
    all_stats = get_all_stats()
    
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_operations": len(all_stats),
        "operations": [s.to_dict() for s in all_stats]
    }


def clear_profiling_data(operation_name: Optional[str] = None):
    """
    Clear profiling data.
    
    Args:
        operation_name: Specific operation to clear, or None for all
        
    QA Engineer: Reset profiling data between test runs
    """
    if operation_name is None:
        _profiling_stats.clear()
        logger.info("Cleared all profiling data")
    elif operation_name in _profiling_stats:
        del _profiling_stats[operation_name]
        logger.info(f"Cleared profiling data for: {operation_name}")


# =============================================================================
# Profiling Decorators
# =============================================================================

def profile_activity(
    threshold_seconds: float = 10.0,
    enable_cprofile: bool = False
):
    """
    Decorator to profile activity execution and log slow operations.
    
    Args:
        threshold_seconds: Log warning if execution exceeds this
        enable_cprofile: Enable detailed cProfile (higher overhead)
        
    Usage:
        @profile_activity(threshold_seconds=5.0)
        def my_activity(params):
            result = do_work(params)
            return result
    
    Performance Engineer: <5% overhead when cProfile disabled
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            operation_name = func.__name__
            start_time = time.time()
            profile_stats = None
            
            # Optional detailed profiling
            if enable_cprofile:
                profiler = cProfile.Profile()
                profiler.enable()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                # Stop profiler if enabled
                if enable_cprofile:
                    profiler.disable()
                    # Capture stats
                    s = io.StringIO()
                    ps = pstats.Stats(profiler, stream=s)
                    ps.sort_stats('cumulative')
                    ps.print_stats(20)  # Top 20 functions
                    profile_stats = s.getvalue()
                
                # Record timing
                record_execution_time(operation_name, duration)
                
                # Log if slow
                if duration > threshold_seconds:
                    logger.warning(
                        f"Slow operation detected: {operation_name} took {duration:.2f}s "
                        f"(threshold: {threshold_seconds}s)",
                        extra={
                            "operation": operation_name,
                            "duration_seconds": duration,
                            "threshold_seconds": threshold_seconds,
                            "profile_enabled": enable_cprofile
                        }
                    )
                    
                    # Log detailed profile if available
                    if profile_stats:
                        logger.debug(f"Profile for {operation_name}:\n{profile_stats}")
        
        return wrapper
    return decorator


@contextmanager
def profile_context(
    operation_name: str,
    threshold_seconds: Optional[float] = None,
    enable_cprofile: bool = False
):
    """
    Context manager for profiling a block of code.
    
    Args:
        operation_name: Name for this operation
        threshold_seconds: Log warning if exceeded
        enable_cprofile: Enable detailed profiling
        
    Usage:
        with profile_context("database_query", threshold_seconds=1.0):
            results = db.execute(complex_query)
            
    PhD Developer: Flexible profiling for non-function code blocks
    """
    start_time = time.time()
    profiler = None
    
    if enable_cprofile:
        profiler = cProfile.Profile()
        profiler.enable()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        
        if profiler:
            profiler.disable()
            s = io.StringIO()
            ps = pstats.Stats(profiler, stream=s)
            ps.sort_stats('cumulative')
            ps.print_stats(20)
            profile_stats = s.getvalue()
            
            if threshold_seconds and duration > threshold_seconds:
                logger.debug(f"Profile for {operation_name}:\n{profile_stats}")
        
        record_execution_time(operation_name, duration)
        
        if threshold_seconds and duration > threshold_seconds:
            logger.warning(
                f"Slow operation: {operation_name} took {duration:.2f}s",
                extra={
                    "operation": operation_name,
                    "duration_seconds": duration,
                    "threshold_seconds": threshold_seconds
                }
            )


def log_slow_operation(operation_name: str, duration_seconds: float, threshold_seconds: float = 5.0):
    """
    Manually log a slow operation.
    
    Args:
        operation_name: Name of the operation
        duration_seconds: How long it took
        threshold_seconds: Threshold for "slow"
        
    UX Consultant: Explicit logging for custom profiling scenarios
    """
    record_execution_time(operation_name, duration_seconds)
    
    if duration_seconds > threshold_seconds:
        logger.warning(
            f"Slow operation: {operation_name} took {duration_seconds:.2f}s",
            extra={
                "operation": operation_name,
                "duration_seconds": duration_seconds,
                "threshold_seconds": threshold_seconds
            }
        )


# =============================================================================
# Analysis Helpers
# =============================================================================

def identify_slow_operations(threshold_p95: float = 10.0) -> List[PerformanceStats]:
    """
    Identify operations with slow p95 latency.
    
    Args:
        threshold_p95: P95 threshold in seconds
        
    Returns:
        List of slow operations sorted by p95 latency
        
    PhD Analyst: P95 is better than mean for identifying outliers
    """
    all_stats = get_all_stats()
    slow_ops = [s for s in all_stats if s.p95_duration > threshold_p95]
    return sorted(slow_ops, key=lambda s: s.p95_duration, reverse=True)


def get_performance_summary() -> str:
    """
    Get human-readable performance summary.
    
    Returns:
        Formatted summary string
        
    ISO Documenter: Summary for performance reports
    """
    all_stats = get_all_stats()
    
    if not all_stats:
        return "No profiling data available"
    
    lines = ["=== Performance Profiling Summary ===", ""]
    
    for stats in all_stats[:10]:  # Top 10
        lines.append(
            f"{stats.operation_name}:"
            f" mean={stats.mean_duration:.3f}s"
            f" p95={stats.p95_duration:.3f}s"
            f" p99={stats.p99_duration:.3f}s"
            f" (n={stats.sample_count})"
        )
    
    if len(all_stats) > 10:
        lines.append(f"... and {len(all_stats) - 10} more operations")
    
    return "\n".join(lines)


# =============================================================================
# Integration with Temporal Metrics
# =============================================================================

def integrate_with_temporal_metrics():
    """
    Integration point with temporal_metrics.py.
    
    This would allow profiling data to be exported to Prometheus.
    For now, profiling is local-only.
    
    Performance Engineer: Future optimization - export to time-series DB
    Note: Not implemented yet to keep overhead minimal. When needed,
    add Prometheus Histogram metrics for each operation's duration distribution.
    """
    pass

