"""
Tests for Data Contracts

Verifies contract creation, validation, and JSON Schema generation.
Reference: docs/CANONICAL_ROADMAP.md - P5 Governance & Contracts
"""
import pytest
import json

from voyant.core.contracts import (
    DataContract,
    ColumnSpec,
    DataType,
    SensitivityLevel,
    ValidationResult,
    validate_schema,
    register_contract,
    get_contract,
    list_contracts,
    clear_registry,
)


class TestColumnSpec:
    """Test column specification."""

    def test_basic_column(self):
        """Should create basic column spec."""
        col = ColumnSpec(
            name="user_id",
            data_type=DataType.INTEGER,
            nullable=False,
        )
        assert col.name == "user_id"
        assert col.data_type == DataType.INTEGER
        assert col.nullable is False

    def test_pii_column(self):
        """Should mark column as PII."""
        col = ColumnSpec(
            name="email",
            data_type=DataType.STRING,
            sensitivity=SensitivityLevel.PII,
        )
        assert col.sensitivity == SensitivityLevel.PII

    def test_column_to_dict(self):
        """Should serialize to dict."""
        col = ColumnSpec(
            name="amount",
            data_type=DataType.FLOAT,
            min_value=0,
            max_value=1000000,
        )
        d = col.to_dict()
        assert d["name"] == "amount"
        assert d["data_type"] == "float"
        assert d["min_value"] == 0
        assert d["max_value"] == 1000000

    def test_column_from_dict(self):
        """Should deserialize from dict."""
        data = {
            "name": "status",
            "data_type": "string",
            "enum_values": ["active", "inactive", "pending"],
        }
        col = ColumnSpec.from_dict(data)
        assert col.name == "status"
        assert col.enum_values == ["active", "inactive", "pending"]


class TestDataContract:
    """Test data contract."""

    def test_create_contract(self):
        """Should create basic contract."""
        contract = DataContract(
            name="orders",
            version="1.0.0",
            description="Order data",
            columns=[
                ColumnSpec(name="order_id", data_type=DataType.STRING, nullable=False),
                ColumnSpec(name="amount", data_type=DataType.FLOAT),
            ],
        )
        assert contract.name == "orders"
        assert len(contract.columns) == 2

    def test_contract_to_dict(self):
        """Should serialize to dict."""
        contract = DataContract(
            name="customers",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER),
            ],
        )
        d = contract.to_dict()
        assert d["name"] == "customers"
        assert len(d["columns"]) == 1

    def test_contract_from_dict(self):
        """Should deserialize from dict."""
        data = {
            "name": "products",
            "version": "2.0.0",
            "columns": [
                {"name": "sku", "data_type": "string"},
                {"name": "price", "data_type": "float"},
            ],
        }
        contract = DataContract.from_dict(data)
        assert contract.name == "products"
        assert contract.version == "2.0.0"
        assert len(contract.columns) == 2

    def test_get_pii_columns(self):
        """Should return PII column names."""
        contract = DataContract(
            name="users",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER),
                ColumnSpec(name="email", data_type=DataType.STRING, sensitivity=SensitivityLevel.PII),
                ColumnSpec(name="ssn", data_type=DataType.STRING, sensitivity=SensitivityLevel.PII),
            ],
        )
        pii = contract.get_pii_columns()
        assert pii == ["email", "ssn"]

    def test_get_sensitive_columns(self):
        """Should return all sensitive column names."""
        contract = DataContract(
            name="accounts",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER),
                ColumnSpec(name="balance", data_type=DataType.FLOAT, sensitivity=SensitivityLevel.CONFIDENTIAL),
                ColumnSpec(name="api_key", data_type=DataType.STRING, sensitivity=SensitivityLevel.SECRET),
            ],
        )
        sensitive = contract.get_sensitive_columns()
        assert "balance" in sensitive
        assert "api_key" in sensitive
        assert "id" not in sensitive


