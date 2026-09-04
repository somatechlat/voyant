"""Tests for schema evolution module."""



from apps.governance.lib.schema_evolution import (
    ChangeType,
    ColumnSchema,
    CompatibilityLevel,
    SchemaChange,
    SchemaEvolutionRegistry,
    SchemaVersion,
    TableSchema,
    compare_schemas,
    reset_registry,
)


class TestChangeType:
    """Test ChangeType enum."""

    def test_column_added(self):
        assert ChangeType.COLUMN_ADDED.value == "column_added"

    def test_column_removed(self):
        assert ChangeType.COLUMN_REMOVED.value == "column_removed"

    def test_type_changed(self):
        assert ChangeType.TYPE_CHANGED.value == "type_changed"

    def test_nullable_changed(self):
        assert ChangeType.NULLABLE_CHANGED.value == "nullable_changed"

    def test_default_changed(self):
        assert ChangeType.DEFAULT_CHANGED.value == "default_changed"


class TestCompatibilityLevel:
    """Test CompatibilityLevel enum."""

    def test_full(self):
        assert CompatibilityLevel.FULL.value == "full"

    def test_backward(self):
        assert CompatibilityLevel.BACKWARD.value == "backward"

    def test_forward(self):
        assert CompatibilityLevel.FORWARD.value == "forward"

    def test_none(self):
        assert CompatibilityLevel.NONE.value == "none"


class TestSchemaChange:
    """Test SchemaChange dataclass."""

    def test_creation(self):
        change = SchemaChange(
            change_type=ChangeType.COLUMN_ADDED,
            column_name="new_col",
            new_value="VARCHAR",
            is_breaking=False,
        )
        assert change.change_type == ChangeType.COLUMN_ADDED
        assert change.column_name == "new_col"
        assert change.new_value == "VARCHAR"
        assert change.is_breaking is False

    def test_to_dict(self):
        change = SchemaChange(
            change_type=ChangeType.TYPE_CHANGED,
            column_name="age",
            old_value="INT",
            new_value="BIGINT",
            is_breaking=False,
        )
        d = change.to_dict()
        assert d["change_type"] == "type_changed"
        assert d["column_name"] == "age"
        assert d["old_value"] == "INT"
        assert d["new_value"] == "BIGINT"
        assert d["is_breaking"] is False

    def test_from_dict(self):
        data = {
            "change_type": "column_removed",
            "column_name": "old_col",
            "old_value": "VARCHAR",
            "new_value": None,
            "is_breaking": True,
        }
        change = SchemaChange.from_dict(data)
        assert change.change_type == ChangeType.COLUMN_REMOVED
        assert change.column_name == "old_col"
        assert change.old_value == "VARCHAR"
        assert change.is_breaking is True

    def test_roundtrip(self):
        original = SchemaChange(
            change_type=ChangeType.NULLABLE_CHANGED,
            column_name="status",
            old_value=True,
            new_value=False,
            is_breaking=True,
        )
        d = original.to_dict()
        restored = SchemaChange.from_dict(d)
        assert restored.change_type == original.change_type
        assert restored.column_name == original.column_name
        assert restored.is_breaking == original.is_breaking


class TestColumnSchema:
    """Test ColumnSchema dataclass."""

    def test_creation(self):
        col = ColumnSchema(name="id", data_type="INTEGER", nullable=False)
        assert col.name == "id"
        assert col.data_type == "INTEGER"
        assert col.nullable is False
        assert col.default is None
        assert col.constraints == []

    def test_to_dict(self):
        col = ColumnSchema(
            name="email",
            data_type="VARCHAR",
            nullable=True,
            default="unknown@example.com",
            constraints=["UNIQUE"],
        )
        d = col.to_dict()
        assert d["name"] == "email"
        assert d["data_type"] == "VARCHAR"
        assert d["nullable"] is True
        assert d["default"] == "unknown@example.com"
        assert d["constraints"] == ["UNIQUE"]

    def test_from_dict(self):
        data = {
            "name": "amount",
            "data_type": "DECIMAL",
            "nullable": True,
            "default": "0.00",
            "constraints": ["NOT NULL"],
        }
        col = ColumnSchema.from_dict(data)
        assert col.name == "amount"
        assert col.data_type == "DECIMAL"
        assert col.constraints == ["NOT NULL"]


