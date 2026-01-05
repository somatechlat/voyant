"""
Event Schema Module for Defining and Validating Structured Event Contracts.

This module provides an in-memory schema registry for defining and validating
structured events, ensuring that all events produced within the Voyant ecosystem
adhere to a clear, versioned contract.

Reference: docs/CANONICAL_ROADMAP.md - P2 Operability

Features:
- A central registry for all event lifecycle schemas.
- Support for semantic versioning and retrieval of the latest schema.
- Schema validation against event data payloads.
- Generation of standard JSON Schema for external tooling.

Personas Applied:
- PhD Developer: Enforces strong contracts and correct schema versioning semantics.
- Analyst: Enables schema evolution tracking and reliable downstream consumption.
- QA: Provides a foundation for comprehensive validation test coverage.
- ISO Documenter: Ensures all event schemas are self-describing.
- Security: Mandates that event schemas be designed to exclude sensitive data/PII.
- Performance: Uses efficient in-memory validation with no I/O on the hot path.
- UX: Produces clear, actionable errors upon validation failure.

Usage:
    from voyant.core.event_schema import (
        EventSchema, FieldSpec, FieldType, register_schema, validate_event
    )

    # 1. Define and register a schema
    schema = EventSchema(
        name="job.started",
        version="1.0.0",
        fields=[
            FieldSpec("job_id", FieldType.STRING, description="Unique job identifier"),
            ...
        ],
    )
    register_schema(schema)

    # 2. Validate an event payload against the schema
    result = validate_event("job.started", {"job_id": "123", ...})
    if not result.valid:
        print(f"Validation failed: {result.errors}")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class FieldType(str, Enum):
    """Enumeration of supported data types for event fields."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    ARRAY = "array"
    OBJECT = "object"
    ENUM = "enum"


@dataclass
class FieldSpec:
    """
    Specification for a single field within an EventSchema.

    Attributes:
        name: The name of the field.
        field_type: The data type of the field, from the FieldType enum.
        required: Whether the field must be present in the event data.
        description: A human-readable description of the field's purpose.
        enum_values: A list of allowed string values if field_type is ENUM.
        default: A default value for the field if not provided.
    """

    name: str
    field_type: FieldType
    required: bool = True
    description: str = ""
    enum_values: Optional[List[str]] = None
    default: Any = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert the field specification to a JSON Schema property definition."""
        type_mapping = {
            FieldType.STRING: {"type": "string"},
            FieldType.INTEGER: {"type": "integer"},
            FieldType.FLOAT: {"type": "number"},
            FieldType.BOOLEAN: {"type": "boolean"},
            FieldType.DATETIME: {"type": "string", "format": "date-time"},
            FieldType.ARRAY: {"type": "array"},
            FieldType.OBJECT: {"type": "object"},
        }

        schema = type_mapping.get(self.field_type, {"type": "string"})

        if self.field_type == FieldType.ENUM and self.enum_values:
            schema["enum"] = self.enum_values

        if self.description:
            schema["description"] = self.description

        if self.default is not None:
            schema["default"] = self.default

        return schema


@dataclass
class EventSchema:
    """
    A full schema definition for a specific type of event.

    Attributes:
        name: The unique name of the event (e.g., "job.started").
        version: The semantic version of the schema (e.g., "1.0.0").
        fields: A list of FieldSpec objects defining the event's payload.
        description: A human-readable description of the event's purpose.
        created_at: An ISO 8601 timestamp of when the schema was defined.
        deprecated: A flag indicating if the schema is deprecated.
        deprecation_message: A message explaining the reason for deprecation.
    """

    name: str
    version: str
    fields: List[FieldSpec]
    description: str = ""

    # Metadata
    created_at: str = ""
    deprecated: bool = False
    deprecation_message: str = ""

    def __post_init__(self):
        """Set the creation timestamp if not provided."""
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat() + "Z"

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert the EventSchema into a standard JSON Schema format."""
        properties = {}
        required = []

        for f in self.fields:
            properties[f.name] = f.to_json_schema()
            if f.required:
                required.append(f.name)

        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": f"urn:voyant:event:{self.name}:{self.version}",
            "title": self.name,
            "description": self.description,
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,  # Disallow unknown fields by default
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the schema."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "fields": [
                {
                    "name": f.name,
                    "type": f.field_type.value,
                    "required": f.required,
                    "description": f.description,
                }
                for f in self.fields
            ],
            "deprecated": self.deprecated,
            "created_at": self.created_at,
        }


