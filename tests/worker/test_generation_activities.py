"""
Tests for GenerationActivities.

Tests the run_generators activity with real plugin registry.
No mocking — uses real GeneratorPlugin implementations.
"""

import os

import pytest
from temporalio.exceptions import ApplicationError

from apps.core.lib.plugin_registry import (
    GeneratorPlugin,
    PluginCategory,
    PluginRegistry,
    register_plugin,
    reset_registry,
)
from apps.worker.activities.generation_activities import GenerationActivities


@pytest.fixture(scope="module")
def activities():
    """Real GenerationActivities instance."""
    return GenerationActivities()


class TestFeatureEnabled:
    """Tests for the _feature_enabled static method."""

    def test_truthy_values(self):
        """All truthy env values return True."""
        for val in ("1", "true", "TRUE", "yes", "on", "ON"):
            os.environ["VOYANT_FEATURE_GEN_FLAG"] = val
            assert GenerationActivities._feature_enabled("gen_flag") is True
        del os.environ["VOYANT_FEATURE_GEN_FLAG"]

    def test_falsy_values(self):
        """Non-truthy env values return False."""
        for val in ("0", "false", "no", "off", ""):
            os.environ["VOYANT_FEATURE_GEN_FLAG"] = val
            assert GenerationActivities._feature_enabled("gen_flag") is False
        del os.environ["VOYANT_FEATURE_GEN_FLAG"]

    def test_missing_env(self):
        """Missing env var returns False."""
        os.environ.pop("VOYANT_FEATURE_MISSING_FLAG", None)
        assert GenerationActivities._feature_enabled("missing_flag") is False


class TestRunGenerators:
    """Tests for the run_generators activity."""

    @pytest.mark.asyncio
    async def test_no_generators_registered(self, activities):
        """Empty registry returns empty dict."""
        reset_registry()
        result = await activities.run_generators({"data": []})
        assert result == {}

    @pytest.mark.asyncio
    async def test_with_test_generator(self, activities):
        """A registered generator plugin is invoked."""
        reset_registry()

        @register_plugin(
            name="test_generator",
            category=PluginCategory.REPORT,
            description="Test generator",
        )
        class TestGenerator(GeneratorPlugin):
            def generate(self, context):
                return {"artifact": "test_report", "rows": len(context.get("data", []))}

        try:
            result = await activities.run_generators({"data": [{"a": 1}, {"a": 2}]})
            assert "test_generator" in result
            assert result["test_generator"]["artifact"] == "test_report"
            assert result["test_generator"]["rows"] == 2
        finally:
            reset_registry()

    @pytest.mark.asyncio
    async def test_non_core_generator_failure_continues(self, activities):
        """Non-core generator failure is captured in _errors, others continue."""
        reset_registry()

        @register_plugin(
            name="failing_gen",
            category=PluginCategory.REPORT,
            is_core=False,
        )
        class FailingGen(GeneratorPlugin):
            def generate(self, context):
                raise RuntimeError("gen failure")

        @register_plugin(
            name="good_gen",
            category=PluginCategory.REPORT,
        )
        class GoodGen(GeneratorPlugin):
            def generate(self, context):
                return {"status": "ok"}

        try:
            result = await activities.run_generators({})
            assert "good_gen" in result
            assert result["good_gen"]["status"] == "ok"
            assert "_errors" in result
            assert any("failing_gen" in e for e in result["_errors"])
        finally:
            reset_registry()

    @pytest.mark.asyncio
    async def test_core_generator_failure_halts(self, activities):
        """Core generator failure raises ApplicationError."""
        reset_registry()

        @register_plugin(
            name="core_failing_gen",
            category=PluginCategory.REPORT,
            is_core=True,
        )
        class CoreFailingGen(GeneratorPlugin):
            def generate(self, context):
                raise RuntimeError("critical gen failure")

        try:
            with pytest.raises(ApplicationError, match="Core generator failed"):
                await activities.run_generators({})
        finally:
            reset_registry()

    @pytest.mark.asyncio
    async def test_feature_flag_disabled_skips(self, activities):
        """Generator with disabled feature flag is skipped."""
        reset_registry()
        os.environ.pop("VOYANT_FEATURE_GATED_GEN", None)

        @register_plugin(
            name="gated_gen",
            category=PluginCategory.REPORT,
            feature_flag="gated_gen",
        )
        class GatedGen(GeneratorPlugin):
            def generate(self, context):
                return {"should": "not_run"}

        try:
            result = await activities.run_generators({})
            assert "gated_gen" not in result
        finally:
            reset_registry()

    @pytest.mark.asyncio
    async def test_feature_flag_enabled_runs(self, activities):
        """Generator with enabled feature flag runs normally."""
        reset_registry()
        os.environ["VOYANT_FEATURE_ACTIVE_GEN"] = "true"

        @register_plugin(
            name="active_gen",
            category=PluginCategory.REPORT,
            feature_flag="active_gen",
        )
        class ActiveGen(GeneratorPlugin):
            def generate(self, context):
                return {"ran": True}

        try:
            result = await activities.run_generators({})
            assert "active_gen" in result
            assert result["active_gen"]["ran"] is True
        finally:
            os.environ.pop("VOYANT_FEATURE_ACTIVE_GEN", None)
            reset_registry()

    @pytest.mark.asyncio
    async def test_generator_load_failure_skips(self, activities):
        """Plugin that fails to instantiate is skipped."""
        reset_registry()

        @register_plugin(
            name="broken_gen",
            category=PluginCategory.REPORT,
        )
        class BrokenGen(GeneratorPlugin):
            def __init__(self):
                raise RuntimeError("cannot init")

            def generate(self, context):
                return {}

        try:
            result = await activities.run_generators({})
            assert "broken_gen" not in result
        finally:
            reset_registry()

    @pytest.mark.asyncio
    async def test_multiple_generators(self, activities):
        """Multiple generators all run and return results."""
        reset_registry()

        @register_plugin(name="gen_a", category=PluginCategory.REPORT)
        class GenA(GeneratorPlugin):
            def generate(self, context):
                return {"name": "A"}

        @register_plugin(name="gen_b", category=PluginCategory.VISUALIZATION)
        class GenB(GeneratorPlugin):
            def generate(self, context):
                return {"name": "B"}

        try:
            result = await activities.run_generators({})
            assert "gen_a" in result
            assert "gen_b" in result
            assert result["gen_a"]["name"] == "A"
            assert result["gen_b"]["name"] == "B"
        finally:
            reset_registry()

    @pytest.mark.asyncio
    async def test_context_passed_to_generator(self, activities):
        """Workflow context is passed through to the generator."""
        reset_registry()

        @register_plugin(name="ctx_gen", category=PluginCategory.REPORT)
        class CtxGen(GeneratorPlugin):
            def generate(self, context):
                return {"received_keys": sorted(context.keys())}

        try:
            result = await activities.run_generators(
                {"job_id": "j1", "source_id": "s1", "data": [1, 2, 3]}
            )
            assert "job_id" in result["ctx_gen"]["received_keys"]
            assert "source_id" in result["ctx_gen"]["received_keys"]
        finally:
            reset_registry()
