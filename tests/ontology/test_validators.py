"""
Unit tests for apps.ontology.validators — Property validation logic.

Covers type checking, required constraints, default values, rule-based
validation, unknown field rejection, and partial-update mode.
Pure logic — no DB, no services.
"""


from apps.ontology.models import PropertyType
from apps.ontology.validators import ValidationError, validate_properties

# ---------------------------------------------------------------------------
# Helpers: lightweight stand-in for Property model instances
# ---------------------------------------------------------------------------


class _PropDef:
    """Minimal object that satisfies the Property interface used by validators."""

    def __init__(
        self,
        name: str,
        property_type: str,
        required: bool = False,
        default_value=None,
        validation_rules=None,
        metadata=None,
    ):
        self.name = name
        self.property_type = property_type
        self.required = required
        self.default_value = default_value
        self.validation_rules = validation_rules or {}
        self.metadata = metadata or {}


# ---------------------------------------------------------------------------
# ValidationError
# ---------------------------------------------------------------------------


class TestValidationError:
    def test_stores_errors(self):
        errors = [{"field": "x", "code": "required", "message": "missing"}]
        exc = ValidationError(errors)
        assert exc.errors == errors
        assert "1 error(s)" in str(exc)

    def test_multiple_errors(self):
        errors = [
            {"field": "a", "code": "required", "message": "missing a"},
            {"field": "b", "code": "required", "message": "missing b"},
        ]
        exc = ValidationError(errors)
        assert "2 error(s)" in str(exc)


# ---------------------------------------------------------------------------
# Type validators — each PropertyType
# ---------------------------------------------------------------------------