@dataclass
class ValidationResult:
    """
    Represents the outcome of an event validation check.

    Attributes:
        valid: True if the event data conforms to the schema, False otherwise.
        errors: A list of validation errors found.
        warnings: A list of non-critical warnings (e.g., use of a deprecated schema).
    """

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a dictionary representation of the validation result."""
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


# =============================================================================
# Schema Registry
# =============================================================================

# In-memory registry mapping (name, version) -> EventSchema
_schema_registry: Dict[Tuple[str, str], EventSchema] = {}
# In-memory mapping of event name -> latest version string
_latest_versions: Dict[str, str] = {}


def register_schema(schema: EventSchema) -> None:
    """
    Register a new event schema in the global registry.

    If a schema with the same name and version already exists, it is overwritten.
    This function also updates the "latest" version pointer for the given schema name.

    Args:
        schema: The EventSchema instance to register.
    """
    key = (schema.name, schema.version)
    _schema_registry[key] = schema

    # Update latest version pointer
    current_latest = _latest_versions.get(schema.name)
    if current_latest is None or _version_gt(schema.version, current_latest):
        _latest_versions[schema.name] = schema.version

    logger.info(f"Registered event schema: {schema.name} v{schema.version}")


def get_schema(name: str, version: Optional[str] = None) -> Optional[EventSchema]:
    """
    Retrieve a schema from the registry by name and optional version.

    Args:
        name: The name of the event schema to retrieve.
        version: The specific version to retrieve. If None, the latest version is returned.

    Returns:
        The requested EventSchema instance, or None if not found.
    """
    if version:
        return _schema_registry.get((name, version))

    # If no version is specified, retrieve the latest version
    latest_version_str = _latest_versions.get(name)
    if latest_version_str:
        return _schema_registry.get((name, latest_version_str))
    return None


def list_schemas() -> List[Dict[str, Any]]:
    """
    List metadata for all registered schemas.

    Returns:
        A list of dictionaries, each containing metadata about a schema.
    """
    return [
        {
            "name": schema.name,
            "version": schema.version,
            "is_latest": schema.version == _latest_versions.get(schema.name),
            "deprecated": schema.deprecated,
        }
        for schema in _schema_registry.values()
    ]


def _version_gt(v1: str, v2: str) -> bool:
    """
    Compare two semantic version strings to determine if v1 is greater than v2.

    A simple implementation for versions like "1.0.0", "1.1.0".
    """
    try:
        parts1 = [int(p) for p in v1.split(".")]
        parts2 = [int(p) for p in v2.split(".")]
        return parts1 > parts2
    except (ValueError, TypeError):
        # Fallback to lexical comparison if parsing fails
        return v1 > v2


# =============================================================================
# Validation Logic
# =============================================================================


def validate_event(
    event_name: str,
    data: Dict[str, Any],
    version: Optional[str] = None,
) -> ValidationResult:
    """
    Validate a given event data payload against its registered schema.

    The validation checks for missing required fields, incorrect data types,
    and unknown fields.

    Args:
        event_name: The name of the event type to validate against.
        data: The event data payload (a dictionary).
        version: A specific schema version to use. If None, the latest is used.

    Returns:
        A ValidationResult object detailing whether the event is valid and
        any errors or warnings.
    """
    schema = get_schema(event_name, version)

    if not schema:
        return ValidationResult(
            valid=False,
            errors=[f"Schema not found for event type: {event_name}"],
        )

    errors = []
    warnings = []

    # Check for use of a deprecated schema
    if schema.deprecated:
        warnings.append(
            f"Event schema {event_name} v{schema.version} is deprecated: {schema.deprecation_message}"
        )

    # 1. Check for missing required fields
    schema_fields = {f.name for f in schema.fields}
    for field_spec in schema.fields:
        if field_spec.required and field_spec.name not in data:
            errors.append(f"Missing required field: '{field_spec.name}'")

    # 2. Check field types for all present fields
    for field_spec in schema.fields:
        if field_spec.name in data:
            value = data[field_spec.name]
            if not _check_type(value, field_spec.field_type, field_spec.enum_values):
                errors.append(
                    f"Invalid type for field '{field_spec.name}': expected {field_spec.field_type.value}, got {type(value).__name__}"
                )

    # 3. Check for unknown fields not defined in the schema
    for key in data:
        if key not in schema_fields:
            warnings.append(f"Unknown field provided: '{key}'")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def _check_type(
    value: Any, expected_type: FieldType, enum_values: Optional[List[str]]
) -> bool:
    """
    Internal helper to check if a value matches the expected FieldType.

    Args:
        value: The value to check.
        expected_type: The FieldType enum member to check against.
        enum_values: A list of allowed values if the type is ENUM.

    Returns:
        True if the type matches, False otherwise.
    """
    if value is None:
        return True  # Type validity for null values is handled by the `required` check.

    type_checks = {
        FieldType.STRING: lambda v: isinstance(v, str),
        FieldType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
        FieldType.FLOAT: lambda v: isinstance(v, (int, float))
        and not isinstance(v, bool),
        FieldType.BOOLEAN: lambda v: isinstance(v, bool),
        FieldType.DATETIME: lambda v: isinstance(v, str),  # Simplified check for ISO string
        FieldType.ARRAY: lambda v: isinstance(v, list),
        FieldType.OBJECT: lambda v: isinstance(v, dict),
    }

    # For ENUM, the base type must be string.
    if expected_type == FieldType.ENUM:
        if not isinstance(value, str):
            return False
        return value in (enum_values or [])

    check_fn = type_checks.get(expected_type)
    if check_fn:
        return check_fn(value)

    return True  # Default to true if no specific check is defined.


# =============================================================================
# Canonical Event Schemas Registration
# =============================================================================


def _register_canonical_schemas():
    """Register all canonical, system-wide Voyant event schemas on module load."""

    # --- Job Lifecycle Events ---
    register_schema(
        EventSchema(
            name="job.started",
            version="1.0.0",
            description="Emitted when a job begins execution.",
            fields=[
                FieldSpec("job_id", FieldType.STRING, description="Unique job identifier"),
                FieldSpec("tenant_id", FieldType.STRING, description="Tenant identifier"),
                FieldSpec(
                    "job_type",
                    FieldType.STRING,
                    description="Type of job (e.g., 'analyze', 'ingest').",
                ),
                FieldSpec(
                    "source_id",
                    FieldType.STRING,
                    required=False,
                    description="Identifier for the data source being processed.",
                ),
                FieldSpec(
                    "started_at", FieldType.DATETIME, description="ISO 8601 job start timestamp."
                ),
            ],
        )
    )

    register_schema(
        EventSchema(
            name="job.completed",
            version="1.0.0",
            description="Emitted when a job completes successfully.",
            fields=[
                FieldSpec("job_id", FieldType.STRING),
                FieldSpec("tenant_id", FieldType.STRING),
                FieldSpec("job_type", FieldType.STRING),
                FieldSpec("completed_at", FieldType.DATETIME),
                FieldSpec("duration_seconds", FieldType.FLOAT),
                FieldSpec("artifact_count", FieldType.INTEGER),
            ],
        )
    )

    register_schema(
        EventSchema(
            name="job.failed",
            version="1.0.0",
            description="Emitted when a job fails during execution.",
            fields=[
                FieldSpec("job_id", FieldType.STRING),
                FieldSpec("tenant_id", FieldType.STRING),
                FieldSpec("job_type", FieldType.STRING),
                FieldSpec("failed_at", FieldType.DATETIME),
                FieldSpec("error_code", FieldType.STRING),
                FieldSpec("error_message", FieldType.STRING),
                FieldSpec("retryable", FieldType.BOOLEAN, default=False),
            ],
        )
    )

    # --- Artifact Events ---
    register_schema(
        EventSchema(
            name="artifact.created",
            version="1.0.0",
            description="Emitted when a new artifact is created and stored.",
            fields=[
                FieldSpec("artifact_key", FieldType.STRING),
                FieldSpec("job_id", FieldType.STRING),
                FieldSpec("tenant_id", FieldType.STRING),
                FieldSpec(
                    "artifact_type",
                    FieldType.ENUM,
                    enum_values=[
                        "profile",
                        "kpi",
                        "quality",
                        "sufficiency",
                        "chart",
                        "narrative",
                    ],
                ),
                FieldSpec("size_bytes", FieldType.INTEGER),
                FieldSpec("created_at", FieldType.DATETIME),
            ],
        )
    )

    # --- Data Lifecycle Events ---
    register_schema(
        EventSchema(
            name="data.ingested",
            version="1.0.0",
            description="Emitted after a data ingestion process completes successfully.",
            fields=[
                FieldSpec("source_id", FieldType.STRING),
                FieldSpec("tenant_id", FieldType.STRING),
                FieldSpec("table_name", FieldType.STRING),
                FieldSpec("row_count", FieldType.INTEGER),
                FieldSpec("ingested_at", FieldType.DATETIME),
            ],
        )
    )

    register_schema(
        EventSchema(
            name="data.drift_detected",
            version="1.0.0",
            description="Emitted when significant statistical drift is detected in a dataset.",
            fields=[
                FieldSpec("source_id", FieldType.STRING),
                FieldSpec("tenant_id", FieldType.STRING),
                FieldSpec("drift_score", FieldType.FLOAT),
                FieldSpec("columns_drifted", FieldType.ARRAY),
                FieldSpec("detected_at", FieldType.DATETIME),
            ],
        )
    )

    # --- Governance & Quota Events ---
    register_schema(
        EventSchema(
            name="quota.warning",
            version="1.0.0",
            description="Emitted when a tenant's quota usage reaches a warning threshold.",
            fields=[
                FieldSpec("tenant_id", FieldType.STRING),
                FieldSpec(
                    "quota_type",
                    FieldType.ENUM,
                    enum_values=[
                        "jobs_per_day",
                        "concurrent_jobs",
                        "storage_gb",
                        "sources_count",
                    ],
                ),
                FieldSpec("current_usage", FieldType.FLOAT),
                FieldSpec("limit", FieldType.FLOAT),
                FieldSpec("percentage", FieldType.FLOAT),
            ],
        )
    )


# Initialize all canonical schemas when this module is first imported.
_register_canonical_schemas()


def clear_registry():
    """
    Clear all schemas from the registry.

    This function is intended for use in testing environments to ensure a
    clean state between test runs.
    """
    _schema_registry.clear()
    _latest_versions.clear()
