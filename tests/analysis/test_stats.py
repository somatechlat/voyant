"""Tests for apps.analysis.lib.stats_primitives — R-backed statistical operations.

These tests exercise the pure Python logic and data flow. Tests that require
a live R backend are marked accordingly.
"""

import pytest

from apps.analysis.lib.stats_primitives import RStatsPrimitives


class TestRStatsPrimitivesInit:
    def test_init_with_default_engine(self):
        """Should initialize without error (REngine may not connect)."""
        try:
            sp = RStatsPrimitives()
            assert sp.r is not None
        except Exception:
            # REngine may fail to connect in test env — that's acceptable
            pytest.skip("R backend not available")

    def test_init_with_custom_engine(self):
        """Should accept a custom engine instance."""
        class FakeEngine:
            def assign(self, name, value): pass
            def eval(self, script): return {}
        sp = RStatsPrimitives(r_engine=FakeEngine())
        assert isinstance(sp.r, FakeEngine)


class TestDescribeColumnValidation:
    def test_empty_vector_raises(self):
        class FakeEngine:
            pass
        sp = RStatsPrimitives(r_engine=FakeEngine())
        with pytest.raises(Exception):
            sp.describe_column([])


class TestCorrelationMatrixValidation:
    def test_basic_structure(self):
        """Verify the method exists and accepts correct parameters."""
        class FakeEngine:
            def assign(self, name, value): pass
            def eval(self, script): return {"a": [1.0, 0.5], "b": [0.5, 1.0]}
        sp = RStatsPrimitives(r_engine=FakeEngine())
        result = sp.correlation_matrix({"a": [1.0, 2.0], "b": [3.0, 4.0]})
        assert isinstance(result, dict)


class TestFitDistributionValidation:
    def test_basic_structure(self):
        class FakeEngine:
            def assign(self, name, value): pass
            def eval(self, script): return {"mean": 0.0, "sd": 1.0}
        sp = RStatsPrimitives(r_engine=FakeEngine())
        result = sp.fit_distribution([1.0, 2.0, 3.0], dist="normal")
        assert isinstance(result, dict)
        assert "mean" in result
