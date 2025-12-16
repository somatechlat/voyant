"""
Data Contracts Module

Schema-based data contracts for validation and enforcement.
Reference: docs/CANONICAL_ROADMAP.md - P5 Governance & Contracts

Features:
- YAML/JSON contract definitions
- JSON Schema generation
- Pre-KPI validation
- Contract versioning
- Column sensitivity classification

Usage:
    from voyant.core.contracts import (
        DataContract, load_contract, validate_data,
        SensitivityLevel, ColumnSpec
    )
    
    # Load contract from YAML
    contract = load_contract("/path/to/contract.yaml")
    
    # Validate data against contract
    result = validate_data(contract, dataframe)
    if not result.valid:
        print(result.errors)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


class SensitivityLevel(str, Enum):
    """Column sensitivity classification levels."""
    PUBLIC = "public"           # No restrictions
    INTERNAL = "internal"       # Internal use only
    CONFIDENTIAL = "confidential"  # Limited access
    PII = "pii"                 # Personal Identifiable Information
    SECRET = "secret"           # Highly restricted


class DataType(str, Enum):
    """Standard data types for contracts."""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    ARRAY = "array"
    OBJECT = "object"
    ANY = "any"


@dataclass
class ColumnSpec:
    """Specification for a single column."""
    name: str
    data_type: DataType
    nullable: bool = True
    description: str = ""
    sensitivity: SensitivityLevel = SensitivityLevel.INTERNAL
    
    # Validation rules
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None  # Regex pattern
    enum_values: Optional[List[str]] = None
    
    # Quality expectations
    max_null_rate: float = 1.0  # 0.0 to 1.0
    unique: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "data_type": self.data_type.value,
            "nullable": self.nullable,
            "description": self.description,
            "sensitivity": self.sensitivity.value,
        }
        if self.min_value is not None:
            result["min_value"] = self.min_value
        if self.max_value is not None:
            result["max_value"] = self.max_value
        if self.min_length is not None:
            result["min_length"] = self.min_length
        if self.max_length is not None:
            result["max_length"] = self.max_length
        if self.pattern:
            result["pattern"] = self.pattern
        if self.enum_values:
            result["enum_values"] = self.enum_values
        if self.max_null_rate < 1.0:
            result["max_null_rate"] = self.max_null_rate
        if self.unique:
            result["unique"] = True
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ColumnSpec":
        return cls(
            name=data["name"],
            data_type=DataType(data.get("data_type", "any")),
            nullable=data.get("nullable", True),
            description=data.get("description", ""),
            sensitivity=SensitivityLevel(data.get("sensitivity", "internal")),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            min_length=data.get("min_length"),
            max_length=data.get("max_length"),
            pattern=data.get("pattern"),
            enum_values=data.get("enum_values"),
            max_null_rate=data.get("max_null_rate", 1.0),
            unique=data.get("unique", False),
        )


@dataclass
class DataContract:
    """Data contract definition."""
    name: str
    version: str
    description: str = ""
    owner: str = ""
    
    # Schema
    columns: List[ColumnSpec] = field(default_factory=list)
    
    # Metadata
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = field(default_factory=list)
    
    # Quality SLAs
    sla_freshness_hours: Optional[int] = None
    sla_completeness_pct: Optional[float] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "owner": self.owner,
            "columns": [c.to_dict() for c in self.columns],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "sla_freshness_hours": self.sla_freshness_hours,
            "sla_completeness_pct": self.sla_completeness_pct,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataContract":
        columns = [
            ColumnSpec.from_dict(c) for c in data.get("columns", [])
        ]
        return cls(
            name=data["name"],
            version=data.get("version", "1.0.0"),
            description=data.get("description", ""),
            owner=data.get("owner", ""),
            columns=columns,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            tags=data.get("tags", []),
            sla_freshness_hours=data.get("sla_freshness_hours"),
            sla_completeness_pct=data.get("sla_completeness_pct"),
        )
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert contract to JSON Schema format."""
        properties = {}
        required = []
        
        for col in self.columns:
            prop = {"description": col.description}
            
            # Map data types
            type_mapping = {
                DataType.STRING: {"type": "string"},
                DataType.INTEGER: {"type": "integer"},
                DataType.FLOAT: {"type": "number"},
                DataType.BOOLEAN: {"type": "boolean"},
                DataType.DATE: {"type": "string", "format": "date"},
                DataType.DATETIME: {"type": "string", "format": "date-time"},
                DataType.TIMESTAMP: {"type": "string", "format": "date-time"},
                DataType.ARRAY: {"type": "array"},
                DataType.OBJECT: {"type": "object"},
                DataType.ANY: {},
            }
            prop.update(type_mapping.get(col.data_type, {}))
            
            # Add validation rules
            if col.min_value is not None:
                prop["minimum"] = col.min_value
            if col.max_value is not None:
                prop["maximum"] = col.max_value
            if col.min_length is not None:
                prop["minLength"] = col.min_length
            if col.max_length is not None:
                prop["maxLength"] = col.max_length
            if col.pattern:
                prop["pattern"] = col.pattern
            if col.enum_values:
                prop["enum"] = col.enum_values
            
            properties[col.name] = prop
            
            if not col.nullable:
                required.append(col.name)
        
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "title": self.name,
            "description": self.description,
            "type": "object",
            "properties": properties,
            "required": required,
        }
    
    def get_pii_columns(self) -> List[str]:
        """Get list of PII column names."""
        return [c.name for c in self.columns if c.sensitivity == SensitivityLevel.PII]
    
    def get_sensitive_columns(self) -> List[str]:
        """Get list of sensitive column names (PII + Secret + Confidential)."""
        sensitive = {SensitivityLevel.PII, SensitivityLevel.SECRET, SensitivityLevel.CONFIDENTIAL}
        return [c.name for c in self.columns if c.sensitivity in sensitive]


