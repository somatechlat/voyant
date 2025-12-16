"""
Tests for Plugin Registry

Verifies generator registration, execution order, and fail-fast behavior.
Reference: docs/CANONICAL_ARCHITECTURE.md Section 7
"""
import pytest
from dataclasses import dataclass

from voyant.core.plugin_registry import (
    register,
    list_generators,
    get_generator,
    run_generators,
    clear_registry,
    GeneratorContext,
    ArtifactResult,
)


@dataclass
class MockSettings:
    """Mock settings for testing feature flags."""
    enable_quality: bool = True
    enable_charts: bool = True
    enable_narrative: bool = True


class TestRegistration:
    """Test generator registration."""

    def setup_method(self):
        """Clear registry before each test."""
        clear_registry()

    def test_register_generator(self):
        """Should register a generator."""
        @register("test_gen", is_core=True, order=10)
        def test_gen(ctx):
            return {"test": "/tmp/test.json"}
        
        gens = list_generators()
        assert len(gens) == 1
        assert gens[0]["name"] == "test_gen"
        assert gens[0]["is_core"] is True
        assert gens[0]["order"] == 10

    def test_register_multiple_sorted_by_order(self):
        """Should maintain order by 'order' field."""
        @register("second", order=20)
        def gen2(ctx):
            return {}

        @register("first", order=10)
        def gen1(ctx):
            return {}

        @register("third", order=30)
        def gen3(ctx):
            return {}
        
        gens = list_generators()
        names = [g["name"] for g in gens]
        assert names == ["first", "second", "third"]

    def test_get_generator(self):
        """Should retrieve generator by name."""
        @register("findme")
        def findme_gen(ctx):
            return {}
        
        gen = get_generator("findme")
        assert gen is not None
        assert gen.name == "findme"

    def test_get_nonexistent_generator(self):
        """Should return None for unknown generator."""
        gen = get_generator("nonexistent")
        assert gen is None


class TestExecution:
    """Test generator execution."""

    def setup_method(self):
        """Clear registry and set up test generators."""
        clear_registry()

    def test_run_single_generator(self):
        """Should run single generator and collect artifacts."""
        @register("single", is_core=True)
        def single_gen(ctx):
            return {"artifact1": f"/artifacts/{ctx['job_id']}/file.json"}
        
        result = run_generators({"job_id": "test123"}, MockSettings())
        
        assert result.success is True
        assert "artifact1" in result.artifacts
        assert result.artifacts["artifact1"] == "/artifacts/test123/file.json"

    def test_run_multiple_generators(self):
        """Should run multiple generators in order."""
        execution_order = []

        @register("first", order=10)
        def first_gen(ctx):
            execution_order.append("first")
            return {"first": "/tmp/first"}

        @register("second", order=20)
        def second_gen(ctx):
            execution_order.append("second")
            return {"second": "/tmp/second"}
        
        result = run_generators({}, MockSettings())
        
        assert execution_order == ["first", "second"]
        assert "first" in result.artifacts
        assert "second" in result.artifacts


class TestFailFastBehavior:
    """Test core vs extended failure handling."""

    def setup_method(self):
        clear_registry()

    def test_core_failure_stops_pipeline(self):
        """Core generator failure should stop execution."""
        execution_order = []

        @register("good", is_core=True, order=10)
        def good_gen(ctx):
            execution_order.append("good")
            return {"good": "/tmp/good"}

        @register("bad_core", is_core=True, order=20)
        def bad_core_gen(ctx):
            execution_order.append("bad_core")
            raise Exception("Core failure!")

        @register("never_runs", is_core=False, order=30)
        def never_runs_gen(ctx):
            execution_order.append("never_runs")
            return {"never": "/tmp/never"}
        
        result = run_generators({}, MockSettings())
        
        assert result.success is False
        assert result.failed_core == "bad_core"
        assert execution_order == ["good", "bad_core"]
        # "never_runs" should NOT have executed

    def test_extended_failure_continues(self):
        """Extended generator failure should not stop execution."""
        execution_order = []

        @register("first", is_core=True, order=10)
        def first_gen(ctx):
            execution_order.append("first")
            return {"first": "/tmp/first"}

        @register("bad_extended", is_core=False, order=20)
        def bad_extended_gen(ctx):
            execution_order.append("bad_extended")
            raise Exception("Extended failure!")

        @register("third", is_core=False, order=30)
        def third_gen(ctx):
            execution_order.append("third")
            return {"third": "/tmp/third"}
        
        result = run_generators({}, MockSettings())
        
        assert result.success is True  # Pipeline succeeded
        assert result.failed_core is None
        assert execution_order == ["first", "bad_extended", "third"]


class TestFeatureFlags:
    """Test feature flag gating."""

    def setup_method(self):
        clear_registry()

    def test_disabled_flag_skips_generator(self):
        """Generator with disabled feature flag should be skipped."""
        execution_order = []

        @register("always", order=10)
        def always_gen(ctx):
            execution_order.append("always")
            return {}

        @register("gated", order=20, feature_flag="enable_quality")
        def gated_gen(ctx):
            execution_order.append("gated")
            return {}
        
        settings = MockSettings(enable_quality=False)
        result = run_generators({}, settings)
        
        assert execution_order == ["always"]
        assert "gated" not in execution_order

    def test_enabled_flag_runs_generator(self):
        """Generator with enabled feature flag should run."""
        execution_order = []

        @register("gated", feature_flag="enable_charts")
        def gated_gen(ctx):
            execution_order.append("gated")
            return {}
        
        settings = MockSettings(enable_charts=True)
        result = run_generators({}, settings)
        
        assert "gated" in execution_order


class TestResultDetails:
    """Test detailed result reporting."""

    def setup_method(self):
        clear_registry()

    def test_result_includes_timing(self):
        """Results should include duration."""
        @register("timed")
        def timed_gen(ctx):
            return {"out": "/tmp/out"}
        
        result = run_generators({}, MockSettings())
        
        assert len(result.results) == 1
        assert result.results[0].name == "timed"
        assert result.results[0].success is True
        assert result.results[0].duration_ms >= 0

    def test_result_includes_error_message(self):
        """Failed results should include error message."""
        @register("failing", is_core=False)
        def failing_gen(ctx):
            raise ValueError("Test error message")
        
        result = run_generators({}, MockSettings())
        
        assert result.results[0].success is False
        assert "Test error message" in result.results[0].error
