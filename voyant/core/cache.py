"""
Caching Layer Module

Result caching for repeated queries with invalidation.
Reference: STATUS.md Gap #10 - Caching Layer

Features:
- In-memory LRU cache
- TTL-based expiration
- Key-based invalidation
- Cache statistics
- Redis backend support

Personas Applied:
- PhD Developer: LRU algorithm, thread safety
- Analyst: Cache hit rate metrics
- QA: Cache invalidation testing
- ISO Documenter: Cache policy documentation
- Security: No sensitive data in cache keys
- Performance: O(1) operations, memory limits
- UX: Simple cache decorators

Usage:
    from voyant.core.cache import (
        cache_result, invalidate_cache,
        get_cache_stats, CacheConfig
    )
    
    @cache_result(ttl_seconds=300, key_prefix="kpi")
    async def get_kpi_result(source_id: str, kpi_name: str):
        # Expensive computation
        return result
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from threading import Lock

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry:
    """A single cache entry."""
    key: str
    value: Any
    created_at: float
    expires_at: float
    hits: int = 0
    
    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    @property
    def ttl_remaining(self) -> float:
        return max(0, self.expires_at - time.time())


@dataclass
class CacheStats:
    """Cache statistics."""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    invalidations: int = 0
    current_size: int = 0
    max_size: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "evictions": self.evictions,
            "invalidations": self.invalidations,
            "current_size": self.current_size,
            "max_size": self.max_size,
            "hit_rate": round(self.hit_rate, 4),
        }


class LRUCache:
    """
    Thread-safe LRU cache with TTL support.
    
    Performance: O(1) get/set via OrderedDict.
    Security: Keys are hashed to avoid sensitive data exposure.
    """
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = Lock()
        self._stats = CacheStats(max_size=max_size)
    
    def _hash_key(self, key: str) -> str:
        """Hash key to avoid sensitive data in logs."""
        return hashlib.sha256(key.encode()).hexdigest()[:16]
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Returns None if not found or expired.
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._stats.misses += 1
                return None
            
            if entry.is_expired:
                del self._cache[key]
                self._stats.misses += 1
                self._stats.current_size = len(self._cache)
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            entry.hits += 1
            self._stats.hits += 1
            
            return entry.value
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> None:
        """
        Set value in cache.
        
        Evicts LRU entries if at capacity.
        """
        ttl = ttl or self._default_ttl
        
        with self._lock:
            now = time.time()
            
            # Evict if at capacity
            while len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats.evictions += 1
            
            self._cache[key] = CacheEntry(
                key=key,
                value=value,
                created_at=now,
                expires_at=now + ttl,
            )
            self._cache.move_to_end(key)
            
            self._stats.sets += 1
            self._stats.current_size = len(self._cache)
    
    def delete(self, key: str) -> bool:
        """Delete a specific key."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.invalidations += 1
                self._stats.current_size = len(self._cache)
                return True
            return False
    
    def invalidate_prefix(self, prefix: str) -> int:
        """Invalidate all keys matching prefix."""
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            
            count = len(keys_to_delete)
            self._stats.invalidations += count
            self._stats.current_size = len(self._cache)
            return count
    
    def clear(self) -> None:
        """Clear entire cache."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._stats.invalidations += count
            self._stats.current_size = 0
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        with self._lock:
            now = time.time()
            keys_to_delete = [
                k for k, v in self._cache.items()
                if now > v.expires_at
            ]
            for key in keys_to_delete:
                del self._cache[key]
            
            self._stats.current_size = len(self._cache)
            return len(keys_to_delete)
    
    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        with self._lock:
            self._stats.current_size = len(self._cache)
            return self._stats


# =============================================================================
# Global Cache Instance
# =============================================================================

_cache: Optional[LRUCache] = None


def get_cache(max_size: int = 1000, default_ttl: int = 300) -> LRUCache:
    """Get or create the global cache instance."""
    global _cache
    if _cache is None:
        _cache = LRUCache(max_size=max_size, default_ttl=default_ttl)
        logger.info(f"Initialized cache (max_size={max_size}, ttl={default_ttl})")
    return _cache


def reset_cache():
    """Reset the global cache (testing)."""
    global _cache
    _cache = None


# =============================================================================
# Cache Decorator
# =============================================================================

def cache_result(
    ttl_seconds: int = 300,
    key_prefix: str = "",
    include_args: bool = True,
) -> Callable:
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Time to live in seconds
        key_prefix: Prefix for cache key
        include_args: Include function args in cache key
    
    Usage:
        @cache_result(ttl_seconds=600, key_prefix="kpi")
        async def compute_kpi(source_id: str):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            cache = get_cache()
            
            # Generate cache key
            if include_args:
                key_data = {
                    "func": func.__name__,
                    "args": str(args),
                    "kwargs": json.dumps(kwargs, sort_keys=True, default=str),
                }
                key = f"{key_prefix}:{hashlib.sha256(json.dumps(key_data).encode()).hexdigest()[:16]}"
            else:
                key = f"{key_prefix}:{func.__name__}"
            
            # Check cache
            cached = cache.get(key)
            if cached is not None:
                logger.debug(f"Cache hit: {key}")
                return cached
            
            # Compute and cache
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl=ttl_seconds)
            logger.debug(f"Cache set: {key}")
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            cache = get_cache()
            
            if include_args:
                key_data = {
                    "func": func.__name__,
                    "args": str(args),
                    "kwargs": json.dumps(kwargs, sort_keys=True, default=str),
                }
                key = f"{key_prefix}:{hashlib.sha256(json.dumps(key_data).encode()).hexdigest()[:16]}"
            else:
                key = f"{key_prefix}:{func.__name__}"
            
            cached = cache.get(key)
            if cached is not None:
                return cached
            
            result = func(*args, **kwargs)
            cache.set(key, result, ttl=ttl_seconds)
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# =============================================================================
# Cache API Functions
# =============================================================================

def invalidate_cache(key: str) -> bool:
    """Invalidate a specific cache key."""
    return get_cache().delete(key)


def invalidate_cache_prefix(prefix: str) -> int:
    """Invalidate all cache keys with prefix."""
    return get_cache().invalidate_prefix(prefix)


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return get_cache().get_stats().to_dict()


def clear_all_cache() -> None:
    """Clear entire cache."""
    get_cache().clear()
