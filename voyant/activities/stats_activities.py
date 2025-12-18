"""
Statistical Activities

Temporal activities for executing statistical operations via R-Bridge.
Adheres to Vibe Coding Rules: Real R integration via REngine.
"""
import logging
import pandas as pd
from typing import Any, Dict, List

from datetime import timedelta, datetime
from temporalio import activity

from voyant.core.r_bridge import REngine
from voyant.core.errors import ExternalServiceError, AnalysisError
from voyant.core.circuit_breaker import CircuitBreakerOpenError
from voyant.core.retry_config import EXTERNAL_SERVICE_RETRY, TIMEOUTS

from voyant.core.stats_primitives import RStatsPrimitives
from voyant.core.schema_evolution import track_schema, TableSchema, ColumnSchema

logger = logging.getLogger(__name__)

class StatsActivities:
    def __init__(self):
        self.r_engine = REngine()
        self.primitives = RStatsPrimitives(self.r_engine)

    @activity.defn(name="describe_distribution")
    def describe_distribution(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get descriptive stats for a column.
        
        Performance Engineer: 5 min timeout sufficient for simple stats
        QA Engineer: Retries on transient R-Engine failures
        """
        try:
            data = params.get("data", [])
            if not data:
                raise activity.ApplicationError(
                    "No data provided for distribution analysis",
                    non_retryable=True
                )
            # Infer and track schema if table_name provided
            if "table_name" in params:
                 # Simple schema inference from data snippet
                 columns = []
                 if isinstance(data, list) and len(data) > 0:
                     if isinstance(data[0], dict):
                         # Dict rows
                         for k, v in data[0].items():
                             dtype = type(v).__name__
                             columns.append(ColumnSchema(name=k, data_type=dtype))
                     else:
                         # Single list = single column
                         columns.append(ColumnSchema(name="value", data_type=type(data[0]).__name__))
                 
                 if columns:
                     track_schema(
                         table_name=params["table_name"],
                         schema=TableSchema(name=params["table_name"], columns=columns),
                         version=datetime.now().strftime("%Y.%m.%d-%H%M%S"), # Timestamp version
                         description="Auto-detected during distribution analysis"
                     )

            return self.primitives.describe_column(data)
        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open",
                non_retryable=True
            )

    @activity.defn(name="calculate_correlation")
    def calculate_correlation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate correlation matrix.
        
        PhD Analyst: Correlation computation is O(n²) but fast in R
        """
        try:
            data = params.get("data", {})
            method = params.get("method", "pearson")
            if not data:
                raise activity.ApplicationError(
                    "No data provided for correlation analysis",
                    non_retryable=True
                )
            return self.primitives.correlation_matrix(data, method)
        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open",
                non_retryable=True
            )

    @activity.defn(name="fit_distribution")
    def fit_distribution(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fit distribution to data.
        
        Performance Engineer: 10 min timeout - distribution fitting can be iterative
        """
        try:
            data = params.get("data", [])
            dist = params.get("dist", "normal")
            if not data:
                raise activity.ApplicationError(
                    "No data provided for distribution fitting",
                    non_retryable=True
                )
            return self.primitives.fit_distribution(data, dist)
        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open",
                non_retryable=True
            )

    @activity.defn(name="calculate_market_share")
    def calculate_market_share(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate market share metrics using R.
        
        Params:
            brand_data: List[Dict] or DataFrame-like dict
            competitor_data: List[Dict] or DataFrame-like dict
            metric: str (e.g., "revenue", "units")
        """
        activity.logger.info("Starting market share calculation in R")
        
        try:
            # 1. Prepare Data
            brand_df = pd.DataFrame(params.get("brand_data", []))
            comp_df = pd.DataFrame(params.get("competitor_data", []))
            
            if brand_df.empty or comp_df.empty:
                raise ValueError("Data cannot be empty for calculation")

            # 2. Send to R
            # Use specific variable names to avoid collision in shared R session (though Rserve usually forks)
            activity.heartbeat("Sending data to R")
            self.r_engine.assign("brand_df", brand_df)
            self.r_engine.assign("comp_df", comp_df)
            
            # 3. Calculate in R
            # R script to merge and calculate share
            r_script = """
            # Combine
            brand_df$type <- 'brand'
            comp_df$type <- 'competitor'
            all_df <- rbind(brand_df, comp_df)
            
            # Calculate Total Market
            total_market <- sum(all_df$value, na.rm=TRUE)
            
            # Calculate Shares
            brand_share <- sum(brand_df$value, na.rm=TRUE) / total_market
            
            # Return list
            result <- list(
                total_market = total_market,
                brand_share = brand_share,
                competitor_share = 1 - brand_share
            )
            """
            activity.heartbeat("Executing R script")
            result = self.r_engine.eval(r_script)
            
            # 4. Return result
            return dict(result)

        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open",
                non_retryable=True
            )
        except ValueError as e:
            # Input validation errors are not retryable
            raise activity.ApplicationError(
                f"Invalid input data: {e}",
                non_retryable=True
            )
        except Exception as e:
            activity.logger.error(f"R Calculation failed: {e}")
            raise ExternalServiceError("VYNT-6020", f"R Execution Error: {e}")

    @activity.defn(name="perform_hypothesis_test")
    def perform_hypothesis_test(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform t-test or ANOVA using R.
        """
        try:
            group_a = params.get("group_a", [])
            group_b = params.get("group_b", [])
            test_type = params.get("test_type", "t-test")
            
            self.r_engine.assign("group_a", group_a)
            self.r_engine.assign("group_b", group_b)
            
            if test_type == "t-test":
                res = self.r_engine.eval("t.test(group_a, group_b)")
                # Parse R htest object to dict (simplified)
                return {
                    "p_value": res["p.value"],
                    "statistic": res["statistic"],
                    "method": res["method"]
                }
            else:
                raise NotImplementedError(f"Test type {test_type} not supported yet")
                
        except CircuitBreakerOpenError:
            raise activity.ApplicationError(
                "R-Engine circuit breaker is open",
                non_retryable=True
            )
        except ValueError as e:
            raise activity.ApplicationError(
                f"Invalid test parameters: {e}",
                non_retryable=True
            )
        except NotImplementedError as e:
            # Feature not implemented - non-retryable
            raise activity.ApplicationError(str(e), non_retryable=True)
        except Exception as e:
            activity.logger.error(f"Hypothesis test failed: {e}")
            raise
