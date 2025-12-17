import pytest
from unittest.mock import MagicMock, patch
import sys

# Mock temporalio before importing the module under test
mock_temporalio = MagicMock()
mock_activity = MagicMock()
mock_activity.defn = lambda x: x

class MockApplicationError(Exception):
    pass

mock_activity.ApplicationError = MockApplicationError
mock_temporalio.activity = mock_activity
sys.modules["temporalio"] = mock_temporalio
sys.modules["temporalio.activity"] = mock_activity

from temporalio import activity
from voyant.activities.generation_activities import GenerationActivities
from voyant.core.plugin_registry import (
    PluginRegistry, GeneratorPlugin, PluginCategory, register_plugin, reset_registry
)

# Mock Generator Plugin
class MockGenerator(GeneratorPlugin):
    def __init__(self, name="mock", should_fail=False):
        self._name = name
        self.should_fail = should_fail
        
    def get_name(self) -> str:
        return self._name

    def generate(self, context):
        if self.should_fail:
            raise ValueError("Generator failed!")
        return {f"{self._name}_artifact": "data"}

@pytest.fixture
def activity_env():
    """Setup clean registry and activity instance."""
    reset_registry()
    registry = PluginRegistry.get_instance()
    # verify registry is empty
    registry.clear()
    
    act_instance = GenerationActivities()
    return act_instance, registry

def test_run_generators_no_plugins(activity_env):
    """Test running with no registered plugins."""
    act, _ = activity_env
    
    # Mock temporal activity context
    with patch("temporalio.activity.logger") as mock_logger:
        results = act.run_generators({})
        assert results == {}
        # Should verify warning log

def test_run_generators_success(activity_env):
    """Test successful execution of a plugin."""
    act, registry = activity_env
    
    # Register a mock plugin
    @register_plugin(name="test_gen", category=PluginCategory.VISUALIZATION)
    class TestGen(MockGenerator):
        def __init__(self):
            super().__init__("test_gen")
            
    # Mock get_plugin to return our instance
    with patch("voyant.core.plugin_registry.get_plugin") as mock_get_plugin:
        mock_get_plugin.return_value = TestGen()
        
        results = act.run_generators({"job_id": "123"})
        
        assert "test_gen" in results
        assert results["test_gen"] == {"test_gen_artifact": "data"}

def test_run_generators_fail_extended(activity_env):
    """Test that failed extended plugin does not stop pipeline."""
    act, registry = activity_env
    
    # Register failing extended plugin
    @register_plugin(name="fail_gen", category=PluginCategory.OTHER, is_core=False)
    class FailGen(MockGenerator):
        def __init__(self):
            super().__init__("fail_gen", should_fail=True)

    with patch("voyant.core.plugin_registry.get_plugin") as mock_get_plugin:
        mock_get_plugin.return_value = FailGen()
        
        results = act.run_generators({})
        
        assert "fail_gen" not in results
        assert "_errors" in results
        assert len(results["_errors"]) == 1

def test_run_generators_fail_core(activity_env):
    """Test that failed core plugin raises ApplicationError."""
    act, registry = activity_env
    
    # Register failing CORE plugin
    @register_plugin(name="core_fail", category=PluginCategory.REPORT, is_core=True)
    class CoreFailGen(MockGenerator):
        def __init__(self):
            super().__init__("core_fail", should_fail=True)

    with patch("voyant.core.plugin_registry.get_plugin") as mock_get_plugin:
        mock_get_plugin.return_value = CoreFailGen()
    
        with pytest.raises(activity.ApplicationError) as excinfo:
            act.run_generators({})
        
        assert "Core generator failed" in str(excinfo.value)
