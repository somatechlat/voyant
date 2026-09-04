"""
Unit tests for apps.core.lib.event_schema — In-memory event schema registry.

Real in-memory registry. No mocks, no external services.
"""

import pytest

from apps.core.lib.event_schema import (
    EventSchema,
    FieldSpec,
    FieldType,
    ValidationResult,
    _version_gt,
    clear_registry,
    get_schema,
    list_schemas,
    register_schema,
    validate_event,
)


@pytest.fixture(autouse=True)
def clean_registry():
    clear_registry()
    yield
    clear_registry()


@pytest.fixture
def sample_schema():
    return EventSchema(
        name="test.event",
        version="1.0.0",
        description="Test event",
        fields=[
            FieldSpec("id", FieldType.STRING, description="Event ID"),
            FieldSpec("count", FieldType.INTEGER, required=True),
            FieldSpec("score", FieldType.FLOAT, required=False),
            FieldSpec("active", FieldType.BOOLEAN, required=False),
            FieldSpec("tags", FieldType.ARRAY, required=False),
            FieldSpec("meta", FieldType.OBJECT, required=False),
        ],
    )


# =============================================================================
# FieldSpec Tests
# =============================================================================


class TestFieldSpec:
    def test_creation(self):
        f = FieldSpec("name", FieldType.STRING, required=True, description="A name")
        assert f.name == "name"
        assert f.field_type == FieldType.STRING
        assert f.required is True
        assert f.description == "A name"

    def test_to_json_schema_string(self):
        f = FieldSpec("x", FieldType.STRING, description="test")
        schema = f.to_json_schema()
        assert schema["type"] == "string"
        assert schema["description"] == "test"

    def test_to_json_schema_integer(self):
        f = FieldSpec("x", FieldType.INTEGER)
        schema = f.to_json_schema()
        assert schema["type"] == "integer"

    def test_to_json_schema_float(self):
        f = FieldSpec("x", FieldType.FLOAT)
        schema = f.to_json_schema()
        assert schema["type"] == "number"

    def test_to_json_schema_boolean(self):
        f = FieldSpec("x", FieldType.BOOLEAN)
        schema = f.to_json_schema()
        assert schema["type"] == "boolean"

    def test_to_json_schema_datetime(self):
        f = FieldSpec("x", FieldType.DATETIME)
        schema = f.to_json_schema()
        assert schema["type"] == "string"
        assert schema["format"] == "date-time"

    def test_to_json_schema_array(self):
        f = FieldSpec("x", FieldType.ARRAY)
        schema = f.to_json_schema()
        assert schema["type"] == "array"

    def test_to_json_schema_object(self):
        f = FieldSpec("x", FieldType.OBJECT)
        schema = f.to_json_schema()
        assert schema["type"] == "object"

    def test_to_json_schema_enum(self):
        f = FieldSpec("x", FieldType.ENUM, enum_values=["a", "b", "c"])
        schema = f.to_json_schema()
        assert schema["enum"] == ["a", "b", "c"]

    def test_to_json_schema_with_default(self):
        f = FieldSpec("x", FieldType.STRING, default="hello")
        schema = f.to_json_schema()
        assert schema["default"] == "hello"

    def test_to_json_schema_enum_without_values(self):
        f = FieldSpec("x", FieldType.ENUM)
        schema = f.to_json_schema()
        assert "enum" not in schema


# =============================================================================
# EventSchema Tests
# =============================================================================


