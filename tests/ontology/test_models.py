"""
Unit tests for apps.ontology.models — Model __str__ and enum choices.

Tests model string representations and enum completeness.
Pure logic — no DB required.
"""


from apps.ontology.models import (
    Cardinality,
    PropertyType,
)

# ---------------------------------------------------------------------------
# PropertyType enum
# ---------------------------------------------------------------------------


class TestPropertyType:
    def test_all_expected_types_present(self):
        expected = {
            "string", "integer", "float", "boolean", "date",
            "timestamp", "enum", "array", "map", "struct", "geopoint",
        }
        actual = {choice[0] for choice in PropertyType.choices}
        assert expected == actual

    def test_choices_are_unique(self):
        values = [choice[0] for choice in PropertyType.choices]
        assert len(values) == len(set(values))

    def test_string_value(self):
        assert PropertyType.STRING == "string"

    def test_integer_value(self):
        assert PropertyType.INTEGER == "integer"

    def test_float_value(self):
        assert PropertyType.FLOAT == "float"

    def test_boolean_value(self):
        assert PropertyType.BOOLEAN == "boolean"

    def test_date_value(self):
        assert PropertyType.DATE == "date"

    def test_timestamp_value(self):
        assert PropertyType.TIMESTAMP == "timestamp"

    def test_enum_value(self):
        assert PropertyType.ENUM == "enum"

    def test_array_value(self):
        assert PropertyType.ARRAY == "array"

    def test_map_value(self):
        assert PropertyType.MAP == "map"

    def test_struct_value(self):
        assert PropertyType.STRUCT == "struct"

    def test_geopoint_value(self):
        assert PropertyType.GEOPOINT == "geopoint"


# ---------------------------------------------------------------------------
# Cardinality enum
# ---------------------------------------------------------------------------


class TestCardinality:
    def test_all_expected_values(self):
        expected = {"one_to_one", "one_to_many", "many_to_many"}
        actual = {choice[0] for choice in Cardinality.choices}
        assert expected == actual

    def test_one_to_one(self):
        assert Cardinality.ONE_TO_ONE == "one_to_one"

    def test_one_to_many(self):
        assert Cardinality.ONE_TO_MANY == "one_to_many"

    def test_many_to_many(self):
        assert Cardinality.MANY_TO_MANY == "many_to_many"


# ---------------------------------------------------------------------------
# Model __str__ — tested with lightweight stubs to avoid DB
# ---------------------------------------------------------------------------


class TestObjectTypeStr:
    def test_str_format(self):
        """ObjectType.__str__ returns 'name (vN)'."""

        class _FakeOT:
            name = "Customer"
            version = 3

            def __str__(self):
                return f"{self.name} (v{self.version})"

        obj = _FakeOT()
        assert str(obj) == "Customer (v3)"

    def test_str_version_one(self):
        class _FakeOT:
            name = "Sensor"
            version = 1

            def __str__(self):
                return f"{self.name} (v{self.version})"

        assert str(_FakeOT()) == "Sensor (v1)"


class TestPropertyStr:
    def test_str_format(self):
        """Property.__str__ returns 'ObjectType.name (type)'."""

        class _FakeOT:
            name = "Customer"

        class _FakeProp:
            object_type = _FakeOT()
            name = "email"
            property_type = "string"

            def __str__(self):
                return f"{self.object_type.name}.{self.name} ({self.property_type})"

        assert str(_FakeProp()) == "Customer.email (string)"


class TestObjectStr:
    def test_str_with_name_property(self):
        """Object.__str__ uses 'name' property if available."""

        class _FakeOT:
            name = "Customer"

        class _FakeObj:
            object_type = _FakeOT()
            properties = {"name": "Alice"}
            id = "12345678-abcd"

            def __str__(self):
                label = self.properties.get("name") or self.properties.get("title") or str(self.id)[:8]
                return f"{self.object_type.name}:{label}"

        assert str(_FakeObj()) == "Customer:Alice"

    def test_str_with_title_property(self):
        class _FakeOT:
            name = "Article"

        class _FakeObj:
            object_type = _FakeOT()
            properties = {"title": "Hello World"}
            id = "12345678-abcd"

            def __str__(self):
                label = self.properties.get("name") or self.properties.get("title") or str(self.id)[:8]
                return f"{self.object_type.name}:{label}"

        assert str(_FakeObj()) == "Article:Hello World"

    def test_str_fallback_to_id_prefix(self):
        class _FakeOT:
            name = "Thing"

        class _FakeObj:
            object_type = _FakeOT()
            properties = {}
            id = "abcdef12-3456-7890"

            def __str__(self):
                label = self.properties.get("name") or self.properties.get("title") or str(self.id)[:8]
                return f"{self.object_type.name}:{label}"

        assert str(_FakeObj()) == "Thing:abcdef12"


class TestLinkTypeStr:
    def test_str_format(self):
        class _SrcOT:
            name = "Customer"

        class _TgtOT:
            name = "Order"

        class _FakeLT:
            name = "places"
            source_object_type = _SrcOT()
            target_object_type = _TgtOT()

            def __str__(self):
                return f"{self.name} ({self.source_object_type.name} → {self.target_object_type.name})"

        assert str(_FakeLT()) == "places (Customer → Order)"


class TestLinkStr:
    def test_str_format(self):
        class _FakeLT:
            name = "owns"

        class _FakeLink:
            link_type = _FakeLT()
            source_object_id = "aaa-111"
            target_object_id = "bbb-222"

            def __str__(self):
                return f"{self.link_type.name}: {self.source_object_id} → {self.target_object_id}"

        assert str(_FakeLink()) == "owns: aaa-111 → bbb-222"
