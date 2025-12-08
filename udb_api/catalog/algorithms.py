"""Registry of available statistical and analytical algorithms.

This catalog allows agents to discover capabilities (regressions, forecasting, etc.)
and execute them against the data.
"""
from typing import Dict, Any, Callable, List, Optional
from pydantic import BaseModel
import duckdb
import re
import math
from scipy import stats  # We use scipy for t-test distributions if needed, or pure SQL

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

@AlgorithmRegistry.register(
    name="z_score",
    description="Add a new column with z-score normalization: (x - mean) / stddev.",
    params=[
        AlgorithmParam(name="column", type="string", description="The column to normalize"),
        AlgorithmParam(name="new_column", type="string", description="Name of the new column to create")
    ],
    tags=["transform", "normalization"]
)
def algo_z_score(con: duckdb.DuckDBPyConnection, table: str, params: Dict[str, Any]):
    col = params["column"]
    new_col = params["new_column"]

    _validate_columns(con, table, [col])

    quoted_table = _quote_identifier(table)
    qcol = _quote_identifier(col)
    qnew = _quote_identifier(new_col)

    # 1. Check if column exists, if so error (or replace?) - let's error for safety
    try:
        con.execute(f"SELECT {qnew} FROM {quoted_table} LIMIT 1")
        return {"error": f"Column {new_col} already exists"}
    except Exception:
        pass # Good, it doesn't exist

    # 2. Add column
    try:
        con.execute(f"ALTER TABLE {quoted_table} ADD COLUMN {qnew} DOUBLE")
    except Exception as e:
        return {"error": f"Failed to add column: {e}"}

    # 3. Update with Z-Score
    # DuckDB window functions make this easy: (x - AVG(x) OVER()) / STDDEV(x) OVER()
    sql = f"""
        UPDATE {quoted_table}
        SET {qnew} = (
            {qcol} - (SELECT avg({qcol}) FROM {quoted_table})
        ) / NULLIF((SELECT stddev({qcol}) FROM {quoted_table}), 0)
    """
    con.execute(sql)

    return {"status": "success", "new_column": new_col}

@AlgorithmRegistry.register(
    name="moving_average",
    description="Calculate simple moving average for a column over a time window.",
    params=[
        AlgorithmParam(name="value_column", type="string", description="Column to smooth"),
        AlgorithmParam(name="date_column", type="string", description="Column to order by"),
        AlgorithmParam(name="window", type="integer", description="Number of periods (e.g., 7)"),
        AlgorithmParam(name="new_column", type="string", description="Name of the new column")
    ],
    tags=["time_series", "transform"]
)
def algo_moving_average(con: duckdb.DuckDBPyConnection, table: str, params: Dict[str, Any]):
    val_col = params["value_column"]
    date_col = params["date_column"]
    window = int(params["window"])
    new_col = params["new_column"]

    _validate_columns(con, table, [val_col, date_col])

    quoted_table = _quote_identifier(table)
    qval = _quote_identifier(val_col)
    qdate = _quote_identifier(date_col)
    qnew = _quote_identifier(new_col)

    try:
        con.execute(f"SELECT {qnew} FROM {quoted_table} LIMIT 1")
        return {"error": f"Column {new_col} already exists"}
    except Exception:
        pass

    try:
        con.execute(f"ALTER TABLE {quoted_table} ADD COLUMN {qnew} DOUBLE")
    except Exception as e:
         return {"error": f"Failed to add column: {e}"}

    # CTE update approach is complex in DuckDB for generic tables lacking primary keys.
    # However, DuckDB supports UPDATE FROM...
    # But to do it safely without a PK is hard.
    # PROPOSAL: We will create a VIEW or a NEW TABLE instead?
    # The prompt implies "add a new column".
    # Let's assume we can match on rowid if needed, but DuckDB exposes rowid.

    sql = f"""
        UPDATE {quoted_table}
        SET {qnew} = calc.ma
        FROM (
            SELECT
                rowid,
                avg({qval}) OVER (
                    ORDER BY {qdate}
                    ROWS BETWEEN {window - 1} PRECEDING AND CURRENT ROW
                ) as ma
            FROM {quoted_table}
        ) as calc
        WHERE {quoted_table}.rowid = calc.rowid
    """
    con.execute(sql)
    return {"status": "success", "new_column": new_col}

@AlgorithmRegistry.register(
    name="t_test_ind",
    description="Independent T-Test to compare means of two groups (e.g., A/B test).",
    params=[
        AlgorithmParam(name="value_column", type="string", description="Metric to compare (e.g., sales)"),
        AlgorithmParam(name="group_column", type="string", description="Column defining groups (e.g., campaign_id)"),
        AlgorithmParam(name="group_a", type="string", description="Value for Group A"),
        AlgorithmParam(name="group_b", type="string", description="Value for Group B")
    ],
    tags=["hypothesis_test", "statistics"]
)
def algo_t_test_ind(con: duckdb.DuckDBPyConnection, table: str, params: Dict[str, Any]):
    val_col = params["value_column"]
    grp_col = params["group_column"]
    ga = params["group_a"]
    gb = params["group_b"]

    _validate_columns(con, table, [val_col, grp_col])
    quoted_table = _quote_identifier(table)
    qval = _quote_identifier(val_col)
    qgrp = _quote_identifier(grp_col)

    # Calculate stats for A
    sql_a = f"""
        SELECT count({qval}), avg({qval}), stddev({qval})
        FROM {quoted_table}
        WHERE {qgrp} = ?
    """
    stats_a = con.execute(sql_a, [ga]).fetchone()

    # Calculate stats for B
    sql_b = f"""
        SELECT count({qval}), avg({qval}), stddev({qval})
        FROM {quoted_table}
        WHERE {qgrp} = ?
    """
    stats_b = con.execute(sql_b, [gb]).fetchone()

    n1, m1, s1 = stats_a
    n2, m2, s2 = stats_b

    if n1 < 2 or n2 < 2:
         return {"error": "Insufficient sample size (need >= 2 per group)"}

    # Welch's T-Test (does not assume equal variance)
    # t = (m1 - m2) / sqrt(s1^2/n1 + s2^2/n2)

    numerator = m1 - m2
    denominator = math.sqrt((s1**2 / n1) + (s2**2 / n2))

    if denominator == 0:
        return {"t_statistic": 0.0, "p_value": 1.0, "significant": False}

    t_stat = numerator / denominator

    # Degrees of freedom (Welch-Satterthwaite equation)
    v1 = s1**2 / n1
    v2 = s2**2 / n2
    dof = ((v1 + v2)**2) / ((v1**2 / (n1-1)) + (v2**2 / (n2-1)))

    # P-value from scipy if available, else approximate or return t-stat only
    # We imported stats from scipy above
    try:
        from scipy import stats
        p_value = 2 * (1 - stats.t.cdf(abs(t_stat), dof)) # Two-tailed
    except ImportError:
        p_value = None # Fallback if scipy missing

    return {
        "group_a": {"n": n1, "mean": m1, "std": s1},
        "group_b": {"n": n2, "mean": m2, "std": s2},
        "t_statistic": t_stat,
        "dof": dof,
        "p_value": p_value,
        "significant": bool(p_value < 0.05) if p_value is not None else None
    }
