"""
Operational Activities: Building Blocks for Automated Data Operations.

This module defines Temporal activities that execute various operational tasks
related to data management and analysis. These activities leverage specialized
primitives for data cleaning, anomaly detection, sentiment analysis, and time
series forecasting.

They are designed to be integrated into workflows that automate routine data
quality checks, anomaly monitoring, and predictive analytics.
"""

import logging
from typing import Any, Dict, List

from temporalio import activity

from apps.analysis.lib.cleaning_primitives import DataCleaningPrimitives
from apps.analysis.lib.forecast_primitives import PROPHET_AVAILABLE, ForecastPrimitives
from apps.analysis.lib.forecasting import forecast
from apps.analysis.lib.ml_primitives import MLPrimitives
from apps.analysis.lib.nlp_primitives import NLPPrimitives

logger = logging.getLogger(__name__)


class OperationalActivities:
    """
    A collection of Temporal activities for executing operational data tasks.

    These activities encapsulate the logic for various data-centric operations,
    making them orchestrable within Temporal workflows.
    """

    def __init__(self):
        """
        Initializes the OperationalActivities with instances of various primitive classes.
        """
        self.ml = MLPrimitives()
        self.nlp = NLPPrimitives()
        self.cleaner = DataCleaningPrimitives()
        # This instance is used for Prophet-based forecasting.
        self.prophet = ForecastPrimitives()

    @activity.defn(name="clean_data")
    def clean_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs data cleaning operations on a dataset.

        Args:
            params: A dictionary containing cleaning parameters:
                - `data` (List[Dict]): The raw input data (list of dictionaries).
                - `strategies` (Dict): A dictionary specifying cleaning strategies
                                     (e.g., for missing values, outliers).

        Returns:
            A dictionary containing the cleaned data and a report of cleaning actions.
        """
        data = params.get("data", [])
        strategies = params.get("strategies", {})

        activity.logger.info(
            f"Cleaning {len(data)} records with strategies: {strategies}."
        )
        # Delegates to the DataCleaningPrimitives for the actual cleaning logic.
        return self.cleaner.clean_dataset(data, strategies)

    @activity.defn(name="detect_anomalies")
    def detect_anomalies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detects anomalies within a given dataset.

        Args:
            params: A dictionary containing anomaly detection parameters:
                - `data` (List[Dict]): The input data for anomaly detection.
                - `contamination` (float, optional): The expected proportion of outliers in the data. Defaults to 0.05.

        Returns:
            A dictionary containing the results of the anomaly detection,
            typically including anomaly scores and labels for each data point.
        """
        data = params.get("data", [])
        contamination = params.get("contamination", 0.05)

        activity.logger.info(
            f"Detecting anomalies in {len(data)} records with contamination={contamination}."
        )
        # Delegates to MLPrimitives for the actual anomaly detection algorithm.
        return self.ml.detect_anomalies(data, contamination)

    @activity.defn(name="analyze_sentiment_batch")
    def analyze_sentiment_batch(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyzes the sentiment of a batch of text inputs.

        Args:
            params: A dictionary containing sentiment analysis parameters:
                - `texts` (List[str]): A list of text strings to analyze.

        Returns:
            A list of dictionaries, each containing the sentiment analysis
            result for a corresponding text input.
        """
        texts = params.get("texts", [])
        activity.logger.info(f"Analyzing sentiment for {len(texts)} texts.")
        # Delegates to NLPPrimitives for the actual sentiment analysis logic.
        return self.nlp.analyze_sentiment(texts)

    @activity.defn(name="fix_data_quality")
    def fix_data_quality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs automatic fixes for common data quality issues in a dataset.

        This activity handles:
        - Missing value imputation using statistical methods.
        - Outlier detection and treatment (e.g., removal, capping).
        - Provides a report summarizing the quality improvements.

        Args:
            params: A dictionary containing data quality fixing parameters:
                - `data` (List[Dict]): The records to clean.
                - `numeric_columns` (List[str]): Names of numeric columns.
                - `categorical_columns` (List[str]): Names of categorical columns.
                - `imputation_strategy` (str, optional): Strategy for missing values
                                                         ("mean", "median", "mode", "ffill").
                - `outlier_strategy` (str, optional): Strategy for outliers ("remove", "cap", "winsorize").
                - `outlier_threshold` (float, optional): Threshold for outlier detection (e.g., Z-score threshold).

        Returns:
            A dictionary containing the `cleaned_data` (List[Dict]) and a
            `quality_report` summarizing the changes made.

        It leverages statistical methods for imputation and outlier treatment, and is
        optimized for efficient in-memory operations on datasets.
        """
        data = params.get("data", [])

        # Configure cleaning strategies based on parameters.
        strategies = {
            "missing_values": params.get("imputation_strategy", "median"),
            "outliers": params.get("outlier_strategy", "cap"),
            "outlier_threshold": params.get("outlier_threshold", 3.0),
            "numeric_columns": params.get("numeric_columns", []),
            "categorical_columns": params.get("categorical_columns", []),
        }

        activity.logger.info(
            f"Fixing data quality for {len(data)} records using strategies: {strategies}."
        )

        # Delegates to the DataCleaningPrimitives for the actual quality fixing logic.
        result = self.cleaner.clean_dataset(data, strategies)

        # The primitive returns a detailed report. We map some keys to match
        # an expected external interface contract for data quality reports.
        report_from_primitive = result["report"]

        # Calculate quality scores based on data completeness
        original_rows = len(data)
        cleaned_rows = report_from_primitive.get("final_row_count", 0)
        missing_before = report_from_primitive.get("missing_values_before", 0)
        missing_after = report_from_primitive.get("missing_values_after", 0)

        # Quality score calculation:
        # - If no data, score is 0.0
        # - Otherwise, score = (total_cells - missing_cells) / total_cells
        if original_rows == 0:
            quality_score_before = 0.0
            quality_score_after = 0.0
        else:
            # Estimate total cells (we need to know column count)
            # For now, use a simple heuristic based on missing values
            numeric_cols = strategies.get("numeric_columns", [])
            categorical_cols = strategies.get("categorical_columns", [])
            total_cols = len(numeric_cols) + len(categorical_cols)

            if total_cols == 0 and data:
                # Auto-detect from first row
                total_cols = len(data[0].keys()) if data else 0

            total_cells_before = (
                original_rows * total_cols if total_cols > 0 else original_rows
            )
            total_cells_after = (
                cleaned_rows * total_cols if total_cols > 0 else cleaned_rows
            )

            quality_score_before = (
                (total_cells_before - missing_before) / total_cells_before
                if total_cells_before > 0
                else 1.0
            )
            quality_score_after = (
                (total_cells_after - missing_after) / total_cells_after
                if total_cells_after > 0
                else 1.0
            )

        return {
            "cleaned_data": result["cleaned_data"],
            "quality_report": {
                "original_rows": original_rows,
                "cleaned_rows": cleaned_rows,
                "missing_value_fixes": missing_before - missing_after,
                "outliers_treated": report_from_primitive.get("outliers_treated", 0),
                "quality_score_before": quality_score_before,
                "quality_score_after": quality_score_after,
                "improvement": quality_score_after - quality_score_before,
            },
        }

    @activity.defn(name="forecast_time_series")
    def forecast_time_series(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a time series forecast using various methods.

        Args:
            params: A dictionary containing forecasting parameters:
                - `values` (List[float]): Historical time series values.
                - `dates` (Optional[List[str]]): Corresponding ISO 8601 date strings.
                - `periods` (int, optional): Number of future periods to forecast. Defaults to 7.
                - `method` (str, optional): Forecasting method ("ema", "linear", "prophet"). Defaults to "ema".
                - `confidence_level` (float, optional): Confidence level for prediction intervals. Defaults to 0.95.

        Returns:
            A dictionary containing the forecast results, including predicted values
            and confidence intervals.

        Raises:
            activity.ApplicationError: If no values are provided, or if Prophet is
                                     requested but not available, or forecasting fails.
        """
        values = params.get("values", [])
        dates = params.get("dates")
        periods = params.get("periods", 7)
        method = params.get("method", "ema")
        confidence = params.get("confidence_level", 0.95)

        activity.logger.info(f"Forecasting {periods} periods using method: '{method}'.")

        if not values:
            raise activity.ApplicationError(
                "No values provided for forecasting activity.", non_retryable=True
            )

        try:
            # Handle Prophet-based forecasting if requested and available.
            if method == "prophet":
                if not PROPHET_AVAILABLE:
                    # Production Rule: Real implementations. If Prophet is explicitly requested
                    # and not available, it's a hard failure to avoid unexpected behavior.
                    raise RuntimeError(
                        "Prophet library is not available in this environment."
                    )
                if not dates:
                    raise RuntimeError("Dates are required for Prophet forecasting.")

                return self.prophet.forecast_prophet(
                    dates=dates, values=values, periods=periods
                )

            # Use native forecasting methods (EMA, Linear, etc.).
            result = forecast(
                values=values,
                periods=periods,
                method=method,
                confidence_level=confidence,
                dates=dates,
            )

            return result.to_dict()

        except Exception as e:
            activity.logger.error(
                f"Forecasting activity failed with method '{method}': {e}"
            )
            raise activity.ApplicationError(
                f"Forecasting failed: {e}", non_retryable=True
            ) from e
