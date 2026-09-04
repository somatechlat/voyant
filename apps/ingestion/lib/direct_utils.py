"""File-to-DuckDB ingestion (CSV, JSON, Parquet, Excel)."""

import logging
import os
from typing import Any

import duckdb
import pandas as pd

from apps.core.lib.errors import IngestionError

logger = logging.getLogger(__name__)


class DirectFileIngester:
    """
    A utility class designed to ingest structured data files directly into a DuckDB database.

    This ingester supports various common file formats and automatically creates
    or appends data to specified tables within the DuckDB instance.
    """

    def __init__(self, db_path: str = ":memory:"):
        """
        Initializes the DirectFileIngester with a connection to a DuckDB database.

        Args:
            db_path (str, optional): The path to the DuckDB database file. If ":memory:",
                                     an in-memory database will be used. Defaults to ":memory:".
        """
        self.conn = duckdb.connect(db_path)

    def ingest_file(self, file_path: str, table_name: str) -> dict[str, Any]:
        """
        Ingests a data file into a specified DuckDB table.

        The file format is automatically detected based on its extension (CSV, JSON, Parquet, Excel).
        If the table does not exist, it will be created. Data is loaded using DuckDB's
        native `read_*_auto` functions or Pandas for Excel.

        Args:
            file_path (str): The full path to the data file to ingest.
            table_name (str): The name of the table in DuckDB where the data will be loaded.

        Returns:
            Dict[str, Any]: A dictionary containing the ingestion status,
                            the target table name, row count, and source file path.

        Raises:
            IngestionError: If the file is not found, the extension is unsupported,
                            or an error occurs during the ingestion process.
        """
        if not os.path.exists(file_path):
            raise IngestionError("VYNT-8001", f"File not found: {file_path}", file_path=file_path)

        _, ext = os.path.splitext(file_path)
        ext = ext.lower()

        try:
            if ext == ".csv":
                self.conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_csv_auto('{file_path}')"
                )
            elif ext == ".json":
                self.conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_json_auto('{file_path}')"
                )
            elif ext == ".parquet":
                self.conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM read_parquet('{file_path}')"
                )
            elif ext in [".xlsx", ".xls"]:
                # For Excel files, use pandas for parsing, then load into DuckDB.
                pd.read_excel(file_path)  # noqa: F841 - DuckDB references this DataFrame directly
                self.conn.execute(f"CREATE TABLE IF NOT EXISTS {table_name} AS SELECT * FROM df")
            else:
                raise IngestionError(
                    "VYNT-8002",
                    f"Unsupported file extension: {ext}. Supported types: CSV, JSON, Parquet, XLSX, XLS.",
                    format=ext,
                )

            # Verify and return the count of rows ingested.
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[  # type: ignore[index]
                0
            ]

            logger.info(
                f"Successfully ingested {count} rows from {file_path} into table {table_name}."
            )
            return {
                "status": "success",
                "table": table_name,
                "rows": count,
                "source": file_path,
            }

        except Exception as e:
            logger.error(f"Failed to ingest file '{file_path}' into table '{table_name}': {e}")
            raise IngestionError(
                "VYNT-8003", f"Direct ingestion failed for {file_path}: {e}"
            ) from e
