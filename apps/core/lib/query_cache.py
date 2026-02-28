"""
Query Result Caching

LRU-based caching for DuckDB query results to reduce database load
and improve response times for repeated queries.

Usage:
    from apps.core.lib.query_cache import get_cached_result, cache_result, invalidate_cache

    # Try cache first
    result = get_cached_result(query_hash)
    if result is None:
        result = execute_query(sql)
        cache_result(query_hash, result, ttl_seconds=300)

    # Or use decorator
    @cached_query(ttl_seconds=60)
    def get_user_stats(user_id: str):
        return db.execute(f"SELECT * FROM stats WHERE user_id = '{user_id}'")
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Cache Configuration
# =============================================================================


@dataclass
class CacheConfig:
    """
    Query cache configuration.

    Performance Engineer: Tuned defaults for typical workloads
    """

    max_size: int = 1000  # Maximum cached items
    default_ttl_seconds: int = 300  # 5 minutes default
    enable_stats: bool = True

    # Memory limits
    max_item_size_bytes: int = 10 * 1024 * 1024  # 10MB per item
    max_total_size_bytes: int = 100 * 1024 * 1024  # 100MB total


@dataclass
class CacheStats:
    """
    Cache statistics for monitoring.

    PhD Analyst: Metrics for cache effectiveness analysis
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    expirations: int = 0
    total_items: int = 0
    total_size_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        """
        Calculate the cache hit rate as a percentage.
        Returns:
            The cache hit rate, or 0.0 if there have been no requests.
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the cache statistics to a dictionary.
        Returns:
            A dictionary representation of the cache statistics.
        """
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "expirations": self.expirations,
            "hit_rate_percent": round(self.hit_rate, 2),
            "total_items": self.total_items,
            "total_size_bytes": self.total_size_bytes,
            "total_size_mb": round(self.total_size_bytes / (1024 * 1024), 2),
        }


@dataclass
class CacheEntry:
    """
    A single cache entry with metadata.
    """

    value: Any
    created_at: float
    expires_at: float
    size_bytes: int
    access_count: int = 0
    last_accessed: float = 0

    def __post_init__(self):
        """Initialize post-creation fields."""
        if self.last_accessed == 0:
            self.last_accessed = self.created_at

    @property
    def is_expired(self) -> bool:
        """
        Check if the cache entry has expired.
        Returns:
            True if the entry is expired, False otherwise.
        """
        return time.time() > self.expires_at

    @property
    def ttl_remaining(self) -> float:
        """
        Get the remaining time-to-live (TTL) for the cache entry.
        Returns:
            The remaining TTL in seconds, or 0 if expired.
        """
        return max(0, self.expires_at - time.time())


# =============================================================================
# Query Cache Implementation
# =============================================================================


