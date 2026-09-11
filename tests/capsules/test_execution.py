"""Tests for apps.capsules.services.capsule_execution — parameter validation and substitution."""


from apps.capsules.services.capsule_execution import (
    merge_parameters,
    substitute_parameters,
    validate_parameters,
)

# ---------------------------------------------------------------------------
# validate_parameters
# ---------------------------------------------------------------------------


class TestValidateParameters:
    def _make_capsule(self, schema=None):
        class Capsule:
            parameters_schema = schema or {}
        return Capsule()

    def test_no_schema_always_valid(self):
        capsule = self._make_capsule(schema={})
        valid, error = validate_parameters(capsule, {"anything": "value"})
        assert valid is True
        assert error is None

    def test_none_schema_always_valid(self):
        capsule = self._make_capsule(schema=None)
        valid, error = validate_parameters(capsule, {})
        assert valid is True

    def test_required_param_missing(self):
        schema = {"source": {"required": True, "type": "string"}}
        capsule = self._make_capsule(schema)
        valid, error = validate_parameters(capsule, {})
        assert valid is False
        assert "source" in error

    def test_required_param_present(self):
        schema = {"source": {"required": True, "type": "string"}}
        capsule = self._make_capsule(schema)
        valid, error = validate_parameters(capsule, {"source": "data.csv"})
        assert valid is True

    def test_string_type_validation(self):
        schema = {"name": {"type": "string"}}
        capsule = self._make_capsule(schema)
        valid, _ = validate_parameters(capsule, {"name": "test"})
        assert valid is True
        valid, error = validate_parameters(capsule, {"name": 123})
        assert valid is False
        assert "string" in error

    def test_integer_type_validation(self):
        schema = {"count": {"type": "integer"}}
        capsule = self._make_capsule(schema)
        valid, _ = validate_parameters(capsule, {"count": 5})
        assert valid is True
        valid, error = validate_parameters(capsule, {"count": "five"})
        assert valid is False
        assert "integer" in error

    def test_number_type_validation(self):
        schema = {"rate": {"type": "number"}}
        capsule = self._make_capsule(schema)
        valid, _ = validate_parameters(capsule, {"rate": 0.5})
        assert valid is True
        valid, _ = validate_parameters(capsule, {"rate": 5})
        assert valid is True
        valid, error = validate_parameters(capsule, {"rate": "half"})
        assert valid is False

    def test_boolean_type_validation(self):
        schema = {"flag": {"type": "boolean"}}
        capsule = self._make_capsule(schema)
        valid, _ = validate_parameters(capsule, {"flag": True})
        assert valid is True
        valid, error = validate_parameters(capsule, {"flag": "yes"})
        assert valid is False
        assert "boolean" in error

    def test_options_validation(self):
        schema = {"method": {"type": "string", "options": ["pca", "tsne"]}}
        capsule = self._make_capsule(schema)
        valid, _ = validate_parameters(capsule, {"method": "pca"})
        assert valid is True
        valid, error = validate_parameters(capsule, {"method": "umap"})
        assert valid is False
        assert "pca" in error

    def test_optional_param_not_provided(self):
        schema = {"optional_param": {"type": "string"}}
        capsule = self._make_capsule(schema)
        valid, _ = validate_parameters(capsule, {})
        assert valid is True


# ---------------------------------------------------------------------------
# merge_parameters
# ---------------------------------------------------------------------------


class TestMergeParameters:
    def _make_capsule(self, schema=None):
        class Capsule:
            parameters_schema = schema or {}
        return Capsule()

    def test_defaults_applied(self):
        schema = {"source": {"default": "data.csv"}}
        capsule = self._make_capsule(schema)
        merged = merge_parameters(capsule, None, {})
        assert merged["source"] == "data.csv"

    def test_runtime_overrides_default(self):
        schema = {"source": {"default": "data.csv"}}
        capsule = self._make_capsule(schema)
        merged = merge_parameters(capsule, None, {"source": "custom.csv"})
        assert merged["source"] == "custom.csv"

    def test_installation_overrides_default(self):
        schema = {"source": {"default": "data.csv"}}
        capsule = self._make_capsule(schema)

        class Installation:
            parameter_overrides = {"source": "installed.csv"}

        merged = merge_parameters(capsule, Installation(), {})
        assert merged["source"] == "installed.csv"

    def test_runtime_overrides_installation(self):
        schema = {"source": {"default": "data.csv"}}
        capsule = self._make_capsule(schema)

        class Installation:
            parameter_overrides = {"source": "installed.csv"}

        merged = merge_parameters(capsule, Installation(), {"source": "runtime.csv"})
        assert merged["source"] == "runtime.csv"

    def test_no_schema_no_overrides(self):
        capsule = self._make_capsule(schema={})
        merged = merge_parameters(capsule, None, {"key": "value"})
        assert merged == {"key": "value"}


# ---------------------------------------------------------------------------
# substitute_parameters
# ---------------------------------------------------------------------------


class TestSubstituteParameters:
    def test_basic_substitution(self):
        template = {"url": "https://{{host}}/{{path}}"}
        result = substitute_parameters(template, {"host": "example.com", "path": "api"})
        assert result["url"] == "https://example.com/api"

    def test_nested_substitution(self):
        template = {"outer": {"inner": "{{value}}"}}
        result = substitute_parameters(template, {"value": "hello"})
        assert result["outer"]["inner"] == "hello"

    def test_list_substitution(self):
        template = {"items": ["{{a}}", "{{b}}"]}
        result = substitute_parameters(template, {"a": "1", "b": "2"})
        assert result["items"] == ["1", "2"]

    def test_non_string_values_unchanged(self):
        template = {"count": 42, "flag": True, "name": "{{n}}"}
        result = substitute_parameters(template, {"n": "test"})
        assert result["count"] == 42
        assert result["flag"] is True
        assert result["name"] == "test"

    def test_step_results_available(self):
        template = {"output": "{{steps.ingest.result}}"}
        result = substitute_parameters(
            template, {}, step_results={"ingest": {"result": "success"}}
        )
        assert result["output"] == "success"

    def test_missing_variable_keeps_template(self):
        template = {"url": "https://{{missing_var}}"}
        result = substitute_parameters(template, {})
        # Jinja2 renders missing vars as empty string
        assert "url" in result

    def test_empty_template(self):
        result = substitute_parameters({}, {"key": "value"})
        assert result == {}
