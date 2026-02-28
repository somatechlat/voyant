import logging
from typing import Any, Dict, List, Optional

from ninja import Field, Router, Schema
from ninja.errors import HttpError

from apps.core.api_utils import auth_guard
from apps.core.lib.trino import get_trino_client

logger = logging.getLogger(__name__)
sql_router = Router(tags=["sql"])


class SqlRequest(Schema):
    """Request schema for executing an ad-hoc SQL query."""

    sql: str = Field(
        ...,
        description="The SQL query string to execute. Only SELECT queries are permitted.",
    )
    limit: int = Field(
        1000,
        ge=1,
        le=10000,
        description="The maximum number of rows to return from the query.",
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional parameters to pass to the SQL query (e.g., for parameterized queries).",
    )


class SqlResponse(Schema):
    """Response schema for the result of an executed SQL query."""

    columns: List[str] = Field(
        ..., description="A list of column names returned by the query."
    )
    rows: List[List[Any]] = Field(
        ...,
        description="A list of lists, where each inner list represents a row of data.",
    )
    row_count: int = Field(..., description="The total number of rows returned.")
    truncated: bool = Field(
        ...,
        description="True if the result set was truncated due to the specified limit.",
    )
    execution_time_ms: int = Field(
        ..., description="The time taken to execute the query in milliseconds."
    )
    query_id: Optional[str] = Field(
        None, description="The unique ID assigned to the query by the Trino engine."
    )


@sql_router.post(
    "/query", response=SqlResponse, summary="Execute Ad-Hoc SQL Query", auth=auth_guard
)
def execute_sql(request, payload: SqlRequest):
    """
    Executes an ad-hoc SQL query against the Trino engine for the current tenant.

    This endpoint strictly enforces a read-only policy via the underlying `TrinoClient`
    to prevent any data modification or destructive operations.
    """
    # Security: Tenant validation and SQL query safety are handled by underlying TrinoClient.
    try:
        client = get_trino_client()
        result = client.execute(payload.sql, limit=payload.limit)
        return SqlResponse(
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            truncated=result.truncated,
            execution_time_ms=result.execution_time_ms,
            query_id=result.query_id,
        )
    except ValueError as exc:
        raise HttpError(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HttpError(503, str(exc)) from exc
    except Exception as exc:
        logger.exception("SQL execution failed")
        raise HttpError(500, f"Query failed due to internal error: {exc}") from exc


@sql_router.get(
    "/tables",
    response=Dict[str, Any],
    summary="List Available Tables",
    auth=auth_guard,
)
def list_tables(request, schema: Optional[str] = None):
    """
    Retrieves a list of all tables accessible via the Trino engine for the current tenant.
    """
    try:
        client = get_trino_client()
        tables = client.get_tables(schema)
        return {"tables": tables, "schema": schema or client.schema}
    except Exception as exc:
        logger.exception("Failed to list tables")
        raise HttpError(500, f"Failed to list tables: {exc}") from exc


@sql_router.get(
    "/tables/{table}/columns",
    response=Dict[str, Any],
    summary="Get Table Columns",
    auth=auth_guard,
)
def get_columns(request, table: str, schema: Optional[str] = None):
    """
    Retrieves the column details for a specific table accessible via the Trino engine.
    """
    try:
        client = get_trino_client()
        columns = client.get_columns(table, schema)
        return {"table": table, "columns": columns}
    except Exception as exc:
        logger.exception("Failed to get columns for table '%s'", table)
        raise HttpError(
            500, f"Failed to get columns for table '{table}': {exc}"
        ) from exc
