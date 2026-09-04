"""
Machine Learning Activities: Building Blocks for ML Workflows.

This module defines Temporal activities that execute various machine learning
and forecasting operations. These activities leverage specialized ML primitives
to perform tasks such as data clustering, model training for classification
and regression, and time series forecasting.
"""

import logging
from typing import Any

from temporalio import activity
from temporalio.exceptions import ApplicationError

from apps.analysis.lib.forecast_primitives import ForecastPrimitives
from apps.analysis.lib.ml_primitives import MLPrimitives
from apps.core.lib.errors import AnalysisError

logger = logging.getLogger(__name__)


class MLActivities:
    """
    A collection of Temporal activities related to machine learning and forecasting.

    These activities encapsulate the logic for common ML tasks, making them
    orchestrable within Temporal workflows.
    """

    def __init__(self):
        """
        Initializes the MLActivities with instances of MLPrimitives and ForecastPrimitives.
        """
        self.ml = MLPrimitives()
        self.forecast = ForecastPrimitives()

    @activity.defn(name="cluster_data")
    def cluster_data(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Performs data clustering using algorithms like K-Means.

        Args:
            params: A dictionary containing clustering parameters:
                - `data` (List[Dict[str, float]]): The input data for clustering.
                - `clusters` (int, optional): The number of clusters to form. Defaults to 3.

        Returns:
            A dictionary containing the clustering results, including cluster assignments
            and potentially quality metrics like silhouette score.

        Raises:
            ApplicationError: If no data is provided or if clustering fails.
        """
        try:
            data = params.get("data", [])
            n_clusters = params.get("clusters", 3)

            if not data:
                raise ApplicationError(
                    "No data provided for clustering activity.", non_retryable=True
                )

            activity.logger.info(f"Clustering {len(data)} records into {n_clusters} clusters.")
            return self.ml.cluster_kmeans(data, n_clusters)

        except AnalysisError as e:
            activity.logger.error(f"Clustering failed: {e}")
            raise ApplicationError(f"Data clustering failed: {e}", non_retryable=True) from e
        except Exception as e:
            activity.logger.error(f"An unexpected error occurred during clustering: {e}")
            raise ApplicationError(
                f"Data clustering failed due to unexpected error: {e}",
                non_retryable=False,
            ) from e

    @activity.defn(name="train_classifier_model")
    def train_classifier_model(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Trains a classification model (e.g., RandomForestClassifier).

        Args:
            params: A dictionary containing classification model training parameters:
                - `data` (List[Dict[str, Any]]): The input training data.
                - `target_col` (str): The name of the target (dependent) variable column.
                - `feature_cols` (List[str]): A list of feature (independent) variable column names.

        Returns:
            A dictionary containing the trained model's performance metrics and metadata.

        Raises:
            ApplicationError: If no data is provided or model training fails.
        """
        try:
            data = params.get("data", [])
            target = params.get("target_col", "target")
            features = params.get("feature_cols", [])

            if not data:
                raise ApplicationError(
                    "No data provided for classification model training.",
                    non_retryable=True,
                )

            activity.heartbeat(f"Training classification model on {len(data)} records.")
            activity.logger.info(
                f"Training classifier on {len(data)} records for target '{target}'."
            )
            return self.ml.train_classifier(data, target, features)

        except AnalysisError as e:
            activity.logger.error(f"Classification model training failed: {e}")
            raise ApplicationError(
                f"Classification model training failed: {e}", non_retryable=True
            ) from e
        except Exception as e:
            activity.logger.error(
                f"An unexpected error occurred during classification model training: {e}"
            )
            raise ApplicationError(
                f"Classification model training failed due to unexpected error: {e}",
                non_retryable=False,
            ) from e

    @activity.defn(name="forecast_time_series")
    def forecast_time_series(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Generates a time series forecast using algorithms like Prophet or EMA.

        Args:
            params: A dictionary containing forecasting parameters:
                - `dates` (List[str]): A list of ISO 8601 date strings for historical data.
                - `values` (List[float]): A list of corresponding numerical values for historical data.
                - `periods` (int, optional): The number of future periods to forecast. Defaults to 30.
                - `method` (str, optional): The forecasting method (e.g., "prophet", "ema").
                - `confidence_level` (float, optional): The confidence level for prediction intervals.

        Returns:
            A dictionary containing the forecast results, including predicted values
            and confidence intervals.

        Raises:
            ApplicationError: If dates/values are missing or forecasting fails.
        """
        try:
            dates = params.get("dates", [])
            values = params.get("values", [])
            periods = params.get("periods", 30)

            if not dates or not values:
                raise ApplicationError(
                    "Dates and values are required for time series forecasting.",
                    non_retryable=True,
                )

            activity.heartbeat(f"Forecasting {periods} periods.")
            activity.logger.info(
                f"Forecasting {periods} periods with method: {params.get('method', 'default')}."
            )
            return self.forecast.forecast_prophet(dates, values, periods)

        except AnalysisError as e:
            activity.logger.error(f"Time series forecasting failed: {e}")
            raise ApplicationError(
                f"Time series forecasting failed: {e}", non_retryable=True
            ) from e
        except Exception as e:
            activity.logger.error(
                f"An unexpected error occurred during time series forecasting: {e}"
            )
            raise ApplicationError(
                f"Time series forecasting failed due to unexpected error: {e}",
                non_retryable=False,
            ) from e

    @activity.defn(name="train_regression_model")
    def train_regression_model(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Trains a linear regression model.

        Args:
            params: A dictionary containing regression model training parameters:
                - `data` (List[Dict[str, float]]): The input training data.
                - `target_col` (str): The name of the target (dependent) variable column.
                - `feature_cols` (List[str]): A list of feature (independent) variable column names.

        Returns:
            A dictionary containing the trained model's coefficients, intercept, and metrics like R-squared.

        Raises:
            ApplicationError: If no data is provided or regression training fails.
        """
        try:
            data = params.get("data", [])
            target = params.get("target_col", "target")
            features = params.get("feature_cols", [])

            if not data:
                raise ApplicationError(
                    "No data provided for regression model training.",
                    non_retryable=True,
                )

            activity.heartbeat(f"Training regression model on {len(data)} records.")
            activity.logger.info(
                f"Training regression on {len(data)} records for target '{target}'."
            )
            return self.ml.train_regression(data, target, features)

        except AnalysisError as e:
            activity.logger.error(f"Regression model training failed: {e}")
            raise ApplicationError(
                f"Regression model training failed: {e}", non_retryable=True
            ) from e
        except Exception as e:
            activity.logger.error(
                f"An unexpected error occurred during regression model training: {e}"
            )
            raise ApplicationError(
                f"Regression model training failed due to unexpected error: {e}",
                non_retryable=False,
            ) from e
