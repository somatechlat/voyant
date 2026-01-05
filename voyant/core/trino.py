"""
Trino Client for Voyant Distributed SQL Queries.

This module provides a dedicated client for connecting to and executing queries
against a Trino cluster. It serves as the primary interface for all SQL-based
data analysis within the Voyant platform, federating queries across various
datastores like Iceberg, PostgreSQL, and Druid.

The client includes a critical security layer to ensure that only safe,
read-only queries are executed, preventing accidental or malicious data
modification or destruction.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from voyant.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """
    A structured representation of the results from a Trino SQL query.

    Attributes:
        columns: A list of column names in the order they were returned.
        rows: A list of lists, where each inner list represents a data row.
        row_count: The number of rows in the result set.
        truncated: A boolean indicating if the result set was truncated by a LIMIT clause.
        execution_time_ms: The total time taken for the query in milliseconds.
        query_id: The unique ID assigned by Trino to this query, for debugging and tracing.
    """

    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: int
    query_id: Optional[str] = None


class TrinoClient:
    """
    A client for executing validated, read-only SQL queries against Trino.

    This client abstracts the connection details and provides helper methods for
    common database metadata operations. It enforces query safety by validating
    all SQL statements against a denylist of destructive commands.

    Performance Note:
        This client maintains a single connection per instance. In highly concurrent
        scenarios, this could become a bottleneck. Future enhancements may include
        a connection pool to manage multiple concurrent connections.
    """

    def __init__(self):
        """Initializes the Trino client with configuration from settings."""
        settings = get_settings()
        self.host = settings.trino_host
        self.port = settings.trino_port
        self.user = settings.trino_user
        self.catalog = settings.trino_catalog
        self.schema = settings.trino_schema
        self.max_rows = settings.max_query_rows
        self._connection = None

    def _get_connection(self):
        """
        Lazily establishes and returns a connection to the Trino cluster.

        If a connection has not yet been established, it will be created and
        cached. If the `trino` package is not installed, this will raise a
        RuntimeError.

        Returns:
            A `trino.dbapi.Connection` object.

        Raises:
            RuntimeError: If the `trino` library is not installed.
            Exception: Any exception raised by the Trino DBAPI during connection.
        """
        if self._connection is None:
            try:
                import trino

                self._connection = trino.dbapi.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    catalog=self.catalog,
                    schema=self.schema,
                )
                logger.info(f"Trino connection established: {self.host}:{self.port}")
            except ImportError:
                raise RuntimeError(
                    "Trino client is not installed. Run: pip install 'trino[dbapi]'"
                )
            except Exception as e:
                logger.error(f"Failed to establish connection to Trino: {e}")
                raise
        return self._connection

    def execute(self, sql: str, limit: Optional[int] = None) -> QueryResult:
        """
        Execute a validated, read-only SQL query.

        Args:
            sql: The SQL query string to execute.
            limit: An optional row limit to apply. If not provided, the default
                   from settings is used.

        Returns:
            A QueryResult object containing the query's results.

        Raises:
            ValueError: If the SQL contains forbidden keywords (e.g., DROP, DELETE).
        """
        start_time = time.time()
        # Enforce the maximum allowed row limit.
        limit = min(limit or self.max_rows, self.max_rows)

        self._validate_sql(sql)
        sql_with_limit = self._apply_limit(sql, limit)

        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(sql_with_limit)

        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchall()

        return QueryResult(
            columns=columns,
            rows=[list(row) for row in rows],
            row_count=len(rows),
            truncated=len(rows) >= limit,
            execution_time_ms=int((time.time() - start_time) * 1000),
            query_id=getattr(cursor, "query_id", None),
        )

    def get_tables(self, schema: Optional[str] = None) -> List[str]:
        """
        List all tables within a given schema.

        Args:
            schema: The schema to query. If None, the client's default schema is used.

        Returns:
            A list of table names.
        """
        target_schema = schema or self.schema
        result = self.execute(f"SHOW TABLES FROM {target_schema}")
        return [row[0] for row in result.rows]

    def get_columns(
        self, table: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Describe the columns of a given table.

        Args:
            table: The name of the table to describe.
            schema: The schema of the table. If None, the client's default is used.

        Returns:
            A list of dictionaries, where each describes a column (e.g., `{'name': ..., 'type': ...}`).
        """
        target_schema = schema or self.schema
        result = self.execute(f"DESCRIBE {target_schema}.{table}")
        columns = []
        for row in result.rows:
            if not row:
                continue
            columns.append({"name": row[0], "type": row[1] if len(row) > 1 else ""})
        return columns

    def _validate_sql(self, sql: str) -> None:
        """
        Perform security validation on a SQL string to prevent destructive queries.

        This method acts as a safeguard against SQL injection and unintended data
        modification by enforcing a read-only query policy. It uses a denylist
        of keywords to prevent destructive commands.

        Args:
            sql: The SQL string to validate.

        Raises:
            ValueError: If the query is not a read-only query or contains forbidden keywords.
        """
        sql_upper = sql.strip().upper()

        allowed_prefixes = ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")
        if not sql_upper.startswith(allowed_prefixes):
            raise ValueError(
                "Invalid query type. Only SELECT, WITH, SHOW, DESCRIBE, and EXPLAIN are allowed."
            )

        forbidden_keywords = [
            "DROP ",
            "DELETE ",
            "TRUNCATE ",
            "INSERT ",
            "UPDATE ",
            "ALTER ",
            "CREATE TABLE",
            "GRANT ",
            "REVOKE ",
        ]
        for kw in forbidden_keywords:
            if kw in sql_upper:
                raise ValueError(f"Forbidden SQL keyword detected: '{kw.strip()}'")

    def _apply_limit(self, sql: str, limit: int) -> str:
        """
        Ensure a LIMIT clause is applied to a SQL query.

        If the query does not already contain a LIMIT clause, this method wraps
        it in a subquery and applies the specified limit to prevent runaway queries.

        Args:
            sql: The SQL string.
            limit: The row limit to apply.

        Returns:
            The modified SQL string with a LIMIT clause.
        """
        # Do not modify the query if a LIMIT clause already exists.
        if " LIMIT " in sql.upper():
            return sql
        # Wrap the original query and apply the system limit.
        return f"SELECT * FROM ({sql}) AS _q LIMIT {limit}"

    def close(self):
        """Close the underlying database connection, if it exists."""
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Trino connection closed.")


# Singleton client instance for application-wide use.
_client: Optional[TrinoClient] = None


def get_trino_client() -> TrinoClient:
    """
    Get the singleton instance of the TrinoClient.

    This factory function ensures that only one TrinoClient is instantiated per
    application process, promoting reuse of the underlying connection.
    """
    global _client
    if _client is None:
        _client = TrinoClient()
    return _client