class TestTableSchema:
    """Test TableSchema dataclass."""

    def test_creation(self):
        schema = TableSchema(
            name="users",
            columns=[
                ColumnSchema(name="id", data_type="INTEGER", nullable=False),
                ColumnSchema(name="name", data_type="VARCHAR"),
            ],
            primary_key=["id"],
        )
        assert schema.name == "users"
        assert len(schema.columns) == 2
        assert schema.primary_key == ["id"]

    def test_get_column(self):
        schema = TableSchema(
            name="orders",
            columns=[
                ColumnSchema(name="order_id", data_type="INTEGER"),
                ColumnSchema(name="total", data_type="DECIMAL"),
            ],
        )
        col = schema.get_column("total")
        assert col is not None
        assert col.data_type == "DECIMAL"

    def test_get_column_not_found(self):
        schema = TableSchema(name="orders", columns=[])
        col = schema.get_column("nonexistent")
        assert col is None

    def test_column_names(self):
        schema = TableSchema(
            name="products",
            columns=[
                ColumnSchema(name="id", data_type="INTEGER"),
                ColumnSchema(name="name", data_type="VARCHAR"),
                ColumnSchema(name="price", data_type="DECIMAL"),
            ],
        )
        assert schema.column_names == {"id", "name", "price"}

    def test_to_dict(self):
        schema = TableSchema(
            name="test",
            columns=[ColumnSchema(name="col1", data_type="VARCHAR")],
        )
        d = schema.to_dict()
        assert d["name"] == "test"
        assert len(d["columns"]) == 1
        assert d["primary_key"] is None

    def test_from_dict(self):
        data = {
            "name": "accounts",
            "columns": [
                {"name": "id", "data_type": "INTEGER", "nullable": False},
                {"name": "balance", "data_type": "DECIMAL", "nullable": True},
            ],
            "primary_key": ["id"],
        }
        schema = TableSchema.from_dict(data)
        assert schema.name == "accounts"
        assert len(schema.columns) == 2
        assert schema.primary_key == ["id"]


class TestSchemaVersion:
    """Test SchemaVersion dataclass."""

    def test_creation(self):
        schema = TableSchema(name="test", columns=[])
        version = SchemaVersion(version="1.0.0", schema=schema)
        assert version.version == "1.0.0"
        assert version.created_at > 0
        assert version.created_by == ""
        assert version.description == ""
        assert version.changes_from_previous == []

    def test_to_dict(self):
        schema = TableSchema(
            name="test",
            columns=[ColumnSchema(name="col1", data_type="VARCHAR")],
        )
        version = SchemaVersion(
            version="2.0.0",
            schema=schema,
            created_by="test_user",
            description="Added col1",
        )
        d = version.to_dict()
        assert d["version"] == "2.0.0"
        assert d["created_by"] == "test_user"
        assert d["description"] == "Added col1"
        assert "schema" in d
        assert "changes" in d


class TestCompareSchemas:
    """Test compare_schemas function."""

    def test_identical_schemas(self):
        schema1 = TableSchema(
            name="test",
            columns=[ColumnSchema(name="id", data_type="INTEGER")],
        )
        schema2 = TableSchema(
            name="test",
            columns=[ColumnSchema(name="id", data_type="INTEGER")],
        )
        changes = compare_schemas(schema1, schema2)
        assert len(changes) == 0

    def test_column_added(self):
        old = TableSchema(name="test", columns=[])
        new = TableSchema(
            name="test",
            columns=[ColumnSchema(name="new_col", data_type="VARCHAR")],
        )
        changes = compare_schemas(old, new)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.COLUMN_ADDED
        assert changes[0].column_name == "new_col"
        assert changes[0].is_breaking is False

    def test_column_added_not_nullable_no_default_is_breaking(self):
        old = TableSchema(name="test", columns=[])
        new = TableSchema(
            name="test",
            columns=[ColumnSchema(name="required_col", data_type="VARCHAR", nullable=False)],
        )
        changes = compare_schemas(old, new)
        assert len(changes) == 1
        assert changes[0].is_breaking is True

    def test_column_removed(self):
        old = TableSchema(
            name="test",
            columns=[ColumnSchema(name="old_col", data_type="VARCHAR")],
        )
        new = TableSchema(name="test", columns=[])
        changes = compare_schemas(old, new)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.COLUMN_REMOVED
        assert changes[0].is_breaking is True

    def test_type_changed(self):
        old = TableSchema(
            name="test",
            columns=[ColumnSchema(name="value", data_type="INTEGER")],
        )
        new = TableSchema(
            name="test",
            columns=[ColumnSchema(name="value", data_type="VARCHAR")],
        )
        changes = compare_schemas(old, new)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.TYPE_CHANGED
        assert changes[0].old_value == "INTEGER"
        assert changes[0].new_value == "VARCHAR"

    def test_type_widening_is_not_breaking(self):
        old = TableSchema(
            name="test",
            columns=[ColumnSchema(name="value", data_type="INTEGER")],
        )
        new = TableSchema(
            name="test",
            columns=[ColumnSchema(name="value", data_type="BIGINT")],
        )
        changes = compare_schemas(old, new)
        assert len(changes) == 1
        assert changes[0].is_breaking is False

    def test_nullable_changed(self):
        old = TableSchema(
            name="test",
            columns=[ColumnSchema(name="status", data_type="VARCHAR", nullable=True)],
        )
        new = TableSchema(
            name="test",
            columns=[ColumnSchema(name="status", data_type="VARCHAR", nullable=False)],
        )
        changes = compare_schemas(old, new)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.NULLABLE_CHANGED
        assert changes[0].is_breaking is True

    def test_default_changed(self):
        old = TableSchema(
            name="test",
            columns=[ColumnSchema(name="status", data_type="VARCHAR", default="active")],
        )
        new = TableSchema(
            name="test",
            columns=[ColumnSchema(name="status", data_type="VARCHAR", default="inactive")],
        )
        changes = compare_schemas(old, new)
        assert len(changes) == 1
        assert changes[0].change_type == ChangeType.DEFAULT_CHANGED
        assert changes[0].is_breaking is False

    def test_multiple_changes(self):
        old = TableSchema(
            name="test",
            columns=[
                ColumnSchema(name="id", data_type="INTEGER"),
                ColumnSchema(name="name", data_type="VARCHAR"),
            ],
        )
        new = TableSchema(
            name="test",
            columns=[
                ColumnSchema(name="id", data_type="INTEGER"),
                ColumnSchema(name="full_name", data_type="VARCHAR"),
                ColumnSchema(name="email", data_type="VARCHAR"),
            ],
        )
        changes = compare_schemas(old, new)
        change_types = {c.change_type for c in changes}
        assert ChangeType.COLUMN_REMOVED in change_types
        assert ChangeType.COLUMN_ADDED in change_types


