"""
Operational Workflows: Orchestrates Automated Data Operations.

This module defines a collection of Temporal workflows that automate various
operational tasks related to data management and analysis. These include
detecting anomalies, analyzing sentiment, fixing data quality issues, and
performing time series forecasting.

Each workflow encapsulates a specific business process, delegating individual
steps to specialized activities.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

# This context manager is necessary to allow importing non-workflow/activity
# modules within the workflow definition. It passes control to the Python
# import system directly, bypassing Temporal's default import handling.
with workflow.unsafe.imports_passed_through():
    from apps.worker.activities.operational_activities import OperationalActivities


@workflow.defn
class DetectAnomaliesWorkflow:
    """
    Temporal workflow for detecting anomalies in a given dataset.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the anomaly detection process.

        This workflow delegates the actual anomaly detection logic to the
        `OperationalActivities.detect_anomalies` activity.

        Args:
            params: A dictionary containing anomaly detection configuration:
                - `data` (List[Any]): The input data for anomaly detection.
                - `contamination` (float): The expected proportion of outliers in the data.

        Returns:
            A dictionary containing the results of the anomaly detection.
        """
        workflow.logger.info("DetectAnomaliesWorkflow started.")

        # Execute the activity to perform the actual anomaly detection.
        # This activity uses algorithms (e.g., Isolation Forest) to identify outliers.
        result = await workflow.execute_activity(
            OperationalActivities.detect_anomalies,
            {
                "data": params.get("data", []),
                "contamination": params.get("contamination", 0.1),
            },
            start_to_close_timeout=timedelta(minutes=5),
        )
        workflow.logger.info("DetectAnomaliesWorkflow completed.")
        return result


@workflow.defn
class AnalyzeSentimentWorkflow:
    """
    Temporal workflow for performing sentiment analysis on text data.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the sentiment analysis process on a list of text inputs.

        This workflow delegates the text processing to the
        `OperationalActivities.analyze_sentiment_batch` activity and
        then aggregates the results.

        Args:
            params: A dictionary containing sentiment analysis configuration:
                - `texts` (List[str]): A list of text strings to analyze.

        Returns:
            A dictionary containing the aggregate sentiment breakdown and detailed results.
        """
        workflow.logger.info("AnalyzeSentimentWorkflow started.")
        texts = params.get("texts", [])

        # Execute the activity to perform batch sentiment analysis on the provided texts.
        results = await workflow.execute_activity(
            OperationalActivities.analyze_sentiment_batch,
            {"texts": texts},
            start_to_close_timeout=timedelta(minutes=10),
        )

        # Aggregate the sentiment results for a high-level overview.
        positive = sum(1 for r in results if r["sentiment"] == "positive")
        negative = sum(1 for r in results if r["sentiment"] == "negative")
        neutral = sum(1 for r in results if r["sentiment"] == "neutral")

        workflow.logger.info(
            f"AnalyzeSentimentWorkflow completed with {len(results)} texts."
        )
        return {
            "total": len(results),
            "breakdown": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
            },
            "details": results,  # Detailed results from the activity
        }


@workflow.defn
class FixDataQualityWorkflow:
    """
    Temporal workflow for automatically fixing common data quality issues.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the data quality remediation process.

        This workflow identifies and automatically corrects issues such as
        missing values and outliers in a dataset by delegating to the
        `OperationalActivities.fix_data_quality` activity.

        Args:
            params: A dictionary containing data quality fixing configuration:
                - `data` (List[Dict[str, Any]]): The input data (list of dictionaries/rows).
                - `numeric_columns` (List[str]): Columns to apply numeric fixes to.
                - `categorical_columns` (List[str]): Columns to apply categorical fixes to.
                - `imputation_strategy` (str): Strategy for missing values (e.g., "median").
                - `outlier_strategy` (str): Strategy for outliers (e.g., "cap").
                - `outlier_threshold` (float): Threshold for outlier detection.

        Returns:
            A dictionary containing the results of the data quality fix, typically
            including a cleaned dataset and a report of changes.
        """
        workflow.logger.info("FixDataQualityWorkflow started.")
        data = params.get("data", [])
        numeric_columns = params.get("numeric_columns", [])
        categorical_columns = params.get("categorical_columns", [])

        # Execute the activity that performs the data cleaning and quality fixes.
        result = await workflow.execute_activity(
            OperationalActivities.fix_data_quality,
            {
                "data": data,
                "numeric_columns": numeric_columns,
                "categorical_columns": categorical_columns,
                "imputation_strategy": params.get("imputation_strategy", "median"),
                "outlier_strategy": params.get("outlier_strategy", "cap"),
                "outlier_threshold": params.get("outlier_threshold", 3.0),
            },
            start_to_close_timeout=timedelta(minutes=15),
        )
        workflow.logger.info("FixDataQualityWorkflow completed.")
        return result


@workflow.defn
class ForecastWorkflow:
    """
    Temporal workflow for performing time series forecasting.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the time series forecasting process.

        This workflow delegates the forecasting model execution to the
        `OperationalActivities.forecast_time_series` activity.

        Args:
            params: A dictionary containing forecasting configuration:
                - `values` (List[float]): Historical time series values.
                - `dates` (List[str]): Corresponding ISO 8601 date strings.
                - `periods` (int): Number of future periods to forecast.
                - `method` (str): Forecasting method (e.g., "ema", "prophet").
                - `confidence_level` (float): Confidence level for prediction intervals.

        Returns:
            A dictionary containing the forecast results, including predicted values
            and confidence intervals.
        """
        workflow.logger.info("ForecastWorkflow started.")
        values = params.get("values", [])
        dates = params.get("dates")

        # Execute the activity that performs the time series forecasting.
        result = await workflow.execute_activity(
            OperationalActivities.forecast_time_series,
            {
                "values": values,
                "dates": dates,
                "periods": params.get("periods", 7),
                "method": params.get("method", "ema"),
                "confidence_level": params.get("confidence_level", 0.95),
            },
            start_to_close_timeout=timedelta(minutes=5),
        )
        workflow.logger.info("ForecastWorkflow completed.")
        return result
