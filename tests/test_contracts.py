"""
Tests for Data Contracts and Schema Validation.

This module contains comprehensive tests for the data contract management system
within the Voyant platform. It verifies the functionality of defining column
specifications, creating and managing data contracts, generating JSON schemas
from these contracts, and validating data against the defined schemas.

It also tests the contract registry's ability to store, retrieve, and manage
different versions of data contracts.

Reference: docs/CANONICAL_ROADMAP.md - P5 Governance & Contracts
"""

from apps.core.lib.contracts import (
    ColumnSpec,
    DataContract,
    DataType,
    SensitivityLevel,
    clear_registry,
    get_contract,
    list_contracts,
    register_contract,
    validate_schema,
)


class TestColumnSpec:
    """
    Tests for the `ColumnSpec` dataclass, verifying its creation, attribute handling,
    and serialization/deserialization capabilities.
    """

    def test_basic_column(self):
        """
        Verifies that a basic `ColumnSpec` can be instantiated with required attributes.
        """
        col = ColumnSpec(
            name="user_id",
            data_type=DataType.INTEGER,
            nullable=False,
        )
        assert col.name == "user_id"
        assert col.data_type == DataType.INTEGER
        assert col.nullable is False

    def test_pii_column(self):
        """
        Ensures that a `ColumnSpec` can correctly be marked with PII sensitivity.
        """
        col = ColumnSpec(
            name="email",
            data_type=DataType.STRING,
            sensitivity=SensitivityLevel.PII,
        )
        assert col.sensitivity == SensitivityLevel.PII

    def test_column_to_dict(self):
        """
        Tests the `ColumnSpec.to_dict()` method for accurate serialization to a dictionary.
        """
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
        """
        Tests the `ColumnSpec.from_dict()` static method for accurate deserialization from a dictionary.
        """
        data = {
            "name": "status",
            "data_type": "string",
            "enum_values": ["active", "inactive", "pending"],
        }
        col = ColumnSpec.from_dict(data)
        assert col.name == "status"
        assert col.enum_values == ["active", "inactive", "pending"]


class TestDataContract:
    """
    Tests for the `DataContract` dataclass, verifying contract creation,
    attribute handling, and methods for retrieving sensitive columns.
    """

    def test_create_contract(self):
        """
        Verifies that a `DataContract` can be instantiated with its name, version,
        description, and a list of `ColumnSpec` objects.
        """
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
        """
        Tests the `DataContract.to_dict()` method for accurate serialization to a dictionary.
        """
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
        """
        Tests the `DataContract.from_dict()` static method for accurate deserialization from a dictionary.
        """
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
        """
        Verifies that `get_pii_columns()` correctly identifies and returns
        the names of columns marked with PII sensitivity.
        """
        contract = DataContract(
            name="users",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER),
                ColumnSpec(
                    name="email",
                    data_type=DataType.STRING,
                    sensitivity=SensitivityLevel.PII,
                ),
                ColumnSpec(
                    name="ssn",
                    data_type=DataType.STRING,
                    sensitivity=SensitivityLevel.PII,
                ),
            ],
        )
        pii = contract.get_pii_columns()
        assert set(pii) == {"email", "ssn"}

    def test_get_sensitive_columns(self):
        """
        Verifies that `get_sensitive_columns()` correctly identifies and returns
        the names of all columns marked with any level of sensitivity (excluding UNSPECIFIED).
        """
        contract = DataContract(
            name="accounts",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER),
                ColumnSpec(
                    name="balance",
                    data_type=DataType.FLOAT,
                    sensitivity=SensitivityLevel.CONFIDENTIAL,
                ),
                ColumnSpec(
                    name="api_key",
                    data_type=DataType.STRING,
                    sensitivity=SensitivityLevel.SECRET,
                ),
            ],
        )
        sensitive = contract.get_sensitive_columns()
        assert "balance" in sensitive
        assert "api_key" in sensitive
        assert "id" not in sensitive


class TestJsonSchema:
    """
    Tests for JSON Schema generation from `DataContract` objects.

    These tests ensure that the generated JSON schemas are valid and correctly
    incorporate validation rules, enum values, and data types from the contract.
    """

    def test_basic_schema(self):
        """
        Verifies that `to_json_schema()` generates a valid basic JSON Schema
        including schema version, title, properties, and required fields.
        """
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
        """
        Ensures that `min_value` and `max_value` from `ColumnSpec` are correctly
        translated into `minimum` and `maximum` validation rules in the JSON Schema.
        """
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
        """
        Verifies that `enum_values` from `ColumnSpec` are correctly
        included as an `enum` array in the generated JSON Schema.
        """
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

        assert schema["properties"]["state"]["enum"] == [
            "draft",
            "published",
            "archived",
        ]