# =============================================================================
# Validation
# =============================================================================

@dataclass
class ValidationError:
    """A single validation error."""
    column: str
    error_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Result of validating data against a contract."""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "errors": [
                {
                    "column": e.column,
                    "error_type": e.error_type,
                    "message": e.message,
                    "details": e.details,
                }
                for e in self.errors
            ],
            "warnings": self.warnings,
            "stats": self.stats,
        }


def validate_schema(
    contract: DataContract,
    columns: List[Dict[str, Any]],
) -> ValidationResult:
    """
    Validate that data columns match contract schema.
    
    Args:
        contract: The data contract
        columns: List of column dicts with 'name' and 'type' keys
    
    Returns:
        ValidationResult
    """
    errors = []
    warnings = []
    
    # Build lookup of actual columns
    actual_columns = {c["name"]: c for c in columns}
    expected_columns = {c.name: c for c in contract.columns}
    
    # Check for missing required columns
    for col_name, col_spec in expected_columns.items():
        if col_name not in actual_columns:
            if not col_spec.nullable:
                errors.append(ValidationError(
                    column=col_name,
                    error_type="missing_required",
                    message=f"Required column '{col_name}' is missing",
                ))
            else:
                warnings.append(f"Optional column '{col_name}' is missing")
    
    # Check for extra columns (not in contract)
    for col_name in actual_columns:
        if col_name not in expected_columns:
            warnings.append(f"Column '{col_name}' found but not in contract")
    
    # Check type compatibility
    for col_name, col_spec in expected_columns.items():
        if col_name in actual_columns:
            actual_type = actual_columns[col_name].get("type", "").lower()
            # Simplified type checking
            if col_spec.data_type != DataType.ANY:
                expected_type = col_spec.data_type.value
                if not _types_compatible(expected_type, actual_type):
                    errors.append(ValidationError(
                        column=col_name,
                        error_type="type_mismatch",
                        message=f"Expected {expected_type}, got {actual_type}",
                        details={"expected": expected_type, "actual": actual_type},
                    ))
    
    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        stats={"columns_checked": len(expected_columns)},
    )


def _types_compatible(expected: str, actual: str) -> bool:
    """Check if actual type is compatible with expected type."""
    # Normalize types
    actual = actual.lower()
    
    # Type compatibility mappings
    compat = {
        "string": ["string", "varchar", "text", "char"],
        "integer": ["integer", "int", "bigint", "smallint", "int64", "int32"],
        "float": ["float", "double", "decimal", "numeric", "real", "float64"],
        "boolean": ["boolean", "bool"],
        "date": ["date"],
        "datetime": ["datetime", "timestamp"],
        "timestamp": ["timestamp", "datetime"],
    }
    
    compatible_types = compat.get(expected, [expected])
    return any(t in actual for t in compatible_types)


# =============================================================================
# I/O Functions
# =============================================================================

def load_contract(path: Union[str, Path]) -> DataContract:
    """
    Load a data contract from YAML or JSON file.
    
    Args:
        path: Path to contract file (.yaml, .yml, or .json)
    
    Returns:
        DataContract object
    """
    path = Path(path)
    
    with open(path) as f:
        content = f.read()
    
    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml
            data = yaml.safe_load(content)
        except ImportError:
            raise ImportError("PyYAML is required for YAML contracts: pip install pyyaml")
    else:
        data = json.loads(content)
    
    return DataContract.from_dict(data)


def save_contract(contract: DataContract, path: Union[str, Path]):
    """Save a data contract to JSON file."""
    path = Path(path)
    
    with open(path, "w") as f:
        json.dump(contract.to_dict(), f, indent=2)


def save_json_schema(contract: DataContract, path: Union[str, Path]):
    """Save contract as JSON Schema."""
    path = Path(path)
    
    with open(path, "w") as f:
        json.dump(contract.to_json_schema(), f, indent=2)


# =============================================================================
# Contract Registry (In-Memory)
# =============================================================================

_contract_registry: Dict[str, Dict[str, DataContract]] = {}  # name -> version -> contract


def register_contract(contract: DataContract):
    """Register a contract in the registry."""
    if contract.name not in _contract_registry:
        _contract_registry[contract.name] = {}
    
    _contract_registry[contract.name][contract.version] = contract
    logger.info(f"Registered contract: {contract.name} v{contract.version}")


def get_contract(name: str, version: Optional[str] = None) -> Optional[DataContract]:
    """
    Get a contract from the registry.
    
    Args:
        name: Contract name
        version: Specific version (None = latest)
    
    Returns:
        DataContract or None if not found
    """
    if name not in _contract_registry:
        return None
    
    versions = _contract_registry[name]
    
    if version:
        return versions.get(version)
    
    # Return latest version
    sorted_versions = sorted(versions.keys(), reverse=True)
    return versions[sorted_versions[0]] if sorted_versions else None


def list_contracts() -> List[Dict[str, Any]]:
    """List all registered contracts."""
    result = []
    for name, versions in _contract_registry.items():
        for version, contract in versions.items():
            result.append({
                "name": name,
                "version": version,
                "owner": contract.owner,
                "column_count": len(contract.columns),
                "tags": contract.tags,
            })
    return result


def clear_registry():
    """Clear all registered contracts (for testing)."""
    _contract_registry.clear()
