"""
Time Travel Service — Query Iceberg table history via Trino.

Implements the time-travel capabilities specified in the Deep-Dive spec §5.2:
- Query by Iceberg snapshot version (``FOR SYSTEM_VERSION AS OF``)
- Query by timestamp (``FOR SYSTEM_TIME AS OF``)
- Diff between two versions (``CHANGES BETWEEN VERSION ... AND ...``)
- List available versions (Iceberg snapshot metadata via REST catalog)

All SQL uses Trino's Iceberg connector syntax for temporal queries.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apps.core.lib.iceberg import IcebergClient, IcebergSnapshot, get_iceberg_client
from apps.core.lib.trino import TrinoClient, get_trino_client
from apps.ontology.models import ObjectType

logger = logging.getLogger(__name__)


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class VersionInfo:
    """A single Iceberg snapshot version entry."""

    snapshot_id: int
    timestamp_ms: int
    timestamp_iso: str
    operation: str
    summary: dict[str, str]


@dataclass
class VersionDiff:
    """Result of diffing two Iceberg snapshot versions."""

    dataset: str
    version_from: int
    version_to: int
    columns: list[str]
    added: list[list[Any]]
    removed: list[list[Any]]
    modified: list[list[Any]]
    added_count: int
    removed_count: int
    modified_count: int


@dataclass
class TimeTravelResult:
    """Result of a time-travel query."""

    dataset: str
    version: int | None
    timestamp: str | None
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    execution_time_ms: int


# ── Identifier validation ────────────────────────────────────────────────────

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(name: str) -> str:
    if not _IDENT_RE.match(name):
        raise ValueError(f"Invalid identifier: {name!r}")
    return name


def _validate_dataset_name(name: str) -> str:
    parts = name.split(".")
    for part in parts:
        _validate_identifier(part)
    return name


# ── Time Travel Service ─────────────────────────────────────────────────────


class TimeTravelService:
    """Provides Iceberg time-travel queries for Ontology backing datasets.

    Usage::

        svc = TimeTravelService(tenant_id="acme")
        result = svc.query_by_version(dataset_id, version_number=47)
        result = svc.query_by_timestamp(dataset_id, timestamp="2026-09-08T02:00:00")
        diff = svc.diff_versions(dataset_id, v1=46, v2=47)
        versions = svc.list_versions(dataset_id)
    """

    def __init__(
        self,
        tenant_id: str,
        trino: TrinoClient | None = None,
        iceberg: IcebergClient | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self._trino = trino or get_trino_client()
        self._iceberg = iceberg or get_iceberg_client()

    # ── Internal helpers ─────────────────────────────────────────────────

    def _resolve_dataset(
        self,
        dataset_id: str,
    ) -> tuple[str, str, str]:
        """Resolve *dataset_id* (ObjectType UUID) to ``(dataset_name, schema, table)``.

        *dataset_id* may be either:
        - An ObjectType UUID → looked up and its ``backing_dataset`` returned
        - A direct fully-qualified table name (``schema.table``) → returned as-is
        """
        # Try as ObjectType UUID first
        ot = ObjectType.objects.filter(
            tenant_id=self.tenant_id,
            id=dataset_id,
            deleted_at__isnull=True,
        ).first()

        if ot and ot.backing_dataset:
            dataset = _validate_dataset_name(ot.backing_dataset)
            parts = dataset.split(".")
            schema = parts[0] if len(parts) > 1 else self._trino.schema
            table = parts[-1]
            return dataset, schema, table

        # Fall back to treating dataset_id as a direct table reference
        dataset = _validate_dataset_name(dataset_id)
        parts = dataset.split(".")
        schema = parts[0] if len(parts) > 1 else self._trino.schema
        table = parts[-1]
        return dataset, schema, table

    def _snapshot_to_version_info(self, snap: IcebergSnapshot) -> VersionInfo:
        ts = datetime.utcfromtimestamp(snap.timestamp_ms / 1000.0)
        return VersionInfo(
            snapshot_id=snap.snapshot_id,
            timestamp_ms=snap.timestamp_ms,
            timestamp_iso=ts.isoformat() + "Z",
            operation=snap.operation,
            summary=snap.summary,
        )

    # ── Public API ───────────────────────────────────────────────────────

    def query_by_version(
        self,
        dataset_id: str,
        version_number: int,
        limit: int = 1000,
    ) -> TimeTravelResult:
        """Query data as of a specific Iceberg snapshot version.

        Uses ``FOR SYSTEM_VERSION AS OF <snapshot_id>`` syntax.

        Args:
            dataset_id: ObjectType UUID or direct table name.
            version_number: Iceberg snapshot ID.
            limit: Max rows to return.

        Returns:
            :class:`TimeTravelResult` with historical data.
        """
        dataset, schema, table = self._resolve_dataset(dataset_id)
        _validate_identifier(table)
        safe_schema = _validate_identifier(schema)

        sql = (
            f"SELECT *\n"
            f"FROM {safe_schema}.{table}\n"
            f"FOR SYSTEM_VERSION AS OF {int(version_number)}\n"
            f"LIMIT {min(limit, self._trino.max_rows)}"
        )

        logger.info("query_by_version SQL: %s", sql)
        result = self._trino.execute(sql)

        return TimeTravelResult(
            dataset=dataset,
            version=version_number,
            timestamp=None,
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            truncated=result.truncated,
            execution_time_ms=result.execution_time_ms,
        )

    def query_by_timestamp(
        self,
        dataset_id: str,
        timestamp: str,
        limit: int = 1000,
    ) -> TimeTravelResult:
        """Query data as of a specific point in time.

        Uses ``FOR SYSTEM_TIME AS OF '<timestamp>'`` syntax.

        Args:
            dataset_id: ObjectType UUID or direct table name.
            timestamp: ISO-8601 timestamp string (e.g. ``'2026-09-08 02:00:00'``).
            limit: Max rows to return.

        Returns:
            :class:`TimeTravelResult` with historical data.
        """
        dataset, schema, table = self._resolve_dataset(dataset_id)
        _validate_identifier(table)
        safe_schema = _validate_identifier(schema)

        # Sanitize timestamp — allow only safe characters
        safe_ts = timestamp.replace("'", "''")

        sql = (
            f"SELECT *\n"
            f"FROM {safe_schema}.{table}\n"
            f"FOR SYSTEM_TIME AS OF TIMESTAMP '{safe_ts}'\n"
            f"LIMIT {min(limit, self._trino.max_rows)}"
        )

        logger.info("query_by_timestamp SQL: %s", sql)
        result = self._trino.execute(sql)

        return TimeTravelResult(
            dataset=dataset,
            version=None,
            timestamp=timestamp,
            columns=result.columns,
            rows=result.rows,
            row_count=result.row_count,
            truncated=result.truncated,
            execution_time_ms=result.execution_time_ms,
        )

    def diff_versions(
        self,
        dataset_id: str,
        v1: int,
        v2: int,
        limit: int = 1000,
    ) -> VersionDiff:
        """Diff two Iceberg snapshot versions to find added/removed/modified rows.

        Uses ``CHANGES BETWEEN VERSION ... AND ...`` syntax.

        This returns a raw diff.  The ``_change_type`` column indicates the
        change kind (``INSERT``, ``DELETE``, ``UPDATE_BEFORE``, ``UPDATE_AFTER``).

        Args:
            dataset_id: ObjectType UUID or direct table name.
            v1: Earlier snapshot ID.
            v2: Later snapshot ID.
            limit: Max rows per change type.

        Returns:
            :class:`VersionDiff` with added/removed/modified row lists.
        """
        dataset, schema, table = self._resolve_dataset(dataset_id)
        _validate_identifier(table)
        safe_schema = _validate_identifier(schema)

        sql = (
            f"SELECT *\n"
            f"FROM {safe_schema}.{table}\n"
            f"CHANGES BETWEEN VERSION {int(v1)} AND {int(v2)}\n"
            f"LIMIT {min(limit, self._trino.max_rows)}"
        )

        logger.info("diff_versions SQL: %s", sql)
        result = self._trino.execute(sql)

        # Classify rows by _change_type column
        added: list[list[Any]] = []
        removed: list[list[Any]] = []
        modified: list[list[Any]] = []

        change_type_idx = None
        for i, col in enumerate(result.columns):
            if col.lower() in ("_change_type", "changetype", "change_type"):
                change_type_idx = i
                break

        if change_type_idx is not None:
            for row in result.rows:
                ct = str(row[change_type_idx]).upper() if row[change_type_idx] else ""
                if ct in ("INSERT",):
                    added.append(row)
                elif ct in ("DELETE",):
                    removed.append(row)
                elif ct in ("UPDATE_BEFORE", "UPDATE_AFTER"):
                    modified.append(row)
                else:
                    added.append(row)  # default bucket
        else:
            # No change type column — all rows are diff results
            added = result.rows

        return VersionDiff(
            dataset=dataset,
            version_from=v1,
            version_to=v2,
            columns=result.columns,
            added=added,
            removed=removed,
            modified=modified,
            added_count=len(added),
            removed_count=len(removed),
            modified_count=len(modified),
        )

    def list_versions(
        self,
        dataset_id: str,
    ) -> list[VersionInfo]:
        """List all Iceberg snapshot versions for a dataset.

        Uses the Iceberg REST catalog to retrieve snapshot metadata.

        Args:
            dataset_id: ObjectType UUID or direct table name.

        Returns:
            List of :class:`VersionInfo` entries, most recent first.
        """
        _, schema, table = self._resolve_dataset(dataset_id)

        try:
            snapshots = self._iceberg.get_snapshots(schema, table)
        except Exception as exc:
            logger.warning(
                "list_versions: Iceberg REST catalog unavailable (%s), "
                "falling back to Trino metadata query",
                exc,
            )
            return self._list_versions_via_trino(schema, table)

        versions = [self._snapshot_to_version_info(s) for s in snapshots]
        # Most recent first
        versions.sort(key=lambda v: v.timestamp_ms, reverse=True)
        return versions

    def _list_versions_via_trino(
        self,
        schema: str,
        table: str,
    ) -> list[VersionInfo]:
        """Fallback: list versions via Trino's ``$snapshots`` metadata table."""
        safe_schema = _validate_identifier(schema)
        safe_table = _validate_identifier(table)

        sql = (
            f"SELECT *\n"
            f"FROM {safe_schema}.\"{safe_table}$snapshots\"\n"
            f"ORDER BY committed_at DESC"
        )

        try:
            result = self._trino.execute(sql, limit=200)
        except Exception as exc:
            logger.error("list_versions_via_trino failed: %s", exc)
            return []

        versions: list[VersionInfo] = []
        col_map = {c.lower(): i for i, c in enumerate(result.columns)}

        for row in result.rows:
            snap_id = row[col_map.get("snapshot_id", 0)] or 0
            committed_at = row[col_map.get("committed_at", 1)] or ""
            summary_idx = col_map.get("summary", None)
            summary = {}
            if summary_idx is not None and row[summary_idx]:
                raw = row[summary_idx]
                if isinstance(raw, dict):
                    summary = raw
                elif isinstance(raw, str):
                    # Parse Trino map type representation
                    summary = {"raw": raw}

            operation = summary.get("operation", "")

            ts_ms = 0
            if isinstance(committed_at, str) and committed_at:
                try:
                    dt = datetime.fromisoformat(committed_at.replace("Z", "+00:00"))
                    ts_ms = int(dt.timestamp() * 1000)
                except (ValueError, OSError):
                    pass
            elif isinstance(committed_at, (int, float)):
                ts_ms = int(committed_at)

            ts_iso = datetime.utcfromtimestamp(ts_ms / 1000.0).isoformat() + "Z" if ts_ms else ""

            versions.append(
                VersionInfo(
                    snapshot_id=int(snap_id),
                    timestamp_ms=ts_ms,
                    timestamp_iso=ts_iso,
                    operation=operation,
                    summary=summary,
                )
            )

        return versions
