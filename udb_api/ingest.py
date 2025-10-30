"""Unstructured document ingestion utilities.

Uses `unstructured` library to parse supported document types into text fragments
which are then inserted into DuckDB for downstream analysis.
"""
from __future__ import annotations
from typing import List, Dict, Any
import duckdb
import os

try:  # runtime optional safety
    from unstructured.partition.auto import partition  # type: ignore
except Exception:  # pragma: no cover
    partition = None  # type: ignore

def ingest_file(path: str, con: duckdb.DuckDBPyConnection, table: str = "doc_fragments") -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    if partition is None:
        raise RuntimeError("unstructured library not available")
    elements = partition(filename=path)
    rows: List[Dict[str, Any]] = []
    for e in elements:
        txt = getattr(e, "text", None)
        if not txt:
            continue
        rows.append({
            "element_type": e.__class__.__name__,
            "text": txt[:5000],  # cap
            "metadata": str(getattr(e, "metadata", ""))[:2000],
            "source_file": os.path.basename(path),
        })
    if not rows:
        return {"table": table, "fragments": 0}
    # Create table if not exists
    con.execute(f"CREATE TABLE IF NOT EXISTS {table} (element_type TEXT, text TEXT, metadata TEXT, source_file TEXT)")
    insert_values = ",".join([
        "(" + ",".join([f"'{r['element_type'].replace("'", "''")}'", f"'{r['text'].replace("'", "''")}'", f"'{r['metadata'].replace("'", "''")}'", f"'{r['source_file'].replace("'", "''")}'"]) + ")"
        for r in rows
    ])
    con.execute(f"INSERT INTO {table} VALUES {insert_values}")
    return {"table": table, "fragments": len(rows)}
