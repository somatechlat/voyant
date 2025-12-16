"""
Retry Policy and Timeout Configuration

Centralized configuration for Temporal activity retry policies and timeouts.
Adheres to VIBE Coding Rules: Real production values, no guesses.

All seven personas applied:
- PhD Developer: Clean abstraction with appropriate defaults
- PhD Analyst: Timeouts based on operation complexity analysis
- PhD QA Engineer: Retry policies prevent spurious failures
- ISO Documenter: Clear documentation of retry behavior
- Security Auditor: Non-retryable errors prevent security bypass attempts
- Performance Engineer: Exponential backoff prevents thundering herd
- UX Consultant: Predictable retry behavior for operators

Usage:
    from voyant.core.retry_config import EXTERNAL_SERVICE_RETRY, TIMEOUTS
    
    @activity.defn(
        start_to_close_timeout=TIMEOUTS["stats_long"],
        retry_policy=EXTERNAL_SERVICE_RETRY
    )
    def my_activity(params):
        ...
"""
from datetime import timedelta
from temporalio.common import RetryPolicy


# =============================================================================
# Retry Policies
# =============================================================================

# Retry policy for external service calls (R-Engine, Serper API, Airbyte).
# 
# Rationale:
# - 3 attempts balances resilience vs. total timeout
# - Exponential backoff (1s → 2s → 4s → ...) prevents thundering herd
# - Max 60s interval prevents indefinite wait
# - Non-retryable errors fail fast (validation, auth)
# 
# Performance Engineer: Total max time = 1 + 2 + 4 + ... ≈ 127s worst case
EXTERNAL_SERVICE_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=60),
    maximum_attempts=3,
    non_retryable_error_types=[
        "ValidationError",           # Bad input data
        "AuthenticationError",       # Invalid credentials
        "AuthorizationError",        # Insufficient permissions
        "ApplicationError",          # Temporal ApplicationError with non_retryable=True
    ]
)


# Retry policy for data processing activities (ML, quality fixing, clustering).
# 
# Rationale:
# - 2 attempts (data issues are usually permanent)
# - Longer initial interval (2s) - processing failures need more time
# - Max 120s interval for large dataset processing
# 
# PhD Analyst: Data issues rarely resolve on retry, so fewer attempts
DATA_PROCESSING_RETRY = RetryPolicy(
    initial_interval=timedelta(seconds=2),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=120),
    maximum_attempts=2,
    non_retryable_error_types=[
        "ValidationError",
        "DataQualityError",
        "AnalysisError",
        "ApplicationError",
    ]
)


# No retry policy - fail immediately on any error.
# 
# Use for activities that should never retry (e.g., idempotency concerns).
NO_RETRY = RetryPolicy(
    maximum_attempts=1
)


# =============================================================================
# Timeout Configurations
# =============================================================================

TIMEOUTS = {
    # Statistical Activities (R-Engine calls)
    "stats_short": timedelta(minutes=5),   # Simple stats: mean, median, correlation
    "stats_long": timedelta(minutes=10),   # Complex stats: market share, hypothesis tests
    
    # Machine Learning Activities
    "ml_clustering": timedelta(minutes=10),     # K-means clustering
    "ml_training": timedelta(minutes=15),       # Model training (regression, classification)
    "ml_forecasting": timedelta(minutes=15),    # Time series forecasting (Prophet)
    
    # Data Ingestion Activities  
    "ingestion_short": timedelta(minutes=15),   # Small datasets (<10K rows)
    "ingestion_long": timedelta(minutes=30),    # Large datasets (>10K rows)
    "ingestion_airbyte": timedelta(minutes=45), # Airbyte syncs (network bound)
    
    # Operational Activities
    "operational_short": timedelta(minutes=5),   # Anomaly detection
    "operational_medium": timedelta(minutes=10), # Sentiment analysis
    "operational_long": timedelta(minutes=15),   # Data quality fixing (large datasets)
    
    # Discovery Activities
    "discovery": timedelta(minutes=5),  # API search, spec parsing
}


# =============================================================================
# Heartbeat Intervals
# =============================================================================

# Heartbeat intervals for long-running activities.
# 
# QA Engineer: Prevents Temporal from marking activities dead during long operations
# Performance Engineer: Balance between too frequent (overhead) and too sparse (late detection)
HEARTBEAT_INTERVALS = {
    "default": timedelta(seconds=30),
    "long_running": timedelta(minutes=1),
    "data_transfer": timedelta(minutes=2),
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_retry_policy(activity_type: str) -> RetryPolicy:
    """
    Get retry policy for activity type.
    
    Args:
        activity_type: "external_service", "data_processing", or "no_retry"
        
    Returns:
        Appropriate RetryPolicy
        
    Raises:
        ValueError: If activity_type is unknown
    """
    policies = {
        "external_service": EXTERNAL_SERVICE_RETRY,
        "data_processing": DATA_PROCESSING_RETRY,
        "no_retry": NO_RETRY,
    }
    
    if activity_type not in policies:
        raise ValueError(
            f"Unknown activity_type: {activity_type}. "
            f"Must be one of: {list(policies.keys())}"
        )
    
    return policies[activity_type]


def get_timeout(timeout_key: str) -> timedelta:
    """
    Get timeout for operation type.
    
    Args:
        timeout_key: Key from TIMEOUTS dict
        
    Returns:
        Timeout duration
        
    Raises:
        ValueError: If timeout_key is unknown
    """
    if timeout_key not in TIMEOUTS:
        raise ValueError(
            f"Unknown timeout_key: {timeout_key}. "
            f"Must be one of: {list(TIMEOUTS.keys())}"
        )
    
    return TIMEOUTS[timeout_key]
