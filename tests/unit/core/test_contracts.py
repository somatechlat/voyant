"""
Unit tests for apps.core.lib.contracts — Data contracts and schema validation.

Real in-memory registry. No mocks, no external services.
"""

import json
import tempfile
from pathlib import Path

import pytest

from apps.core.lib.contracts import (
    ColumnSpec,
    DataContract,
    DataType,
    SensitivityLevel,
    ValidationError,
    ValidationResult,
    clear_registry,
    get_contract,
    list_contracts,
    load_contract,
    register_contract,
    save_contract,
    save_json_schema,
    validate_schema,
)


@pytest.fixture(autouse=True)
def clean_registry():
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def sample_column():
    return ColumnSpec(
        name="email",
        data_type=DataType.STRING,
        nullable=False,
        description="User email address",
        sensitivity=SensitivityLevel.PII,
        min_length=5,
        max_length=255,
        pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$",
    )


@pytest.fixture
def sample_contract(sample_column):
    return DataContract(
        name="users",
        version="1.0.0",
        description="User data contract",
        owner="platform-team",
        columns=[
            sample_column,
            ColumnSpec(name="age", data_type=DataType.INTEGER, nullable=True,
                       min_value=0, max_value=200),
            ColumnSpec(name="active", data_type=DataType.BOOLEAN, nullable=False),
        ],
        tags=["users", "auth"],
        sla_freshness_hours=24,
        sla_completeness_pct=99.5,
    )


# =============================================================================
# ColumnSpec Tests
# =============================================================================


class TestColumnSpec:
    def test_creation(self, sample_column):
        assert sample_column.name == "email"
        assert sample_column.data_type == DataType.STRING
        assert sample_column.nullable is False
        assert sample_column.sensitivity == SensitivityLevel.PII

    def test_to_dict_minimal(self):
        col = ColumnSpec(name="id", data_type=DataType.INTEGER)
        d = col.to_dict()
        assert d["name"] == "id"
        assert d["data_type"] == "integer"
        assert d["nullable"] is True
        assert "min_value" not in d
        assert "max_value" not in d

    def test_to_dict_with_all_fields(self, sample_column):
        d = sample_column.to_dict()
        assert d["name"] == "email"
        assert d["min_length"] == 5
        assert d["max_length"] == 255
        assert d["pattern"] == r"^[\w\.-]+@[\w\.-]+\.\w+$"
        assert d["sensitivity"] == "pii"

    def test_to_dict_unique_field(self):
        col = ColumnSpec(name="id", data_type=DataType.STRING, unique=True)
        d = col.to_dict()
        assert d["unique"] is True

    def test_to_dict_max_null_rate(self):
        col = ColumnSpec(name="x", data_type=DataType.STRING, max_null_rate=0.1)
        d = col.to_dict()
        assert d["max_null_rate"] == 0.1

    def test_from_dict_roundtrip(self, sample_column):
        d = sample_column.to_dict()
        restored = ColumnSpec.from_dict(d)
        assert restored.name == sample_column.name
        assert restored.data_type == sample_column.data_type
        assert restored.nullable == sample_column.nullable
        assert restored.sensitivity == sample_column.sensitivity
        assert restored.min_length == sample_column.min_length
        assert restored.max_length == sample_column.max_length

    def test_from_dict_defaults(self):
        col = ColumnSpec.from_dict({"name": "x", "data_type": "any"})
        assert col.nullable is True
        assert col.sensitivity == SensitivityLevel.INTERNAL
        assert col.max_null_rate == 1.0
        assert col.unique is False


# =============================================================================
# DataContract Tests
# =============================================================================


