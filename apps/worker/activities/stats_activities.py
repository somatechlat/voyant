"""
Statistical Activities: Building Blocks for R-based Statistical Analysis.

This module defines Temporal activities that execute various statistical
operations by leveraging an R-Bridge (R-Engine). These activities enable
complex statistical analyses, such as descriptive statistics, correlation
analysis, distribution fitting, market share calculation, and hypothesis testing,
to be performed within Temporal workflows.
"""

import logging
from datetime import datetime
from typing import Any, Dict

import pandas as pd
from temporalio import activity

from apps.core.lib.circuit_breaker import CircuitBreakerOpenError
from apps.core.lib.errors import ExternalServiceError
from apps.core.lib.r_bridge import REngine
from apps.core.lib.schema_evolution import ColumnSchema, TableSchema, track_schema
from apps.core.lib.stats_primitives import RStatsPrimitives

logger = logging.getLogger(__name__)


class StatsActivities:
    """
    A collection of Temporal activities for executing statistical operations via an R-Engine.

    These activities provide an interface to R's powerful statistical capabilities,
    allowing complex analyses to be integrated into data processing workflows.
    """

    def __init__(self):
        """
        Initializes the StatsActivities with an R-Engine instance and statistical primitives.
        """
        self.r_engine = REngine()
        self.primitives = RStatsPrimitives(self.r_engine)

    @activity.defn(name="describe_distribution")
    def describe_distribution(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates descriptive statistics for a specified data distribution.

        This activity can also infer and track schema changes if a table name is provided.

        Args:
            params: A dictionary containing activity parameters:
                - `data` (List[Any]): The data (e.g., a list of numbers) for which to calculate statistics.
                - `table_name` (str, optional): The name of the table from which data was derived.
                                                If provided, attempts to infer and track schema.

        Returns:
            A dictionary containing descriptive statistics of the data.

        Raises:
            activity.ApplicationError: If no data is provided or R-Engine is unavailable.
        """
        try:
            data = params.get("data", [])
            if not data:
                raise activity.ApplicationError(
                    "No data provided for distribution analysis.", non_retryable=True
                )
            # Infer and track schema if table_name provided
            if "table_name" in params:
                # Simple schema inference from data snippet
                columns = []
                if isinstance(data, list) and len(data) > 0:
                    if isinstance(data[0], dict):
                        # Data is a list of dicts (rows)
                        for k, v in data[0].items():
                            dtype = type(v).__name__
                            columns.append(ColumnSchema(name=k, data_type=dtype))
                    else:
                        # Data is a single list, assume single column
                        columns.append(
                            ColumnSchema(name="value", data_type=type(data[0]).__name__)
                        )

                if columns:
                    # Track schema with a timestamp as version
                    track_schema(
                        table_name=params["table_name"],
                        schema=TableSchema(name=params["table_name"], columns=columns),
                        version=datetime.now().strftime("%Y.%m.%d-%H%M%S"),
                        description="Auto-detected during distribution analysis",
                    )

            return self.primitives.describe_column(data)
        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open. Service unavailable.",
                non_retryable=True,
            )
        except Exception as e:
            logger.error(f"Distribution analysis failed: {e}")
            raise activity.ApplicationError(
                f"Distribution analysis failed: {e}", non_retryable=False
            ) from e

    @activity.defn(name="calculate_correlation")
    def calculate_correlation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates the correlation matrix for a given dataset.

        Args:
            params: A dictionary containing activity parameters:
                - `data` (Dict[str, List[float]]): The input data as a dictionary of column names to lists of values.
                - `method` (str, optional): The correlation method (e.g., "pearson", "spearman"). Defaults to "pearson".

        Returns:
            A dictionary representing the correlation matrix.

        Raises:
            activity.ApplicationError: If no data is provided or R-Engine is unavailable.
        """
        try:
            data = params.get("data", {})
            method = params.get("method", "pearson")
            if not data:
                raise activity.ApplicationError(
                    "No data provided for correlation analysis.", non_retryable=True
                )
            return self.primitives.correlation_matrix(data, method)
        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open. Service unavailable.",
                non_retryable=True,
            )
        except Exception as e:
            logger.error(f"Correlation calculation failed: {e}")
            raise activity.ApplicationError(
                f"Correlation calculation failed: {e}", non_retryable=False
            ) from e

    @activity.defn(name="fit_distribution")
    def fit_distribution(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fits a statistical distribution to a given dataset.

        Args:
            params: A dictionary containing activity parameters:
                - `data` (List[float]): The input data to which to fit the distribution.
                - `dist` (str, optional): The name of the distribution to fit (e.g., "normal", "lognormal").
                                        Defaults to "normal".

        Returns:
            A dictionary containing parameters of the fitted distribution and goodness-of-fit metrics.

        Raises:
            activity.ApplicationError: If no data is provided or R-Engine is unavailable.
        """
        try:
            data = params.get("data", [])
            dist = params.get("dist", "normal")
            if not data:
                raise activity.ApplicationError(
                    "No data provided for distribution fitting.", non_retryable=True
                )
            return self.primitives.fit_distribution(data, dist)
        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open. Service unavailable.",
                non_retryable=True,
            )
        except Exception as e:
            logger.error(f"Distribution fitting failed: {e}")
            raise activity.ApplicationError(
                f"Distribution fitting failed: {e}", non_retryable=False
            ) from e

    @activity.defn(name="calculate_market_share")
    def calculate_market_share(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculates market share metrics based on provided brand and competitor data.

        This activity sends data to the R-Engine for statistical computation.

        Args:
            params: A dictionary containing activity parameters:
                - `brand_data` (List[Dict]): Data for the primary brand.
                - `competitor_data` (List[Dict]): Data for competitors.
                - `metric` (str): The metric to use for market share calculation (e.g., "revenue", "units").

        Returns:
            A dictionary containing the total market size, brand share, and competitor share.

        Raises:
            activity.ApplicationError: If input data is empty or R-Engine is unavailable.
            ExternalServiceError: If R-Engine execution encounters an unexpected error.
        """
        activity.logger.info("Starting market share calculation in R.")

        try:
            # 1. Prepare Data for R.
            # Convert incoming lists of dictionaries to Pandas DataFrames, then assign to R.
            brand_df = pd.DataFrame(params.get("brand_data", []))
            comp_df = pd.DataFrame(params.get("competitor_data", []))

            if brand_df.empty or comp_df.empty:
                raise ValueError(
                    "Brand or competitor data cannot be empty for market share calculation."
                )

            # 2. Send Data to R-Engine.
            activity.heartbeat("Sending data to R-Engine for market share calculation.")
            self.r_engine.assign("brand_df", brand_df)
            self.r_engine.assign("comp_df", comp_df)

            # 3. Execute R Script for Calculation.
            r_script = """
            # Combine brand and competitor dataframes, adding a 'type' column for identification.
            brand_df$type <- 'brand'
            comp_df$type <- 'competitor'
            all_df <- rbind(brand_df, comp_df)
            
            # Calculate the total market size based on the 'value' metric.
            total_market <- sum(all_df$value, na.rm=TRUE)
            
            # Calculate the primary brand's market share.
            brand_share <- sum(brand_df$value, na.rm=TRUE) / total_market
            
            # Aggregate results into a list (R's equivalent of a dictionary for returning).
            result <- list(
                total_market = total_market,
                brand_share = brand_share,
                competitor_share = 1 - brand_share
            )
            """
            activity.heartbeat("Executing R script for market share calculation.")
            result = self.r_engine.eval(r_script)

            # 4. Return the calculated market share metrics.
            return dict(result)

        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open. Service unavailable.",
                non_retryable=True,
            )
        except ValueError as e:
            raise activity.ApplicationError(
                f"Invalid input data for market share calculation: {e}",
                non_retryable=True,
            ) from e
        except Exception as e:
            logger.error(f"R-Engine market share calculation failed: {e}")
            raise ExternalServiceError("VYNT-6020", f"R Execution Error: {e}") from e

    @activity.defn(name="perform_hypothesis_test")
    def perform_hypothesis_test(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs a statistical hypothesis test (e.g., t-test) using the R-Engine.

        Args:
            params: A dictionary containing hypothesis test parameters:
                - `group_a` (List[float]): Numerical data for Group A.
                - `group_b` (List[float]): Numerical data for Group B.
                - `test_type` (str, optional): The type of statistical test to perform (e.g., "t-test").
                                             Currently, only "t-test" is fully supported.

        Returns:
            A dictionary containing the results of the hypothesis test, such as
            p-value, test statistic, and method used.

        Raises:
            activity.ApplicationError: If invalid test parameters are provided,
                                     or if the R-Engine is unavailable, or an
                                     unsupported test type is requested.
        """
        try:
            group_a = params.get("group_a", [])
            group_b = params.get("group_b", [])
            test_type = params.get("test_type", "t-test")

            # Send data to R-Engine.
            self.r_engine.assign("group_a", group_a)
            self.r_engine.assign("group_b", group_b)

            # Execute the specified hypothesis test in R.
            if test_type == "t-test":
                activity.logger.info("Executing t-test in R.")
                res = self.r_engine.eval("t.test(group_a, group_b)")
                # Parse and return relevant fields from the R 'htest' object.
                return {
                    "p_value": res["p.value"],
                    "statistic": res["statistic"],
                    "method": res["method"],
                }
            else:
                raise ValueError(
                    f"Hypothesis test type '{test_type}' is not supported."
                )

        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open. Service unavailable.",
                non_retryable=True,
            )
        except ValueError as e:
            raise activity.ApplicationError(
                f"Invalid test parameters: {e}", non_retryable=True
            ) from e
        except Exception as e:
            logger.error(f"Hypothesis test failed: {e}")
            raise activity.ApplicationError(
                f"Hypothesis test failed due to unexpected error: {e}",
                non_retryable=False,
            ) from e
