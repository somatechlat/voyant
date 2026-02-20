"""
Data Contracts Module for Schema Validation and Governance.

This module provides a comprehensive system for defining, managing, and enforcing
schema-based data contracts. It is a cornerstone of the platform's data governance
capabilities, ensuring that data conforms to expected quality, format, and
sensitivity standards before it is used in analysis.

Reference: docs/CANONICAL_ROADMAP.md - P5 Governance & Contracts

Features:
- Loading contract definitions from YAML or JSON files.
- In-memory registry for managing and versioning contracts.
- Validation of data schemas against a contract.
- Classification of data sensitivity (e.g., PII, Secret).
- Generation of standard JSON Schema for external tools.

Usage:
    from apps.core.lib.contracts import load_contract, validate_schema

    # Load a contract from a YAML file
    contract = load_contract("/path/to/contract.yaml")

    # Validate a dataset's schema against the contract
    column_schema = [{"name": "id", "type": "integer"}, ...]
    result = validate_schema(contract, column_schema)
    if not result.valid:
        print(f"Schema validation failed: {result.errors}")
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class SensitivityLevel(str, Enum):
    """
    Enumeration for data sensitivity classification.
    """

    PUBLIC = "public"  # No restrictions on access.
    INTERNAL = "internal"  # For internal company use only.
    CONFIDENTIAL = "confidential"  # Restricted to specific teams or roles.
    PII = "pii"  # Personally Identifiable Information, subject to privacy regulations.
    SECRET = "secret"  # Highly restricted, mission-critical business secrets.


class DataType(str, Enum):
    """Enumeration of standard, abstract data types used in contracts."""

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
    """
    Defines the contract for a single column in a dataset.

    This includes data type, nullability, sensitivity, validation rules, and
    data quality expectations.

    Attributes:
        name: The name of the column.
        data_type: The expected data type from the DataType enum.
        nullable: Whether the column is allowed to contain null values.
        description: A human-readable description of the column.
        sensitivity: The data sensitivity classification for this column.
        min_value: The minimum allowed value for a numeric column.
        max_value: The maximum allowed value for a numeric column.
        min_length: The minimum allowed length for a string column.
        max_length: The maximum allowed length for a string column.
        pattern: A regex pattern that string values must match.
        enum_values: A list of allowed values for an enum-type column.
        max_null_rate: The maximum allowed percentage of null values (0.0 to 1.0).
        unique: Whether all values in the column must be unique.
    """

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
    pattern: Optional[str] = None
    enum_values: Optional[List[str]] = None

    # Quality expectations
    max_null_rate: float = 1.0
    unique: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert the column specification to a dictionary."""
        result = {
            "name": self.name,
            "data_type": self.data_type.value,
            "nullable": self.nullable,
            "description": self.description,
            "sensitivity": self.sensitivity.value,
        }
        # Add optional fields only if they are set
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
        """Create a ColumnSpec instance from a dictionary."""
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
    """
    Represents a full data contract for a dataset, including schema, metadata,
    and quality SLAs.

    Attributes:
        name: The unique name of the data contract.
        version: The semantic version of the contract (e.g., "1.0.0").
        description: A human-readable description of the dataset's purpose.
        owner: The team or individual responsible for this dataset.
        columns: A list of ColumnSpec objects defining the schema.
        created_at: ISO 8601 timestamp of when the contract was created.
        updated_at: ISO 8601 timestamp of the last update.
        tags: A list of tags for categorizing and searching for the contract.
        sla_freshness_hours: Service Level Agreement for how recent the data must be.
        sla_completeness_pct: Service Level Agreement for the minimum percentage of data completeness.
    """

    name: str
    version: str
    description: str = ""
    owner: str = ""
    columns: List[ColumnSpec] = field(default_factory=list)

    # Metadata
    created_at: str = ""
    updated_at: str = ""
    tags: List[str] = field(default_factory=list)

    # Quality SLAs
    sla_freshness_hours: Optional[int] = None
    sla_completeness_pct: Optional[float] = None

    def __post_init__(self):
        """Set default timestamps after initialization."""
        timestamp = datetime.utcnow().isoformat()
        if not self.created_at:
            self.created_at = timestamp
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """Convert the DataContract to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataContract":
        """Create a DataContract instance from a dictionary."""
        columns = [ColumnSpec.from_dict(c) for c in data.get("columns", [])]
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
        """Convert the data contract into a standard JSON Schema document."""
        properties = {}
        required = []

        for col in self.columns:
            prop: Dict[str, Any] = {"description": col.description}

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

            # Add validation rules from the column spec
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
        """Get a list of all column names marked as PII."""
        return [c.name for c in self.columns if c.sensitivity == SensitivityLevel.PII]

    def get_sensitive_columns(self) -> List[str]:
        """Get a list of all sensitive columns (PII, Secret, Confidential)."""
        sensitive_levels = {
            SensitivityLevel.PII,
            SensitivityLevel.SECRET,
            SensitivityLevel.CONFIDENTIAL,
        }
        return [c.name for c in self.columns if c.sensitivity in sensitive_levels]


# =============================================================================
# Validation Logic
# =============================================================================


@dataclass
class ValidationError:
    """Represents a single, specific validation error against a contract."""

    column: str
    error_type: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Represents the complete result of validating data against a contract."""

    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the validation result to a dictionary."""
        return {
            "valid": self.valid,
            "error_count": len(self.errors),
            "errors": [asdict(e) for e in self.errors],
            "warnings": self.warnings,
            "stats": self.stats,
        }


def validate_schema(
    contract: DataContract,
    columns: List[Dict[str, Any]],
) -> ValidationResult:
    """
    Validate that a given physical schema matches the contract's logical schema.

    This checks for missing or extra columns and verifies type compatibility.

    Args:
        contract: The DataContract to validate against.
        columns: A list of dictionaries representing the physical schema,
                 each with 'name' and 'type' keys.

    Returns:
        A ValidationResult object summarizing the findings.
    """
    errors = []
    warnings = []

    actual_columns = {c["name"]: c for c in columns}
    expected_columns = {c.name: c for c in contract.columns}

    # Check for missing required columns from the contract
    for col_name, col_spec in expected_columns.items():
        if col_name not in actual_columns:
            if not col_spec.nullable:
                errors.append(
                    ValidationError(
                        column=col_name,
                        error_type="missing_required",
                        message=f"Required column '{col_name}' is missing.",
                    )
                )
            else:
                warnings.append(f"Optional column '{col_name}' is missing.")

    # Check for extra columns in the data not defined in the contract
    for col_name in actual_columns:
        if col_name not in expected_columns:
            warnings.append(f"Column '{col_name}' exists in data but not in contract.")

    # Check for type compatibility between contract and actual schema
    for col_name, col_spec in expected_columns.items():
        if col_name in actual_columns:
            actual_type = actual_columns[col_name].get("type", "").lower()
            if col_spec.data_type != DataType.ANY:
                expected_type = col_spec.data_type.value
                if not _types_compatible(expected_type, actual_type):
                    errors.append(
                        ValidationError(
                            column=col_name,
                            error_type="type_mismatch",
                            message=f"Expected type '{expected_type}' but found '{actual_type}'.",
                            details={"expected": expected_type, "actual": actual_type},
                        )
                    )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        stats={"columns_checked": len(expected_columns)},
    )


def _types_compatible(expected: str, actual: str) -> bool:
    """
    Check if an actual physical data type is compatible with an expected logical type.

    This provides a lenient mapping, e.g., 'varchar' is compatible with 'string'.
    """
    actual = actual.lower()

    # Mappings from logical contract type to potential physical types
    compatibility_map = {
        "string": ["string", "varchar", "text", "char"],
        "integer": ["integer", "int", "bigint", "smallint", "int64", "int32"],
        "float": ["float", "double", "decimal", "numeric", "real", "float64"],
        "boolean": ["boolean", "bool"],
        "date": ["date"],
        "datetime": ["datetime", "timestamp"],
        "timestamp": ["timestamp", "datetime"],
    }

    compatible_types = compatibility_map.get(expected, [expected])
    return any(t in actual for t in compatible_types)


# =============================================================================
# I/O and Registry Functions
# =============================================================================


def load_contract(path: Union[str, Path]) -> DataContract:
    """
    Load a DataContract from a YAML or JSON file.

    Args:
        path: The file path to the contract.

    Returns:
        A DataContract instance.

    Raises:
        ImportError: If a YAML file is provided but `PyYAML` is not installed.
        FileNotFoundError: If the specified path does not exist.
    """
    path = Path(path)
    with path.open() as f:
        content = f.read()

    if path.suffix in (".yaml", ".yml"):
        try:
            import yaml

            data = yaml.safe_load(content)
        except ImportError as e:
            raise ImportError(
                "PyYAML is required to load YAML contracts. Please run: pip install PyYAML"
            ) from e
    else:
        data = json.loads(content)

    return DataContract.from_dict(data)


def save_contract(contract: DataContract, path: Union[str, Path]):
    """
    Save a DataContract to a JSON file.

    Args:
        contract: The DataContract instance to save.
        path: The file path where the contract will be saved.
    """
    path = Path(path)
    with path.open("w") as f:
        json.dump(contract.to_dict(), f, indent=2)


def save_json_schema(contract: DataContract, path: Union[str, Path]):
    """
    Save a DataContract's representation as a JSON Schema document.

    Args:
        contract: The DataContract instance to convert and save.
        path: The file path where the JSON Schema will be saved.
    """
    path = Path(path)
    with path.open("w") as f:
        json.dump(contract.to_json_schema(), f, indent=2)


# --- In-Memory Contract Registry ---

_contract_registry: Dict[str, Dict[str, DataContract]] = {}


def register_contract(contract: DataContract):
    """
    Register a DataContract in the in-memory registry.

    Args:
        contract: The DataContract to register.
    """
    if contract.name not in _contract_registry:
        _contract_registry[contract.name] = {}

    _contract_registry[contract.name][contract.version] = contract
    logger.info(f"Registered contract: {contract.name} v{contract.version}")


def get_contract(name: str, version: Optional[str] = None) -> Optional[DataContract]:
    """
    Get a contract from the registry by name and optional version.

    Args:
        name: The name of the contract.
        version: The specific version to retrieve. If None, the latest version is returned.

    Returns:
        The DataContract instance or None if not found.
    """
    if name not in _contract_registry:
        return None

    versions = _contract_registry[name]
    if not versions:
        return None

    if version:
        return versions.get(version)

    # Return latest version by sorting keys semantically (if possible)
    try:
        sorted_versions = sorted(
            versions.keys(), key=lambda v: [int(p) for p in v.split(".")], reverse=True
        )
    except (ValueError, TypeError):
        sorted_versions = sorted(versions.keys(), reverse=True)

    return versions[sorted_versions[0]] if sorted_versions else None


def list_contracts() -> List[Dict[str, Any]]:
    """
    List metadata for all contracts currently in the registry.

    Returns:
        A list of dictionaries, each containing summary info about a contract.
    """
    result = []
    for name, versions in _contract_registry.items():
        for version, contract in versions.items():
            result.append(
                {
                    "name": name,
                    "version": version,
                    "owner": contract.owner,
                    "column_count": len(contract.columns),
                    "tags": contract.tags,
                }
            )
    return result


def clear_registry():
    """Clear all contracts from the registry. Used primarily for testing."""
    _contract_registry.clear()
