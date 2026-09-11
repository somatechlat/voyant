"""Tests for data contract validation module."""

from apps.governance.lib.contract_validator import (
    DataContractValidator,
    DataQualityRuleValidator,  # type: ignore[attr-defined]
    JSONSchemaValidator,  # type: ignore[attr-defined]
    ValidationResult,
)


class TestValidationResult:
    """Test ValidationResult dataclass."""

    def test_valid_result_defaults(self):
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.checked_rows == 0
        assert result.failed_rows == 0

    def test_invalid_result_with_errors(self):
        result = ValidationResult(
            valid=False,
            errors=["Column missing", "Type mismatch"],
            checked_rows=100,
            failed_rows=5,
        )
        assert result.valid is False
        assert len(result.errors) == 2
        assert "Column missing" in result.errors
        assert result.checked_rows == 100
        assert result.failed_rows == 5

    def test_result_with_warnings(self):
        result = ValidationResult(
            valid=True,
            warnings=["Deprecated column usage"],
            checked_rows=50,
        )
        assert result.valid is True
        assert len(result.warnings) == 1
        assert result.failed_rows == 0


class TestJSONSchemaValidator:
    """Test JSONSchemaValidator (stub implementation)."""

    def setup_method(self):
        self.validator = JSONSchemaValidator()

    def test_validate_schema_returns_valid(self):
        data = {"name": "test", "value": 42}
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = self.validator.validate_schema(data, schema)
        assert result.valid is True
        assert result.checked_rows == 1

    def test_validate_schema_with_empty_data(self):
        result = self.validator.validate_schema({}, {})
        assert result.valid is True

    def test_validate_schema_with_complex_schema(self):
        data = {"user_id": 123, "email": "test@example.com"}
        schema = {
            "type": "object",
            "required": ["user_id", "email"],
            "properties": {
                "user_id": {"type": "integer"},
                "email": {"type": "string", "format": "email"},
            },
        }
        result = self.validator.validate_schema(data, schema)
        assert result.valid is True


class TestDataQualityRuleValidator:
    """Test DataQualityRuleValidator (stub implementation)."""

    def setup_method(self):
        self.validator = DataQualityRuleValidator()

    def test_validate_quality_rules_returns_valid(self):
        data = [{"col1": "a"}, {"col1": "b"}]
        rules = [{"type": "not_null", "column": "col1"}]
        result = self.validator.validate_quality_rules(data, rules)
        assert result.valid is True
        assert result.checked_rows == 2
        assert result.failed_rows == 0

    def test_validate_quality_rules_empty_data(self):
        result = self.validator.validate_quality_rules([], [])
        assert result.valid is True
        assert result.checked_rows == 0

    def test_validate_quality_rules_multiple_rules(self):
        data = [{"id": 1, "name": "test"}]
        rules = [
            {"type": "not_null", "column": "id"},
            {"type": "unique", "column": "name"},
            {"type": "range", "column": "id", "min": 0, "max": 100},
        ]
        result = self.validator.validate_quality_rules(data, rules)
        assert result.valid is True
        assert result.checked_rows == 1


class TestDataContractValidator:
    """Test DataContractValidator orchestrator."""

    def setup_method(self):
        self.validator = DataContractValidator()

    def test_validate_with_default_validators(self):
        data = [{"col1": "value1"}]
        contract = type("Contract", (), {"name": "test_contract"})()
        result = self.validator.validate(data, contract)
        assert result.valid is True
        assert result.checked_rows == 1

    def test_validate_with_custom_validators(self):
        class CustomSchemaValidator:
            def validate_schema(self, data, schema):
                return ValidationResult(valid=True, checked_rows=1)

        class CustomQualityValidator:
            def validate_quality_rules(self, data, rules):
                return ValidationResult(valid=True, checked_rows=len(data))

        validator = DataContractValidator(
            schema_validator=CustomSchemaValidator(),  # type: ignore[reportArgumentType]
            quality_validator=CustomQualityValidator(),  # type: ignore[reportArgumentType]
        )
        data = [{"col1": "value1"}]
        contract = type("Contract", (), {"name": "custom_contract"})()
        result = validator.validate(data, contract)
        assert result.valid is True

    def test_validate_empty_data(self):
        contract = type("Contract", (), {"name": "empty_contract"})()
        result = self.validator.validate([], contract)
        assert result.valid is True
        assert result.checked_rows == 0

    def test_validate_multiple_records(self):
        data = [{"id": i, "value": f"item_{i}"} for i in range(10)]
        contract = type("Contract", (), {"name": "batch_contract"})()
        result = self.validator.validate(data, contract)
        assert result.valid is True
        assert result.checked_rows == 10

    def test_validator_initialization_with_custom_validators(self):
        custom_schema = JSONSchemaValidator()
        custom_quality = DataQualityRuleValidator()
        validator = DataContractValidator(
            schema_validator=custom_schema,
            quality_validator=custom_quality,
        )
        assert validator.schema_validator is custom_schema
        assert validator.quality_validator is custom_quality

    def test_validator_default_initialization(self):
        validator = DataContractValidator()
        assert isinstance(validator.schema_validator, JSONSchemaValidator)
        assert isinstance(validator.quality_validator, DataQualityRuleValidator)
