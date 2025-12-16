"""
Machine Learning Activities

Temporal activities for executing ML and Forecasting operations.
Adheres to Vibe Coding Rules: Exposes real ML primitives.
"""
import logging
from typing import Any, Dict, List

from temporalio import activity

from voyant.core.ml_primitives import MLPrimitives
from voyant.core.forecast_primitives import ForecastPrimitives

logger = logging.getLogger(__name__)

class MLActivities:
    def __init__(self):
        self.ml = MLPrimitives()
        self.forecast = ForecastPrimitives()

    @activity.defn
    def cluster_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform clustering on data.
        Params:
            data: List[Dict[str, float]]
            clusters: int
        """
        data = params.get("data", [])
        n_clusters = params.get("clusters", 3)
        
        activity.logger.info(f"Clustering {len(data)} records into {n_clusters} clusters")
        return self.ml.cluster_kmeans(data, n_clusters)

    @activity.defn
    def train_classifier_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train a classification model.
        """
        data = params.get("data", [])
        target = params.get("target_col", "target")
        features = params.get("feature_cols", [])
        
        activity.logger.info(f"Training classifier on {len(data)} records for target '{target}'")
        return self.ml.train_classifier(data, target, features)

    @activity.defn
    def forecast_time_series(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate time series forecast.
        """
        dates = params.get("dates", [])
        values = params.get("values", [])
        periods = params.get("periods", 30)
        
        activity.logger.info(f"Forecasting {periods} periods with Prophet")
        return self.forecast.forecast_prophet(dates, values, periods)
    
    @activity.defn
    def train_regression_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train a linear regression model.
        """
        data = params.get("data", [])
        target = params.get("target_col", "target")
        features = params.get("feature_cols", [])
        
        activity.logger.info(f"Training regression on {len(data)} records for target '{target}'")
        return self.ml.train_regression(data, target, features)
