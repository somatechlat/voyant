import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from voyant.core.r_bridge import REngine
from voyant.core.stats import StatisticalEngine
from voyant.core.errors import ExternalServiceError, ValidationError

@pytest.fixture
def mock_r_engine():
    with patch("voyant.core.stats.REngine") as MockREngine:
        engine = MockREngine.return_value
        yield engine

def test_check_normality(mock_r_engine):
    # Setup
    stats = StatisticalEngine()
    df = pd.DataFrame({"val": [1, 2, 3, 4, 5]})
    
    # Mock R responses
    # eval() is called multiple times. 
    # 1. shapiro.test -> void
    # 2. res$statistic -> 0.98
    # 3. res$p.value -> 0.6
    # 4. res$p.value -> 0.6
    mock_r_engine.eval.side_effect = [None, 0.98, 0.6, 0.6]
    
    result = stats.check_normality(df, "val")
    
    # Verify basics
    assert result["test"] == "Shapiro-Wilk"
    assert result["is_normal"] is True
    assert result["p_value"] == 0.6
    
    # Verify R interaction
    mock_r_engine.assign.assert_called_once()  # Should assign data
    assert "shapiro.test" in mock_r_engine.eval.call_args_list[0][0][0]

def test_anova(mock_r_engine):
    stats = StatisticalEngine()
    df = pd.DataFrame({
        "val": [1, 2, 3, 10, 11, 12],
        "group": ["A", "A", "A", "B", "B", "B"]
    })
    
    # Mock responses
    # 1. aov() -> void
    # 2. summary() -> void
    # 3. F value -> 50.0
    # 4. Pr(>F) -> 0.001
    mock_r_engine.eval.side_effect = [None, None, 50.0, 0.001]
    
    result = stats.anova(df, "val", "group")
    
    assert result["significant"] is True
    assert result["f_statistic"] == 50.0

def test_t_test_validation():
    stats = StatisticalEngine()
    # 3 groups - invalid for t-test
    df = pd.DataFrame({
        "val": [1, 2, 3],
        "group": ["A", "B", "C"]
    })
    
    with pytest.raises(ValidationError):
        stats.t_test(df, "group", "val")
