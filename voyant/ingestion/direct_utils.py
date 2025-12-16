"""
Direct Ingestion Utilities

Utilities for direct file ingestion (CSV, JSON, Excel, Parquet) into DuckDB/Arrow.
Adheres to Vibe Coding Rules: Real data structures using Pandas/DuckDB.
"""
import os
import logging
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import duckdb

from voyant.core.errors import IngestionError

logger = logging.getLogger(__name__)

class DirectFileIngester:
    """Ingests structured files directly into DuckDB."""
    
    def __init__(self, db_path: str = ":memory:"):
        self.conn = duckdb.connect(db_path)

    def ingest_file(self, file_path: str, table_name: str) -> Dict[str, Any]:
        """
        Ingest a file into a DuckDB table.
        Auto-detects format from extension.
        """
        if not os.path.exists(file_path):
            raise IngestionError("VYNT-4004", f"File not found: {file_path}")

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        try:
            if ext == ".csv":
                self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_csv_auto('{file_path}')")
            elif ext == ".json":
                self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_json_auto('{file_path}')")
            elif ext == ".parquet":
                self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_parquet('{file_path}')")
            elif ext in [".xlsx", ".xls"]:
                # DuckDB has an excel extension but it's cleaner to use pandas for complex excel
                df = pd.read_excel(file_path)
                self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df")
            else:
                 raise IngestionError("VYNT-4007", f"Unsupported file extension: {ext}")
            
            # Verify row count
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            
            return {
                "status": "success",
                "table": table_name,
                "rows": count,
                "source": file_path
            }

        except Exception as e:
            logger.error(f"Failed to ingest {file_path}: {e}")
            raise IngestionError("VYNT-4008", f"Direct ingestion failed: {e}")
