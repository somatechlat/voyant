"""
Unit tests for apps.core.lib.namespace_analyzer — Tenant namespace isolation.

Real analyzer instances. No mocks, no external services.
"""

import pytest

from apps.core.lib.namespace_analyzer import (
    IsolationMode,
    NamespaceAnalyzer,
    NamespaceConfig,
    NamespaceViolationError,
)


# =============================================================================
# NamespaceConfig Tests
# =============================================================================


class TestNamespaceConfig:
    def test_defaults(self):
        cfg = NamespaceConfig()
        assert cfg.mode == IsolationMode.PREFIX
        assert cfg.separator == "_"
        assert cfg.strict is True
        assert cfg.custom_pattern is None

    def test_custom_config(self):
        cfg = NamespaceConfig(
            mode=IsolationMode.SCHEMA, separator="-", strict=False,
        )
        assert cfg.mode == IsolationMode.SCHEMA
        assert cfg.separator == "-"
        assert cfg.strict is False


# =============================================================================
# Prefix Mode Tests
# =============================================================================


class TestPrefixMode:
    @pytest.fixture
    def analyzer(self):
        return NamespaceAnalyzer(
            NamespaceConfig(mode=IsolationMode.PREFIX, strict=False)
        )

    @pytest.fixture
    def strict_analyzer(self):
        return NamespaceAnalyzer(
            NamespaceConfig(mode=IsolationMode.PREFIX, strict=True)
        )

    def test_valid_prefix(self, analyzer):
        assert analyzer.validate_access("t123", "t123_orders") is True

    def test_invalid_prefix(self, analyzer):
        assert analyzer.validate_access("t123", "t456_orders") is False

    def test_exact_match_not_enough(self, analyzer):
        """Table name must start with prefix including separator."""
        assert analyzer.validate_access("t123", "t123") is False

    def test_prefix_with_custom_separator(self):
        analyzer = NamespaceAnalyzer(
            NamespaceConfig(mode=IsolationMode.PREFIX, separator="-", strict=False)
        )
        assert analyzer.validate_access("t1", "t1-orders") is True
        assert analyzer.validate_access("t1", "t1_orders") is False

    def test_strict_raises(self, strict_analyzer):
        with pytest.raises(NamespaceViolationError):
            strict_analyzer.validate_access("t1", "other_table")

    def test_non_strict_returns_false(self, analyzer):
        result = analyzer.validate_access("t1", "other_table")
        assert result is False

    def test_empty_tenant_id_strict(self, strict_analyzer):
        with pytest.raises(ValueError, match="required"):
            strict_analyzer.validate_access("", "table")

    def test_empty_table_name_strict(self, strict_analyzer):
        with pytest.raises(ValueError, match="required"):
            strict_analyzer.validate_access("t1", "")

    def test_empty_inputs_non_strict(self, analyzer):
        assert analyzer.validate_access("", "table") is False
        assert analyzer.validate_access("t1", "") is False

    def test_get_allowed_prefix(self, analyzer):
        assert analyzer.get_allowed_prefix("t123") == "t123_"


# =============================================================================
# Schema Mode Tests
# =============================================================================


class TestSchemaMode:
    @pytest.fixture
    def analyzer(self):
        return NamespaceAnalyzer(
            NamespaceConfig(mode=IsolationMode.SCHEMA, strict=False)
        )

    def test_valid_schema(self, analyzer):
        assert analyzer.validate_access("tenant1", "tenant1.orders") is True

    def test_invalid_schema(self, analyzer):
        assert analyzer.validate_access("tenant1", "tenant2.orders") is False

    def test_no_dot(self, analyzer):
        assert analyzer.validate_access("tenant1", "orders") is False

    def test_multiple_dots(self, analyzer):
        # Only splits on first dot
        assert analyzer.validate_access("tenant1", "tenant1.schema.orders") is True

    def test_get_allowed_prefix(self):
        analyzer = NamespaceAnalyzer(NamespaceConfig(mode=IsolationMode.SCHEMA))
        assert analyzer.get_allowed_prefix("t1") == "t1."


# =============================================================================
# Custom Pattern Mode Tests
# =============================================================================


class TestCustomPatternMode:
    def test_matching_pattern(self):
        analyzer = NamespaceAnalyzer(
            NamespaceConfig(custom_pattern=r"^voyant_\w+_\w+$")
        )
        assert analyzer.validate_access("t1", "voyant_t1_orders") is True

    def test_non_matching_pattern(self):
        analyzer = NamespaceAnalyzer(
            NamespaceConfig(custom_pattern=r"^voyant_\w+_\w+$", strict=False)
        )
        assert analyzer.validate_access("t1", "other_table") is False

    def test_pattern_overrides_mode(self):
        """Custom pattern takes precedence over mode."""
        analyzer = NamespaceAnalyzer(
            NamespaceConfig(
                mode=IsolationMode.PREFIX,
                custom_pattern=r"^shared_\w+$",
            )
        )
        # Would fail PREFIX mode but passes custom pattern
        assert analyzer.validate_access("t1", "shared_orders") is True


# =============================================================================
# Metadata Mode Tests
# =============================================================================


class TestMetadataMode:
    def test_metadata_mode_always_denies(self):
        analyzer = NamespaceAnalyzer(
            NamespaceConfig(mode=IsolationMode.METADATA, strict=False)
        )
        assert analyzer.validate_access("t1", "t1_orders") is False

    def test_metadata_mode_strict_raises(self):
        analyzer = NamespaceAnalyzer(
            NamespaceConfig(mode=IsolationMode.METADATA, strict=True)
        )
        with pytest.raises(NamespaceViolationError):
            analyzer.validate_access("t1", "t1_orders")


# =============================================================================
# Violation Error Tests
# =============================================================================


class TestViolationError:
    def test_error_message_contains_details(self):
        analyzer = NamespaceAnalyzer(NamespaceConfig())
        with pytest.raises(NamespaceViolationError) as exc_info:
            analyzer.validate_access("t1", "other_table")
        msg = str(exc_info.value)
        assert "other_table" in msg
        assert "t1" in msg
        assert "prefix" in msg


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    def test_tenant_id_is_prefix_of_another(self):
        analyzer = NamespaceAnalyzer(
            NamespaceConfig(mode=IsolationMode.PREFIX, strict=False)
        )
        # "t1" should not match "t12_orders"
        assert analyzer.validate_access("t1", "t12_orders") is False

    def test_table_name_with_special_chars(self):
        analyzer = NamespaceAnalyzer(
            NamespaceConfig(mode=IsolationMode.PREFIX, strict=False)
        )
        assert analyzer.validate_access("t1", "t1_orders-v2") is True

    def test_unicode_tenant_id(self):
        analyzer = NamespaceAnalyzer(
            NamespaceConfig(mode=IsolationMode.PREFIX, strict=False)
        )
        assert analyzer.validate_access("日本語", "日本語_orders") is True
