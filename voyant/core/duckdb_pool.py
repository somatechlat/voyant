"""
DuckDB Connection Pool

Thread-safe connection pool for DuckDB to improve performance under concurrent load.
Reduces connection overhead and enables efficient resource reuse.

Seven personas applied:
- PhD Developer: Thread-safe pool with proper lifecycle management
- PhD Analyst: Connection metrics for pool utilization analysis
- PhD QA Engineer: Connection validation and health checks
- ISO Documenter: Clear pool configuration and usage guidelines
- Security Auditor: No credential exposure, safe connection reuse
- Performance Engineer: Minimal contention, efficient resource allocation
- UX Consultant: Simple API, automatic connection management

Usage:
    from voyant.core.duckdb_pool import get_connection, execute_query
    
    # Option 1: Context manager (recommended)
    with get_connection() as conn:
        result = conn.execute("SELECT * FROM table").fetchall()
    
    # Option 2: Helper function
    result = execute_query("SELECT COUNT(*) FROM table")
"""
from __future__ import annotations

import duckdb
import logging
import threading
from typing import Optional, Any, List, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
from queue import Queue, Empty
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class PoolConfig:
    """
    Connection pool configuration.
    
    Performance Engineer: Tuned defaults based on typical workload
    """
    database_path: str = ":memory:"
    min_connections: int = 2
    max_connections: int = 10
    connection_timeout: float = 30.0  # seconds
    validate_on_checkout: bool = True
    auto_reconnect: bool = True


# =============================================================================
# Connection Pool
# =============================================================================

class DuckDBConnectionPool:
    """
    Thread-safe connection pool for DuckDB.
    
    PhD Developer: Implements object pool pattern with lifecycle management
    """
    
    def __init__(self, config: PoolConfig):
        """
        Initialize connection pool.
        
        Args:
            config: Pool configuration
        """
        self.config = config
        self._pool: Queue = Queue(maxsize=config.max_connections)
        self._all_connections: List[duckdb.DuckDBPyConnection] = []
        self._lock = threading.Lock()
        self._initialized = False
        
        # Metrics
        self._total_created = 0
        self._total_checkouts = 0
        self._total_checkins = 0
        self._total_validations_failed = 0
        
        logger.info(
            f"DuckDB pool initialized: {config.database_path}, "
            f"min={config.min_connections}, max={config.max_connections}"
        )
    
    def initialize(self):
        """
        Initialize pool with minimum connections.
        
        QA Engineer: Fail fast on initialization errors
        """
        if self._initialized:
            return
        
        with self._lock:
            if self._initialized:  # Double-check after acquiring lock
                return
            
            try:
                for _ in range(self.config.min_connections):
                    conn = self._create_connection()
                    self._pool.put(conn)
                
                self._initialized = True
                logger.info(f"Pool initialized with {self.config.min_connections} connections")
                
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise
    
    def _create_connection(self) -> duckdb.DuckDBPyConnection:
        """
        Create a new DuckDB connection.
        
        Returns:
            New connection
            
        PhD Developer: Centralized connection creation
        """
        try:
            conn = duckdb.connect(self.config.database_path)
            
            with self._lock:
                self._total_created += 1
                self._all_connections.append(conn)
            
            logger.debug(f"Created new connection (total: {self._total_created})")
            return conn
            
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            raise
    
    def _validate_connection(self, conn: duckdb.DuckDBPyConnection) -> bool:
        """
        Validate that connection is healthy.
        
        Args:
            conn: Connection to validate
            
        Returns:
            True if connection is valid
            
        QA Engineer: Health check prevents application errors from bad connections
        """
        try:
            # Simple query to test connection
            conn.execute("SELECT 1").fetchone()
            return True
        except Exception as e:
            logger.warning(f"Connection validation failed: {e}")
            with self._lock:
                self._total_validations_failed += 1
            return False
    
    def get_connection(self, timeout: Optional[float] = None) -> duckdb.DuckDBPyConnection:
        """
        Get a connection from the pool.
        
        Args:
            timeout: Max seconds to wait, None=use config default
            
        Returns:
            Database connection
            
        Raises:
            Empty: If no connection available within timeout
            
        Performance Engineer: Non-blocking checkout with timeout
        """
        if not self._initialized:
            self.initialize()
        
        timeout = timeout or self.config.connection_timeout
        
        try:
            # Try to get from pool
            conn = self._pool.get(timeout=timeout)
            
            # Validate if configured
            if self.config.validate_on_checkout:
                if not self._validate_connection(conn):
                    if self.config.auto_reconnect:
                        logger.info("Connection invalid, creating new one")
                        conn = self._create_connection()
                    else:
                        raise Exception("Connection validation failed")
            
            with self._lock:
                self._total_checkouts += 1
            
            logger.debug(f"Checked out connection (checkouts: {self._total_checkouts})")
            return conn
            
        except Empty:
            # Pool empty - try to create new connection if under max
            with self._lock:
                if len(self._all_connections) < self.config.max_connections:
                    logger.info("Pool empty, creating new connection")
                    conn = self._create_connection()
                    self._total_checkouts += 1
                    return conn
                else:
                    raise Empty(
                        f"Connection pool exhausted (max={self.config.max_connections}), "
                        f"waited {timeout}s"
                    )
    
    def return_connection(self, conn: duckdb.DuckDBPyConnection):
        """
        Return a connection to the pool.
        
        Args:
            conn: Connection to return
            
        PhD Developer: Proper resource cleanup
        """
        try:
            # Validate before returning
            if self.config.validate_on_checkout and not self._validate_connection(conn):
                logger.warning("Not returning invalid connection to pool")
                return
            
            self._pool.put_nowait(conn)
            
            with self._lock:
                self._total_checkins += 1
            
            logger.debug(f"Returned connection to pool (checkins: {self._total_checkins})")
            
        except Exception as e:
            logger.error(f"Failed to return connection: {e}")
    
    @contextmanager
    def connection(self):
        """
        Context manager for automatic connection management.
        
        Usage:
            with pool.connection() as conn:
                result = conn.execute(query)
                
        UX Consultant: Pythonic API, automatic cleanup
        """
        conn = self.get_connection()
        try:
            yield conn
        finally:
            self.return_connection(conn)
    
    def close_all(self):
        """
        Close all connections in the pool.
        
        ISO Documenter: Proper shutdown procedure for graceful termination
        """
        logger.info("Closing all pool connections")
        
        with self._lock:
            for conn in self._all_connections:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            
            self._all_connections.clear()
            self._initialized = False
        
        # Clear the queue
        while not self._pool.empty():
            try:
                self._pool.get_nowait()
            except Empty:
                break
        
        logger.info("All connections closed")
    
    def get_stats(self) -> dict:
        """
        Get pool statistics.
        
        Returns:
            Dictionary with pool stats
            
        PhD Analyst: Metrics for pool sizing and performance optimization
        """
        return {
            "total_created": self._total_created,
            "total_checkouts": self._total_checkouts,
            "total_checkins": self._total_checkins,
            "validations_failed": self._total_validations_failed,
            "pool_size": self._pool.qsize(),
            "total_connections": len(self._all_connections),
            "max_connections": self.config.max_connections
        }