class TestSchemaEvolutionRegistry:
    """Test SchemaEvolutionRegistry with DuckDB backend."""

    def setup_method(self):
        reset_registry()
        self.registry = SchemaEvolutionRegistry()
        self.registry.clear()

    def teardown_method(self):
        self.registry.close()
        reset_registry()

    def test_register_first_version(self):
        schema = TableSchema(
            name="users",
            columns=[
                ColumnSchema(name="id", data_type="INTEGER", nullable=False),
                ColumnSchema(name="name", data_type="VARCHAR"),
            ],
        )
        version = self.registry.register("users", schema, "1.0.0", "Initial schema")
        assert version.version == "1.0.0"
        assert version.description == "Initial schema"
        assert len(version.changes_from_previous) == 0

    def test_register_second_version(self):
        schema_v1 = TableSchema(
            name="users",
            columns=[ColumnSchema(name="id", data_type="INTEGER")],
        )
        self.registry.register("users", schema_v1, "1.0.0")

        schema_v2 = TableSchema(
            name="users",
            columns=[
                ColumnSchema(name="id", data_type="INTEGER"),
                ColumnSchema(name="email", data_type="VARCHAR"),
            ],
        )
        version = self.registry.register("users", schema_v2, "2.0.0", "Added email")
        assert version.version == "2.0.0"
        assert len(version.changes_from_previous) == 1
        assert version.changes_from_previous[0].change_type == ChangeType.COLUMN_ADDED

    def test_get_version(self):
        schema = TableSchema(
            name="orders",
            columns=[ColumnSchema(name="order_id", data_type="INTEGER")],
        )
        self.registry.register("orders", schema, "1.0.0")
        retrieved = self.registry.get_version("orders", "1.0.0")
        assert retrieved is not None
        assert retrieved.version == "1.0.0"
        assert retrieved.schema.name == "orders"

    def test_get_latest_version(self):
        schema_v1 = TableSchema(
            name="products",
            columns=[ColumnSchema(name="id", data_type="INTEGER")],
        )
        self.registry.register("products", schema_v1, "1.0.0")

        schema_v2 = TableSchema(
            name="products",
            columns=[
                ColumnSchema(name="id", data_type="INTEGER"),
                ColumnSchema(name="price", data_type="DECIMAL"),
            ],
        )
        self.registry.register("products", schema_v2, "2.0.0")

        latest = self.registry.get_version("products")
        assert latest is not None
        assert latest.version == "2.0.0"

    def test_get_nonexistent_version(self):
        result = self.registry.get_version("nonexistent", "1.0.0")
        assert result is None

    def test_get_history(self):
        schema_v1 = TableSchema(
            name="events",
            columns=[ColumnSchema(name="id", data_type="INTEGER")],
        )
        self.registry.register("events", schema_v1, "1.0.0", "Initial")

        schema_v2 = TableSchema(
            name="events",
            columns=[
                ColumnSchema(name="id", data_type="INTEGER"),
                ColumnSchema(name="timestamp", data_type="TIMESTAMP"),
            ],
        )
        self.registry.register("events", schema_v2, "2.0.0", "Added timestamp")

        history = self.registry.get_history("events")
        assert len(history) == 2
        assert history[0]["version"] == "1.0.0"
        assert history[1]["version"] == "2.0.0"

    def test_list_tables(self):
        schema = TableSchema(
            name="test",
            columns=[ColumnSchema(name="id", data_type="INTEGER")],
        )
        self.registry.register("table_a", schema, "1.0.0")
        self.registry.register("table_b", schema, "1.0.0")

        tables = self.registry.list_tables()
        assert "table_a" in tables
        assert "table_b" in tables

    def test_register_duplicate_version(self):
        schema = TableSchema(
            name="test",
            columns=[ColumnSchema(name="id", data_type="INTEGER")],
        )
        v1 = self.registry.register("test", schema, "1.0.0")
        v2 = self.registry.register("test", schema, "1.0.0")
        assert v1.version == v2.version

    def test_clear(self):
        schema = TableSchema(
            name="test",
            columns=[ColumnSchema(name="id", data_type="INTEGER")],
        )
        self.registry.register("test", schema, "1.0.0")
        self.registry.clear()
        assert self.registry.get_version("test", "1.0.0") is None
