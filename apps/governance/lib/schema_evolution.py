"""
Schema evolution tracking with DuckDB persistence.

Reference: STATUS.md Gap #3 - Schema Evolution Handling
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import duckdb

from apps.core.config import get_settings

logger = logging.getLogger(__name__)


class CompatibilityLevel(StrEnum):
    FULL = "full"  # Fully compatible in both directions.
    BACKWARD = (
        "backward"  # New schema can read old data (e.g., column added with default).
    )
    FORWARD = "forward"  # Old schema can read new data (e.g., column removed).
    NONE = "none"  # A breaking change exists between versions.


class ChangeType(StrEnum):
    COLUMN_ADDED = "column_added"
    COLUMN_REMOVED = "column_removed"
    COLUMN_RENAMED = "column_renamed"
    TYPE_CHANGED = "type_changed"
    NULLABLE_CHANGED = "nullable_changed"
    DEFAULT_CHANGED = "default_changed"
    CONSTRAINT_ADDED = "constraint_added"
    CONSTRAINT_REMOVED = "constraint_removed"


@dataclass
class SchemaChange:
    """Atomic change between two schema versions."""

    change_type: ChangeType
    column_name: str
    old_value: Any = None
    new_value: Any = None
    is_breaking: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "change_type": self.change_type.value,
            "column_name": self.column_name,
            "old_value": str(self.old_value) if self.old_value is not None else None,
            "new_value": str(self.new_value) if self.new_value is not None else None,
            "is_breaking": self.is_breaking,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchemaChange:
        return cls(
            change_type=ChangeType(data["change_type"]),
            column_name=data["column_name"],
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            is_breaking=data.get("is_breaking", False),
        )


@dataclass
class ColumnSchema:
    """Schema definition for a single table column."""

    name: str
    data_type: str
    nullable: bool = True
    default: Any = None
    constraints: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ColumnSchema:
        return cls(**data)


@dataclass
class TableSchema:
    """Full schema for a table."""

    name: str
    columns: list[ColumnSchema]
    primary_key: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "columns": [c.to_dict() for c in self.columns],
            "primary_key": self.primary_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TableSchema:
        return cls(
            name=data["name"],
            columns=[ColumnSchema.from_dict(c) for c in data.get("columns", [])],
            primary_key=data.get("primary_key"),
        )

    def get_column(self, name: str) -> ColumnSchema | None:
        for col in self.columns:
            if col.name == name:
                return col
        return None

    @property
    def column_names(self) -> set[str]:
        return {c.name for c in self.columns}


@dataclass
class SchemaVersion:
    """Versioned snapshot of a table's schema."""

    version: str
    schema: TableSchema
    created_at: float = 0
    created_by: str = ""
    description: str = ""
    changes_from_previous: list[SchemaChange] = field(default_factory=list)

    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "schema": self.schema.to_dict(),
            "created_at": datetime.fromtimestamp(self.created_at).isoformat(),
            "created_by": self.created_by,
            "description": self.description,
            "changes": [c.to_dict() for c in self.changes_from_previous],
        }


@dataclass
class CompatibilityReport:
    source_version: str
    target_version: str
    compatibility: CompatibilityLevel
    changes: list[SchemaChange]
    breaking_changes: list[SchemaChange]

    @property
    def is_compatible(self) -> bool:
        return len(self.breaking_changes) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_version": self.source_version,
            "target_version": self.target_version,
            "compatibility": self.compatibility.value,
            "is_compatible": self.is_compatible,
            "total_changes": len(self.changes),
            "breaking_changes_count": len(self.breaking_changes),
            "changes": [c.to_dict() for c in self.changes],
            "breaking_changes": [c.to_dict() for c in self.breaking_changes],
        }


# =============================================================================
# Schema Comparison Logic
# =============================================================================


