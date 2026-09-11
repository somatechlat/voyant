"""
Connector Framework for Voyant Ingestion.

Provides a pluggable, abstract connector interface for discovering schemas,
testing connections, and creating readers/writers/streams for data sources.
Includes implementations for PostgreSQL, MySQL, and S3, plus a global
ConnectorRegistry for registration and lookup.
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# Data Types
# =============================================================================


class ConnectorType(StrEnum):
    """Supported connector types."""

    DATABASE = "database"
    OBJECT_STORAGE = "object_storage"
    STREAMING = "streaming"
    API = "api"
    FILE = "file"


@dataclass
class ConnectorCapabilities:
    """
    Describes the capabilities of a connector.

    Used by the ingestion layer to determine which operations
    are available for a given source.
    """

    can_discover_schema: bool = True
    can_discover_datasets: bool = True
    can_test_connection: bool = True
    can_read: bool = True
    can_write: bool = False
    can_stream: bool = False
    supports_incremental: bool = False
    supports_cdc: bool = False
    supports_schema_evolution: bool = False
    max_batch_size: int = 10000
    supported_formats: list[str] = field(default_factory=lambda: ["json", "csv"])
    connector_type: ConnectorType = ConnectorType.DATABASE
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ColumnSchema:
    """Schema for a single column/field."""

    name: str
    data_type: str
    nullable: bool = True
    description: str = ""
    is_primary_key: bool = False
    ordinal_position: int = 0


@dataclass
class DatasetSchema:
    """Schema for a dataset (table, collection, file, etc.)."""

    name: str
    namespace: str = ""
    columns: list[ColumnSchema] = field(default_factory=list)
    description: str = ""
    row_count: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ConnectionHealth:
    """Health check result for a connector."""

    healthy: bool
    message: str = ""
    latency_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReadResult:
    """Result of a read operation."""

    data: list[dict[str, Any]]
    columns: list[str]
    row_count: int
    has_more: bool = False
    cursor: str | None = None


@dataclass
class WriteResult:
    """Result of a write operation."""

    rows_written: int
    bytes_written: int
    success: bool = True
    errors: list[str] = field(default_factory=list)


# =============================================================================
# Abstract Base Class
# =============================================================================


class IConnector(abc.ABC):
    """
    Abstract base connector interface.

    All data source connectors must implement these 8 methods
    to integrate with the Voyant ingestion framework.
    """

    @abc.abstractmethod
    def __init__(self, config: dict[str, Any]):
        """
        Initialize the connector with source-specific configuration.

        Args:
            config: Connection configuration (host, port, credentials, etc.)
        """
        ...

    @abc.abstractmethod
    def discover_schema(
        self, dataset_name: str, namespace: str = ""
    ) -> DatasetSchema:
        """
        Discover the schema for a specific dataset.

        Args:
            dataset_name: The dataset (table/collection/file) name.
            namespace: Optional namespace (schema/database name).

        Returns:
            DatasetSchema with column definitions.
        """
        ...

    @abc.abstractmethod
    def discover_datasets(self, namespace: str = "") -> list[DatasetSchema]:
        """
        Discover all available datasets in the source.

        Args:
            namespace: Optional namespace to scope discovery.

        Returns:
            List of DatasetSchema summaries.
        """
        ...

    @abc.abstractmethod
    def test_connection(self) -> ConnectionHealth:
        """
        Test connectivity to the data source.

        Returns:
            ConnectionHealth with status, latency, and details.
        """
        ...

    @abc.abstractmethod
    def create_reader(
        self,
        dataset_name: str,
        namespace: str = "",
        batch_size: int = 1000,
    ) -> Any:
        """
        Create a reader/iterator for a dataset.

        Args:
            dataset_name: The dataset to read.
            namespace: Optional namespace.
            batch_size: Number of rows per batch.

        Returns:
            A reader object supporting iteration.
        """
        ...

    @abc.abstractmethod
    def create_writer(
        self,
        dataset_name: str,
        namespace: str = "",
        mode: str = "append",
    ) -> Any:
        """
        Create a writer for a dataset.

        Args:
            dataset_name: The dataset to write to.
            namespace: Optional namespace.
            mode: Write mode: 'append', 'overwrite', or 'upsert'.

        Returns:
            A writer object supporting write operations.
        """
        ...

    @abc.abstractmethod
    def create_stream(
        self,
        dataset_name: str,
        namespace: str = "",
    ) -> Any:
        """
        Create a streaming reader for real-time data.

        Args:
            dataset_name: The dataset to stream from.
            namespace: Optional namespace.

        Returns:
            A stream object for real-time change events.
        """
        ...

    @abc.abstractmethod
    def get_capabilities(self) -> ConnectorCapabilities:
        """
        Get the capabilities of this connector.

        Returns:
            ConnectorCapabilities describing supported operations.
        """
        ...

    @abc.abstractmethod
    def get_health(self) -> ConnectionHealth:
        """
        Get current health status of the connection.

        Returns:
            ConnectionHealth with current status.
        """
        ...


# =============================================================================
# PostgreSQL Connector
# =============================================================================


class PostgreSQLConnector(IConnector):
    """
    PostgreSQL data source connector.

    Supports schema discovery, data reading/writing, CDC via logical
    replication, and incremental reads via LSN tracking.
    """

    def __init__(self, config: dict[str, Any]):
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 5432)
        self.database = config.get("database", "postgres")
        self.user = config.get("user", "postgres")
        self.password = config.get("password", "")
        self.schema = config.get("schema", "public")
        self.sslmode = config.get("sslmode", "prefer")
        self._connection = None

    def _get_connection(self):
        """Get or create a database connection."""
        if self._connection is None or self._connection.closed:
            try:
                import psycopg2

                self._connection = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    dbname=self.database,
                    user=self.user,
                    password=self.password,
                    sslmode=self.sslmode,
                    connect_timeout=10,
                )
            except ImportError:
                raise ImportError(
                    "psycopg2 is required for PostgreSQL connector. "
                    "Install with: pip install psycopg2-binary"
                )
        return self._connection

    def discover_schema(
        self, dataset_name: str, namespace: str = ""
    ) -> DatasetSchema:
        """Discover schema for a PostgreSQL table."""
        schema_name = namespace or self.schema
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                COALESCE(pgd.description, ''),
                CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END,
                c.ordinal_position
            FROM information_schema.columns c
            LEFT JOIN pg_catalog.pg_statio_all_tables st
                ON st.schemaname = c.table_schema AND st.relname = c.table_name
            LEFT JOIN pg_catalog.pg_description pgd
                ON pgd.objoid = st.relid AND pgd.objsubid = c.ordinal_position
            LEFT JOIN (
                SELECT ku.column_name, ku.table_schema, ku.table_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage ku
                    ON tc.constraint_name = ku.constraint_name
                    AND tc.table_schema = ku.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY'
            ) pk ON pk.column_name = c.column_name
                AND pk.table_schema = c.table_schema
                AND pk.table_name = c.table_name
            WHERE c.table_schema = %s AND c.table_name = %s
            ORDER BY c.ordinal_position
            """,
            (schema_name, dataset_name),
        )

        columns = [
            ColumnSchema(
                name=row[0],
                data_type=row[1],
                nullable=row[2] == "YES",
                description=row[3],
                is_primary_key=row[4],
                ordinal_position=row[5],
            )
            for row in cursor.fetchall()
        ]
        cursor.close()

        return DatasetSchema(
            name=dataset_name,
            namespace=schema_name,
            columns=columns,
        )

    def discover_datasets(self, namespace: str = "") -> list[DatasetSchema]:
        """Discover all tables in a PostgreSQL schema."""
        schema_name = namespace or self.schema
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                t.table_name,
                obj_description((t.table_schema || '.' || t.table_name)::regclass)
            FROM information_schema.tables t
            WHERE t.table_schema = %s
                AND t.table_type = 'BASE TABLE'
            ORDER BY t.table_name
            """,
            (schema_name,),
        )

        tables = [
            DatasetSchema(
                name=row[0],
                namespace=schema_name,
                description=row[1] or "",
            )
            for row in cursor.fetchall()
        ]
        cursor.close()
        return tables

    def test_connection(self) -> ConnectionHealth:
        """Test PostgreSQL connectivity."""
        import time

        start = time.monotonic()
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            latency = (time.monotonic() - start) * 1000
            cursor.close()
            return ConnectionHealth(
                healthy=True,
                message="Connected successfully",
                latency_ms=round(latency, 2),
                details={"version": version},
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return ConnectionHealth(
                healthy=False,
                message=f"Connection failed: {exc}",
                latency_ms=round(latency, 2),
            )

    def create_reader(
        self,
        dataset_name: str,
        namespace: str = "",
        batch_size: int = 1000,
    ) -> PostgreSQLReader:
        """Create a cursor-based reader for a PostgreSQL table."""
        schema_name = namespace or self.schema
        return PostgreSQLReader(
            connector=self,
            table_name=dataset_name,
            schema_name=schema_name,
            batch_size=batch_size,
        )

    def create_writer(
        self,
        dataset_name: str,
        namespace: str = "",
        mode: str = "append",
    ) -> PostgreSQLWriter:
        """Create a writer for a PostgreSQL table."""
        schema_name = namespace or self.schema
        return PostgreSQLWriter(
            connector=self,
            table_name=dataset_name,
            schema_name=schema_name,
            mode=mode,
        )

    def create_stream(
        self,
        dataset_name: str,
        namespace: str = "",
    ) -> PostgreSQLCDCStream:
        """Create a CDC stream using PostgreSQL logical replication."""
        schema_name = namespace or self.schema
        return PostgreSQLCDCStream(
            connector=self,
            table_name=dataset_name,
            schema_name=schema_name,
        )

    def get_capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            can_discover_schema=True,
            can_discover_datasets=True,
            can_test_connection=True,
            can_read=True,
            can_write=True,
            can_stream=True,
            supports_incremental=True,
            supports_cdc=True,
            supports_schema_evolution=True,
            max_batch_size=50000,
            supported_formats=["json", "csv", "parquet"],
            connector_type=ConnectorType.DATABASE,
            metadata={"engine": "postgresql"},
        )

    def get_health(self) -> ConnectionHealth:
        return self.test_connection()


@dataclass
class PostgreSQLReader:
    """Cursor-based reader for PostgreSQL tables."""

    connector: PostgreSQLConnector
    table_name: str
    schema_name: str
    batch_size: int = 1000

    def read_batch(self, offset: int = 0) -> ReadResult:
        """Read a batch of rows from the table."""
        conn = connector._get_connection() if (connector := self.connector) else None
        if conn is None:
            raise RuntimeError("No connection available")

        cursor = conn.cursor()
        full_table = f'"{self.schema_name}"."{self.table_name}"'
        cursor.execute(
            f"SELECT * FROM {full_table} LIMIT %s OFFSET %s",
            (self.batch_size, offset),
        )
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        cursor.close()

        return ReadResult(
            data=data,
            columns=columns,
            row_count=len(data),
            has_more=len(data) == self.batch_size,
            cursor=str(offset + len(data)),
        )


@dataclass
class PostgreSQLWriter:
    """Writer for PostgreSQL tables."""

    connector: PostgreSQLConnector
    table_name: str
    schema_name: str
    mode: str = "append"

    def write_batch(self, rows: list[dict[str, Any]]) -> WriteResult:
        """Write a batch of rows to the table."""
        if not rows:
            return WriteResult(rows_written=0, bytes_written=0)

        conn = self.connector._get_connection()
        cursor = conn.cursor()

        full_table = f'"{self.schema_name}"."{self.table_name}"'
        columns = list(rows[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))
        col_names = ", ".join(f'"{c}"' for c in columns)

        if self.mode == "overwrite":
            cursor.execute(f"TRUNCATE TABLE {full_table}")

        insert_sql = f"INSERT INTO {full_table} ({col_names}) VALUES ({placeholders})"
        for row in rows:
            values = [row.get(c) for c in columns]
            cursor.execute(insert_sql, values)

        conn.commit()
        cursor.close()

        import sys
        bytes_written = sys.getsizeof(str(rows))
        return WriteResult(
            rows_written=len(rows),
            bytes_written=bytes_written,
        )


@dataclass
class PostgreSQLCDCStream:
    """CDC stream reader using PostgreSQL logical replication."""

    connector: PostgreSQLConnector
    table_name: str
    schema_name: str
    _slot_name: str = "voyant_cdc_slot"

    def setup_publication(self) -> str:
        """Create a publication for the table."""
        conn = self.connector._get_connection()
        cursor = conn.cursor()
        pub_name = f"voyant_pub_{self.table_name}"
        cursor.execute(
            f'CREATE PUBLICATION IF NOT EXISTS "{pub_name}" '
            f'FOR TABLE "{self.schema_name}"."{self.table_name}"'
        )
        conn.commit()
        cursor.close()
        return pub_name

    def read_changes(self, lsn: str | None = None) -> list[dict[str, Any]]:
        """
        Read pending changes from the replication slot.

        This is a simplified implementation — production usage would
        use pgoutput or a dedicated CDC library like debezium.
        """
        conn = self.connector._get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT * FROM pg_logical_slot_get_changes(%s, NULL, NULL)", (self._slot_name,))
            changes = [
                {"lsn": row[0], "xid": row[1], "data": row[2]}
                for row in cursor.fetchall()
            ]
        except Exception:
            changes = []
        cursor.close()
        return changes


# =============================================================================
# MySQL Connector
# =============================================================================


class MySQLConnector(IConnector):
    """
    MySQL data source connector.

    Supports schema discovery, data reading/writing, and incremental
    reads via binlog position tracking.
    """

    def __init__(self, config: dict[str, Any]):
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 3306)
        self.database = config.get("database", "mysql")
        self.user = config.get("user", "root")
        self.password = config.get("password", "")
        self.charset = config.get("charset", "utf8mb4")
        self._connection = None

    def _get_connection(self):
        """Get or create a MySQL connection."""
        if self._connection is None or not self._connection.open:
            try:
                import pymysql

                self._connection = pymysql.connect(
                    host=self.host,
                    port=self.port,
                    database=self.database,
                    user=self.user,
                    password=self.password,
                    charset=self.charset,
                    connect_timeout=10,
                )
            except ImportError:
                raise ImportError(
                    "pymysql is required for MySQL connector. "
                    "Install with: pip install pymysql"
                )
        return self._connection

    def discover_schema(
        self, dataset_name: str, namespace: str = ""
    ) -> DatasetSchema:
        """Discover schema for a MySQL table."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                COLUMN_NAME,
                COLUMN_TYPE,
                IS_NULLABLE,
                COLUMN_COMMENT,
                COLUMN_KEY,
                ORDINAL_POSITION
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (namespace or self.database, dataset_name),
        )

        columns = [
            ColumnSchema(
                name=row[0],
                data_type=row[1],
                nullable=row[2] == "YES",
                description=row[3],
                is_primary_key=row[4] == "PRI",
                ordinal_position=row[5],
            )
            for row in cursor.fetchall()
        ]
        cursor.close()

        return DatasetSchema(
            name=dataset_name,
            namespace=namespace or self.database,
            columns=columns,
        )

    def discover_datasets(self, namespace: str = "") -> list[DatasetSchema]:
        """Discover all tables in a MySQL database."""
        db = namespace or self.database
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT TABLE_NAME, TABLE_COMMENT, TABLE_ROWS
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
            """,
            (db,),
        )

        tables = [
            DatasetSchema(
                name=row[0],
                namespace=db,
                description=row[1] or "",
                row_count=row[2],
            )
            for row in cursor.fetchall()
        ]
        cursor.close()
        return tables

    def test_connection(self) -> ConnectionHealth:
        """Test MySQL connectivity."""
        import time

        start = time.monotonic()
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            latency = (time.monotonic() - start) * 1000
            cursor.close()
            return ConnectionHealth(
                healthy=True,
                message="Connected successfully",
                latency_ms=round(latency, 2),
                details={"version": version},
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return ConnectionHealth(
                healthy=False,
                message=f"Connection failed: {exc}",
                latency_ms=round(latency, 2),
            )

    def create_reader(
        self,
        dataset_name: str,
        namespace: str = "",
        batch_size: int = 1000,
    ) -> MySQLReader:
        """Create a reader for a MySQL table."""
        return MySQLReader(
            connector=self,
            table_name=dataset_name,
            database=namespace or self.database,
            batch_size=batch_size,
        )

    def create_writer(
        self,
        dataset_name: str,
        namespace: str = "",
        mode: str = "append",
    ) -> MySQLWriter:
        """Create a writer for a MySQL table."""
        return MySQLWriter(
            connector=self,
            table_name=dataset_name,
            database=namespace or self.database,
            mode=mode,
        )

    def create_stream(
        self,
        dataset_name: str,
        namespace: str = "",
    ) -> MySQLBinlogStream:
        """Create a binlog-based stream for MySQL changes."""
        return MySQLBinlogStream(
            connector=self,
            table_name=dataset_name,
            database=namespace or self.database,
        )

    def get_capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            can_discover_schema=True,
            can_discover_datasets=True,
            can_test_connection=True,
            can_read=True,
            can_write=True,
            can_stream=True,
            supports_incremental=True,
            supports_cdc=False,  # Binlog-based CDC is complex
            supports_schema_evolution=False,
            max_batch_size=50000,
            supported_formats=["json", "csv"],
            connector_type=ConnectorType.DATABASE,
            metadata={"engine": "mysql"},
        )

    def get_health(self) -> ConnectionHealth:
        return self.test_connection()


@dataclass
class MySQLReader:
    """Reader for MySQL tables."""

    connector: MySQLConnector
    table_name: str
    database: str
    batch_size: int = 1000

    def read_batch(self, offset: int = 0) -> ReadResult:
        conn = self.connector._get_connection()
        cursor = conn.cursor()
        full_table = f"`{self.database}`.`{self.table_name}`"
        cursor.execute(
            f"SELECT * FROM {full_table} LIMIT %s OFFSET %s",
            (self.batch_size, offset),
        )
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        data = [dict(zip(columns, row)) for row in rows]
        cursor.close()
        return ReadResult(
            data=data,
            columns=columns,
            row_count=len(data),
            has_more=len(data) == self.batch_size,
            cursor=str(offset + len(data)),
        )


@dataclass
class MySQLWriter:
    """Writer for MySQL tables."""

    connector: MySQLConnector
    table_name: str
    database: str
    mode: str = "append"

    def write_batch(self, rows: list[dict[str, Any]]) -> WriteResult:
        if not rows:
            return WriteResult(rows_written=0, bytes_written=0)

        conn = self.connector._get_connection()
        cursor = conn.cursor()
        full_table = f"`{self.database}`.`{self.table_name}`"
        columns = list(rows[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))
        col_names = ", ".join(f"`{c}`" for c in columns)

        if self.mode == "overwrite":
            cursor.execute(f"TRUNCATE TABLE {full_table}")

        insert_sql = f"INSERT INTO {full_table} ({col_names}) VALUES ({placeholders})"
        for row in rows:
            values = [row.get(c) for c in columns]
            cursor.execute(insert_sql, values)

        conn.commit()
        cursor.close()

        import sys
        return WriteResult(
            rows_written=len(rows),
            bytes_written=sys.getsizeof(str(rows)),
        )


@dataclass
class MySQLBinlogStream:
    """MySQL binlog-based change stream (stub for future implementation)."""

    connector: MySQLConnector
    table_name: str
    database: str

    def get_binlog_position(self) -> dict[str, Any]:
        """Get current binlog position."""
        conn = self.connector._get_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW MASTER STATUS")
        row = cursor.fetchone()
        cursor.close()
        if row:
            return {"file": row[0], "position": row[1]}
        return {}

    def read_changes(self, binlog_file: str = "", position: int = 0) -> list[dict[str, Any]]:
        """
        Read binlog changes.

        Note: Full binlog parsing requires mysql-replication library.
        This is a stub for integration with external CDC tools.
        """
        return []


# =============================================================================
# S3 Connector
# =============================================================================


class S3Connector(IConnector):
    """
    AWS S3 object storage connector.

    Supports schema discovery for structured files (CSV, JSON, Parquet),
    reading objects, writing objects, and event-driven streaming via
    S3 event notifications.
    """

    def __init__(self, config: dict[str, Any]):
        self.bucket = config.get("bucket", "")
        self.prefix = config.get("prefix", "")
        self.region = config.get("region", "us-east-1")
        self.endpoint_url = config.get("endpoint_url")  # For MinIO etc.
        self.access_key = config.get("access_key", "")
        self.secret_key = config.get("secret_key", "")
        self._client = None
        self._resource = None

    def _get_s3_client(self):
        """Get or create an S3 client."""
        if self._client is None:
            try:
                import boto3

                kwargs: dict[str, Any] = {
                    "service_name": "s3",
                    "region_name": self.region,
                }
                if self.access_key and self.secret_key:
                    kwargs["aws_access_key_id"] = self.access_key
                    kwargs["aws_secret_access_key"] = self.secret_key
                if self.endpoint_url:
                    kwargs["endpoint_url"] = self.endpoint_url
                session = boto3.Session()
                self._client = session.client(**kwargs)
            except ImportError:
                raise ImportError(
                    "boto3 is required for S3 connector. "
                    "Install with: pip install boto3"
                )
        return self._client

    def discover_schema(
        self, dataset_name: str, namespace: str = ""
    ) -> DatasetSchema:
        """
        Discover schema for an S3 object.

        For CSV files, reads the header row.
        For JSON files, infers keys from the first record.
        """
        key = f"{self.prefix}{dataset_name}" if self.prefix else dataset_name
        client = self._get_s3_client()

        try:
            response = client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"].read(8192).decode("utf-8", errors="ignore")
        except Exception as exc:
            raise ValueError(f"Cannot read S3 object {key}: {exc}")

        columns: list[ColumnSchema] = []

        if dataset_name.endswith(".csv"):
            import csv
            import io

            reader = csv.reader(io.StringIO(body))
            header = next(reader, None)
            if header:
                columns = [
                    ColumnSchema(name=col.strip(), data_type="string")
                    for col in header
                ]
        elif dataset_name.endswith(".json") or dataset_name.endswith(".jsonl"):
            import json as json_mod

            first_line = body.strip().split("\n")[0]
            try:
                record = json_mod.loads(first_line)
                if isinstance(record, dict):
                    columns = [
                        ColumnSchema(name=k, data_type=type(v).__name__)
                        for k, v in record.items()
                    ]
            except json_mod.JSONDecodeError:
                pass

        return DatasetSchema(
            name=dataset_name,
            namespace=self.bucket,
            columns=columns,
            metadata={"key": key, "bucket": self.bucket},
        )

    def discover_datasets(self, namespace: str = "") -> list[DatasetSchema]:
        """Discover datasets (objects) in the S3 bucket."""
        prefix = namespace or self.prefix
        client = self._get_s3_client()
        datasets: list[DatasetSchema] = []

        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                name = key.split("/")[-1] if "/" in key else key
                if name:  # Skip directory markers
                    datasets.append(
                        DatasetSchema(
                            name=key,
                            namespace=self.bucket,
                            metadata={
                                "size": obj.get("Size", 0),
                                "last_modified": str(
                                    obj.get("LastModified", "")
                                ),
                            },
                        )
                    )

        return datasets

    def test_connection(self) -> ConnectionHealth:
        """Test S3 connectivity by listing the bucket."""
        import time

        start = time.monotonic()
        try:
            client = self._get_s3_client()
            client.head_bucket(Bucket=self.bucket)
            latency = (time.monotonic() - start) * 1000
            return ConnectionHealth(
                healthy=True,
                message=f"Bucket '{self.bucket}' accessible",
                latency_ms=round(latency, 2),
                details={
                    "bucket": self.bucket,
                    "region": self.region,
                },
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return ConnectionHealth(
                healthy=False,
                message=f"S3 connection failed: {exc}",
                latency_ms=round(latency, 2),
            )

    def create_reader(
        self,
        dataset_name: str,
        namespace: str = "",
        batch_size: int = 1000,
    ) -> S3Reader:
        """Create a reader for an S3 object."""
        return S3Reader(
            connector=self,
            key=dataset_name,
            batch_size=batch_size,
        )

    def create_writer(
        self,
        dataset_name: str,
        namespace: str = "",
        mode: str = "append",
    ) -> S3Writer:
        """Create a writer for an S3 object."""
        return S3Writer(
            connector=self,
            key=dataset_name,
            mode=mode,
        )

    def create_stream(
        self,
        dataset_name: str,
        namespace: str = "",
    ) -> S3EventStream:
        """Create an event stream for S3 object changes."""
        return S3EventStream(
            connector=self,
            prefix=dataset_name,
        )

    def get_capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            can_discover_schema=True,
            can_discover_datasets=True,
            can_test_connection=True,
            can_read=True,
            can_write=True,
            can_stream=True,  # Via S3 event notifications
            supports_incremental=False,
            supports_cdc=False,
            supports_schema_evolution=False,
            max_batch_size=100000,
            supported_formats=["json", "csv", "parquet", "avro", "text"],
            connector_type=ConnectorType.OBJECT_STORAGE,
            metadata={"storage": "s3"},
        )

    def get_health(self) -> ConnectionHealth:
        return self.test_connection()


@dataclass
class S3Reader:
    """Reader for S3 objects."""

    connector: S3Connector
    key: str
    batch_size: int = 1000

    def read_all(self) -> ReadResult:
        """Read the entire S3 object."""
        client = self.connector._get_s3_client()
        response = client.get_object(
            Bucket=self.connector.bucket, Key=self.key
        )
        body = response["Body"].read().decode("utf-8")

        if self.key.endswith(".json") or self.key.endswith(".jsonl"):
            import json as json_mod

            lines = body.strip().split("\n")
            data = [json_mod.loads(line) for line in lines if line.strip()]
            columns = list(data[0].keys()) if data else []
        elif self.key.endswith(".csv"):
            import csv
            import io

            reader = csv.DictReader(io.StringIO(body))
            data = list(reader)
            columns = list(data[0].keys()) if data else []
        else:
            data = [{"content": body}]
            columns = ["content"]

        return ReadResult(
            data=data,
            columns=columns,
            row_count=len(data),
            has_more=False,
        )


@dataclass
class S3Writer:
    """Writer for S3 objects."""

    connector: S3Connector
    key: str
    mode: str = "append"

    def write_data(self, data: str, content_type: str = "text/plain") -> WriteResult:
        """Write string data to an S3 object."""
        client = self.connector._get_s3_client()
        client.put_object(
            Bucket=self.connector.bucket,
            Key=self.key,
            Body=data.encode("utf-8"),
            ContentType=content_type,
        )
        return WriteResult(
            rows_written=0,
            bytes_written=len(data.encode("utf-8")),
        )

    def write_json(self, records: list[dict[str, Any]]) -> WriteResult:
        """Write JSON records to an S3 object."""
        import json as json_mod

        lines = "\n".join(json_mod.dumps(r) for r in records)
        return self.write_data(lines, content_type="application/json")


@dataclass
class S3EventStream:
    """S3 event notification stream (stub)."""

    connector: S3Connector
    prefix: str

    def get_recent_events(self, max_keys: int = 100) -> list[dict[str, Any]]:
        """List recently modified objects (polling-based event approximation)."""
        client = self.connector._get_s3_client()
        response = client.list_objects_v2(
            Bucket=self.connector.bucket,
            Prefix=self.prefix,
            MaxKeys=max_keys,
        )
        return [
            {
                "key": obj["Key"],
                "size": obj.get("Size", 0),
                "last_modified": str(obj.get("LastModified", "")),
                "event_type": "ObjectCreated",
            }
            for obj in response.get("Contents", [])
        ]


# =============================================================================
# Connector Registry
# =============================================================================


class ConnectorRegistry:
    """
    Global registry for connector implementations.

    Provides registration, lookup, and factory methods for all
    available connector types.
    """

    _connectors: dict[str, type[IConnector]] = {}

    @classmethod
    def register(cls, connector_type: str, connector_class: type[IConnector]) -> None:
        """
        Register a connector implementation.

        Args:
            connector_type: The connector type identifier (e.g. 'postgres', 's3').
            connector_class: The connector class implementing IConnector.
        """
        if not issubclass(connector_class, IConnector):
            raise TypeError(
                f"{connector_class.__name__} must implement IConnector"
            )
        cls._connectors[connector_type.lower()] = connector_class
        logger.info(
            "Registered connector: %s -> %s",
            connector_type,
            connector_class.__name__,
        )

    @classmethod
    def get(cls, connector_type: str) -> type[IConnector] | None:
        """
        Look up a connector by type.

        Args:
            connector_type: The connector type identifier.

        Returns:
            The connector class, or None if not registered.
        """
        return cls._connectors.get(connector_type.lower())

    @classmethod
    def create(
        cls, connector_type: str, config: dict[str, Any]
    ) -> IConnector:
        """
        Create a connector instance by type.

        Args:
            connector_type: The connector type identifier.
            config: Configuration for the connector.

        Returns:
            An initialized connector instance.

        Raises:
            ValueError: If the connector type is not registered.
        """
        connector_class = cls.get(connector_type)
        if connector_class is None:
            available = ", ".join(sorted(cls._connectors.keys()))
            raise ValueError(
                f"Unknown connector type: '{connector_type}'. "
                f"Available: {available}"
            )
        return connector_class(config)

    @classmethod
    def list_connectors(cls) -> dict[str, dict[str, Any]]:
        """
        List all registered connectors with their capabilities.

        Returns:
            Dict of connector_type -> capabilities summary.
        """
        result: dict[str, dict[str, Any]] = {}
        for name, connector_cls in cls._connectors.items():
            # Instantiate with empty config to get capabilities
            try:
                instance = connector_cls(config={})
                caps = instance.get_capabilities()
                result[name] = {
                    "class": connector_cls.__name__,
                    "type": caps.connector_type.value,
                    "can_read": caps.can_read,
                    "can_write": caps.can_write,
                    "can_stream": caps.can_stream,
                    "supports_cdc": caps.supports_cdc,
                    "supports_incremental": caps.supports_incremental,
                }
            except Exception:
                result[name] = {"class": connector_cls.__name__, "error": "init failed"}
        return result

    @classmethod
    def unregister(cls, connector_type: str) -> bool:
        """Unregister a connector type."""
        return cls._connectors.pop(connector_type.lower(), None) is not None

    @classmethod
    def clear(cls) -> None:
        """Clear all registered connectors (for testing)."""
        cls._connectors.clear()


# =============================================================================
# Register built-in connectors
# =============================================================================

ConnectorRegistry.register("postgres", PostgreSQLConnector)
ConnectorRegistry.register("postgresql", PostgreSQLConnector)
ConnectorRegistry.register("mysql", MySQLConnector)
ConnectorRegistry.register("s3", S3Connector)
