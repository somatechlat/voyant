"""Registry of available statistical and analytical algorithms.

This catalog allows agents to discover capabilities (regressions, forecasting, etc.)
and execute them against the data.
"""
from typing import Dict, Any, Callable, List, Optional
from pydantic import BaseModel
import duckdb
import re

class AlgorithmParam(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True

class AlgorithmSpec(BaseModel):
    name: str
    description: str
    params: List[AlgorithmParam]
    tags: List[str] = []

class AlgorithmRegistry:
    _registry: Dict[str, Any] = {}

    @classmethod
    def register(cls, name: str, description: str, params: List[AlgorithmParam], tags: List[str] = None):
        def decorator(func: Callable):
            cls._registry[name] = {
                "spec": AlgorithmSpec(name=name, description=description, params=params, tags=tags or []),
                "func": func
            }
            return func
        return decorator

    @classmethod
    def list_algorithms(cls) -> List[AlgorithmSpec]:
        return [item["spec"] for item in cls._registry.values()]

    @classmethod
    def get_algorithm(cls, name: str) -> Optional[Any]:
        return cls._registry.get(name)

    @classmethod
    def execute(cls, name: str, con: duckdb.DuckDBPyConnection, table: str, params: Dict[str, Any]) -> Any:
        algo = cls._registry.get(name)
        if not algo:
            raise ValueError(f"Algorithm '{name}' not found")
        # Validate params exist
        spec = algo["spec"]
        for p in spec.params:
            if p.required and p.name not in params:
                raise ValueError(f"Missing required parameter: {p.name}")

        return algo["func"](con, table, params)

def _quote_identifier(identifier: str) -> str:
    """Safely quote a SQL identifier (table or column name)."""
    return f'"{identifier.replace("\"", "\"\"")}"'

def _validate_columns(con: duckdb.DuckDBPyConnection, table: str, columns: List[str]):
    """Ensure all columns exist in the table to prevent injection/errors."""
    # Get schema
    # Using describe is safer than assuming table structure
    quoted_table = _quote_identifier(table)
    try:
        # We rely on DuckDB to throw if table doesn't exist when we DESCRIBE it
        schema = con.execute(f"DESCRIBE {quoted_table}").fetchall()
    except Exception:
        raise ValueError(f"Table {table} not found or invalid")

    valid_cols = {r[0] for r in schema}
    for col in columns:
        if col not in valid_cols:
            raise ValueError(f"Column '{col}' not found in table '{table}'")

# --- Implementations ---

@AlgorithmRegistry.register(
    name="correlation_matrix",
    description="Compute the correlation matrix for all numeric columns in the table.",
    params=[],
    tags=["statistics", "exploratory"]
)
def algo_correlation_matrix(con: duckdb.DuckDBPyConnection, table: str, params: Dict[str, Any]):
    quoted_table = _quote_identifier(table)

    # Identify numeric columns
    # DuckDB DESCRIBE returns column_name, column_type, ...
    schema = con.execute(f"DESCRIBE {quoted_table}").fetchall()

    # improved type checking
    numeric_types = {'INTEGER', 'BIGINT', 'DOUBLE', 'FLOAT', 'REAL', 'SMALLINT', 'TINYINT', 'HUGEINT'}
    numeric_cols = []
    for r in schema:
        col_name = r[0]
        col_type = r[1].upper()
        # Handle DECIMAL(x,y)
        if col_type in numeric_types or col_type.startswith("DECIMAL"):
            numeric_cols.append(col_name)

    if not numeric_cols:
        return {"error": "No numeric columns found"}

    results = []
    for i, col1 in enumerate(numeric_cols):
        q_col1 = _quote_identifier(col1)
        for col2 in numeric_cols[i+1:]:
            q_col2 = _quote_identifier(col2)
            try:
                val = con.execute(f"SELECT corr({q_col1}, {q_col2}) FROM {quoted_table}").fetchone()[0]
                results.append({"col1": col1, "col2": col2, "correlation": val})
            except Exception:
                # Fallback if corr fails (e.g. incompatible types despite check)
                results.append({"col1": col1, "col2": col2, "correlation": None})

    return {"matrix": results}

@AlgorithmRegistry.register(
    name="linear_regression",
    description="Simple linear regression (y = mx + b) between two columns.",
    params=[
        AlgorithmParam(name="target", type="string", description="The dependent variable (y)"),
        AlgorithmParam(name="feature", type="string", description="The independent variable (x)")
    ],
    tags=["regression", "statistics"]
)
def algo_linear_regression(con: duckdb.DuckDBPyConnection, table: str, params: Dict[str, Any]):
    y = params["target"]
    x = params["feature"]

    _validate_columns(con, table, [y, x])

    quoted_table = _quote_identifier(table)
    qy = _quote_identifier(y)
    qx = _quote_identifier(x)

    # DuckDB: regr_slope(y, x), regr_intercept(y, x), regr_r2(y, x)
    sql = f"""
        SELECT
            regr_slope({qy}, {qx}) as slope,
            regr_intercept({qy}, {qx}) as intercept,
            regr_r2({qy}, {qx}) as r_squared,
            regr_count({qy}, {qx}) as count
        FROM {quoted_table}
    """
    row = con.execute(sql).fetchone()
    if not row:
        return {"error": "Computation failed"}

    return {
        "slope": row[0],
        "intercept": row[1],
        "r_squared": row[2],
        "count": row[3],
        "equation": f"{y} = {row[0]:.4f} * {x} + {row[1]:.4f}"
    }

@AlgorithmRegistry.register(
    name="summary_stats",
    description="Calculate detailed summary statistics for a specific column.",
    params=[
        AlgorithmParam(name="column", type="string", description="The column to analyze")
    ],
    tags=["statistics", "exploratory"]
)
def algo_summary_stats(con: duckdb.DuckDBPyConnection, table: str, params: Dict[str, Any]):
    col = params["column"]

    _validate_columns(con, table, [col])

    quoted_table = _quote_identifier(table)
    qcol = _quote_identifier(col)

    sql = f"""
        SELECT
            min({qcol}) as min_val,
            max({qcol}) as max_val,
            avg({qcol}) as mean,
            stddev({qcol}) as stddev,
            median({qcol}) as median,
            quantile_cont({qcol}, 0.25) as q25,
            quantile_cont({qcol}, 0.75) as q75
        FROM {quoted_table}
    """
    row = con.execute(sql).fetchone()
    return {
        "min": row[0],
        "max": row[1],
        "mean": row[2],
        "stddev": row[3],
        "median": row[4],
        "q25": row[5],
        "q75": row[6]
    }
