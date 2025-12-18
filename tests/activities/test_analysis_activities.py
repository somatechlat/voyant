import sys
import pytest
from unittest.mock import MagicMock, patch

# Mock temporalio before import
mock_temporal = MagicMock()
mock_activity = MagicMock()
mock_activity.defn = lambda x: x

class ApplicationError(Exception): pass
mock_activity.ApplicationError = ApplicationError

mock_temporal.activity = mock_activity
sys.modules["temporalio"] = mock_temporal

from voyant.activities.analysis_activities import AnalysisActivities
from voyant.core.plugin_registry import PluginMetadata, PluginCategory, AnalyzerPlugin

# Mock Plugin Registry helpers
@patch("voyant.activities.analysis_activities.get_analyzers")
@patch("voyant.activities.analysis_activities.get_plugin")
def test_run_analyzers_success(mock_get_plugin, mock_get_analyzers):
    # Setup Metadata
    meta = PluginMetadata(
        name="test_analyzer",
        category=PluginCategory.STATISTICS,
        version="1.0",
        description="test",
        is_core=False
    )
    mock_get_analyzers.return_value = [meta]
    
    # Setup Plugin Instance
    mock_plugin = MagicMock(spec=AnalyzerPlugin)
    mock_plugin.analyze.return_value = {"status": "ok"}
    mock_get_plugin.return_value = mock_plugin
    
    activity = AnalysisActivities()
    
    params = {
        "data": [{"a": 1}],
        "context": {"global": 1}
    }
    
    results = activity.run_analyzers(params)
    
    assert "test_analyzer" in results
    assert results["test_analyzer"] == {"status": "ok"}
    
    # Verify calls
    mock_plugin.analyze.assert_called_once()
    args, _ = mock_plugin.analyze.call_args
    assert args[0] == [{"a": 1}]
    assert args[1]["global"] == 1

@patch("voyant.activities.analysis_activities.get_analyzers")
@patch("voyant.activities.analysis_activities.get_plugin")
def test_run_analyzers_filter(mock_get_plugin, mock_get_analyzers):
    meta1 = PluginMetadata(name="a1", category=PluginCategory.STATISTICS, version="1.0", description="", is_core=False)
    meta2 = PluginMetadata(name="a2", category=PluginCategory.STATISTICS, version="1.0", description="", is_core=False)
    mock_get_analyzers.return_value = [meta1, meta2]
    
    mock_plugin = MagicMock(spec=AnalyzerPlugin)
    mock_plugin.analyze.return_value = {}
    mock_get_plugin.return_value = mock_plugin
    
    activity = AnalysisActivities()
    
    # Run only a2
    results = activity.run_analyzers({"data": [], "analyzers": ["a2"]})
    
    assert "a2" in results
    assert "a1" not in results

@patch("voyant.activities.analysis_activities.get_analyzers")
@patch("voyant.activities.analysis_activities.get_plugin")
def test_core_failure_raises(mock_get_plugin, mock_get_analyzers):
    # Setup Core Metadata
    meta = PluginMetadata(
        name="core_analyzer",
        category=PluginCategory.SECURITY,
        version="1.0",
        description="core",
        is_core=True # CRITICAL
    )
    mock_get_analyzers.return_value = [meta]
    
    # Setup Plugin that fails
    mock_plugin = MagicMock()
    mock_plugin.analyze.side_effect = Exception("Boom")
    mock_get_plugin.return_value = mock_plugin
    
    activity = AnalysisActivities()
    
    # Should raise ApplicationError provided by temporal (mocked or real)
    # Since we imported temporalio.activity, it might be hard to catch the exact class if not running in worker
    # But usually it raises.
    # We'll rely on the fact exception propagates
    with pytest.raises(Exception) as exc:
        activity.run_analyzers({"data": []})
        
    assert "Core analyzer failed" in str(exc.value)
