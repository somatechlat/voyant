"""
SQL API Routes

Guarded SQL execution via Trino.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from voyant.core import get_trino_client, QueryResult

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sql")


# =============================================================================
# Models
# =============================================================================

class SqlRequest(BaseModel):
    sql: str = Field(..., description="SQL query (SELECT only)")
    limit: int = Field(default=1000, ge=1, le=10000)
    parameters: Optional[Dict[str, Any]] = None


class SqlResponse(BaseModel):
    columns: List[str]
    rows: List[List[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: int
    query_id: Optional[str] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/query", response_model=SqlResponse)
async def execute_sql(request: SqlRequest):
    """Execute guarded SQL query via Trino."""
    try:
        client = get_trino_client()
        result = client.execute(request.sql, limit=request.limit)
        
        return SqlResponse(
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            truncated=result.truncated,
            execution_time_ms=result.execution_time_ms,
            query_id=result.query_id,
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("SQL execution failed")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/tables")
async def list_tables(schema: Optional[str] = None):
    """List available tables."""
    try:
        client = get_trino_client()
        tables = client.get_tables(schema)
        return {"tables": tables, "schema": schema or client.schema}
    except Exception as e:
        logger.exception("Failed to list tables")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table}/columns")
async def get_columns(table: str, schema: Optional[str] = None):
    """Get columns for a table."""
    try:
        client = get_trino_client()
        columns = client.get_columns(table, schema)
        return {"table": table, "columns": columns}
    except Exception as e:
        logger.exception(f"Failed to get columns for {table}")
        raise HTTPException(status_code=500, detail=str(e))
