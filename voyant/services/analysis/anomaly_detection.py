"""
Anomaly Detection Service

Implements statistical outlier detection using Isolation Forest.
Registered as an AnalyzerPlugin in the Voyant platform.

Personas:
- PhD Developer: Unsupervised learning (Isolation Forest)
- Analyst: Outlier scoring and visualization
- Performance: Sampled execution for large datasets
"""
from typing import Any, Dict, List, Optional
import logging
import json
import pandas as pd
import numpy as np

# Try importing sklearn, handle case if missing (though required for ML)
try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from voyant.core.plugin_registry import register_plugin, AnalyzerPlugin, PluginCategory
from voyant.core.errors import AnalysisError

logger = logging.getLogger(__name__)

@register_plugin(
    name="anomaly_detector",
    category=PluginCategory.STATISTICS,
    version="1.0.0",
    description="Detects statistical outliers using Isolation Forest",
    is_core=False
)
class AnomalyDetector(AnalyzerPlugin):
    """
    detects anomalies in numerical data using Isolation Forest.
    """
    
    def analyze(self, data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze numerical data for anomalies.
        
        Args:
            data: pandas.DataFrame containing numerical columns or List[Dict]
            context: configuration (contamination, features)
            
        Returns:
            Dict containing:
            - anomalies: List of anomalous records
            - stats: Summary statistics
            - visualization: Plotly-ready JSON
        """
        if not SKLEARN_AVAILABLE:
            raise AnalysisError("VYNT-ML-001", "scikit-learn is required for anomaly detection")
            
        # 1. Data Prep
        df = self._to_dataframe(data)
        if df.empty:
            return {"status": "skipped", "reason": "empty_data"}
            
        # Select features
        features = context.get("features")
        if not features:
            # Auto-select numeric
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            features = numeric_cols
            
        if not features:
            logger.warning("No numeric features found for anomaly detection")
            return {"status": "skipped", "reason": "no_numeric_features"}
            
        X = df[features].dropna()
        if len(X) < 10:
             return {"status": "skipped", "reason": "insufficient_data", "count": len(X)}

        # 2. Model Training
        # Contamination: 'auto' or float (0.0 to 0.5)
        contamination = context.get("contamination", "auto")
        model = IsolationForest(contamination=contamination, random_state=42, n_jobs=-1)
        
        model.fit(X)
        
        # 3. Prediction
        # -1 for outliers, 1 for inliers
        predictions = model.predict(X)
        scores = model.decision_function(X) # lower is more anomalous
        
        # 4. Result Formatting
        X = X.copy()
        X['anomaly_score'] = scores
        X['is_anomaly'] = predictions == -1
        
        anomalies = X[X['is_anomaly']]
        
        # Sort by severity (lowest score)
        anomalies = anomalies.sort_values('anomaly_score', ascending=True)
        
        result = {
            "status": "success",
            "total_rows": len(df),
            "analyzed_rows": len(X),
            "anomaly_count": len(anomalies),
            "anomaly_percentage": float(len(anomalies) / len(X)),
            "features_used": features,
            "top_anomalies": anomalies.head(20).to_dict(orient="records"),
            "visualization": self._generate_plot_spec(X, features)
        }
        
        return result
        
    def _to_dataframe(self, data: Any) -> pd.DataFrame:
        """Convert input to DataFrame safely."""
        if isinstance(data, pd.DataFrame):
            return data
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
             # Handle columnar dict
             return pd.DataFrame(data)
        raise AnalysisError("VYNT-DATA-002", f"Unsupported data type: {type(data)}")

    def _generate_plot_spec(self, df: pd.DataFrame, features: List[str]) -> Dict[str, Any]:
        """Generate a Scatter plot metadata for outliers."""
        # Simple scatter of first 2 features (or Index vs Feature if 1 dim)
        if len(features) >= 2:
            x_col, y_col = features[0], features[1]
        else:
            x_col = df.index.name or "index"
            y_col = features[0]
            df = df.reset_index(names=x_col)
            
        return {
            "type": "scatter",
            "x": x_col,
            "y": y_col,
            "data": {
                "inliers": df[~df['is_anomaly']][[x_col, y_col]].to_dict(orient="list"),
                "outliers": df[df['is_anomaly']][[x_col, y_col]].to_dict(orient="list")
            },
            "title": f"Anomaly Usage: {y_col} vs {x_col}"
        }