class TestValidation:
    """
    Tests for the `validate_schema` function, ensuring it correctly
    validates actual column structures against a defined `DataContract`.
    """

    def test_valid_schema(self):
        """
        Verifies that `validate_schema` returns a valid result with no errors
        when the actual columns match the contract.
        """
        contract = DataContract(
            name="orders",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER, nullable=False),
                ColumnSpec(name="amount", data_type=DataType.FLOAT),
            ],
        )
        actual_columns = [
            {"name": "id", "type": "bigint"},  # Example actual type mapping
            {"name": "amount", "type": "double"},
        ]

        result = validate_schema(contract, actual_columns)
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_required_column(self):
        """
        Ensures that `validate_schema` flags an error when a required column
        defined in the contract is missing from the actual columns.
        """
        contract = DataContract(
            name="orders",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER, nullable=False),
            ],
        )
        actual_columns = []  # 'id' is missing.

        result = validate_schema(contract, actual_columns)
        assert result.valid is False
        assert any(e.error_type == "missing_required" for e in result.errors)

    def test_type_mismatch(self):
        """
        Ensures that `validate_schema` flags an error when a column's actual data type
        does not match the type specified in the contract.
        """
        contract = DataContract(
            name="products",
            version="1.0.0",
            columns=[
                ColumnSpec(name="price", data_type=DataType.FLOAT),
            ],
        )
        actual_columns = [
            {
                "name": "price",
                "type": "varchar",
            },  # Actual type is string, contract expects float.
        ]

        result = validate_schema(contract, actual_columns)
        assert result.valid is False
        assert any(e.error_type == "type_mismatch" for e in result.errors)

    def test_extra_columns_warning(self):
        """
        Verifies that `validate_schema` issues a warning (but still considers the schema valid)
        when extra columns are present in the actual data that are not defined in the contract.
        """
        contract = DataContract(
            name="simple",
            version="1.0.0",
            columns=[
                ColumnSpec(name="id", data_type=DataType.INTEGER),
            ],
        )
        actual_columns = [
            {"name": "id", "type": "int"},
            {
                "name": "extra_col",
                "type": "string",
            },  # This column is not in the contract.
        ]

        result = validate_schema(contract, actual_columns)
        assert (
            result.valid is True
        )  # Extra columns should typically result in warnings, not hard errors.
        assert any("extra_col" in w for w in result.warnings)


class TestContractRegistry:
    """
    Tests for the global `DataContract` registry, verifying its ability to
    register, retrieve (by specific version or latest), and list contracts.
    """

    def setup_method(self):
        """
        Clears the global contract registry before each test to ensure test isolation.
        """
        clear_registry()

    def test_register_contract(self):
        """
        Verifies that a `DataContract` can be successfully registered and
        then retrieved from the registry.
        """
        contract = DataContract(name="test", version="1.0.0")
        register_contract(contract)

        retrieved = get_contract("test")
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_get_specific_version(self):
        """
        Ensures that a specific version of a contract can be retrieved
        when multiple versions of the same contract name exist.
        """
        register_contract(DataContract(name="test", version="1.0.0"))
        register_contract(DataContract(name="test", version="2.0.0"))

        v1 = get_contract("test", "1.0.0")
        assert v1.version == "1.0.0"

        v2 = get_contract("test", "2.0.0")
        assert v2.version == "2.0.0"

    def test_get_latest_version(self):
        """
        Verifies that `get_contract` retrieves the latest version of a contract
        when no specific version is requested.
        """
        register_contract(DataContract(name="test", version="1.0.0"))
        register_contract(DataContract(name="test", version="2.0.0"))

        latest = get_contract("test")
        assert latest.version == "2.0.0"

    def test_list_contracts(self):
        """
        Tests `list_contracts()` to ensure it returns a list of all currently
        registered contracts, including their names.
        """
        register_contract(DataContract(name="a", version="1.0.0"))
        register_contract(DataContract(name="b", version="1.0.0"))

        contracts = list_contracts()
        assert len(contracts) == 2
        names = {c["name"] for c in contracts}
        assert "a" in names
        assert "b" in names
