"""KPI engine supporting multi-query execution with safety checks and timing."""
from __future__ import annotations
import time
import duckdb
from typing import List, Dict, Any, Optional
from .security import validate_sql


def execute_kpis(con: duckdb.DuckDBPyConnection, kpi_spec: Optional[Any]) -> List[Dict[str, Any]]:
    """Execute KPI specifications.

    kpi_spec may be:
      - None (returns empty list)
      - str (single SQL)
      - list of {name, sql}
    Returns list of {name, rows, columns, executionMs, rowCount}.
    """
    if not kpi_spec:
        return []
    specs: List[Dict[str, str]]
    if isinstance(kpi_spec, str):
        specs = [{"name": "kpi_1", "sql": kpi_spec}]
    elif isinstance(kpi_spec, list):
        specs = []
        for i, item in enumerate(kpi_spec, start=1):
            if isinstance(item, str):
                specs.append({"name": f"kpi_{i}", "sql": item})
            else:
                name = item.get("name") or f"kpi_{i}"
                sql = item.get("sql")
                if not sql:
                    continue
                specs.append({"name": name, "sql": sql})
    else:
        return []

    results: List[Dict[str, Any]] = []
    for spec in specs:
        sql = spec["sql"].strip()
        validate_sql(sql)
        start = time.time()
        df = con.execute(sql).df()
        elapsed = int((time.time() - start) * 1000)
        # truncate rows to prevent huge payloads
        max_rows = 5000
        truncated = len(df) > max_rows
        if truncated:
            df = df.head(max_rows)
        results.append(
            {
                "name": spec["name"],
                "columns": list(df.columns),
                "rows": df.to_records(index=False).tolist(),
                "rowCount": len(df),
                "executionMs": elapsed,
                "truncated": truncated,
            }
        )
    return results