class TestEventSchema:
    def test_creation(self, sample_schema):
        assert sample_schema.name == "test.event"
        assert sample_schema.version == "1.0.0"
        assert len(sample_schema.fields) == 6

    def test_default_created_at(self):
        schema = EventSchema(name="x", version="1.0.0", fields=[])
        assert schema.created_at == "1970-01-01T00:00:00Z"

    def test_to_json_schema(self, sample_schema):
        js = sample_schema.to_json_schema()
        assert js["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert js["$id"] == "urn:voyant:event:test.event:1.0.0"
        assert js["title"] == "test.event"
        assert js["type"] == "object"
        assert js["additionalProperties"] is False
        assert "id" in js["properties"]
        assert "id" in js["required"]
        assert "count" in js["required"]
        # Optional fields should not be required
        assert "score" not in js["required"]

    def test_to_dict(self, sample_schema):
        d = sample_schema.to_dict()
        assert d["name"] == "test.event"
        assert d["version"] == "1.0.0"
        assert len(d["fields"]) == 6
        assert d["deprecated"] is False

    def test_deprecated_schema(self):
        schema = EventSchema(
            name="old.event", version="1.0.0", fields=[],
            deprecated=True, deprecation_message="Use new.event instead",
        )
        assert schema.deprecated is True
        assert schema.deprecation_message == "Use new.event instead"


# =============================================================================
# Schema Registry Tests
# =============================================================================


class TestSchemaRegistry:
    def test_register_and_get(self, sample_schema):
        register_schema(sample_schema)
        found = get_schema("test.event", "1.0.0")
        assert found is not None
        assert found.name == "test.event"

    def test_get_latest_version(self):
        s1 = EventSchema(name="ev", version="1.0.0", fields=[])
        s2 = EventSchema(name="ev", version="2.0.0", fields=[])
        register_schema(s1)
        register_schema(s2)
        latest = get_schema("ev")
        assert latest is not None
        assert latest.version == "2.0.0"

    def test_get_nonexistent(self):
        assert get_schema("nonexistent") is None

    def test_overwrite_same_version(self, sample_schema):
        register_schema(sample_schema)
        new_schema = EventSchema(
            name="test.event", version="1.0.0",
            fields=[FieldSpec("x", FieldType.STRING)],
        )
        register_schema(new_schema)
        found = get_schema("test.event", "1.0.0")
        assert found is not None
        assert len(found.fields) == 1

    def test_list_schemas(self, sample_schema):
        register_schema(sample_schema)
        schemas = list_schemas()
        assert len(schemas) >= 1
        names = [s["name"] for s in schemas]
        assert "test.event" in names

    def test_list_schemas_is_latest(self):
        s1 = EventSchema(name="ev", version="1.0.0", fields=[])
        s2 = EventSchema(name="ev", version="2.0.0", fields=[])
        register_schema(s1)
        register_schema(s2)
        schemas = list_schemas()
        for s in schemas:
            if s["name"] == "ev":
                if s["version"] == "2.0.0":
                    assert s["is_latest"] is True
                else:
                    assert s["is_latest"] is False


# =============================================================================
# Version Comparison Tests
# =============================================================================


class TestVersionComparison:
    def test_version_gt_major(self):
        assert _version_gt("2.0.0", "1.0.0") is True

    def test_version_gt_minor(self):
        assert _version_gt("1.2.0", "1.1.0") is True

    def test_version_gt_patch(self):
        assert _version_gt("1.0.2", "1.0.1") is True

    def test_version_equal(self):
        assert _version_gt("1.0.0", "1.0.0") is False

    def test_version_less(self):
        assert _version_gt("1.0.0", "2.0.0") is False

    def test_version_invalid_fallback(self):
        # Should fallback to lexical comparison
        result = _version_gt("b", "a")
        assert result is True


# =============================================================================
# Validation Tests
# =============================================================================


class TestValidateEvent:
    def test_valid_event(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {
            "id": "abc",
            "count": 5,
            "score": 3.14,
            "active": True,
            "tags": ["a", "b"],
            "meta": {"key": "val"},
        })
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_required_field(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {"count": 1})
        assert result.valid is False
        assert any("id" in e for e in result.errors)

    def test_wrong_type_string(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {"id": 123, "count": 1})
        assert result.valid is False
        assert any("id" in e for e in result.errors)

    def test_wrong_type_integer(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {"id": "abc", "count": "not_int"})
        assert result.valid is False
        assert any("count" in e for e in result.errors)

    def test_wrong_type_float(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {
            "id": "abc", "count": 1, "score": "not_float",
        })
        assert result.valid is False

    def test_wrong_type_boolean(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {
            "id": "abc", "count": 1, "active": "yes",
        })
        assert result.valid is False

    def test_wrong_type_array(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {
            "id": "abc", "count": 1, "tags": "not_array",
        })
        assert result.valid is False

    def test_wrong_type_object(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {
            "id": "abc", "count": 1, "meta": "not_object",
        })
        assert result.valid is False

    def test_unknown_field_warns(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {
            "id": "abc", "count": 1, "unknown_field": "value",
        })
        assert result.valid is True
        assert any("unknown_field" in w for w in result.warnings)

    def test_schema_not_found(self):
        result = validate_event("nonexistent", {"data": 1})
        assert result.valid is False
        assert any("not found" in e for e in result.errors)

    def test_optional_field_absent(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {"id": "abc", "count": 1})
        assert result.valid is True

    def test_null_value_passes_type_check(self, sample_schema):
        register_schema(sample_schema)
        result = validate_event("test.event", {
            "id": "abc", "count": 1, "score": None,
        })
        assert result.valid is True

    def test_enum_field_valid(self):
        schema = EventSchema(
            name="enum.test", version="1.0.0",
            fields=[
                FieldSpec("status", FieldType.ENUM, enum_values=["active", "inactive"]),
            ],
        )
        register_schema(schema)
        result = validate_event("enum.test", {"status": "active"})
        assert result.valid is True

    def test_enum_field_invalid_value(self):
        schema = EventSchema(
            name="enum.test", version="1.0.0",
            fields=[
                FieldSpec("status", FieldType.ENUM, enum_values=["active", "inactive"]),
            ],
        )
        register_schema(schema)
        result = validate_event("enum.test", {"status": "deleted"})
        assert result.valid is False

    def test_enum_field_non_string(self):
        schema = EventSchema(
            name="enum.test", version="1.0.0",
            fields=[
                FieldSpec("status", FieldType.ENUM, enum_values=["active"]),
            ],
        )
        register_schema(schema)
        result = validate_event("enum.test", {"status": 123})
        assert result.valid is False

    def test_deprecated_schema_warns(self):
        schema = EventSchema(
            name="old.event", version="1.0.0",
            fields=[FieldSpec("id", FieldType.STRING)],
            deprecated=True, deprecation_message="Use new.event",
        )
        register_schema(schema)
        result = validate_event("old.event", {"id": "abc"})
        assert result.valid is True
        assert any("deprecated" in w.lower() for w in result.warnings)

    def test_validate_specific_version(self):
        s1 = EventSchema(
            name="ev", version="1.0.0",
            fields=[FieldSpec("x", FieldType.STRING)],
        )
        s2 = EventSchema(
            name="ev", version="2.0.0",
            fields=[FieldSpec("x", FieldType.INTEGER)],
        )
        register_schema(s1)
        register_schema(s2)
        # v1 accepts string
        r1 = validate_event("ev", {"x": "hello"}, version="1.0.0")
        assert r1.valid is True
        # v2 rejects string
        r2 = validate_event("ev", {"x": "hello"}, version="2.0.0")
        assert r2.valid is False

    def test_integer_not_bool(self):
        """Booleans should not pass integer type check."""
        schema = EventSchema(
            name="int.test", version="1.0.0",
            fields=[FieldSpec("val", FieldType.INTEGER)],
        )
        register_schema(schema)
        result = validate_event("int.test", {"val": True})
        assert result.valid is False

    def test_float_accepts_int(self):
        """Integers should pass float type check."""
        schema = EventSchema(
            name="float.test", version="1.0.0",
            fields=[FieldSpec("val", FieldType.FLOAT)],
        )
        register_schema(schema)
        result = validate_event("float.test", {"val": 42})
        assert result.valid is True


# =============================================================================
# ValidationResult Tests
# =============================================================================


class TestValidationResult:
    def test_to_dict(self):
        result = ValidationResult(valid=True, errors=[], warnings=["w1"])
        d = result.to_dict()
        assert d["valid"] is True
        assert d["warnings"] == ["w1"]
        assert d["errors"] == []
