"""Data contract validation engine.

Validates data records against DataContract schema definitions and quality rules.
Integrated with the ingestion pipeline via Temporal workflow activities.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "ValidationResult",
    "SchemaValidator",
    "QualityRuleValidator",
    "DataContractValidator",
]

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a data contract validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_rows: int = 0
    failed_rows: int = 0

    def merge(self, other: ValidationResult) -> ValidationResult:
        """Merge another validation result into this one."""
        return ValidationResult(
            valid=self.valid and other.valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            checked_rows=self.checked_rows + other.checked_rows,
            failed_rows=self.failed_rows + other.failed_rows,
        )


class SchemaValidator:
    """Validates data records against a schema definition."""

    def validate_schema(self, data: dict[str, Any], schema: dict) -> ValidationResult:
        """Validate a single data record against a schema.

        Args:
            data: Data record to validate.
            schema: Schema definition with fields list.

        Returns:
            ValidationResult with errors for each field violation.
        """
        errors = []
        fields = schema.get("fields", [])

        for field_def in fields:
            name = field_def.get("name", "")
            required = field_def.get("required", False)
            field_type = field_def.get("type", "string")
            value = data.get(name)

            if value is None:
                if required:
                    errors.append(f"Required field '{name}' is missing")
                continue

            if not self._check_type(value, field_type):
                errors.append(
                    f"Field '{name}' expected type '{field_type}', got '{type(value).__name__}'"
                )

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            checked_rows=1,
            failed_rows=1 if errors else 0,
        )

    @staticmethod
    def _check_type(value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "integer": (int,),
            "float": (int, float),
            "boolean": bool,
            "array": list,
            "map": dict,
            "object": dict,
        }
        expected = type_map.get(expected_type)
        if expected is None:
            return True
        return isinstance(value, expected)


class QualityRuleValidator:
    """Validates data against quality rules (not_null, unique, pattern, range)."""

    def validate_quality_rules(
        self, data: list[dict[str, Any]], rules: list[dict]
    ) -> ValidationResult:
        """Validate a dataset against quality rules.

        Args:
            data: List of data records.
            rules: Quality rules to apply.

        Returns:
            ValidationResult with errors for each rule violation.
        """
        errors = []
        warnings = []
        failed_rows = 0

        for rule in rules:
            rule_type = rule.get("type", "")
            column = rule.get("column", "")

            if rule_type == "not_null":
                violations = sum(1 for row in data if row.get(column) is None)
                if violations > 0:
                    errors.append(f"not_null violation: {column} has {violations} null values")
                    failed_rows += violations

            elif rule_type == "unique":
                values = [row.get(column) for row in data if row.get(column) is not None]
                duplicates = len(values) - len(set(str(v) for v in values))
                if duplicates > 0:
                    errors.append(f"unique violation: {column} has {duplicates} duplicate values")
                    failed_rows += duplicates

            elif rule_type == "pattern":
                pattern = rule.get("pattern", "")
                if pattern:
                    regex = re.compile(pattern)
                    violations = sum(
                        1
                        for row in data
                        if row.get(column) is not None
                        and not regex.match(str(row[column]))
                    )
                    if violations > 0:
                        errors.append(
                            f"pattern violation: {column} has {violations} values not matching '{pattern}'"
                        )
                        failed_rows += violations

            elif rule_type == "range":
                min_val = rule.get("min")
                max_val = rule.get("max")
                for row in data:
                    val = row.get(column)
                    if val is None:
                        continue
                    try:
                        num = float(val)
                    except (ValueError, TypeError):
                        continue
                    if min_val is not None and num < min_val:
                        errors.append(f"range violation: {column}={num} < min({min_val})")
                        failed_rows += 1
                    if max_val is not None and num > max_val:
                        errors.append(f"range violation: {column}={num} > max({max_val})")
                        failed_rows += 1

            elif rule_type == "not_empty":
                violations = sum(
                    1 for row in data if not row.get(column) or str(row.get(column)).strip() == ""
                )
                if violations > 0:
                    errors.append(f"not_empty violation: {column} has {violations} empty values")
                    failed_rows += violations

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            checked_rows=len(data),
            failed_rows=failed_rows,
        )


class DataContractValidator:
    """Orchestrates validation of data against a DataContract."""

    def __init__(
        self,
        schema_validator: SchemaValidator | None = None,
        quality_validator: QualityRuleValidator | None = None,
    ) -> None:
        self.schema_validator = schema_validator or SchemaValidator()
        self.quality_validator = quality_validator or QualityRuleValidator()

    def validate(
        self, data: list[dict[str, Any]], contract: Any
    ) -> ValidationResult:
        """Validate data against all contract rules.

        Args:
            data: List of data records to validate.
            contract: DataContract model instance with schema_definition and quality_rules.

        Returns:
            ValidationResult combining schema and quality check results.
        """
        schema = getattr(contract, "schema_definition", None) or {}
        rules = getattr(contract, "quality_rules", None) or []

        result = ValidationResult(valid=True, checked_rows=len(data))

        # Schema validation (per-row)
        if schema.get("fields"):
            for row in data:
                row_result = self.schema_validator.validate_schema(row, schema)
                result = result.merge(row_result)

        # Quality rule validation (dataset-level)
        if rules:
            quality_result = self.quality_validator.validate_quality_rules(data, rules)
            result = result.merge(quality_result)

        logger.info(
            "Contract '%s': %d rows checked, %d errors, valid=%s",
            getattr(contract, "name", "unknown"),
            result.checked_rows,
            len(result.errors),
            result.valid,
        )

        return result
