import sys
import pytest
from unittest.mock import MagicMock, patch
from voyant.core.r_bridge import REngine
from voyant.core.errors import ExternalServiceError, SystemError

def test_r_bridge_dependency_check():
    """Test that it fails gracefully if pyRserve is missing."""
    # Remove pyRserve from sys.modules to simulate missing
    with patch.dict("sys.modules"):
        if "pyRserve" in sys.modules:
            del sys.modules["pyRserve"]
            
        engine = REngine()
        # Mock import to raise ImportError
        with patch("builtins.__import__", side_effect=ImportError):
            with pytest.raises(SystemError) as exc:
                engine._ensure_dependency()
        
        assert "pyRserve library not installed" in str(exc.value)

def test_r_bridge_connect_fail():
    """Test connection failure handling."""
    mock_pyRserve = MagicMock()
    mock_pyRserve.connect.side_effect = Exception("Connection refused")
    
    with patch.dict(sys.modules, {"pyRserve": mock_pyRserve}):
        engine = REngine()
        with pytest.raises(ExternalServiceError) as exc:
            engine.connect()
            
        assert "Failed to connect" in str(exc.value)

def test_r_bridge_eval():
    mock_conn = MagicMock()
    mock_conn.eval.return_value = 42
    
    mock_pyRserve = MagicMock()
    mock_pyRserve.connect.return_value = mock_conn
    
    with patch.dict(sys.modules, {"pyRserve": mock_pyRserve}):
        engine = REngine()
        result = engine.eval("1+1")
        
        assert result == 42
        mock_conn.eval.assert_called_with("1+1")
