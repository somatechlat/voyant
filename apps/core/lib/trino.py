"""
Trino client with read-only query enforcement.

All SQL is validated against a denylist of destructive keywords before execution.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from typing import Any

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Trino SQL query result."""

    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: int
    query_id: str | None = None


class TrinoClient:
    """Validated, read-only Trino SQL client."""

    def __init__(self):
        settings = get_settings()
        self.host = settings.trino_host
        self.port = settings.trino_port
        self.user = settings.trino_user
        self.catalog = settings.trino_catalog
        self.schema = settings.trino_schema
        self.max_rows = settings.max_query_rows
        self._connection = None

    def _get_connection(self):
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
                raise RuntimeError("Trino client is not installed. Run: pip install 'trino[dbapi]'")
            except Exception as e:
                logger.error(f"Failed to establish connection to Trino: {e}")
                raise
        return self._connection

    def execute(
        self,
        sql: str,
        limit: int | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> QueryResult:
        start_time = time.time()
        # Enforce the maximum allowed row limit.
        limit = min(limit or self.max_rows, self.max_rows)

        self._validate_sql(sql)
        sql_with_limit = self._apply_limit(sql, limit)

        conn = self._get_connection()
        cursor = conn.cursor()
        if parameters:
            cursor.execute(sql_with_limit, parameters)
        else:
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

    @staticmethod
    def _validate_identifier(name: str) -> str:
        """Reject identifiers that contain injection-viable characters."""
        if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", name):
            raise ValueError(
                f"Invalid identifier: {name!r}. "
                "Only alphanumeric characters and underscores are allowed."
            )
        return name

    def get_tables(self, schema: str | None = None) -> list[str]:
        target_schema = self._validate_identifier(schema or self.schema)
        result = self.execute(f"SHOW TABLES FROM {target_schema}")
        return [row[0] for row in result.rows]

    def get_columns(self, table: str, schema: str | None = None) -> list[dict[str, Any]]:
        target_schema = self._validate_identifier(schema or self.schema)
        safe_table = self._validate_identifier(table)
        result = self.execute(f"DESCRIBE {target_schema}.{safe_table}")
        columns = []
        for row in result.rows:
            if not row:
                continue
            columns.append({"name": row[0], "type": row[1] if len(row) > 1 else ""})
        return columns

    def _validate_sql(self, sql: str) -> None:
        """
        Perform security validation on a SQL string to prevent destructive queries.

        Enforces read-only query policy using prefix allowlist and keyword denylist.
        Strips SQL comments before validation to prevent bypass.
        Blocks multi-statement injection via semicolons.

        Args:
            sql: The SQL string to validate.

        Raises:
            ValueError: If the query is not a read-only query or contains forbidden keywords.
        """
        # Block multi-statement injection — semicolons only allowed at the very end
        # (Trailing semicolon is harmless and commonly added by tools)
        semicolon_body = sql.rstrip().rstrip(";")
        if ";" in semicolon_body:
            raise ValueError("Multi-statement queries are not allowed (semicolon detected).")

        # Strip single-line comments (-- ...) and multi-line comments before validating
        stripped = re.sub(r"--[^\n]*", "", sql)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.DOTALL)
        sql_upper = stripped.strip().upper()

        allowed_prefixes = ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")
        if not sql_upper.startswith(allowed_prefixes):
            raise ValueError(
                "Invalid query type. Only SELECT, WITH, SHOW, DESCRIBE, and EXPLAIN are allowed."
            )

        forbidden_keywords = [
            # DDL — schema mutation
            "DROP ",
            "CREATE ",
            "ALTER ",
            "TRUNCATE ",
            "RENAME ",
            # DML — data mutation
            "DELETE ",
            "INSERT ",
            "UPDATE ",
            "MERGE ",
            "UPSERT ",
            # Privilege escalation
            "GRANT ",
            "REVOKE ",
            # Session / procedural manipulation
            "SET ",
            "RESET ",
            "CALL ",
            "EXECUTE ",
            "PREPARE ",
            "DEALLOCATE ",
            # UNION-based exfiltration (covers UNION SELECT and UNION ALL SELECT)
            "UNION ",
            # Exfiltration / injection vectors
            "INTO OUTFILE",
            "INTO DUMPFILE",
            "LOAD_FILE(",
            "BENCHMARK(",
            "SLEEP(",
            "WAITFOR DELAY",
            "PG_SLEEP(",
            "DBMS_PIPE.RECEIVE_MESSAGE(",
        ]
        for kw in forbidden_keywords:
            if kw in sql_upper:
                raise ValueError(f"Forbidden SQL keyword detected: '{kw.strip()}'")

    def _apply_limit(self, sql: str, limit: int) -> str:
        # Do not modify the query if a LIMIT clause already exists.
        if " LIMIT " in sql.upper():
            return sql
        # Wrap the original query and apply the system limit.
        return f"SELECT * FROM ({sql}) AS _q LIMIT {limit}"

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
            logger.info("Trino connection closed.")


# Singleton client instance for application-wide use.
_client: TrinoClient | None = None


def get_trino_client() -> TrinoClient:
    global _client
    if _client is None:
        _client = TrinoClient()
    return _client