def compare_schemas(
    old_schema: TableSchema,
    new_schema: TableSchema,
) -> list[SchemaChange]:
    changes = []
    old_columns = {c.name: c for c in old_schema.columns}
    new_columns = {c.name: c for c in new_schema.columns}

    # Check for added columns
    for name in new_columns.keys() - old_columns.keys():
        col = new_columns[name]
        changes.append(
            SchemaChange(
                change_type=ChangeType.COLUMN_ADDED,
                column_name=name,
                new_value=col.data_type,
                # A new, non-nullable column without a default is a breaking change.
                is_breaking=not col.nullable and col.default is None,
            )
        )

    # Check for removed columns
    for name in old_columns.keys() - new_columns.keys():
        changes.append(
            SchemaChange(
                change_type=ChangeType.COLUMN_REMOVED,
                column_name=name,
                old_value=old_columns[name].data_type,
                is_breaking=True,  # Removing a column is always considered breaking.
            )
        )

    # Check for modified columns (present in both schemas)
    for name in old_columns.keys() & new_columns.keys():
        old_col = old_columns[name]
        new_col = new_columns[name]

        # Check for data type change
        if old_col.data_type != new_col.data_type:
            # A type change is breaking unless it's a "widening" (e.g., INT -> BIGINT).
            is_breaking = not _is_type_widening(old_col.data_type, new_col.data_type)
            changes.append(
                SchemaChange(
                    change_type=ChangeType.TYPE_CHANGED,
                    column_name=name,
                    old_value=old_col.data_type,
                    new_value=new_col.data_type,
                    is_breaking=is_breaking,
                )
            )

        # Check for change in nullability
        if old_col.nullable != new_col.nullable:
            # Making a nullable column non-nullable is a breaking change.
            is_breaking = old_col.nullable and not new_col.nullable
            changes.append(
                SchemaChange(
                    change_type=ChangeType.NULLABLE_CHANGED,
                    column_name=name,
                    old_value=old_col.nullable,
                    new_value=new_col.nullable,
                    is_breaking=is_breaking,
                )
            )

        # Check for change in default value (non-breaking)
        if old_col.default != new_col.default:
            changes.append(
                SchemaChange(
                    change_type=ChangeType.DEFAULT_CHANGED,
                    column_name=name,
                    old_value=old_col.default,
                    new_value=new_col.default,
                    is_breaking=False,
                )
            )

    return changes


def _is_type_widening(old_type: str, new_type: str) -> bool:
    """
    Check if a data type change is a safe "widening" conversion (e.g., INT to FLOAT).

    Returns True if the change is safe, False if it is a breaking change.
    """
    # Simplified type promotion hierarchy. Lower numbers can be safely promoted to higher ones.
    type_order = {
        "int": 1,
        "integer": 1,
        "smallint": 1,
        "bigint": 2,
        "long": 2,
        "float": 3,
        "double": 4,
        "decimal": 5,
        "numeric": 5,
        "string": 10,
        "text": 10,
        "varchar": 10,
        "char": 10,
    }
    old_order = type_order.get(old_type.lower(), 99)
    new_order = type_order.get(new_type.lower(), 99)
    return new_order >= old_order


# =============================================================================
# Schema Registry (Persisted in DuckDB)
# =============================================================================