class TestTypeValidators:
    """Validate that each PropertyType accepts/rejects the right values."""

    def test_string_accepts_str(self):
        defs = [_PropDef("name", PropertyType.STRING)]
        norm, errs = validate_properties({"name": "hello"}, defs)
        assert errs == []
        assert norm["name"] == "hello"

    def test_string_rejects_int(self):
        defs = [_PropDef("name", PropertyType.STRING)]
        _, errs = validate_properties({"name": 42}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_integer_accepts_int(self):
        defs = [_PropDef("count", PropertyType.INTEGER)]
        norm, errs = validate_properties({"count": 7}, defs)
        assert errs == []
        assert norm["count"] == 7

    def test_integer_rejects_bool(self):
        """Booleans must not pass integer validation."""
        defs = [_PropDef("count", PropertyType.INTEGER)]
        _, errs = validate_properties({"count": True}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_integer_rejects_str(self):
        defs = [_PropDef("count", PropertyType.INTEGER)]
        _, errs = validate_properties({"count": "7"}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_float_accepts_float(self):
        defs = [_PropDef("price", PropertyType.FLOAT)]
        norm, errs = validate_properties({"price": 3.14}, defs)
        assert errs == []
        assert norm["price"] == 3.14

    def test_float_accepts_int(self):
        """Integers are valid floats."""
        defs = [_PropDef("price", PropertyType.FLOAT)]
        norm, errs = validate_properties({"price": 5}, defs)
        assert errs == []
        assert norm["price"] == 5

    def test_float_rejects_bool(self):
        defs = [_PropDef("price", PropertyType.FLOAT)]
        _, errs = validate_properties({"price": False}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_boolean_accepts_true(self):
        defs = [_PropDef("active", PropertyType.BOOLEAN)]
        norm, errs = validate_properties({"active": True}, defs)
        assert errs == []
        assert norm["active"] is True

    def test_boolean_rejects_str(self):
        defs = [_PropDef("active", PropertyType.BOOLEAN)]
        _, errs = validate_properties({"active": "yes"}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_date_accepts_valid(self):
        defs = [_PropDef("dob", PropertyType.DATE)]
        norm, errs = validate_properties({"dob": "2024-01-15"}, defs)
        assert errs == []
        assert norm["dob"] == "2024-01-15"

    def test_date_rejects_invalid_format(self):
        defs = [_PropDef("dob", PropertyType.DATE)]
        _, errs = validate_properties({"dob": "15-01-2024"}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_date_rejects_non_string(self):
        defs = [_PropDef("dob", PropertyType.DATE)]
        _, errs = validate_properties({"dob": 20240115}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_timestamp_accepts_iso(self):
        defs = [_PropDef("ts", PropertyType.TIMESTAMP)]
        norm, errs = validate_properties({"ts": "2024-01-15T10:30:00Z"}, defs)
        assert errs == []
        assert norm["ts"] == "2024-01-15T10:30:00Z"

    def test_timestamp_accepts_offset(self):
        defs = [_PropDef("ts", PropertyType.TIMESTAMP)]
        norm, errs = validate_properties({"ts": "2024-01-15T10:30:00+05:30"}, defs)
        assert errs == []

    def test_timestamp_rejects_invalid(self):
        defs = [_PropDef("ts", PropertyType.TIMESTAMP)]
        _, errs = validate_properties({"ts": "not-a-timestamp"}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_array_accepts_list(self):
        defs = [_PropDef("tags", PropertyType.ARRAY)]
        norm, errs = validate_properties({"tags": ["a", "b"]}, defs)
        assert errs == []
        assert norm["tags"] == ["a", "b"]

    def test_array_rejects_dict(self):
        defs = [_PropDef("tags", PropertyType.ARRAY)]
        _, errs = validate_properties({"tags": {"a": 1}}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_map_accepts_dict(self):
        defs = [_PropDef("meta", PropertyType.MAP)]
        norm, errs = validate_properties({"meta": {"k": "v"}}, defs)
        assert errs == []
        assert norm["meta"] == {"k": "v"}

    def test_map_rejects_list(self):
        defs = [_PropDef("meta", PropertyType.MAP)]
        _, errs = validate_properties({"meta": [1, 2]}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_geopoint_accepts_two_element_list(self):
        defs = [_PropDef("loc", PropertyType.GEOPOINT)]
        norm, errs = validate_properties({"loc": [40.7128, -74.0060]}, defs)
        assert errs == []
        assert norm["loc"] == [40.7128, -74.0060]

    def test_geopoint_rejects_three_elements(self):
        defs = [_PropDef("loc", PropertyType.GEOPOINT)]
        _, errs = validate_properties({"loc": [40.0, -74.0, 10.0]}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_geopoint_rejects_non_list(self):
        defs = [_PropDef("loc", PropertyType.GEOPOINT)]
        _, errs = validate_properties({"loc": "40.7,-74.0"}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)

    def test_enum_accepts_valid_choice(self):
        defs = [
            _PropDef(
                "status",
                PropertyType.ENUM,
                validation_rules={"enum_values": ["active", "inactive"]},
            )
        ]
        norm, errs = validate_properties({"status": "active"}, defs)
        assert errs == []
        assert norm["status"] == "active"

    def test_enum_rejects_invalid_choice(self):
        defs = [
            _PropDef(
                "status",
                PropertyType.ENUM,
                validation_rules={"enum_values": ["active", "inactive"]},
            )
        ]
        _, errs = validate_properties({"status": "deleted"}, defs)
        assert any(e["code"] == "invalid_choice" for e in errs)

    def test_struct_accepts_dict(self):
        defs = [_PropDef("address", PropertyType.STRUCT)]
        norm, errs = validate_properties({"address": {"city": "NY"}}, defs)
        assert errs == []
        assert norm["address"] == {"city": "NY"}

    def test_struct_rejects_non_dict(self):
        defs = [_PropDef("address", PropertyType.STRUCT)]
        _, errs = validate_properties({"address": "NY"}, defs)
        assert any(e["code"] == "invalid_type" for e in errs)


# ---------------------------------------------------------------------------
# Required / default
# ---------------------------------------------------------------------------


class TestRequiredAndDefault:
    def test_required_field_missing_raises(self):
        defs = [_PropDef("name", PropertyType.STRING, required=True)]
        _, errs = validate_properties({}, defs)
        assert len(errs) == 1
        assert errs[0]["code"] == "required"
        assert errs[0]["field"] == "name"

    def test_required_field_present_ok(self):
        defs = [_PropDef("name", PropertyType.STRING, required=True)]
        norm, errs = validate_properties({"name": "ok"}, defs)
        assert errs == []
        assert norm["name"] == "ok"

    def test_optional_field_missing_no_error(self):
        defs = [_PropDef("name", PropertyType.STRING, required=False)]
        norm, errs = validate_properties({}, defs)
        assert errs == []
        assert norm["name"] is None

    def test_default_value_applied(self):
        defs = [_PropDef("status", PropertyType.STRING, default_value="active")]
        norm, errs = validate_properties({}, defs)
        assert errs == []
        assert norm["status"] == "active"

    def test_default_value_overridden_by_provided(self):
        defs = [_PropDef("status", PropertyType.STRING, default_value="active")]
        norm, errs = validate_properties({"status": "paused"}, defs)
        assert errs == []
        assert norm["status"] == "paused"

    def test_partial_skips_required_check(self):
        """partial=True should skip required validation (PATCH semantics)."""
        defs = [_PropDef("name", PropertyType.STRING, required=True)]
        norm, errs = validate_properties({}, defs, partial=True)
        assert errs == []
        assert norm["name"] is None


# ---------------------------------------------------------------------------
# Rule-based validation
# ---------------------------------------------------------------------------


class TestRuleValidation:
    def test_regex_match(self):
        defs = [
            _PropDef(
                "email",
                PropertyType.STRING,
                validation_rules={"regex": r"^[^@]+@[^@]+\.[^@]+$"},
            )
        ]
        norm, errs = validate_properties({"email": "a@b.com"}, defs)
        assert errs == []

    def test_regex_no_match(self):
        defs = [
            _PropDef(
                "email",
                PropertyType.STRING,
                validation_rules={"regex": r"^[^@]+@[^@]+\.[^@]+$"},
            )
        ]
        _, errs = validate_properties({"email": "not-an-email"}, defs)
        assert any(e["code"] == "regex" for e in errs)

    def test_min_value_pass(self):
        defs = [_PropDef("age", PropertyType.INTEGER, validation_rules={"min": 0})]
        norm, errs = validate_properties({"age": 25}, defs)
        assert errs == []

    def test_min_value_fail(self):
        defs = [_PropDef("age", PropertyType.INTEGER, validation_rules={"min": 0})]
        _, errs = validate_properties({"age": -1}, defs)
        assert any(e["code"] == "min" for e in errs)

    def test_max_value_pass(self):
        defs = [_PropDef("score", PropertyType.INTEGER, validation_rules={"max": 100})]
        norm, errs = validate_properties({"score": 100}, defs)
        assert errs == []

    def test_max_value_fail(self):
        defs = [_PropDef("score", PropertyType.INTEGER, validation_rules={"max": 100})]
        _, errs = validate_properties({"score": 101}, defs)
        assert any(e["code"] == "max" for e in errs)

    def test_min_length_pass(self):
        defs = [
            _PropDef("name", PropertyType.STRING, validation_rules={"min_length": 3})
        ]
        norm, errs = validate_properties({"name": "abc"}, defs)
        assert errs == []

    def test_min_length_fail(self):
        defs = [
            _PropDef("name", PropertyType.STRING, validation_rules={"min_length": 3})
        ]
        _, errs = validate_properties({"name": "ab"}, defs)
        assert any(e["code"] == "min_length" for e in errs)

    def test_max_length_pass(self):
        defs = [
            _PropDef("code", PropertyType.STRING, validation_rules={"max_length": 5})
        ]
        norm, errs = validate_properties({"code": "ABCDE"}, defs)
        assert errs == []

    def test_max_length_fail(self):
        defs = [
            _PropDef("code", PropertyType.STRING, validation_rules={"max_length": 5})
        ]
        _, errs = validate_properties({"code": "ABCDEF"}, defs)
        assert any(e["code"] == "max_length" for e in errs)

    def test_enum_values_rule_pass(self):
        defs = [
            _PropDef(
                "color",
                PropertyType.STRING,
                validation_rules={"enum_values": ["red", "green", "blue"]},
            )
        ]
        norm, errs = validate_properties({"color": "red"}, defs)
        assert errs == []

    def test_enum_values_rule_fail(self):
        defs = [
            _PropDef(
                "color",
                PropertyType.STRING,
                validation_rules={"enum_values": ["red", "green", "blue"]},
            )
        ]
        _, errs = validate_properties({"color": "yellow"}, defs)
        assert any(e["code"] == "enum_values" for e in errs)

    def test_multiple_rules_on_same_field(self):
        """Both min_length and regex should be checked."""
        defs = [
            _PropDef(
                "code",
                PropertyType.STRING,
                validation_rules={"min_length": 3, "regex": r"^[A-Z]+$"},
            )
        ]
        # Passes both
        norm, errs = validate_properties({"code": "ABC"}, defs)
        assert errs == []
        # Fails regex (lowercase)
        _, errs = validate_properties({"code": "abc"}, defs)
        assert any(e["code"] == "regex" for e in errs)


# ---------------------------------------------------------------------------
# Unknown fields
# ---------------------------------------------------------------------------


class TestUnknownFields:
    def test_extra_field_rejected(self):
        defs = [_PropDef("name", PropertyType.STRING)]
        _, errs = validate_properties({"name": "ok", "extra": "bad"}, defs)
        assert any(e["code"] == "unknown_field" and e["field"] == "extra" for e in errs)

    def test_only_known_fields_accepted(self):
        defs = [_PropDef("a", PropertyType.STRING), _PropDef("b", PropertyType.INTEGER)]
        norm, errs = validate_properties({"a": "x", "b": 1}, defs)
        assert errs == []
        assert norm == {"a": "x", "b": 1}

    def test_empty_properties_with_no_required(self):
        defs = [_PropDef("opt", PropertyType.STRING)]
        norm, errs = validate_properties({}, defs)
        assert errs == []
        assert norm == {"opt": None}


# ---------------------------------------------------------------------------
# Combined / edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_no_property_defs(self):
        """Empty schema: any provided property is unknown."""
        _, errs = validate_properties({"anything": 1}, [])
        assert any(e["code"] == "unknown_field" for e in errs)

    def test_empty_input_empty_schema(self):
        norm, errs = validate_properties({}, [])
        assert norm == {}
        assert errs == []

    def test_null_value_for_optional_field(self):
        defs = [_PropDef("note", PropertyType.STRING)]
        norm, errs = validate_properties({"note": None}, defs)
        assert errs == []
        assert norm["note"] is None

    def test_default_value_for_null_explicit(self):
        """Explicitly passing None should still trigger default."""
        defs = [_PropDef("level", PropertyType.INTEGER, default_value=1)]
        norm, errs = validate_properties({"level": None}, defs)
        assert errs == []
        assert norm["level"] == 1

    def test_multiple_errors_accumulated(self):
        defs = [
            _PropDef("a", PropertyType.STRING, required=True),
            _PropDef("b", PropertyType.INTEGER, required=True),
        ]
        _, errs = validate_properties({}, defs)
        assert len(errs) == 2
        fields = {e["field"] for e in errs}
        assert fields == {"a", "b"}