# =============================================================================
# Global Pool Instance
# =============================================================================

_global_pool: Optional[DuckDBConnectionPool] = None
_pool_lock = threading.Lock()


def initialize_pool(config: Optional[PoolConfig] = None):
    """
    Initialize the global connection pool.
    
    Args:
        config: Pool configuration, or None for defaults
        
    Performance Engineer: Lazy initialization on first use
    """
    global _global_pool
    
    if config is None:
        from voyant.core.config import get_settings
        settings = get_settings()
        config = PoolConfig(
            database_path=settings.duckdb_path,
            min_connections=2,
            max_connections=10
        )
    
    with _pool_lock:
        if _global_pool is None:
            _global_pool = DuckDBConnectionPool(config)
            _global_pool.initialize()
            logger.info("Global DuckDB pool initialized")


def get_pool() -> DuckDBConnectionPool:
    """
    Get the global connection pool.
    
    Returns:
        Global pool instance
        
    PhD Developer: Singleton pattern for global resource
    """
    if _global_pool is None:
        initialize_pool()
    return _global_pool


@contextmanager
def get_connection():
    """
    Get a connection from the global pool.
    
    Usage:
        with get_connection() as conn:
            result = conn.execute("SELECT * FROM table")
            
    UX Consultant: Simple API for common use case
    """
    pool = get_pool()
    with pool.connection() as conn:
        yield conn


def execute_query(query: str, parameters: Optional[Tuple] = None) -> List[Tuple]:
    """
    Execute a query using a pooled connection.
    
    Args:
        query: SQL query
        parameters: Query parameters
        
    Returns:
        Query results
        
    Performance Engineer: Convenience function for simple queries
    """
    with get_connection() as conn:
        if parameters:
            result = conn.execute(query, parameters).fetchall()
        else:
            result = conn.execute(query).fetchall()
        return result


def get_pool_stats() -> dict:
    """
    Get statistics for the global pool.
    
    Returns:
        Pool statistics
        
    ISO Documenter: Metrics for monitoring and capacity planning
    """
    if _global_pool:
        return _global_pool.get_stats()
    return {"status": "not_initialized"}