class QueryCache:
    """
    Thread-safe LRU cache for query results.

    PhD Developer: Implements LRU with TTL support
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize the thread-safe LRU cache.
        Args:
            config: A CacheConfig object. If None, uses default configuration.
        """
        self.config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._stats = CacheStats()

        logger.info(f"Query cache initialized: max_size={self.config.max_size}")

    def _estimate_size(self, value: Any) -> int:
        """
        Estimate the memory size of a given value.
        This provides a basic estimation and may not be perfectly accurate.
        Args:
            value: The value to estimate.
        Returns:
            The estimated size in bytes.
        """
        if value is None:
            return 0

        # For common types
        if isinstance(value, (str, bytes)):
            return len(value)
        if isinstance(value, (list, tuple)):
            return sum(self._estimate_size(item) for item in value)
        if isinstance(value, dict):
            return sum(
                self._estimate_size(k) + self._estimate_size(v)
                for k, v in value.items()
            )

        # Default estimate
        return 100

    def _evict_if_needed(self):
        """
        Evict the oldest entries if the cache size or total memory exceeds limits.
        This method is called internally when adding new items.
        """
        # Evict by count
        while len(self._cache) >= self.config.max_size:
            key, entry = self._cache.popitem(last=False)
            self._stats.evictions += 1
            self._stats.total_size_bytes -= entry.size_bytes
            logger.debug(f"Evicted cache entry: {key[:20]}...")

        # Evict by total size
        while self._stats.total_size_bytes > self.config.max_total_size_bytes:
            if not self._cache:
                break
            key, entry = self._cache.popitem(last=False)
            self._stats.evictions += 1
            self._stats.total_size_bytes -= entry.size_bytes

    def _cleanup_expired(self):
        """
        Remove all expired entries from the cache.
        This ensures that stale data is not served.
        """
        now = time.time()
        expired_keys = [
            key for key, entry in self._cache.items() if entry.expires_at < now
        ]
        for key in expired_keys:
            entry = self._cache.pop(key, None)
            if entry:
                self._stats.expirations += 1
                self._stats.total_size_bytes -= entry.size_bytes

    def get(self, cache_key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.
        If the item is found, its access is recorded for LRU tracking.
        Args:
            cache_key: The key of the item to retrieve.
        Returns:
            The cached value, or None if not found or expired.
        """
        with self._lock:
            entry = self._cache.get(cache_key)

            if entry is None:
                self._stats.misses += 1
                return None

            if entry.is_expired:
                # Remove expired entry
                del self._cache[cache_key]
                self._stats.expirations += 1
                self._stats.total_size_bytes -= entry.size_bytes
                self._stats.misses += 1
                return None

            # Hit - update access metadata and move to end (LRU)
            entry.access_count += 1
            entry.last_accessed = time.time()
            self._cache.move_to_end(cache_key)
            self._stats.hits += 1

            logger.debug(f"Cache hit: {cache_key[:20]}...")
            return entry.value

    def set(
        self, cache_key: str, value: Any, ttl_seconds: Optional[int] = None
    ) -> bool:
        """
        Add or update a value in the cache with a specific TTL.
        Args:
            cache_key: The key for the cache entry.
            value: The value to be cached.
            ttl_seconds: Time-to-live in seconds. If None, uses the default TTL.
        Returns:
            True if the value was successfully cached, False otherwise.
        """
        if value is None:
            return False

        size = self._estimate_size(value)

        # Check item size limit
        if size > self.config.max_item_size_bytes:
            logger.warning(f"Value too large to cache: {size} bytes")
            return False

        ttl = ttl_seconds or self.config.default_ttl_seconds
        now = time.time()

        entry = CacheEntry(
            value=value, created_at=now, expires_at=now + ttl, size_bytes=size
        )

        with self._lock:
            # Remove old entry if exists
            if cache_key in self._cache:
                old_entry = self._cache.pop(cache_key)
                self._stats.total_size_bytes -= old_entry.size_bytes

            # Evict if needed
            self._evict_if_needed()

            # Store
            self._cache[cache_key] = entry
            self._stats.total_size_bytes += size
            self._stats.total_items = len(self._cache)

            logger.debug(f"Cached: {cache_key[:20]}... (TTL: {ttl}s)")
            return True

    def invalidate(self, cache_key: str) -> bool:
        """
        Remove a specific entry from the cache.
        Args:
            cache_key: The key of the entry to invalidate.
        Returns:
            True if the entry was found and removed, False otherwise.
        """
        with self._lock:
            entry = self._cache.pop(cache_key, None)
            if entry:
                self._stats.total_size_bytes -= entry.size_bytes
                self._stats.total_items = len(self._cache)
                return True
            return False

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all entries where the key starts with a given pattern.
        Args:
            pattern: The prefix pattern to match against cache keys.
        Returns:
            The number of entries that were invalidated.
        """
        with self._lock:
            keys_to_remove = [
                key for key in self._cache.keys() if key.startswith(pattern)
            ]

            for key in keys_to_remove:
                entry = self._cache.pop(key, None)
                if entry:
                    self._stats.total_size_bytes -= entry.size_bytes

            self._stats.total_items = len(self._cache)
            return len(keys_to_remove)

    def clear(self):
        """Clear all entries from the cache."""
        with self._lock:
            self._cache.clear()
            self._stats.total_items = 0
            self._stats.total_size_bytes = 0
            logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get the current statistics for the cache.
        Returns:
            A dictionary containing cache statistics.
        """
        with self._lock:
            self._stats.total_items = len(self._cache)
            return self._stats.to_dict()

    def cleanup(self):
        """
        Run a cleanup cycle to remove all expired entries from the cache.
        This should be called periodically in a background task.
        """
        with self._lock:
            self._cleanup_expired()
            self._stats.total_items = len(self._cache)


# =============================================================================
# Global Cache Instance
# =============================================================================

_global_cache: Optional[QueryCache] = None
_cache_lock = threading.Lock()


def get_cache() -> QueryCache:
    """
    Get the global singleton instance of the query cache.
    Initializes the cache on the first call.
    Returns:
        The global QueryCache instance.
    """
    global _global_cache
    if _global_cache is None:
        with _cache_lock:
            if _global_cache is None:
                _global_cache = QueryCache()
    return _global_cache


def generate_cache_key(sql: str, params: Optional[Tuple] = None) -> str:
    """
    Generate a deterministic cache key from an SQL query and its parameters.
    Args:
        sql: The SQL query string.
        params: A tuple of query parameters.
    Returns:
        A SHA256 hash of the query and parameters, truncated to 32 chars.
    """
    key_data = sql
    if params:
        key_data += str(params)

    return hashlib.sha256(key_data.encode()).hexdigest()[:32]


def get_cached_result(cache_key: str) -> Optional[Any]:
    """
    Retrieve a result from the global cache using its key.
    Args:
        cache_key: The key of the item to retrieve.
    Returns:
        The cached result, or None if not found.
    """
    return get_cache().get(cache_key)


def cache_result(cache_key: str, result: Any, ttl_seconds: int = 300) -> bool:
    """
    Store a result in the global cache.
    Args:
        cache_key: The key to store the result under.
        result: The result to be cached.
        ttl_seconds: The time-to-live for the cached item in seconds.
    Returns:
        True if the result was cached successfully, False otherwise.
    """
    return get_cache().set(cache_key, result, ttl_seconds)


def invalidate_cache(cache_key: str) -> bool:
    """
    Invalidate a specific result in the global cache.
    Args:
        cache_key: The key of the item to invalidate.
    Returns:
        True if the item was successfully invalidated, False otherwise.
    """
    return get_cache().invalidate(cache_key)


def invalidate_table_cache(table_name: str) -> int:
    """
    Invalidate all cached queries that are associated with a specific table.
    This is done by matching a key prefix convention.
    Args:
        table_name: The name of the table to invalidate cache for.
    Returns:
        The number of cache entries that were invalidated.
    """
    return get_cache().invalidate_pattern(f"table_{table_name}_")


def get_cache_stats() -> Dict[str, Any]:
    """
    Get the current statistics for the global cache.
    Returns:
        A dictionary containing cache statistics.
    """
    return get_cache().get_stats()


def clear_cache():
    """Clear all data from the global cache."""
    get_cache().clear()


# =============================================================================
# Decorator for Cached Queries
# =============================================================================


def cached_query(ttl_seconds: int = 300, key_prefix: str = "query"):
    """
    Decorator to cache query function results.

    Args:
        ttl_seconds: Cache TTL
        key_prefix: Prefix for cache keys

    Usage:
        @cached_query(ttl_seconds=60)
        def get_user_stats(user_id: str) -> List[Dict]:
            return db.execute(f"SELECT * FROM stats WHERE user_id = ?", (user_id,))

    UX Consultant: Simple decorator-based API
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_data = f"{key_prefix}:{func.__name__}:{str(args)}:{str(sorted(kwargs.items()))}"
            cache_key = hashlib.sha256(key_data.encode()).hexdigest()[:32]

            # Try cache
            result = get_cached_result(cache_key)
            if result is not None:
                return result

            # Execute and cache
            result = func(*args, **kwargs)
            cache_result(cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator
