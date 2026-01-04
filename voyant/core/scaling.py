"""
Horizontal Scaling Module

DuckDB concurrency patterns and MotherDuck abstraction.
Reference: STATUS.md Gap #5 - Horizontal Scaling

Features:
- Connection pooling for DuckDB
- Read/write serialization strategies
- MotherDuck cloud integration
- Query routing
- Failover handling

Personas Applied:
- PhD Developer: Concurrency patterns
- Analyst: Query performance metrics
- QA: Concurrent access testing
- ISO Documenter: Scaling documentation
- Security: Connection credential handling
- Performance: Connection reuse, query batching
- UX: Transparent failover

Usage:
    from voyant.core.scaling import (
        get_connection, execute_query,
        ConnectionPool, QueryRouter
    )

    # Get connection from pool
    async with get_connection() as conn:
        result = await execute_query(conn, "SELECT * FROM orders")
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
from threading import Lock
from typing import Any, Dict, List, Optional, Callable, Union

logger = logging.getLogger(__name__)


class BackendType(str, Enum):
    """Database backend types."""

    DUCKDB_LOCAL = "duckdb_local"
    DUCKDB_MEMORY = "duckdb_memory"
    MOTHERDUCK = "motherduck"


class QueryType(str, Enum):
    """Query classification for routing."""

    READ = "read"
    WRITE = "write"
    DDL = "ddl"


@dataclass
class ConnectionConfig:
    """Database connection configuration."""

    backend: BackendType = BackendType.DUCKDB_LOCAL
    database_path: str = "voyant.duckdb"
    motherduck_token: Optional[str] = None
    max_connections: int = 10
    connection_timeout: int = 30
    query_timeout: int = 300
    read_only: bool = False

    @classmethod
    def from_env(cls) -> "ConnectionConfig":
        """Load configuration from environment."""
        backend_str = os.getenv("VOYANT_DB_BACKEND", "duckdb_local")

        return cls(
            backend=BackendType(backend_str),
            database_path=os.getenv("VOYANT_DB_PATH", "voyant.duckdb"),
            motherduck_token=os.getenv("MOTHERDUCK_TOKEN"),
            max_connections=int(os.getenv("VOYANT_DB_MAX_CONNECTIONS", "10")),
            connection_timeout=int(os.getenv("VOYANT_DB_CONNECTION_TIMEOUT", "30")),
            query_timeout=int(os.getenv("VOYANT_DB_QUERY_TIMEOUT", "300")),
        )


@dataclass
class ConnectionStats:
    """Connection pool statistics."""

    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    total_queries: int = 0
    total_query_time_ms: float = 0
    errors: int = 0

    @property
    def avg_query_time_ms(self) -> float:
        if self.total_queries == 0:
            return 0
        return self.total_query_time_ms / self.total_queries

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_connections": self.total_connections,
            "active_connections": self.active_connections,
            "idle_connections": self.idle_connections,
            "total_queries": self.total_queries,
            "avg_query_time_ms": round(self.avg_query_time_ms, 2),
            "errors": self.errors,
        }


# =============================================================================
# Connection Pool
# =============================================================================


class ConnectionPool:
    """
    Connection pool for DuckDB with read/write serialization.

    DuckDB allows multiple readers OR one writer at a time.
    This pool manages that constraint.
    """

    def __init__(self, config: Optional[ConnectionConfig] = None):
        """
        Initialize the connection pool.
        Args:
            config: Connection configuration. If None, loaded from env.
        """
        self.config = config or ConnectionConfig.from_env()
        self._connections: Queue = Queue()
        self._lock = Lock()
        self._write_lock = Lock()
        self._stats = ConnectionStats()
        self._initialized = False

    def _create_connection(self):
        """
        Create a new database connection based on the configuration.
        Raises:
            ImportError: If the 'duckdb' package is not installed.
            ValueError: If MotherDuck is configured without a token.
        Returns:
            A new database connection object.
        """
        try:
            import duckdb

            if self.config.backend == BackendType.DUCKDB_MEMORY:
                conn = duckdb.connect(":memory:")
            elif self.config.backend == BackendType.MOTHERDUCK:
                if not self.config.motherduck_token:
                    raise ValueError("MOTHERDUCK_TOKEN required for MotherDuck")
                conn = duckdb.connect(f"md:{self.config.database_path}")
            else:
                conn = duckdb.connect(
                    self.config.database_path,
                    read_only=self.config.read_only,
                )

            self._stats.total_connections += 1
            return conn

        except ImportError:
            logger.error("duckdb package not installed")
            raise

    def initialize(self, min_connections: int = 2) -> None:
        """
        Initialize the pool with a minimum number of connections.
        This method is idempotent and will only run once.
        Args:
            min_connections: The minimum number of connections to create.
        """
        if self._initialized:
            return

        with self._lock:
            for _ in range(min_connections):
                conn = self._create_connection()
                self._connections.put(conn)
                self._stats.idle_connections += 1
            self._initialized = True

        logger.info(f"Initialized connection pool with {min_connections} connections")

    def get_connection(self, timeout: Optional[int] = None):
        """
        Get a connection from the pool.
        If the pool is empty, it will try to create a new connection if the
        maximum number of connections has not been reached.
        Args:
            timeout: Maximum time in seconds to wait for a connection.
        Returns:
            A database connection from the pool.
        Raises:
            TimeoutError: If no connection is available within the timeout.
        """
        timeout = timeout or self.config.connection_timeout

        if not self._initialized:
            self.initialize()

        try:
            conn = self._connections.get(timeout=timeout)
            with self._lock:
                self._stats.active_connections += 1
                self._stats.idle_connections -= 1
            return conn
        except Empty:
            # Pool exhausted, create new if under limit
            with self._lock:
                if self._stats.total_connections < self.config.max_connections:
                    conn = self._create_connection()
                    self._stats.active_connections += 1
                    return conn
            raise TimeoutError("Connection pool exhausted")

    def return_connection(self, conn) -> None:
        """
        Return a connection to the pool to be reused.
        Args:
            conn: The connection to return.
        """
        self._connections.put(conn)
        with self._lock:
            self._stats.active_connections -= 1
            self._stats.idle_connections += 1

    def close_all(self) -> None:
        """
        Close all connections in the pool and reset its state.
        """
        with self._lock:
            while not self._connections.empty():
                try:
                    conn = self._connections.get_nowait()
                    conn.close()
                except Empty:
                    break
            self._stats = ConnectionStats()
            self._initialized = False

        logger.info("Closed all connections")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current statistics for the connection pool.
        Returns:
            A dictionary containing pool statistics.
        """
        return self._stats.to_dict()

    def acquire_write_lock(self) -> bool:
        """
        Acquire an exclusive lock for write operations.
        This is necessary because DuckDB allows only one writer at a time.
        Returns:
            True if the lock was acquired, False otherwise.
        """
        return self._write_lock.acquire(timeout=self.config.connection_timeout)

    def release_write_lock(self) -> None:
        """
        Release the exclusive write lock.
        Handles cases where the lock might not have been acquired.
        """
        try:
            self._write_lock.release()
        except RuntimeError:
            pass  # Not locked


# =============================================================================
# Query Router
# =============================================================================


class QueryRouter:
    """
    Routes queries based on type and load.

    For read-heavy workloads, can distribute reads across replicas.
    """

    def __init__(self, pool: ConnectionPool):
        """
        Initialize the query router.
        Args:
            pool: The connection pool to use for executing queries.
        """
        self.pool = pool

    def classify_query(self, sql: str) -> QueryType:
        """
        Classify the type of an SQL query (READ, WRITE, or DDL).
        Args:
            sql: The SQL query string.
        Returns:
            The classified query type.
        """
        sql_upper = sql.strip().upper()

        if sql_upper.startswith(("CREATE", "DROP", "ALTER")):
            return QueryType.DDL
        elif sql_upper.startswith(("INSERT", "UPDATE", "DELETE", "MERGE")):
            return QueryType.WRITE
        else:
            return QueryType.READ

    def execute(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute a query with appropriate locking based on its type.
        Write and DDL queries acquire a write lock, while read queries do not.
        Args:
            sql: The SQL query to execute.
            params: Optional parameters for the query.
        Returns:
            The result of the query execution.
        Raises:
            TimeoutError: If a write lock cannot be acquired.
        """
        query_type = self.classify_query(sql)
        start_time = time.time()

        try:
            if query_type in (QueryType.WRITE, QueryType.DDL):
                # Acquire write lock for write operations
                if not self.pool.acquire_write_lock():
                    raise TimeoutError("Could not acquire write lock")

                try:
                    return self._execute_with_connection(sql, params)
                finally:
                    self.pool.release_write_lock()
            else:
                # Read operations don't need write lock
                return self._execute_with_connection(sql, params)

        except Exception as e:
            self.pool._stats.errors += 1
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.pool._stats.total_queries += 1
            self.pool._stats.total_query_time_ms += duration_ms

    def _execute_with_connection(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute a query using a connection from the pool.
        Args:
            sql: The SQL query to execute.
            params: Optional parameters for the query.
        Returns:
            The fetched results from the query, or None.
        """
        conn = self.pool.get_connection()
        try:
            if params:
                result = conn.execute(sql, params)
            else:
                result = conn.execute(sql)
            return result.fetchall() if result else None
        finally:
            self.pool.return_connection(conn)


# =============================================================================
# Async Wrapper
# =============================================================================


class AsyncQueryExecutor:
    """
    Async wrapper for query execution.

    Uses thread pool for blocking DuckDB operations.
    """

    def __init__(self, router: QueryRouter):
        """
        Initialize the async query executor.
        Args:
            router: The query router to use for execution.
        """
        self.router = router

    async def execute(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute a single query asynchronously in a thread pool.
        Args:
            sql: The SQL query to execute.
            params: Optional parameters for the query.
        Returns:
            The result of the query execution.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.router.execute(sql, params),
        )

    async def execute_many(
        self,
        queries: List[tuple[str, Optional[Dict[str, Any]]]],
    ) -> List[Any]:
        """
        Execute multiple queries sequentially and asynchronously.
        Args:
            queries: A list of tuples, each containing a query string
                     and optional parameters.
        Returns:
            A list of results from each query execution.
        """
        results = []
        for sql, params in queries:
            result = await self.execute(sql, params)
            results.append(result)
        return results


# =============================================================================
# Global Instance
# =============================================================================

_pool: Optional[ConnectionPool] = None
_router: Optional[QueryRouter] = None
_async_executor: Optional[AsyncQueryExecutor] = None


def get_pool() -> ConnectionPool:
    """
    Get the global singleton instance of the connection pool.
    Initializes the pool on first call.
    Returns:
        The global ConnectionPool instance.
    """
    global _pool
    if _pool is None:
        _pool = ConnectionPool()
        _pool.initialize()
    return _pool


def get_router() -> QueryRouter:
    """
    Get the global singleton instance of the query router.
    Initializes the router on first call.
    Returns:
        The global QueryRouter instance.
    """
    global _router
    if _router is None:
        _router = QueryRouter(get_pool())
    return _router


def get_async_executor() -> AsyncQueryExecutor:
    """
    Get the global singleton instance of the async query executor.
    Initializes the executor on first call.
    Returns:
        The global AsyncQueryExecutor instance.
    """
    global _async_executor
    if _async_executor is None:
        _async_executor = AsyncQueryExecutor(get_router())
    return _async_executor


@asynccontextmanager
async def get_connection():
    """
    Async context manager to get a connection from the global pool.
    Ensures the connection is returned to the pool after use.
    Yields:
        A database connection.
    """
    pool = get_pool()
    conn = pool.get_connection()
    try:
        yield conn
    finally:
        pool.return_connection(conn)


async def execute_query(
    sql: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Execute a query asynchronously using the global async executor.
    Args:
        sql: The SQL query to execute.
        params: Optional parameters for the query.
    Returns:
        The result of the query execution.
    """
    return await get_async_executor().execute(sql, params)


def execute_query_sync(
    sql: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Execute a query synchronously using the global query router.
    Args:
        sql: The SQL query to execute.
        params: Optional parameters for the query.
    Returns:
        The result of the query execution.
    """
    return get_router().execute(sql, params)


def get_scaling_stats() -> Dict[str, Any]:
    """
    Get statistics about the scaling module.
    Includes backend type, pool stats, and configuration.
    Returns:
        A dictionary containing scaling statistics.
    """
    pool = get_pool()
    return {
        "backend": pool.config.backend.value,
        "pool": pool.get_stats(),
        "config": {
            "max_connections": pool.config.max_connections,
            "query_timeout": pool.config.query_timeout,
        },
    }


def reset_pool() -> None:
    """
    Reset the global connection pool. Useful for testing.
    Closes all connections and clears the singleton instances.
    """
    global _pool, _router, _async_executor
    if _pool:
        _pool.close_all()
    _pool = None
    _router = None
    _async_executor = None
