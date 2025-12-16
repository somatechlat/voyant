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
        missing_strat = strategies.get("missing_values", "drop")
        drop_dupes = strategies.get("duplicates", "drop") == "drop"
        norm_strings = strategies.get("normalize_strings", True)

        # 1. Duplicates
        if drop_dupes:
            dupe_count = df.duplicated().sum()
            df = df.drop_duplicates()
            report["duplicates_removed"] = int(dupe_count)

        # 2. String Normalization
        if norm_strings:
            str_cols = df.select_dtypes(include=['object']).columns
            for col in str_cols:
                # Strip and lower
                df[col] = df[col].astype(str).str.strip().str.lower()
                # Restore NaNs for 'nan' strings
                df[col] = df[col].replace('nan', np.nan)
            report["strings_normalized"] = True

        # 3. Missing Values
        report["missing_values_before"] = int(df.isna().sum().sum())
        
        if missing_strat == "drop":
            df = df.dropna()
        elif missing_strat in ["mean", "median"]:
            num_cols = df.select_dtypes(include=[np.number]).columns
            for col in num_cols:
                if missing_strat == "mean":
                    val = df[col].mean()
                else:
                    val = df[col].median()
                df[col] = df[col].fillna(val)
        elif missing_strat == "mode":
             for col in df.columns:
                 if not df[col].mode().empty:
                     df[col] = df[col].fillna(df[col].mode()[0])

        report["missing_values_after"] = int(df.isna().sum().sum())
        report["final_row_count"] = len(df)
        report["removed_rows"] = original_count - len(df)

        return {
            "cleaned_data": df.to_dict(orient="records"),
            "report": report
        }
