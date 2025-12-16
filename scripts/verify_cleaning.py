"""
Verification Script for Data Cleaning

Tests FIX_DATA_QUALITY primitives.
"""
import logging
import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
sys.path.append(os.getcwd())

from voyant.core.cleaning_primitives import DataCleaningPrimitives

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_clean")

def test_cleaning():
    logger.info("Testing Data Cleaning...")
    cleaner = DataCleaningPrimitives()
    
    # Generate dirty data
    data = [
        {"id": 1, "name": " Alice ", "age": 25, "score": 100},
        {"id": 1, "name": " Alice ", "age": 25, "score": 100}, # Dupe
        {"id": 2, "name": "Bob", "age": np.nan, "score": 50}, # Missing
        {"id": 3, "name": "nan", "age": 30, "score": 75}, # String 'nan'
    ]
    
    strategies = {
        "missing_values": "mean",
        "duplicates": "drop",
        "normalize_strings": True
    }
    
    try:
        result = cleaner.clean_dataset(data, strategies)
        df = pd.DataFrame(result["cleaned_data"])
        report = result["report"]
        
        logger.info(f"Report: {report}")
        logger.info(f"Cleaned Data:\n{df.to_string()}")
        
        # Assertions
        assert len(df) == 3, "Duplicates not removed"
        assert not df['age'].isna().any(), "Age not imputed"
        assert df.iloc[0]['name'] == 'alice', "String not normalized"
        
    except Exception as e:
        logger.error(f"Cleaning Failed: {e}")

if __name__ == "__main__":
    test_cleaning()