class TestDataContract:
    def test_creation(self, sample_contract):
        assert sample_contract.name == "users"
        assert sample_contract.version == "1.0.0"
        assert len(sample_contract.columns) == 3
        assert sample_contract.created_at != ""
        assert sample_contract.updated_at != ""

    def test_to_dict(self, sample_contract):
        d = sample_contract.to_dict()
        assert d["name"] == "users"
        assert d["version"] == "1.0.0"
        assert len(d["columns"]) == 3
        assert d["tags"] == ["users", "auth"]

    def test_from_dict_roundtrip(self, sample_contract):
        d = sample_contract.to_dict()
        restored = DataContract.from_dict(d)
        assert restored.name == sample_contract.name
        assert restored.version == sample_contract.version
        assert len(restored.columns) == len(sample_contract.columns)

    def test_to_json_schema(self, sample_contract):
        schema = sample_contract.to_json_schema()
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["title"] == "users"
        assert schema["type"] == "object"
        assert "email" in schema["properties"]
        assert "active" in schema["properties"]
        # Non-nullable columns should be required
        assert "email" in schema["required"]
        assert "active" in schema["required"]
        # Nullable columns should not be required
        assert "age" not in schema["required"]

    def test_json_schema_type_mapping(self):
        contract = DataContract(
            name="types", version="1.0.0",
            columns=[
                ColumnSpec(name="s", data_type=DataType.STRING),
                ColumnSpec(name="i", data_type=DataType.INTEGER),
                ColumnSpec(name="f", data_type=DataType.FLOAT),
                ColumnSpec(name="b", data_type=DataType.BOOLEAN),
                ColumnSpec(name="d", data_type=DataType.DATE),
                ColumnSpec(name="dt", data_type=DataType.DATETIME),
                ColumnSpec(name="ts", data_type=DataType.TIMESTAMP),
                ColumnSpec(name="a", data_type=DataType.ARRAY),
                ColumnSpec(name="o", data_type=DataType.OBJECT),
            ],
        )
        schema = contract.to_json_schema()
        assert schema["properties"]["s"]["type"] == "string"
        assert schema["properties"]["i"]["type"] == "integer"
        assert schema["properties"]["f"]["type"] == "number"
        assert schema["properties"]["b"]["type"] == "boolean"
        assert schema["properties"]["d"]["format"] == "date"
        assert schema["properties"]["dt"]["format"] == "date-time"
        assert schema["properties"]["a"]["type"] == "array"
        assert schema["properties"]["o"]["type"] == "object"

    def test_json_schema_validation_rules(self):
        contract = DataContract(
            name="rules", version="1.0.0",
            columns=[
                ColumnSpec(name="x", data_type=DataType.INTEGER,
                           min_value=0, max_value=100),
                ColumnSpec(name="y", data_type=DataType.STRING,
                           min_length=1, max_length=50,
                           pattern=r"^[a-z]+$",
                           enum_values=["a", "b", "c"]),
            ],
        )
        schema = contract.to_json_schema()
        assert schema["properties"]["x"]["minimum"] == 0
        assert schema["properties"]["x"]["maximum"] == 100
        assert schema["properties"]["y"]["minLength"] == 1
        assert schema["properties"]["y"]["maxLength"] == 50
        assert schema["properties"]["y"]["pattern"] == r"^[a-z]+$"
        assert schema["properties"]["y"]["enum"] == ["a", "b", "c"]

    def test_get_pii_columns(self, sample_contract):
        pii = sample_contract.get_pii_columns()
        assert pii == ["email"]

    def test_get_sensitive_columns(self, sample_contract):
        # email is PII, which is in the sensitive set
        sensitive = sample_contract.get_sensitive_columns()
        assert "email" in sensitive

    def test_get_sensitive_columns_with_confidential(self):
        contract = DataContract(
            name="test", version="1.0.0",
            columns=[
                ColumnSpec(name="pub", data_type=DataType.STRING,
                           sensitivity=SensitivityLevel.PUBLIC),
                ColumnSpec(name="conf", data_type=DataType.STRING,
                           sensitivity=SensitivityLevel.CONFIDENTIAL),
                ColumnSpec(name="sec", data_type=DataType.STRING,
                           sensitivity=SensitivityLevel.SECRET),
            ],
        )
        sensitive = contract.get_sensitive_columns()
        assert "pub" not in sensitive
        assert "conf" in sensitive
        assert "sec" in sensitive


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidateSchema:
    def test_valid_schema(self, sample_contract):
        columns = [
            {"name": "email", "type": "varchar"},
            {"name": "age", "type": "int"},
            {"name": "active", "type": "boolean"},
        ]
        result = validate_schema(sample_contract, columns)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_required_column(self, sample_contract):
        columns = [
            {"name": "age", "type": "int"},
        ]
        result = validate_schema(sample_contract, columns)
        assert result.valid is False
        assert any(e.error_type == "missing_required" for e in result.errors)

    def test_missing_optional_column_warns(self, sample_contract):
        columns = [
            {"name": "email", "type": "varchar"},
            {"name": "active", "type": "boolean"},
        ]
        result = validate_schema(sample_contract, columns)
        assert result.valid is True
        assert any("age" in w for w in result.warnings)

    def test_extra_column_warns(self, sample_contract):
        columns = [
            {"name": "email", "type": "varchar"},
            {"name": "age", "type": "int"},
            {"name": "active", "type": "boolean"},
            {"name": "extra", "type": "string"},
        ]
        result = validate_schema(sample_contract, columns)
        assert result.valid is True
        assert any("extra" in w for w in result.warnings)

    def test_type_mismatch(self, sample_contract):
        columns = [
            {"name": "email", "type": "integer"},  # Should be string
            {"name": "age", "type": "int"},
            {"name": "active", "type": "boolean"},
        ]
        result = validate_schema(sample_contract, columns)
        assert result.valid is False
        assert any(e.error_type == "type_mismatch" for e in result.errors)

    def test_type_compatibility_varchar(self, sample_contract):
        columns = [
            {"name": "email", "type": "varchar"},
            {"name": "age", "type": "bigint"},
            {"name": "active", "type": "bool"},
        ]
        result = validate_schema(sample_contract, columns)
        assert result.valid is True

    def test_any_type_accepts_all(self):
        contract = DataContract(
            name="flex", version="1.0.0",
            columns=[ColumnSpec(name="data", data_type=DataType.ANY)],
        )
        result = validate_schema(contract, [{"name": "data", "type": "whatever"}])
        assert result.valid is True

    def test_validation_result_to_dict(self, sample_contract):
        columns = [
            {"name": "email", "type": "integer"},
            {"name": "active", "type": "boolean"},
        ]
        result = validate_schema(sample_contract, columns)
        d = result.to_dict()
        assert "valid" in d
        assert "error_count" in d
        assert "errors" in d
        assert "warnings" in d
        assert "stats" in d


