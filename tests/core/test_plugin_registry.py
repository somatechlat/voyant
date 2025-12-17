"""
Test Plugin Registry

Verifies the "Platform of Platforms" pattern implementation.
"""
import pytest
from typing import Dict, Any

from voyant.core.plugin_registry import (
    PluginRegistry, register_plugin, GeneratorPlugin, 
    PluginCategory, get_generators, get_plugin
)

# Mock Plugin
@register_plugin(
    name="test_viz",
    category=PluginCategory.VISUALIZATION,
    description="Test Visualization",
    version="1.0.0",
    order=10
)
class TestVizGenerator(GeneratorPlugin):
    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"test_artifact": "generated"}

@register_plugin(
    name="test_report",
    category=PluginCategory.REPORT,
    description="Test Report",
    order=20
)
class TestReportGenerator(GeneratorPlugin):
    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return {"report": "done"}

@pytest.fixture(autouse=True)
def clean_registry():
    """Reset registry before each test."""
    PluginRegistry.get_instance().clear()
    # Re-register mocks
    PluginRegistry.get_instance().register(
        TestVizGenerator, "test_viz", PluginCategory.VISUALIZATION, 
        description="Test Visualization", order=10
    )
    PluginRegistry.get_instance().register(
        TestReportGenerator, "test_report", PluginCategory.REPORT, 
        description="Test Report", order=20
    )
    yield

def test_registry_singleton():
    reg1 = PluginRegistry.get_instance()
    reg2 = PluginRegistry.get_instance()
    assert reg1 is reg2

def test_get_generators():
    gens = get_generators()
    assert len(gens) == 2
    assert gens[0].name == "test_viz"  # Order 10
    assert gens[1].name == "test_report" # Order 20

def test_get_plugin_instance():
    plugin = get_plugin("test_viz")
    assert isinstance(plugin, TestVizGenerator)
    assert plugin.get_name() == "TestVizGenerator"

def test_get_plugin_category_filter():
    reg = PluginRegistry.get_instance()
    viz_plugins = reg.get_plugins_by_category(PluginCategory.VISUALIZATION)
    assert len(viz_plugins) == 1
    assert viz_plugins[0].name == "test_viz"

def test_plugin_execution():
    plugin = get_plugin("test_viz")
    result = plugin.generate({})
    assert result == {"test_artifact": "generated"}

def test_invalid_plugin_instantiation():
    plugin = get_plugin("non_existent")
    assert plugin is None
