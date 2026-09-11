"""
CDC (Change Data Capture) Service for PostgreSQL.

Provides a connector that uses PostgreSQL's logical replication protocol
to capture INSERT, UPDATE, and DELETE operations in real-time, converting
them into a normalized change-event format for downstream processing.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2.extras import LogicalReplicationConnection

logger = logging.getLogger(__name__)


# =============================================================================
# Enums & Data Classes
# =============================================================================


class CDCOperation(StrEnum):
    """Represents the type of change captured from the WAL."""

    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


class CDCStatus(StrEnum):
    """Lifecycle states for a CDC connection."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ChangeEvent:
    """
    A single normalized change event captured from a replication stream.

    Attributes:
        operation: The type of change (INSERT, UPDATE, DELETE).
        table: The source table name.
        schema: The source schema name.
        timestamp: When the change was captured (UTC).
        before: Row data before the change (None for INSERTs).
        after: Row data after the change (None for DELETEs).
        primary_key: Value(s) of the primary key column(s).
        lsn: The WAL Log Sequence Number of this change.
    """

    operation: CDCOperation
    table: str
    schema: str
    timestamp: datetime
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    primary_key: Any
    lsn: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dictionary for JSON storage."""
        return {
            "operation": self.operation.value,
            "table": self.table,
            "schema": self.schema,
            "timestamp": self.timestamp.isoformat(),
            "before": self.before,
            "after": self.after,
            "primary_key": self.primary_key,
            "lsn": self.lsn,
        }


@dataclass
class CDCConfig:
    """
    Configuration for a CDC connector.

    Attributes:
        connection_string: psycopg2-compatible DSN.
        replication_slot_name: Name of the PostgreSQL logical replication slot.
        publication_name: Name of the PostgreSQL publication.
        tables: List of table names to monitor (empty = all tables in publication).
        poll_interval: Seconds between polling attempts (default 1.0).
        batch_size: Maximum events to buffer before flushing (default 1000).
    """

    connection_string: str
    replication_slot_name: str = "voyant_cdc_slot"
    publication_name: str = "voyant_cdc_pub"
    tables: list[str] = field(default_factory=list)
    poll_interval: float = 1.0
    batch_size: int = 1000


# =============================================================================
# Base Connector
# =============================================================================


class CDCConnector(ABC):
    """
    Abstract base class for Change Data Capture connectors.

    Subclasses must implement the connection lifecycle (connect, disconnect)
    and the streaming/consumption logic.
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish the replication connection to the source database."""

    @abstractmethod
    def disconnect(self) -> None:
        """Cleanly close the replication connection."""

    @abstractmethod
    def consume_stream(
        self,
        callback: Any,
        batch_size: int = 1000,
    ) -> None:
        """
        Consume changes from the replication stream.

        Args:
            callback: Callable invoked with a list of ChangeEvent objects.
            batch_size: Number of events to accumulate before calling callback.
        """

    @abstractmethod
    def get_last_lsn(self) -> str | None:
        """Return the last acknowledged LSN (Log Sequence Number)."""


# =============================================================================
# PostgreSQL CDC Connector
# =============================================================================


class PostgreSQLCDCConnector(CDCConnector):
    """
    CDC connector using PostgreSQL's logical replication protocol.

    Uses psycopg2's ``LogicalReplicationConnection`` to connect to a
    replication slot, decode WAL entries via ``pgoutput`` (the built-in
    logical decoding plugin), and emit normalized ``ChangeEvent`` objects.

    Usage::

        config = CDCConfig(
            connection_string="postgresql://user:pass@host:5432/db",
            replication_slot_name="voyant_slot",
            publication_name="voyant_pub",
        )
        connector = PostgreSQLCDCConnector(config)
        connector.connect()
        connector.consume_stream(callback=my_handler)
        connector.disconnect()
    """

    def __init__(self, config: CDCConfig) -> None:
        self.config = config
        self._connection: Any | None = None
        self._last_lsn: str | None = None
        self._running: bool = False
        self._status: CDCStatus = CDCStatus.CREATED
        logger.info(
            "PostgreSQLCDCConnector initialized: slot=%s, publication=%s, tables=%s",
            config.replication_slot_name,
            config.publication_name,
            config.tables or ["<all>"],
        )

    # -----------------------------------------------------------------
    # Properties
    # -----------------------------------------------------------------

    @property
    def status(self) -> CDCStatus:
        return self._status

    @property
    def is_connected(self) -> bool:
        return self._connection is not None and not self._connection.closed

    # -----------------------------------------------------------------
    # Connection Lifecycle
    # -----------------------------------------------------------------

    def connect(self) -> None:
        """
        Open a logical-replication connection to PostgreSQL.

        The connection uses ``psycopg2.extras.LogicalReplicationConnection``
        which enables the ``START_REPLICATION`` protocol.
        """
        try:
            self._status = CDCStatus.STARTING
            self._connection = psycopg2.connect(
                self.config.connection_string,
                connection_factory=LogicalReplicationConnection,
            )
            self._status = CDCStatus.RUNNING
            logger.info(
                "PostgreSQL logical replication connection established to %s",
                self.config.connection_string.split("@")[-1],
            )
        except psycopg2.Error:
            self._status = CDCStatus.FAILED
            logger.exception("Failed to establish logical replication connection")
            raise

    def disconnect(self) -> None:
        """Cleanly close the replication connection."""
        if self._connection and not self._connection.closed:
            try:
                self._connection.close()
                logger.info("PostgreSQL logical replication connection closed")
            except psycopg2.Error:
                logger.warning("Error closing replication connection", exc_info=True)
            finally:
                self._connection = None
        self._running = False
        self._status = CDCStatus.STOPPED

    # -----------------------------------------------------------------
    # Replication Slot & Publication Management
    # -----------------------------------------------------------------

    def setup_replication(self, dsn: str | None = None) -> dict[str, Any]:
        """
        Create the replication slot and publication if they do not exist.

        Uses a regular (non-replication) connection to issue DDL.

        Args:
            dsn: Optional DSN override.  Falls back to the config connection
                 string with ``replication`` stripped from any parameter.

        Returns:
            Dict with ``slot_created`` and ``publication_created`` booleans.
        """
        conn_str = dsn or self.config.connection_string
        conn = psycopg2.connect(conn_str)
        conn.autocommit = True
        cur = conn.cursor()
        result: dict[str, Any] = {"slot_created": False, "publication_created": False}

        try:
            # Create replication slot (idempotent)
            cur.execute(
                "SELECT 1 FROM pg_replication_slots WHERE slot_name = %s",
                (self.config.replication_slot_name,),
            )
            if cur.fetchone() is None:
                cur.execute(
                    "SELECT pg_create_logical_replication_slot(%s, 'pgoutput')",
                    (self.config.replication_slot_name,),
                )
                result["slot_created"] = True
                logger.info(
                    "Created replication slot: %s", self.config.replication_slot_name
                )
            else:
                logger.info(
                    "Replication slot already exists: %s",
                    self.config.replication_slot_name,
                )

            # Create publication (idempotent)
            cur.execute(
                "SELECT 1 FROM pg_publication WHERE pubname = %s",
                (self.config.publication_name,),
            )
            if cur.fetchone() is None:
                if self.config.tables:
                    table_list = ", ".join(
                        f'"{t}"' for t in self.config.tables
                    )
                    cur.execute(
                        f"CREATE PUBLICATION {self.config.publication_name} "
                        f"FOR TABLE {table_list}"
                    )
                else:
                    cur.execute(
                        f"CREATE PUBLICATION {self.config.publication_name} "
                        f"FOR ALL TABLES"
                    )
                result["publication_created"] = True
                logger.info(
                    "Created publication: %s", self.config.publication_name
                )
            else:
                logger.info(
                    "Publication already exists: %s", self.config.publication_name
                )
        finally:
            cur.close()
            conn.close()

        return result

    # -----------------------------------------------------------------
    # Stream Consumption
    # -----------------------------------------------------------------

    def consume_stream(
        self,
        callback: Any,
        batch_size: int | None = None,
    ) -> None:
        """
        Start consuming the logical replication stream.

        This is a **blocking** call that polls the replication slot,
        decodes WAL messages via the ``pgoutput`` plugin, parses them
        into ``ChangeEvent`` objects, and delivers batches to *callback*.

        Args:
            callback: Callable that receives ``list[ChangeEvent]``.
            batch_size: Override for the config batch size.
        """
        if not self.is_connected:
            raise RuntimeError("Not connected — call connect() first")

        effective_batch = batch_size or self.config.batch_size
        self._running = True
        self._status = CDCStatus.RUNNING
        batch: list[ChangeEvent] = []

        logger.info("Starting CDC stream consumption (batch_size=%d)", effective_batch)

        class _StreamConsumer:
            """psycopg2 replication consumer callback adapter."""

            def __init__(self, outer: PostgreSQLCDCConnector) -> None:
                self.outer = outer

            def __call__(self, msg: Any) -> None:
                """Called by psycopg2 for each WAL message."""
                nonlocal batch
                try:
                    events = self.outer._decode_message(msg)
                    if events:
                        batch.extend(events)

                    if len(batch) >= effective_batch:
                        callback(batch)
                        batch = []
                except Exception:
                    logger.exception("Error processing WAL message")

                # Acknowledge the message so the slot advances
                msg.cursor.send_feedback(flush_lsn=msg.data_start)

        consumer = _StreamConsumer(self)

        try:
            cur = self._connection.cursor()
            cur.start_replication(
                slot_name=self.config.replication_slot_name,
                decode=True,
                options={"proto_version": "1", "publication_names": self.config.publication_name},
            )
            logger.info(
                "Replication stream started on slot %s",
                self.config.replication_slot_name,
            )

            while self._running:
                msg = cur.read_message()
                if msg:
                    consumer(msg)
                else:
                    # Flush remaining partial batch
                    if batch:
                        callback(batch)
                        batch = []
                    # Brief sleep to avoid tight-loop when idle
                    import time

                    time.sleep(self.config.poll_interval)

        except psycopg2.Error:
            self._status = CDCStatus.FAILED
            logger.exception("Replication stream error")
            raise
        finally:
            # Flush any remaining events
            if batch:
                try:
                    callback(batch)
                except Exception:
                    logger.exception("Error flushing final batch")

    def stop(self) -> None:
        """Signal the stream consumer to stop gracefully."""
        self._running = False
        logger.info("CDC stream stop requested")

    # -----------------------------------------------------------------
    # LSN Tracking
    # -----------------------------------------------------------------

    def get_last_lsn(self) -> str | None:
        """Return the last acknowledged LSN."""
        return self._last_lsn

    def commit_checkpoint(self, lsn: str) -> None:
        """
        Advance the watermark / checkpoint to the given LSN.

        Args:
            lsn: The LSN string to record as the new watermark.
        """
        self._last_lsn = lsn
        logger.info("CDC checkpoint advanced to LSN %s", lsn)

    # -----------------------------------------------------------------
    # WAL Message Decoding
    # -----------------------------------------------------------------

    def _decode_message(self, msg: Any) -> list[ChangeEvent]:
        """
        Decode a single WAL message into zero or more ``ChangeEvent`` objects.

        The ``pgoutput`` plugin delivers logical-replication messages whose
        payload is a protobuf-like binary format.  psycopg2 (with
        ``decode=True``) wraps this into ``msg.payload`` as a Python object
        whose structure depends on the message type.

        For robustness we handle the common payload shapes produced by
        ``pgoutput``:
        - ``Begin``, ``Commit`` — control messages (no events).
        - ``Relation`` — describes the table schema (used for column mapping).
        - ``Insert``, ``Update``, ``Delete`` — the actual data changes.

        Args:
            msg: A psycopg2 replication message.

        Returns:
            A (possibly empty) list of ``ChangeEvent`` objects.
        """
        events: list[ChangeEvent] = []

        payload = msg.payload
        if payload is None:
            return events

        # pgoutput decoded messages have a `type` attribute or dict key
        msg_type = getattr(payload, "type", None) or (
            payload.get("type") if isinstance(payload, dict) else None
        )

        if msg_type is None:
            return events

        timestamp = datetime.now(UTC)
        lsn = str(msg.data_start) if hasattr(msg, "data_start") else ""

        def _extract_row(row: Any) -> dict[str, Any]:
            """Normalize a row from the payload into a dict."""
            if isinstance(row, dict):
                return row
            # psycopg2 pgoutput may expose column tuples
            if hasattr(row, "keys"):
                return dict(row.keys(), row.values())  # type: ignore[arg-type]
            if isinstance(row, (list, tuple)):
                return {f"col_{i}": v for i, v in enumerate(row)}
            return {}

        def _extract_pk(row_data: dict[str, Any]) -> Any:
            """Best-effort primary key extraction."""
            for key in ("id", "pk", "pk_id"):
                if key in row_data:
                    return row_data[key]
            return None

        table = getattr(payload, "relation", None)
        table_name = ""
        schema_name = "public"
        if table:
            table_name = getattr(table, "name", "") or (
                table.get("name", "") if isinstance(table, dict) else ""
            )
            schema_name = getattr(table, "namespace", None) or (
                table.get("namespace", "public") if isinstance(table, dict) else "public"
            )

        if msg_type == "insert":
            row_data = _extract_row(
                getattr(payload, "new", None) or payload.get("new", {})
            )
            events.append(
                ChangeEvent(
                    operation=CDCOperation.INSERT,
                    table=table_name,
                    schema=schema_name,
                    timestamp=timestamp,
                    before=None,
                    after=row_data,
                    primary_key=_extract_pk(row_data),
                    lsn=lsn,
                )
            )

        elif msg_type == "update":
            old_data = _extract_row(
                getattr(payload, "old", None) or payload.get("old", {})
            )
            new_data = _extract_row(
                getattr(payload, "new", None) or payload.get("new", {})
            )
            events.append(
                ChangeEvent(
                    operation=CDCOperation.UPDATE,
                    table=table_name,
                    schema=schema_name,
                    timestamp=timestamp,
                    before=old_data or None,
                    after=new_data,
                    primary_key=_extract_pk(new_data) or _extract_pk(old_data),
                    lsn=lsn,
                )
            )

        elif msg_type == "delete":
            old_data = _extract_row(
                getattr(payload, "old", None) or payload.get("old", {})
            )
            events.append(
                ChangeEvent(
                    operation=CDCOperation.DELETE,
                    table=table_name,
                    schema=schema_name,
                    timestamp=timestamp,
                    before=old_data or None,
                    after=None,
                    primary_key=_extract_pk(old_data),
                    lsn=lsn,
                )
            )

        if events:
            self._last_lsn = lsn

        return events


# =============================================================================
# Convenience Factory
# =============================================================================

_global_connector: PostgreSQLCDCConnector | None = None


def get_cdc_connector(config: CDCConfig | None = None) -> PostgreSQLCDCConnector:
    """
    Return a singleton ``PostgreSQLCDCConnector``.

    Args:
        config: Configuration to use on first call.  Subsequent calls
                ignore *config* and return the cached instance.

    Returns:
        The global ``PostgreSQLCDCConnector`` instance.
    """
    global _global_connector
    if _global_connector is None:
        if config is None:
            raise ValueError("CDCConfig required for first connector instantiation")
        _global_connector = PostgreSQLCDCConnector(config)
    return _global_connector