# =============================================================================
# Registry Tests
# =============================================================================


class TestContractRegistry:
    def test_register_and_get(self, sample_contract):
        register_contract(sample_contract)
        found = get_contract("users", "1.0.0")
        assert found is not None
        assert found.name == "users"

    def test_get_latest_version(self):
        c1 = DataContract(name="test", version="1.0.0")
        c2 = DataContract(name="test", version="2.0.0")
        register_contract(c1)
        register_contract(c2)
        latest = get_contract("test")
        assert latest is not None
        assert latest.version == "2.0.0"

    def test_get_nonexistent(self):
        assert get_contract("nonexistent") is None

    def test_get_specific_version(self):
        c1 = DataContract(name="test", version="1.0.0")
        c2 = DataContract(name="test", version="2.0.0")
        register_contract(c1)
        register_contract(c2)
        found = get_contract("test", "1.0.0")
        assert found is not None
        assert found.version == "1.0.0"

    def test_list_contracts(self, sample_contract):
        register_contract(sample_contract)
        register_contract(DataContract(name="other", version="1.0.0"))
        contracts = list_contracts()
        assert len(contracts) == 2
        names = [c["name"] for c in contracts]
        assert "users" in names
        assert "other" in names

    def test_list_contracts_empty(self):
        assert list_contracts() == []


# =============================================================================
# I/O Tests
# =============================================================================


class TestContractIO:
    def test_save_and_load_json(self, sample_contract, tmp_path):
        path = tmp_path / "contract.json"
        save_contract(sample_contract, path)
        loaded = load_contract(path)
        assert loaded.name == sample_contract.name
        assert loaded.version == sample_contract.version
        assert len(loaded.columns) == len(sample_contract.columns)

    def test_save_json_schema(self, sample_contract, tmp_path):
        path = tmp_path / "schema.json"
        save_json_schema(sample_contract, path)
        with open(path) as f:
            schema = json.load(f)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["title"] == "users"

    def test_load_contract_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_contract(tmp_path / "nonexistent.json")
