"""
Trino Client for Voyant

Production SQL execution via Trino (SQL federation over Iceberg, Druid, PostgreSQL).
This is the ONLY SQL execution path in Voyant v3.0.0.
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
    """Result of a SQL query."""
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: int
    query_id: Optional[str] = None


class TrinoClient:
    """
    Trino client for SQL execution.
    
    Federates queries across:
    - Iceberg (data lake tables)
    - PostgreSQL (metadata)
    - Druid (OLAP cubes)
    """
    
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
        """Get or create Trino connection."""
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
                raise RuntimeError("trino package not installed. Run: pip install trino")
            except Exception as e:
                logger.error(f"Trino connection failed: {e}")
                raise
        return self._connection
    
    def execute(self, sql: str, limit: Optional[int] = None) -> QueryResult:
        """Execute a validated SQL query."""
        start_time = time.time()
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
            query_id=getattr(cursor, 'query_id', None),
        )
    
    def _validate_sql(self, sql: str) -> None:
        """Validate SQL is safe."""
        sql_upper = sql.strip().upper()
        
        allowed = ("SELECT", "WITH", "SHOW", "DESCRIBE", "EXPLAIN")
        if not any(sql_upper.startswith(p) for p in allowed):
            raise ValueError("Only SELECT queries allowed")
        
        forbidden = ["DROP ", "DELETE ", "TRUNCATE ", "INSERT ", "UPDATE ", "ALTER ", "CREATE TABLE", "GRANT ", "REVOKE "]
        for kw in forbidden:
            if kw in sql_upper:
                raise ValueError(f"Forbidden keyword: {kw.strip()}")
    
    def _apply_limit(self, sql: str, limit: int) -> str:
        """Apply LIMIT if not present."""
        if " LIMIT " in sql.upper():
            return sql
        return f"SELECT * FROM ({sql}) AS _q LIMIT {limit}"
    
    def close(self):
        """Close connection."""
        if self._connection:
            self._connection.close()
            self._connection = None


_client: Optional[TrinoClient] = None

def get_trino_client() -> TrinoClient:
    """Get singleton Trino client."""
    global _client
    if _client is None:
        _client = TrinoClient()
    return _client
