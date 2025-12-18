"""
Data Cleaning Primitives

Primitives for the FIX_DATA_QUALITY preset.
Adheres to Vibe Coding Rules: Uses Pandas for real data manipulation.
"""
import logging
from typing import Any, Dict, List, Optional, Union
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class DataCleaningPrimitives:
    """
    Core data cleaning operations.
    """
    
    def clean_dataset(self, 
                     data: List[Dict[str, Any]], 
                     strategies: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Clean a dataset based on strategies.
        
        Strategies keys:
        - missing_values: 'drop', 'mean', 'median', 'mode' (default: 'drop')
        - duplicates: 'drop', 'keep' (default: 'drop')
        - normalize_strings: bool (default: True)
        """
        if not data:
            return {"cleaned_data": [], "report": "No data"}
            
        df = pd.DataFrame(data)
        original_count = len(df)
        report = {}
        
        strategies = strategies or {}
        missing_strat = strategies.get("missing_values", "drop") # drop, mean, median, mode, ffill
        drop_dupes = strategies.get("duplicates", "drop") == "drop"
        norm_strings = strategies.get("normalize_strings", True)
        outlier_strat = strategies.get("outliers", "none") # none, remove, cap, winsorize
        outlier_thresh = strategies.get("outlier_threshold", 3.0)
        numeric_cols = strategies.get("numeric_columns", [])
        categorical_cols = strategies.get("categorical_columns", [])

        # Auto-detect columns if not provided
        if not numeric_cols:
             numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        if not categorical_cols:
             categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        # 1. Duplicates
        if drop_dupes:
            dupe_count = df.duplicated().sum()
            df = df.drop_duplicates()
            report["duplicates_removed"] = int(dupe_count)

        # 2. String Normalization
        if norm_strings:
            for col in categorical_cols:
                if col in df.columns:
                    # Strip and lower
                    df[col] = df[col].astype(str).str.strip().str.lower()
                    # Restore NaNs for 'nan' strings
                    df[col] = df[col].replace('nan', np.nan)
            report["strings_normalized"] = True

        # 3. Missing Values
        report["missing_values_before"] = int(df.isna().sum().sum())
        
        if missing_strat == "drop":
            df = df.dropna()
        elif missing_strat in ["mean", "median", "mode", "ffill"]:
            # Numeric Imputation
            for col in numeric_cols:
                if col in df.columns:
                    if missing_strat == "mean":
                         df[col] = df[col].fillna(df[col].mean())
                    elif missing_strat == "median":
                         df[col] = df[col].fillna(df[col].median())
                    elif missing_strat == "mode":
                         if not df[col].mode().empty:
                             df[col] = df[col].fillna(df[col].mode()[0])
                    elif missing_strat == "ffill":
                        df[col] = df[col].fillna(method='ffill').fillna(method='bfill')

            # Categorical Imputation (Mode typically)
            for col in categorical_cols:
                if col in df.columns:
                     if not df[col].mode().empty:
                         df[col] = df[col].fillna(df[col].mode()[0])

        report["missing_values_after"] = int(df.isna().sum().sum())

        # 4. Outliers
        outliers_treated = 0
        if outlier_strat != "none":
            from scipy import stats
            for col in numeric_cols:
                if col not in df.columns: continue
                if df[col].nunique() < 2: continue # constant or empty

                z_scores = np.abs(stats.zscore(df[col].dropna()))
                # Align indices
                z_scores_series = pd.Series(z_scores, index=df[col].dropna().index)
                mask = z_scores_series > outlier_thresh
                
                count = mask.sum()
                if count > 0:
                    outliers_treated += count
                    if outlier_strat == "remove":
                        df = df.drop(index=mask[mask].index)
                    elif outlier_strat == "cap":
                         mean = df[col].mean()
                         std = df[col].std()
                         lower = mean - (outlier_thresh * std)
                         upper = mean + (outlier_thresh * std)
                         df[col] = df[col].clip(lower=lower, upper=upper)
                    elif outlier_strat == "winsorize":
                         lower = df[col].quantile(0.05)
                         upper = df[col].quantile(0.95)
                         df[col] = df[col].clip(lower=lower, upper=upper)

        report["outliers_treated"] = int(outliers_treated)
        report["final_row_count"] = len(df)
        report["removed_rows"] = original_count - len(df)

        return {
            "cleaned_data": df.to_dict(orient="records"),
            "report": report
        }
