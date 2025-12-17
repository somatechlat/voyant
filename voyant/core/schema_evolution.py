"""
Schema Evolution Module

Persistent baseline management for quality/drift versioning.
Reference: STATUS.md Gap #3 - Schema Evolution Handling

Features:
- Schema version tracking (DuckDB backend)
- Backward/forward compatibility checks
- Migration path detection
- Breaking change detection
- Schema diff generation

Personas Applied:
- PhD Developer: Semantic versioning, Persistent storage
- Analyst: History tracking
- Security: SQL injection prevention (parameterized queries)
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import duckdb
from voyant.core.config import get_settings

logger = logging.getLogger(__name__)


class CompatibilityLevel(str, Enum):
    """Schema compatibility levels."""
    FULL = "full"              # Fully compatible both ways
    BACKWARD = "backward"      # New schema can read old data
    FORWARD = "forward"        # Old schema can read new data
    NONE = "none"              # Breaking changes present


class ChangeType(str, Enum):
    """Types of schema changes."""
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
    """A single schema change."""
    change_type: ChangeType
    column_name: str
    old_value: Any = None
    new_value: Any = None
    is_breaking: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_type": self.change_type.value,
            "column_name": self.column_name,
            "old_value": str(self.old_value) if self.old_value else None,
            "new_value": str(self.new_value) if self.new_value else None,
            "is_breaking": self.is_breaking,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaChange":
        return cls(
            change_type=ChangeType(data["change_type"]),
            column_name=data["column_name"],
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            is_breaking=data.get("is_breaking", False)
        )


@dataclass
class ColumnSchema:
    """Schema for a single column."""
    name: str
    data_type: str
    nullable: bool = True
    default: Any = None
    constraints: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "default": self.default,
            "constraints": self.constraints,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ColumnSchema":
        return cls(
            name=data["name"],
            data_type=data["data_type"],
            nullable=data.get("nullable", True),
            default=data.get("default"),
            constraints=data.get("constraints", []),
        )


@dataclass
class TableSchema:
    """Schema for a table."""
    name: str
    columns: List[ColumnSchema]
    primary_key: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "columns": [c.to_dict() for c in self.columns],
            "primary_key": self.primary_key,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TableSchema":
        return cls(
            name=data["name"],
            columns=[ColumnSchema.from_dict(c) for c in data.get("columns", [])],
            primary_key=data.get("primary_key"),
        )
    
    def get_column(self, name: str) -> Optional[ColumnSchema]:
        for col in self.columns:
            if col.name == name:
                return col
        return None
    
    @property
    def column_names(self) -> Set[str]:
        return {c.name for c in self.columns}


@dataclass
class SchemaVersion:
    """A versioned schema snapshot."""
    version: str                 # Semantic version
    schema: TableSchema
    created_at: float = 0
    created_by: str = ""
    description: str = ""
    changes_from_previous: List[SchemaChange] = field(default_factory=list)
    
    def __post_init__(self):
        if self.created_at == 0:
            self.created_at = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
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
    """Report on compatibility between two schema versions."""
    source_version: str
    target_version: str
    compatibility: CompatibilityLevel
    changes: List[SchemaChange]
    breaking_changes: List[SchemaChange]
    
    @property
    def is_compatible(self) -> bool:
        return len(self.breaking_changes) == 0
    
    def to_dict(self) -> Dict[str, Any]:
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
# Schema Comparison
# =============================================================================

def compare_schemas(
    old_schema: TableSchema,
    new_schema: TableSchema,
) -> List[SchemaChange]:
    """Compare two schemas and return list of changes."""
    changes = []
    
    old_columns = {c.name: c for c in old_schema.columns}
    new_columns = {c.name: c for c in new_schema.columns}
    
    # Find added columns
    for name in new_columns.keys() - old_columns.keys():
        col = new_columns[name]
        changes.append(SchemaChange(
            change_type=ChangeType.COLUMN_ADDED,
            column_name=name,
            new_value=col.data_type,
            # Adding non-nullable column without default is breaking
            is_breaking=not col.nullable and col.default is None,
        ))
    
    # Find removed columns
    for name in old_columns.keys() - new_columns.keys():
        changes.append(SchemaChange(
            change_type=ChangeType.COLUMN_REMOVED,
            column_name=name,
            old_value=old_columns[name].data_type,
            is_breaking=True,  # Removing columns is always breaking
        ))
    
    # Find modified columns
    for name in old_columns.keys() & new_columns.keys():
        old_col = old_columns[name]
        new_col = new_columns[name]
        
        # Type change
        if old_col.data_type != new_col.data_type:
            is_breaking = not _is_type_widening(old_col.data_type, new_col.data_type)
            changes.append(SchemaChange(
                change_type=ChangeType.TYPE_CHANGED,
                column_name=name,
                old_value=old_col.data_type,
                new_value=new_col.data_type,
                is_breaking=is_breaking,
            ))
        
        # Nullable change
        if old_col.nullable != new_col.nullable:
            # Making nullable -> non-nullable is breaking
            is_breaking = old_col.nullable and not new_col.nullable
            changes.append(SchemaChange(
                change_type=ChangeType.NULLABLE_CHANGED,
                column_name=name,
                old_value=old_col.nullable,
                new_value=new_col.nullable,
                is_breaking=is_breaking,
            ))
        
        # Default change
        if old_col.default != new_col.default:
            changes.append(SchemaChange(
                change_type=ChangeType.DEFAULT_CHANGED,
                column_name=name,
                old_value=old_col.default,
                new_value=new_col.default,
                is_breaking=False,
            ))
    
    return changes


def _is_type_widening(old_type: str, new_type: str) -> bool:
    """Check if type change is widening (safe)."""
    type_order = {
        "int": 1, "integer": 1, "smallint": 1,
        "bigint": 2, "long": 2,
        "float": 3,
        "double": 4,
        "decimal": 5, "numeric": 5,
        "string": 10, "text": 10, "varchar": 10, "char": 10
    }
    old_order = type_order.get(old_type.lower(), 0)
    new_order = type_order.get(new_type.lower(), 0)
    return new_order >= old_order


# =============================================================================
# Schema Registry (DuckDB Persistent)
# =============================================================================

class SchemaEvolutionRegistry:
    """Persistent registry for tracking schema versions using DuckDB."""
    
    def __init__(self):
        self.settings = get_settings()
        self._conn = duckdb.connect(database=self.settings.duckdb_path)
        self._init_db()

    def _init_db(self):
        """Initialize the schema versions table."""
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
                )
            """)
        except Exception as e:
            logger.error(f"Failed to init DB: {e}")
            raise
    
    def register(
        self,
        table_name: str,
        schema: TableSchema,
        version: str,
        description: str = "",
        created_by: str = "",
    ) -> SchemaVersion:
        """Register a new schema version."""
        try:
            # Calculate changes from previous
            prev_version = self.get_version(table_name) # Latest
            changes = []
            if prev_version:
                changes = compare_schemas(prev_version.schema, schema)
            
            changes_json = json.dumps([c.to_dict() for c in changes])
            schema_json = json.dumps(schema.to_dict())
            created_at = time.time()
            
            self._conn.execute("""
                INSERT INTO schema_versions 
                (table_name, version, schema_json, created_at, created_by, description, changes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (table_name, version, schema_json, created_at, created_by, description, changes_json))
            
            # Explicit commit often not needed in autocommit mode but good for safety
            # self.conn.commit() 
            
            logger.info(f"Registered schema {table_name} v{version} with {len(changes)} changes")
            
            return SchemaVersion(
                version=version,
                schema=schema,
                created_at=created_at,
                created_by=created_by,
                description=description,
                changes_from_previous=changes
            )
        except duckdb.ConstraintException:
            logger.warning(f"Schema {table_name} v{version} already exists")
            # Return existing
            return self.get_version(table_name, version)
    
    def get_version(
        self,
        table_name: str,
        version: Optional[str] = None,
    ) -> Optional[SchemaVersion]:
        """Get a specific version or latest."""
        if version:
            result = self._conn.execute("""
                SELECT version, schema_json, created_at, created_by, description, changes_json
                FROM schema_versions
                WHERE table_name = ? AND version = ?
            """, (table_name, version)).fetchone()
        else:
            # Latest by created_at
            result = self._conn.execute("""
                SELECT version, schema_json, created_at, created_by, description, changes_json
                FROM schema_versions
                WHERE table_name = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (table_name,)).fetchone()
        
        if not result:
            return None
            
        return self._row_to_version(result)
    
    def get_history(self, table_name: str) -> List[Dict[str, Any]]:
        """Get version history for a table."""
        rows = self._conn.execute("""
            SELECT version, schema_json, created_at, created_by, description, changes_json
            FROM schema_versions
            WHERE table_name = ?
            ORDER BY created_at ASC
        """, (table_name,)).fetchall()
        
        history = []
        for row in rows:
            v = self._row_to_version(row)
            history.append({
                "version": v.version,
                "created_at": datetime.fromtimestamp(v.created_at).isoformat(),
                "description": v.description,
                "changes_count": len(v.changes_from_previous),
                "breaking_changes": sum(1 for c in v.changes_from_previous if c.is_breaking),
            })
        return history

    def _row_to_version(self, row: Tuple) -> SchemaVersion:
        """Helper to convert DB row to SchemaVersion object."""
        # row: version, schema_json, created_at, created_by, description, changes_json
        version_str, schema_str, created_at, created_by, description, changes_str = row
        
        schema_dict = json.loads(schema_str)
        changes_list = json.loads(changes_str)
        
        return SchemaVersion(
            version=version_str,
            schema=TableSchema.from_dict(schema_dict),
            created_at=created_at,
            created_by=created_by,
            description=description,
            changes_from_previous=[SchemaChange.from_dict(c) for c in changes_list]
        )
    
    def list_tables(self) -> List[str]:
        """List all tracked tables."""
        result = self._conn.execute("SELECT DISTINCT table_name FROM schema_versions").fetchall()
        return [r[0] for r in result]

    def clear(self):
        """Clear registry (testing)."""
        self._conn.execute("DELETE FROM schema_versions")
        
    def close(self):
        """Close database connection."""
        try:
            self._conn.close()
        except:
            pass

    def __del__(self):
        self.close()


# =============================================================================
# Global Instance
# =============================================================================

_registry: Optional[SchemaEvolutionRegistry] = None


def get_registry() -> SchemaEvolutionRegistry:
    global _registry
    if _registry is None:
        _registry = SchemaEvolutionRegistry()
    return _registry


def track_schema(
    table_name: str,
    schema: TableSchema,
    version: str,
    description: str = "",
) -> SchemaVersion:
    return get_registry().register(table_name, schema, version, description)


def get_schema_history(table_name: str) -> List[Dict[str, Any]]:
    return get_registry().get_history(table_name)


def get_latest_schema(table_name: str) -> Optional[TableSchema]:
    version = get_registry().get_version(table_name)
    return version.schema if version else None


def check_schema_compatibility(
    table_name: str,
    source_version: str,
    target_version: str,
) -> Optional[Dict[str, Any]]:
    report = get_registry().check_compatibility(table_name, source_version, target_version)
    return report.to_dict() if report else None


def reset_registry():
    """Reset the registry (testing)."""
    global _registry
    if _registry:
        try:
            _registry.close()
        except:
            pass
    _registry = None
    _registry = None