class TestJsonSchema:
    """Test JSON Schema generation."""

    def test_basic_schema(self):
        """Should generate valid JSON Schema."""
        contract = DataContract(
            name="events",
            version="1.0.0",
            columns=[
                ColumnSpec(name="event_id", data_type=DataType.STRING, nullable=False),
                ColumnSpec(name="timestamp", data_type=DataType.TIMESTAMP),
            ],
        )
        schema = contract.to_json_schema()
        
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["title"] == "events"
        assert "event_id" in schema["properties"]
        assert "event_id" in schema["required"]

    def test_schema_with_validation_rules(self):
        """Should include validation rules in schema."""
        contract = DataContract(
            name="scores",
            version="1.0.0",
            columns=[
                ColumnSpec(
                    name="score",
                    data_type=DataType.INTEGER,
                    min_value=0,
                    max_value=100,
                ),
            ],
        )
        schema = contract.to_json_schema()
        
        assert schema["properties"]["score"]["minimum"] == 0
        assert schema["properties"]["score"]["maximum"] == 100

    def test_schema_with_enum(self):
        """Should include enum values in schema."""
        contract = DataContract(
            name="status",
            version="1.0.0",
            columns=[
                ColumnSpec(
                    name="state",
                    data_type=DataType.STRING,
                    enum_values=["draft", "published", "archived"],
                ),
            ],
        )
        schema = contract.to_json_schema()
        
        assert schema["properties"]["state"]["enum"] == ["draft", "published", "archived"]


class TestValidation:
    """Test schema validation."""

    def test_valid_schema(self):
        """Should pass valid schema."""
        contract = DataContract(
            name="orders",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER, nullable=False),
                ColumnSpec(name="amount", data_type=DataType.FLOAT),
            ],
        )
        actual_columns = [
            {"name": "id", "type": "bigint"},
            {"name": "amount", "type": "double"},
        ]
        
        result = validate_schema(contract, actual_columns)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_required_column(self):
        """Should fail on missing required column."""
        contract = DataContract(
            name="orders",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER, nullable=False),
            ],
        )
        actual_columns = []  # Missing id
        
        result = validate_schema(contract, actual_columns)
        assert result.valid is False
        assert any(e.error_type == "missing_required" for e in result.errors)

    def test_type_mismatch(self):
        """Should fail on type mismatch."""
        contract = DataContract(
            name="products",
            version="1.0.0",
            columns=[
                ColumnSpec(name="price", data_type=DataType.FLOAT),
            ],
        )
        actual_columns = [
            {"name": "price", "type": "varchar"},  # String instead of float
        ]
        
        result = validate_schema(contract, actual_columns)
        assert result.valid is False
        assert any(e.error_type == "type_mismatch" for e in result.errors)

    def test_extra_columns_warning(self):
        """Should warn about extra columns not in contract."""
        contract = DataContract(
            name="simple",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER),
            ],
        )
        actual_columns = [
            {"name": "id", "type": "int"},
            {"name": "extra_col", "type": "string"},
        ]
        
        result = validate_schema(contract, actual_columns)
        assert result.valid is True  # Extra columns are warnings, not errors
        assert any("extra_col" in w for w in result.warnings)


class TestContractRegistry:
    """Test contract registry."""

    def setup_method(self):
        """Clear registry before each test."""
        clear_registry()

    def test_register_contract(self):
        """Should register contract."""
        contract = DataContract(name="test", version="1.0.0")
        register_contract(contract)
        
        retrieved = get_contract("test")
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_get_specific_version(self):
        """Should get specific version."""
        register_contract(DataContract(name="test", version="1.0.0"))
        register_contract(DataContract(name="test", version="2.0.0"))
        
        v1 = get_contract("test", "1.0.0")
        assert v1.version == "1.0.0"
        
        v2 = get_contract("test", "2.0.0")
        assert v2.version == "2.0.0"

    def test_get_latest_version(self):
        """Should get latest version when no version specified."""
        register_contract(DataContract(name="test", version="1.0.0"))
        register_contract(DataContract(name="test", version="2.0.0"))
        
        latest = get_contract("test")
        assert latest.version == "2.0.0"

    def test_list_contracts(self):
        """Should list all contracts."""
        register_contract(DataContract(name="a", version="1.0.0"))
        register_contract(DataContract(name="b", version="1.0.0"))
        
        contracts = list_contracts()
        assert len(contracts) == 2
        names = [c["name"] for c in contracts]
        assert "a" in names
        assert "b" in names