class SchemaEvolutionRegistry:
    def __init__(self):
        self.settings = get_settings()
        self._conn = duckdb.connect(database=self.settings.duckdb_path, read_only=False)
        self._init_db()

    def _init_db(self):
        try:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_versions (
                    table_name VARCHAR,
                    version VARCHAR,
                    schema_json VARCHAR,
                    created_at DOUBLE,
                    created_by VARCHAR,
                    description VARCHAR,
                    changes_json VARCHAR,
                    PRIMARY KEY (table_name, version)
                );
                """)
        except Exception as e:
            logger.error(f"Failed to initialize schema evolution database: {e}")
            raise

    def register(
        self,
        table_name: str,
        schema: TableSchema,
        version: str,
        description: str = "",
        created_by: str = "",
    ) -> SchemaVersion:
        try:
            latest_version = self.get_version(table_name)
            changes = []
            if latest_version:
                changes = compare_schemas(latest_version.schema, schema)

            changes_json = json.dumps([c.to_dict() for c in changes])
            schema_json = json.dumps(schema.to_dict())
            created_at = time.time()

            # Use parameterized queries to prevent SQL injection.
            self._conn.execute(
                """
                INSERT INTO schema_versions (
                    table_name, version, schema_json, created_at, created_by, description, changes_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    table_name,
                    version,
                    schema_json,
                    created_at,
                    created_by,
                    description,
                    changes_json,
                ),
            )
            logger.info(
                f"Registered schema {table_name} v{version} with {len(changes)} changes."
            )

            return SchemaVersion(
                version=version,
                schema=schema,
                created_at=created_at,
                created_by=created_by,
                description=description,
                changes_from_previous=changes,
            )
        except duckdb.ConstraintException:
            logger.warning(
                f"Schema version {table_name} v{version} already exists. Returning existing."
            )
            return self.get_version(table_name, version)  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Failed to register schema {table_name} v{version}: {e}")
            raise

    def get_version(
        self,
        table_name: str,
        version: str | None = None,
    ) -> SchemaVersion | None:
        if version:
            query = (
                "SELECT * FROM schema_versions WHERE table_name = ? AND version = ?;"
            )
            params = (table_name, version)
        else:
            query = "SELECT * FROM schema_versions WHERE table_name = ? ORDER BY created_at DESC LIMIT 1;"
            params = (table_name,)

        result = self._conn.execute(query, params).fetchone()
        return self._row_to_version(result) if result else None

    def get_history(self, table_name: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT * FROM schema_versions WHERE table_name = ? ORDER BY created_at ASC;",
            (table_name,),
        ).fetchall()

        history = []
        for row in rows:
            v = self._row_to_version(row)
            history.append(
                {
                    "version": v.version,
                    "created_at": datetime.fromtimestamp(v.created_at).isoformat(),
                    "description": v.description,
                    "changes_count": len(v.changes_from_previous),
                    "breaking_changes": sum(
                        1 for c in v.changes_from_previous if c.is_breaking
                    ),
                }
            )
        return history

    def _row_to_version(self, row: tuple) -> SchemaVersion:
        _, version_str, schema_str, created_at, created_by, description, changes_str = (
            row
        )
        return SchemaVersion(
            version=version_str,
            schema=TableSchema.from_dict(json.loads(schema_str)),
            created_at=created_at,
            created_by=created_by,
            description=description,
            changes_from_previous=[
                SchemaChange.from_dict(c) for c in json.loads(changes_str)
            ],
        )

    def list_tables(self) -> list[str]:
        result = self._conn.execute(
            "SELECT DISTINCT table_name FROM schema_versions;"
        ).fetchall()
        return [r[0] for r in result]

    def clear(self):
        """Clear all schema versions from the database. For testing only."""
        self._conn.execute("DELETE FROM schema_versions;")

    def close(self):
        if hasattr(self, "_conn") and self._conn:
            try:
                self._conn.close()
            except Exception as e:
                logger.warning(f"Error closing DuckDB connection: {e}")

    def __del__(self):
        self.close()


# =============================================================================
# Global Singleton Accessor
# =============================================================================

_registry: SchemaEvolutionRegistry | None = None


def get_registry() -> SchemaEvolutionRegistry:
    global _registry
    if _registry is None:
        _registry = SchemaEvolutionRegistry()
    return _registry


def track_schema(
    table_name: str, schema: TableSchema, version: str, description: str = ""
) -> SchemaVersion:
    """Register a new schema version in the global registry."""
    return get_registry().register(table_name, schema, version, description)


def get_schema_history(table_name: str) -> list[dict[str, Any]]:
    """Get the version history of a table."""
    return get_registry().get_history(table_name)


def get_latest_schema(table_name: str) -> TableSchema | None:
    """Get the latest schema for a table."""
    version_obj = get_registry().get_version(table_name)
    return version_obj.schema if version_obj else None


def check_schema_compatibility(
    table_name: str, source_version: str, target_version: str
) -> dict[str, Any] | None:
    """Generate a compatibility report between two versions."""
    registry = get_registry()
    source = registry.get_version(table_name, source_version)
    target = registry.get_version(table_name, target_version)
    if not source or not target:
        return None

    changes = compare_schemas(source.schema, target.schema)
    breaking_changes = [change for change in changes if change.is_breaking]

    if not changes:
        compatibility = CompatibilityLevel.FULL
    elif breaking_changes:
        compatibility = CompatibilityLevel.NONE
    elif any(change.change_type == ChangeType.COLUMN_ADDED for change in changes):
        compatibility = CompatibilityLevel.BACKWARD
    elif any(change.change_type == ChangeType.COLUMN_REMOVED for change in changes):
        compatibility = CompatibilityLevel.FORWARD
    else:
        compatibility = CompatibilityLevel.FULL

    report = CompatibilityReport(
        source_version=source_version,
        target_version=target_version,
        compatibility=compatibility,
        changes=changes,
        breaking_changes=breaking_changes,
    )
    return report.to_dict()


def reset_registry():
    """Reset the global registry. Used primarily for testing."""
    global _registry
    if _registry:
        _registry.close()
    _registry = None
