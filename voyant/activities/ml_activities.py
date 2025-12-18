"""
Machine Learning Activities

Temporal activities for executing ML and Forecasting operations.
Adheres to Vibe Coding Rules: Exposes real ML primitives.
"""
import logging
from typing import Any, Dict, List
from datetime import timedelta

from temporalio import activity

from voyant.core.ml_primitives import MLPrimitives
from voyant.core.forecast_primitives import ForecastPrimitives
from voyant.core.retry_config import DATA_PROCESSING_RETRY, TIMEOUTS
from voyant.core.errors import AnalysisError

logger = logging.getLogger(__name__)

class MLActivities:
    def __init__(self):
        self.ml = MLPrimitives()
        self.forecast = ForecastPrimitives()

    @activity.defn(name="cluster_data")
    def cluster_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform clustering on data.
        
        Params:
            data: List[Dict[str, float]]
            clusters: int
            
        Performance Engineer: 10 min timeout for large datasets
        PhD Analyst: K-means is O(n*k*i) where i=iterations
        """
        try:
            data = params.get("data", [])
            n_clusters = params.get("clusters", 3)
            
            if not data:
                raise activity.ApplicationError(
                    "No data provided for clustering",
                    non_retryable=True
                )
            
            activity.logger.info(f"Clustering {len(data)} records into {n_clusters} clusters")
            return self.ml.cluster_kmeans(data, n_clusters)
            
        except AnalysisError as e:
            activity.logger.error(f"Clustering failed: {e}")
            raise activity.ApplicationError(
                f"Clustering error: {e}",
                non_retryable=True
            )

    @activity.defn(name="train_classifier_model")
    def train_classifier_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train a classification model.
        
        QA Engineer: Heartbeat every minute during training
        """
        try:
            data = params.get("data", [])
            target = params.get("target_col", "target")
            features = params.get("feature_cols", [])
            
            if not data:
                raise activity.ApplicationError(
                    "No data provided for model training",
                    non_retryable=True
                )
            
            activity.heartbeat(f"Training on {len(data)} records")
            activity.logger.info(f"Training classifier on {len(data)} records for target '{target}'")
            return self.ml.train_classifier(data, target, features)
            
        except AnalysisError as e:
            raise activity.ApplicationError(
                f"Model training failed: {e}",
                non_retryable=True
            )

    @activity.defn(name="forecast_time_series")
    def forecast_time_series(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate time series forecast.
        
        Performance Engineer: 15 min timeout for Prophet (can be slow)
        """
        try:
            dates = params.get("dates", [])
            values = params.get("values", [])
            periods = params.get("periods", 30)
            
            if not dates or not values:
                raise activity.ApplicationError(
                    "Dates and values required for forecasting",
                    non_retryable=True
                )
            
            activity.heartbeat(f"Forecasting {periods} periods")
            activity.logger.info(f"Forecasting {periods} periods with Prophet")
            return self.forecast.forecast_prophet(dates, values, periods)
            
        except AnalysisError as e:
            raise activity.ApplicationError(
                f"Forecasting failed: {e}",
                non_retryable=True
            )
    
    @activity.defn(name="train_regression_model")
    def train_regression_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train a linear regression model.
        
        PhD Developer: Proper error handling for invalid inputs
        """
        try:
            data = params.get("data", [])
            target = params.get("target_col", "target")
            features = params.get("feature_cols", [])
            
            if not data:
                raise activity.ApplicationError(
                    "No data provided for regression training",
                    non_retryable=True
                )
            
            activity.heartbeat(f"Training on {len(data)} records")
            activity.logger.info(f"Training regression on {len(data)} records for target '{target}'")
            return self.ml.train_regression(data, target, features)
            
        except AnalysisError as e:
            raise activity.ApplicationError(
                f"Regression training failed: {e}",
                non_retryable=True
            )
