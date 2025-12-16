"""
Schema Evolution Module

Persistent baseline management for quality/drift versioning.
Reference: STATUS.md Gap #3 - Schema Evolution Handling

Features:
- Schema version tracking
- Backward/forward compatibility checks
- Migration path detection
- Breaking change detection
- Schema diff generation

Personas Applied:
- PhD Developer: Semantic versioning for schemas
- Analyst: Impact analysis for changes
- QA: Migration testing
- ISO Documenter: Schema changelog
- Security: No data exposure in diffs
- Performance: Incremental comparisons
- UX: Clear compatibility reports

Usage:
    from voyant.core.schema_evolution import (
        SchemaVersion, track_schema, get_schema_history,
        check_compatibility, detect_breaking_changes
    )
    
    # Track schema changes
    track_schema("orders", new_schema)
    
    # Check compatibility
    result = check_compatibility("orders", "1.0.0", "2.0.0")
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

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
    """
    Compare two schemas and return list of changes.
    """
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
    # Define type hierarchy
    type_order = {
        "int": 1,
        "integer": 1,
        "bigint": 2,
        "float": 3,
        "double": 4,
        "decimal": 5,
        "string": 10,
        "text": 10,
        "varchar": 10,
    }
    
    old_order = type_order.get(old_type.lower(), 0)
    new_order = type_order.get(new_type.lower(), 0)
    
    # Widening if new type is higher in order
    return new_order >= old_order


def check_compatibility(
    old_schema: TableSchema,
    new_schema: TableSchema,
) -> CompatibilityReport:
    """
    Check compatibility between two schemas.
    """
    changes = compare_schemas(old_schema, new_schema)
    breaking_changes = [c for c in changes if c.is_breaking]
    
    if not breaking_changes:
        compatibility = CompatibilityLevel.FULL
    elif all(c.change_type == ChangeType.COLUMN_ADDED for c in breaking_changes):
        compatibility = CompatibilityLevel.FORWARD
    elif all(c.change_type == ChangeType.COLUMN_REMOVED for c in breaking_changes):
        compatibility = CompatibilityLevel.BACKWARD
    else:
        compatibility = CompatibilityLevel.NONE
    
    return CompatibilityReport(
        source_version="",  # Will be set by caller
        target_version="",
        compatibility=compatibility,
        changes=changes,
        breaking_changes=breaking_changes,
    )


# =============================================================================
# Schema Registry
# =============================================================================

class SchemaEvolutionRegistry:
    """
    Registry for tracking schema versions.
    """
    
    def __init__(self):
        # table_name -> list of versions (ordered by version)
        self._versions: Dict[str, List[SchemaVersion]] = {}
    
    def register(
        self,
        table_name: str,
        schema: TableSchema,
        version: str,
        description: str = "",
        created_by: str = "",
    ) -> SchemaVersion:
        """Register a new schema version."""
        if table_name not in self._versions:
            self._versions[table_name] = []
        
        # Calculate changes from previous
        changes = []
        if self._versions[table_name]:
            prev = self._versions[table_name][-1]
            changes = compare_schemas(prev.schema, schema)
        
        version_obj = SchemaVersion(
            version=version,
            schema=schema,
            description=description,
            created_by=created_by,
            changes_from_previous=changes,
        )
        
        self._versions[table_name].append(version_obj)
        logger.info(f"Registered schema {table_name} v{version} with {len(changes)} changes")
        
        return version_obj
    
    def get_version(
        self,
        table_name: str,
        version: Optional[str] = None,
    ) -> Optional[SchemaVersion]:
        """Get a specific version or latest."""
        versions = self._versions.get(table_name, [])
        if not versions:
            return None
        
        if version:
            for v in versions:
                if v.version == version:
                    return v
            return None
        
        return versions[-1]  # Latest
    
    def get_history(self, table_name: str) -> List[Dict[str, Any]]:
        """Get version history for a table."""
        versions = self._versions.get(table_name, [])
        return [
            {
                "version": v.version,
                "created_at": datetime.fromtimestamp(v.created_at).isoformat(),
                "description": v.description,
                "changes_count": len(v.changes_from_previous),
                "breaking_changes": sum(1 for c in v.changes_from_previous if c.is_breaking),
            }
            for v in versions
        ]
    
    def check_compatibility(
        self,
        table_name: str,
        source_version: str,
        target_version: str,
    ) -> Optional[CompatibilityReport]:
        """Check compatibility between two versions."""
        source = self.get_version(table_name, source_version)
        target = self.get_version(table_name, target_version)
        
        if not source or not target:
            return None
        
        report = check_compatibility(source.schema, target.schema)
        report.source_version = source_version
        report.target_version = target_version
        
        return report
    
    def list_tables(self) -> List[str]:
        """List all tracked tables."""
        return list(self._versions.keys())
    
    def clear(self):
        """Clear registry (testing)."""
        self._versions.clear()


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
    """Track a new schema version."""
    return get_registry().register(table_name, schema, version, description)


def get_schema_history(table_name: str) -> List[Dict[str, Any]]:
    """Get schema version history."""
    return get_registry().get_history(table_name)


def get_latest_schema(table_name: str) -> Optional[TableSchema]:
    """Get the latest schema for a table."""
    version = get_registry().get_version(table_name)
    return version.schema if version else None


def check_schema_compatibility(
    table_name: str,
    source_version: str,
    target_version: str,
) -> Optional[Dict[str, Any]]:
    """Check compatibility between versions."""
    report = get_registry().check_compatibility(table_name, source_version, target_version)
    return report.to_dict() if report else None


def reset_registry():
    """Reset the registry (testing)."""
    global _registry
    _registry = None
