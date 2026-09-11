"""
Ontology Engine — Property Validation.

ONT-F-002 to ONT-F-005: Validates object properties against the
object type schema at create/update time. Supports type coercion,
required constraints, default values, and custom validation rules.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from apps.ontology.models import Property, PropertyType


class ValidationError(Exception):
    """Raised when property validation fails."""

    def __init__(self, errors: list[dict[str, str]]):
        self.errors = errors
        super().__init__(f"Validation failed: {len(errors)} error(s)")


# ---------------------------------------------------------------------------
# Type-level validators
# ---------------------------------------------------------------------------

_TYPE_VALIDATORS = {
    PropertyType.STRING: lambda v: isinstance(v, str),
    PropertyType.INTEGER: lambda v: isinstance(v, int) and not isinstance(v, bool),
    PropertyType.FLOAT: lambda v: isinstance(v, (int, float))
    and not isinstance(v, bool),
    PropertyType.BOOLEAN: lambda v: isinstance(v, bool),
    PropertyType.DATE: lambda v: isinstance(v, str) and _is_valid_date(v),
    PropertyType.TIMESTAMP: lambda v: isinstance(v, str) and _is_valid_timestamp(v),
    PropertyType.ARRAY: lambda v: isinstance(v, list),
    PropertyType.MAP: lambda v: isinstance(v, dict),
    PropertyType.GEOPOINT: lambda v: isinstance(v, list) and len(v) == 2,
}


def _is_valid_date(value: str) -> bool:
    try:
        datetime.strptime(value, "%Y-%m-%d").date()
        return True
    except (ValueError, TypeError):
        return False


def _is_valid_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# Rule-based validators
# ---------------------------------------------------------------------------

_RULE_VALIDATORS = {
    "regex": lambda value, rule: bool(re.fullmatch(rule, str(value))),
    "min": lambda value, rule: value >= rule,
    "max": lambda value, rule: value <= rule,
    "min_length": lambda value, rule: len(str(value)) >= rule,
    "max_length": lambda value, rule: len(str(value)) <= rule,
    "enum_values": lambda value, rule: value in rule,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_properties(
    properties: dict[str, Any],
    property_defs: list[Property],
    *,
    partial: bool = False,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """
    Validate and normalise an instance's properties against its object type schema.

    Args:
        properties: Raw property values from the user.
        property_defs: List of Property model instances defining the schema.
        partial: If True, skip required-checks (used for PATCH updates).

    Returns:
        (normalised_properties, list_of_errors)
        If errors is non-empty, the caller should reject the request.
    """
    errors: list[dict[str, str]] = []
    normalised: dict[str, Any] = {}

    defs_by_name: dict[str, Property] = {p.name: p for p in property_defs}

    for prop_def in property_defs:
        value = properties.get(prop_def.name)

        # --- default / required ---
        if value is None:
            if prop_def.required and not partial:
                errors.append(
                    {
                        "field": prop_def.name,
                        "code": "required",
                        "message": f"'{prop_def.name}' is required",
                    }
                )
                continue
            if prop_def.default_value is not None:
                value = prop_def.default_value
            else:
                normalised[prop_def.name] = None
                continue

        # --- type check ---
        if prop_def.property_type == PropertyType.ENUM:
            allowed = (prop_def.validation_rules or {}).get("enum_values", [])
            if allowed and value not in allowed:
                errors.append(
                    {
                        "field": prop_def.name,
                        "code": "invalid_choice",
                        "message": f"'{prop_def.name}' must be one of {allowed}, got {value!r}",
                    }
                )
                continue
        elif prop_def.property_type == PropertyType.STRUCT:
            if not isinstance(value, dict):
                errors.append(
                    {
                        "field": prop_def.name,
                        "code": "invalid_type",
                        "message": f"'{prop_def.name}' must be a dict, got {type(value).__name__}",
                    }
                )
                continue
        else:
            validator = _TYPE_VALIDATORS.get(prop_def.property_type)
            if validator and not validator(value):
                errors.append(
                    {
                        "field": prop_def.name,
                        "code": "invalid_type",
                        "message": (
                            f"'{prop_def.name}' expects {prop_def.property_type}, got {type(value).__name__}"
                        ),
                    }
                )
                continue

        # --- rule-based validation ---
        rules = prop_def.validation_rules or {}
        for rule_name, rule_value in rules.items():
            rule_fn = _RULE_VALIDATORS.get(rule_name)
            if rule_fn and not rule_fn(value, rule_value):
                errors.append(
                    {
                        "field": prop_def.name,
                        "code": rule_name,
                        "message": f"'{prop_def.name}' failed rule '{rule_name}'",
                    }
                )
                continue

        normalised[prop_def.name] = value

    # Extra properties not in schema — reject them
    known = set(defs_by_name.keys())
    for key in properties:
        if key not in known:
            errors.append(
                {
                    "field": key,
                    "code": "unknown_field",
                    "message": f"Unknown property '{key}' not defined in object type",
                }
            )

    return normalised, errors
