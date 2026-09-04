"""
Unit tests for apps.core.lib.plugin_registry — Plugin registry and decorators.

Real singleton registry. No mocks.
"""

import pytest

from apps.core.lib.plugin_registry import (
    AnalyzerPlugin,
    GeneratorPlugin,
    PluginCategory,
    PluginMetadata,
    PluginRegistry,
    VoyantPlugin,
    get_analyzers,
    get_generators,
    get_plugin,
    register_plugin,
    reset_registry,
)


@pytest.fixture(autouse=True)
def clean_registry():
    reset_registry()
    yield
    reset_registry()


# =============================================================================
# Test Plugin Classes
# =============================================================================


class SampleGenerator(GeneratorPlugin):
    def generate(self, context):
        return {"output": "generated"}


class SampleAnalyzer(AnalyzerPlugin):
    def analyze(self, data, context):
        return {"result": "analyzed"}


class SamplePlugin(VoyantPlugin):
    pass


# =============================================================================
# PluginRegistry Tests
# =============================================================================


class TestPluginRegistry:
    def test_singleton(self):
        r1 = PluginRegistry.get_instance()
        r2 = PluginRegistry.get_instance()
        assert r1 is r2

    def test_cannot_reinstantiate(self):
        with pytest.raises(RuntimeError, match="singleton"):
            PluginRegistry()

    def test_register_and_get_instance(self):
        registry = PluginRegistry.get_instance()
        registry.register(
            cls_obj=SampleGenerator,
            name="test_gen",
            category=PluginCategory.VISUALIZATION,
            version="1.0.0",
            description="Test generator",
        )
        instance = registry.get_plugin_instance("test_gen")
        assert instance is not None
        assert isinstance(instance, SampleGenerator)

    def test_get_nonexistent_plugin(self):
        registry = PluginRegistry.get_instance()
        assert registry.get_plugin_instance("nonexistent") is None

    def test_register_overwrite(self):
        registry = PluginRegistry.get_instance()
        registry.register(SampleGenerator, "test", PluginCategory.VISUALIZATION)
        registry.register(SampleAnalyzer, "test", PluginCategory.DATA_QUALITY)
        meta = registry.get_all_metadata()
        assert len(meta) == 1
        assert meta[0].category == PluginCategory.DATA_QUALITY

    def test_get_all_metadata_sorted_by_order(self):
        registry = PluginRegistry.get_instance()
        registry.register(SampleGenerator, "b", PluginCategory.VISUALIZATION, order=200)
        registry.register(SampleAnalyzer, "a", PluginCategory.DATA_QUALITY, order=10)
        meta = registry.get_all_metadata()
        assert meta[0].name == "a"
        assert meta[1].name == "b"

    def test_get_plugins_by_category(self):
        registry = PluginRegistry.get_instance()
        registry.register(SampleGenerator, "gen", PluginCategory.VISUALIZATION)
        registry.register(SampleAnalyzer, "ana", PluginCategory.DATA_QUALITY)
        registry.register(SamplePlugin, "other", PluginCategory.OTHER)

        viz = registry.get_plugins_by_category(PluginCategory.VISUALIZATION)
        assert len(viz) == 1
        assert viz[0].name == "gen"

    def test_metadata_fields(self):
        registry = PluginRegistry.get_instance()
        registry.register(
            SampleGenerator, "test", PluginCategory.REPORT,
            version="2.0.0", description="desc", is_core=True,
            feature_flag="FF_TEST", order=50,
        )
        meta = registry.get_all_metadata()
        assert len(meta) == 1
        m = meta[0]
        assert m.name == "test"
        assert m.category == PluginCategory.REPORT
        assert m.version == "2.0.0"
        assert m.description == "desc"
        assert m.is_core is True
        assert m.feature_flag == "FF_TEST"
        assert m.order == 50

    def test_clear(self):
        registry = PluginRegistry.get_instance()
        registry.register(SampleGenerator, "test", PluginCategory.VISUALIZATION)
        assert len(registry.get_all_metadata()) == 1
        registry.clear()
        assert len(registry.get_all_metadata()) == 0

    def test_instance_caching(self):
        registry = PluginRegistry.get_instance()
        registry.register(SampleGenerator, "test", PluginCategory.VISUALIZATION)
        i1 = registry.get_plugin_instance("test")
        i2 = registry.get_plugin_instance("test")
        assert i1 is i2

    def test_re_register_clears_cached_instance(self):
        registry = PluginRegistry.get_instance()
        registry.register(SampleGenerator, "test", PluginCategory.VISUALIZATION)
        i1 = registry.get_plugin_instance("test")
        registry.register(SampleGenerator, "test", PluginCategory.VISUALIZATION)
        i2 = registry.get_plugin_instance("test")
        # Should be a new instance after re-registration
        assert i1 is not i2


