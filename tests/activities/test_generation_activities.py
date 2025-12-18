
import pytest
from typing import Dict, Any
from temporalio.testing import ActivityEnvironment
from voyant.activities.generation_activities import GenerationActivities
from voyant.core.plugin_registry import (
    GeneratorPlugin, PluginCategory, register_plugin, reset_registry
)
from voyant.core.errors import ArtifactGenerationError
from temporalio import activity
from temporalio.exceptions import ApplicationError

# Real Plugin Implementation for Testing
class TestGenerator(GeneratorPlugin):
    def __init__(self, name="test_gen", should_fail=False):
        self._name = name
        self.should_fail = should_fail
        
    def get_name(self) -> str:
        return self._name

    def generate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        if self.should_fail:
            raise ValueError("Generator failed!")
        return {f"{self._name}_artifact": "real_data"}


@pytest.fixture
def clean_registry():
    reset_registry()
    yield
    reset_registry()

@pytest.mark.asyncio
async def test_run_generators_no_plugins(clean_registry):
    """Test running with no registered plugins (Real Logic)."""
    env = ActivityEnvironment()
    act = GenerationActivities()
    
    # Run activity in environment
    results = await env.run(act.run_generators, {})
    assert results == {}

@pytest.mark.asyncio
async def test_run_generators_success(clean_registry):
    """Test successful execution of a plugin (Real Registry)."""
    env = ActivityEnvironment()
    act = GenerationActivities()
    
    # 1. Register Plugin using real decorator
    @register_plugin(name="test_gen", category=PluginCategory.VISUALIZATION)
    class MyGen(TestGenerator):
        def __init__(self):
            super().__init__("test_gen")
            
    # 2. Run Activity
    results = await env.run(act.run_generators, {"job_id": "123"})
    
    assert "test_gen" in results
    assert results["test_gen"] == {"test_gen_artifact": "real_data"}

@pytest.mark.asyncio
async def test_run_generators_fail_extended(clean_registry):
    """Test that failed extended plugin does not stop pipeline (Real Logic)."""
    env = ActivityEnvironment()
    act = GenerationActivities()
    
    # Register failing extended plugin
    @register_plugin(name="fail_gen", category=PluginCategory.OTHER, is_core=False)
    class FailGen(TestGenerator):
        def __init__(self):
            super().__init__("fail_gen", should_fail=True)

    results = await env.run(act.run_generators, {})
    
    assert "fail_gen" not in results
    assert "_errors" in results
    assert len(results["_errors"]) == 1

@pytest.mark.asyncio
async def test_run_generators_fail_core(clean_registry):
    """Test that failed core plugin raises ApplicationError (Real Logic)."""
    env = ActivityEnvironment()
    act = GenerationActivities()
    
    # Register failing CORE plugin
    @register_plugin(name="core_fail", category=PluginCategory.REPORT, is_core=True)
    class CoreFailGen(TestGenerator):
        def __init__(self):
            super().__init__("core_fail", should_fail=True)

    # ActivityEnvironment raises the actual exception (ApplicationError)
    with pytest.raises(ApplicationError) as excinfo:
        await env.run(act.run_generators, {})
    
    assert "Core generator failed" in str(excinfo.value)
