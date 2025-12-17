"""
Operational Activities

Temporal activities for Operational Presets (Anomalies, Sentiment, etc.).
"""
import logging
from typing import Any, Dict, List

from temporalio import activity

from voyant.core.ml_primitives import MLPrimitives
from voyant.core.nlp_primitives import NLPPrimitives
from voyant.core.cleaning_primitives import DataCleaningPrimitives
from voyant.core.forecasting import forecast, get_available_methods
from voyant.core.forecast_primitives import ForecastPrimitives, PROPHET_AVAILABLE
from voyant.core.retry_config import DATA_PROCESSING_RETRY, TIMEOUTS

logger = logging.getLogger(__name__)

class OperationalActivities:
    def __init__(self):
        self.ml = MLPrimitives()
        self.nlp = NLPPrimitives()
        self.cleaner = DataCleaningPrimitives()
        self.prophet = ForecastPrimitives()

    @activity.defn(
        name="clean_data",
        start_to_close_timeout=TIMEOUTS["operational_short"],
        retry_policy=DATA_PROCESSING_RETRY
    )
    def clean_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean dataset activity.
        """
        data = params.get("data", [])
        strategies = params.get("strategies", {})
        
        activity.logger.info(f"Cleaning {len(data)} records")
        return self.cleaner.clean_dataset(data, strategies)

    @activity.defn(
        name="detect_anomalies",
        start_to_close_timeout=TIMEOUTS["operational_short"],
        retry_policy=DATA_PROCESSING_RETRY
    )
    def detect_anomalies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect anomalies in data.
        """
        data = params.get("data", [])
        contamination = params.get("contamination", 0.05)
        
        activity.logger.info(f"Detecting anomalies in {len(data)} records")
        return self.ml.detect_anomalies(data, contamination)

    @activity.defn(
        name="analyze_sentiment_batch",
        start_to_close_timeout=TIMEOUTS["operational_medium"],
        retry_policy=DATA_PROCESSING_RETRY
    )
    def analyze_sentiment_batch(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a batch of text.
        """
        texts = params.get("texts", [])
        activity.logger.info(f"Analyzing sentiment for {len(texts)} texts")
        return self.nlp.analyze_sentiment(texts)

    @activity.defn(
        name="fix_data_quality",
        start_to_close_timeout=TIMEOUTS["operational_long"],
        retry_policy=DATA_PROCESSING_RETRY
    )
    def fix_data_quality(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fix data quality issues in dataset.
        
        Performs:
        - Missing value imputation (mean, median, mode, forward-fill)
        - Outlier detection and treatment (IQR, Z-score, Winsorization)
        - Data validation and scoring
        
        PhD-level Analyst: Uses statistical methods for imputation.
        QA Engineer: Comprehensive validation before/after.
        Performance Engineer: Efficient in-memory operations.
        
        Args:
            params: {
                "data": List[Dict] - Records to clean,
                "numeric_columns": List[str] - Numeric column names,
                "categorical_columns": List[str] - Categorical column names,
                "imputation_strategy": str - "mean", "median", "mode", "ffill",
                "outlier_strategy": str - "remove", "cap", "winsorize",
                "outlier_threshold": float - Z-score threshold (default 3.0)
            }
        
        Returns:
            {
                "cleaned_data": List[Dict],
                "quality_report": {
                    "original_rows": int,
                    "cleaned_rows": int,
                    "missing_value_fixes": int,
                    "outliers_treated": int,
                    "quality_score_before": float,
                    "quality_score_after": float
                }
            }
        """
        import pandas as pd
        import numpy as np
        from scipy import stats
        
        data = params.get("data", [])
        numeric_cols = params.get("numeric_columns", [])
        categorical_cols = params.get("categorical_columns", [])
        imputation_strategy = params.get("imputation_strategy", "median")
        outlier_strategy = params.get("outlier_strategy", "cap")
        outlier_threshold = params.get("outlier_threshold", 3.0)
        
        activity.logger.info(
            f"Fixing data quality for {len(data)} records, "
            f"imputation={imputation_strategy}, outliers={outlier_strategy}"
        )
        
        if not data:
            return {
                "cleaned_data": [],
                "quality_report": {
                    "original_rows": 0,
                    "cleaned_rows": 0,
                    "missing_value_fixes": 0,
                    "outliers_treated": 0,
                    "quality_score_before": 0.0,
                    "quality_score_after": 0.0
                }
            }
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        original_rows = len(df)
        
        # Calculate initial quality score
        total_cells = df.size
        missing_cells = df.isnull().sum().sum()
        quality_score_before = 1.0 - (missing_cells / total_cells) if total_cells > 0 else 0.0
        
        missing_fixes = 0
        outliers_treated = 0
        
        # 1. Handle missing values
        for col in numeric_cols:
            if col not in df.columns:
                continue
            
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                if imputation_strategy == "mean":
                    df[col].fillna(df[col].mean(), inplace=True)
                elif imputation_strategy == "median":
                    df[col].fillna(df[col].median(), inplace=True)
                elif imputation_strategy == "mode":
                    mode_val = df[col].mode()
                    if len(mode_val) > 0:
                        df[col].fillna(mode_val[0], inplace=True)
                elif imputation_strategy == "ffill":
                    df[col].fillna(method='ffill', inplace=True)
                    df[col].fillna(method='bfill', inplace=True)  # Handle leading NaNs
                
                missing_fixes += missing_count
        
        for col in categorical_cols:
            if col not in df.columns:
                continue
            
            missing_count = df[col].isnull().sum()
            if missing_count > 0:
                mode_val = df[col].mode()
                if len(mode_val) > 0:
                    df[col].fillna(mode_val[0], inplace=True)
                missing_fixes += missing_count
        
        # 2. Handle outliers in numeric columns
        for col in numeric_cols:
            if col not in df.columns:
                continue
            
            # Skip if column has too many missing values or is constant
            if df[col].std() == 0 or df[col].isnull().all():
                continue
            
            # Z-score method
            z_scores = np.abs(stats.zscore(df[col].dropna()))
            outlier_mask = z_scores > outlier_threshold
            outlier_count = outlier_mask.sum()
            
            if outlier_count > 0:
                if outlier_strategy == "remove":
                    # Remove outlier rows
                    valid_indices = df[col].dropna().index[~outlier_mask]
                    df = df.loc[df.index.isin(valid_indices)]
                    outliers_treated += outlier_count
                    
                elif outlier_strategy == "cap":
                    # Cap at mean ± threshold * std
                    mean = df[col].mean()
                    std = df[col].std()
                    lower_bound = mean - (outlier_threshold * std)
                    upper_bound = mean + (outlier_threshold * std)
                    
                    df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
                    outliers_treated += outlier_count
                    
                elif outlier_strategy == "winsorize":
                    # Winsorize at 5th and 95th percentiles
                    lower = df[col].quantile(0.05)
                    upper = df[col].quantile(0.95)
                    df[col] = df[col].clip(lower=lower, upper=upper)
                    outliers_treated += outlier_count
        
        cleaned_rows = len(df)
        
        # Calculate final quality score
        missing_cells_after = df.isnull().sum().sum()
        total_cells_after = df.size
        quality_score_after = 1.0 - (missing_cells_after / total_cells_after) if total_cells_after > 0 else 0.0
        
        # Convert back to list of dicts
        cleaned_data = df.to_dict(orient='records')
        
        quality_report = {
            "original_rows": original_rows,
            "cleaned_rows": cleaned_rows,
            "missing_value_fixes": missing_fixes,
            "outliers_treated": outliers_treated,
            "quality_score_before": round(quality_score_before, 4),
            "quality_score_after": round(quality_score_after, 4),
            "improvement": round(quality_score_after - quality_score_before, 4)
        }
        
        activity.logger.info(
            f"Data quality fixed: {original_rows} → {cleaned_rows} rows, "
            f"quality score: {quality_score_before:.2%} → {quality_score_after:.2%}"
        )
        
        return {
            "cleaned_data": cleaned_data,
            "quality_report": quality_report
        }

    @activity.defn(
        name="forecast_time_series",
        start_to_close_timeout=TIMEOUTS["operational_medium"],
        retry_policy=DATA_PROCESSING_RETRY
    )
    def forecast_time_series(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate time series forecast.
        
        Supports both native methods (EMA/Linear) and Prophet (if available).
        
        Args:
            params: {
                "values": List[float],
                "dates": Optional[List[str]],
                "periods": int,
                "method": str ("ema", "linear", "prophet"),
                "confidence_level": float
            }
        """
        values = params.get("values", [])
        dates = params.get("dates")
        periods = params.get("periods", 7)
        method = params.get("method", "ema")
        confidence = params.get("confidence_level", 0.95)
        
        activity.logger.info(f"Forecasting {periods} periods using {method}")
        
        if not values:
             raise activity.ApplicationError("No values provided for forecasting", non_retryable=True)

        try:
            # Use Prophet if requested and available
            if method == "prophet":
                if not PROPHET_AVAILABLE:
                    # Fallback or error? VIBE says "Real implementations".
                    # If user asked for Prophet and it's missing, we should probably fail or warn.
                    # But if we want robust fallback, we could switch to EMA.
                    # Let's stick to explicit failure for now to avoid surprises.
                    raise RuntimeError("Prophet is not available")
                    
                if not dates:
                    raise RuntimeError("Dates are required for Prophet forecasting")
                    
                return self.prophet.forecast_prophet(
                    dates=dates,
                    values=values,
                    periods=periods
                )
            
            # Use Native Methods
            result = forecast(
                values=values,
                periods=periods,
                method=method,
                confidence_level=confidence,
                dates=dates
            )
            
            return result.to_dict()
            
        except Exception as e:
            activity.logger.error(f"Forecasting failed: {e}")
            raise activity.ApplicationError(f"Forecasting failed: {e}", non_retryable=True)