# =============================================================================
# Decorator Tests
# =============================================================================


class TestRegisterPluginDecorator:
    def test_decorator_registers_plugin(self):
        @register_plugin(name="dec_gen", category=PluginCategory.VISUALIZATION)
        class DecGenerator(GeneratorPlugin):
            def generate(self, context):
                return {}

        instance = get_plugin("dec_gen")
        assert instance is not None
        assert isinstance(instance, DecGenerator)

    def test_decorator_rejects_non_subclass(self):
        with pytest.raises(TypeError, match="must inherit from VoyantPlugin"):
            @register_plugin(name="bad", category=PluginCategory.OTHER)
            class BadPlugin:
                pass

    def test_decorator_with_all_params(self):
        @register_plugin(
            name="full_plugin",
            category=PluginCategory.SECURITY,
            version="3.0.0",
            description="Full params",
            is_core=True,
            feature_flag="FF_FULL",
            order=1,
        )
        class FullPlugin(VoyantPlugin):
            pass

        registry = PluginRegistry.get_instance()
        meta = registry.get_all_metadata()
        assert len(meta) == 1
        m = meta[0]
        assert m.name == "full_plugin"
        assert m.version == "3.0.0"
        assert m.is_core is True


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestHelperFunctions:
    def test_get_generators(self):
        @register_plugin(name="gen1", category=PluginCategory.VISUALIZATION)
        class Gen1(GeneratorPlugin):
            def generate(self, context):
                return {}

        @register_plugin(name="ana1", category=PluginCategory.DATA_QUALITY)
        class Ana1(AnalyzerPlugin):
            def analyze(self, data, context):
                return {}

        generators = get_generators()
        assert len(generators) == 1
        assert generators[0].name == "gen1"

    def test_get_analyzers(self):
        @register_plugin(name="gen1", category=PluginCategory.VISUALIZATION)
        class Gen1(GeneratorPlugin):
            def generate(self, context):
                return {}

        @register_plugin(name="ana1", category=PluginCategory.DATA_QUALITY)
        class Ana1(AnalyzerPlugin):
            def analyze(self, data, context):
                return {}

        analyzers = get_analyzers()
        assert len(analyzers) == 1
        assert analyzers[0].name == "ana1"

    def test_get_plugin(self):
        @register_plugin(name="myplug", category=PluginCategory.OTHER)
        class MyPlug(VoyantPlugin):
            pass

        instance = get_plugin("myplug")
        assert instance is not None

    def test_get_plugin_nonexistent(self):
        assert get_plugin("nonexistent") is None

    def test_reset_registry(self):
        @register_plugin(name="temp", category=PluginCategory.OTHER)
        class Temp(VoyantPlugin):
            pass

        assert get_plugin("temp") is not None
        reset_registry()
        assert get_plugin("temp") is None


# =============================================================================
# PluginCategory Tests
# =============================================================================


class TestPluginCategory:
    def test_all_values(self):
        assert PluginCategory.VISUALIZATION == "visualization"
        assert PluginCategory.REPORT == "report"
        assert PluginCategory.DATA_QUALITY == "data_quality"
        assert PluginCategory.STATISTICS == "statistics"
        assert PluginCategory.SECURITY == "security"
        assert PluginCategory.OTHER == "other"


# =============================================================================
# PluginMetadata Tests
# =============================================================================


class TestPluginMetadata:
    def test_dataclass(self):
        meta = PluginMetadata(
            name="test",
            category=PluginCategory.VISUALIZATION,
            version="1.0.0",
            description="desc",
            is_core=False,
        )
        assert meta.name == "test"
        assert meta.order == 100
        assert meta.feature_flag is None
