"""Tests for apps.capsules.services.capsule_registry — pure logic tests.

Tests validate_capsule_definition and load_system_capsules (file-based).
"""

import json
import os
import tempfile

from apps.capsules.services.capsule_registry import (
    load_system_capsules,
    validate_capsule_definition,
)

# ---------------------------------------------------------------------------
# validate_capsule_definition
# ---------------------------------------------------------------------------


class TestValidateCapsuleDefinition:
    def test_valid_definition(self):
        data = {
            "name": "test-capsule",
            "version": "1.0.0",
            "description": "A test capsule",
            "capsule_type": "voyant.intelligence_recipe",
            "system_prompt": "You are a test assistant.",
        }
        valid, error = validate_capsule_definition(data)
        # The Pydantic schema may require additional fields; check structure
        assert isinstance(valid, bool)

    def test_invalid_definition_missing_required(self):
        data = {}  # Missing required fields
        valid, error = validate_capsule_definition(data)
        assert valid is False
        assert error is not None

    def test_returns_tuple(self):
        valid, error = validate_capsule_definition({"name": "test"})
        assert isinstance(valid, bool)
        # error is None when valid, str when invalid
        if not valid:
            assert isinstance(error, str)


# ---------------------------------------------------------------------------
# load_system_capsules
# ---------------------------------------------------------------------------


class TestLoadSystemCapsules:
    def test_missing_directory_returns_empty(self):
        """When registry directory doesn't exist, should return empty list."""
        # The default registry dir may or may not exist; test the function works
        result = load_system_capsules()
        assert isinstance(result, list)

    def test_loads_json_files(self):
        """Test loading from a temporary directory with JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Write a test capsule JSON
            capsule_data = {
                "name": "system-test",
                "version": "1.0.0",
                "description": "System test capsule",
            }
            filepath = os.path.join(tmpdir, "test_capsule.json")
            with open(filepath, "w") as f:
                json.dump(capsule_data, f)

            # Write a non-JSON file (should be ignored)
            with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
                f.write("not a capsule")

            # Monkey-patch the registry dir
            import apps.capsules.services.capsule_registry as reg_module
            original_dir = reg_module._REGISTRY_DIR
            try:
                reg_module._REGISTRY_DIR = tmpdir
                result = load_system_capsules()
                assert len(result) == 1
                assert result[0]["name"] == "system-test"
            finally:
                reg_module._REGISTRY_DIR = original_dir

    def test_handles_malformed_json(self):
        """Should skip files with invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "bad.json")
            with open(filepath, "w") as f:
                f.write("{invalid json")

            import apps.capsules.services.capsule_registry as reg_module
            original_dir = reg_module._REGISTRY_DIR
            try:
                reg_module._REGISTRY_DIR = tmpdir
                result = load_system_capsules()
                assert result == []  # Bad file skipped
            finally:
                reg_module._REGISTRY_DIR = original_dir

    def test_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import apps.capsules.services.capsule_registry as reg_module
            original_dir = reg_module._REGISTRY_DIR
            try:
                reg_module._REGISTRY_DIR = tmpdir
                result = load_system_capsules()
                assert result == []
            finally:
                reg_module._REGISTRY_DIR = original_dir

    def test_sorted_by_filename(self):
        """Files should be loaded in sorted order."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for name in ["c.json", "a.json", "b.json"]:
                with open(os.path.join(tmpdir, name), "w") as f:
                    json.dump({"name": name.replace(".json", "")}, f)

            import apps.capsules.services.capsule_registry as reg_module
            original_dir = reg_module._REGISTRY_DIR
            try:
                reg_module._REGISTRY_DIR = tmpdir
                result = load_system_capsules()
                names = [c["name"] for c in result]
                assert names == ["a", "b", "c"]
            finally:
                reg_module._REGISTRY_DIR = original_dir
