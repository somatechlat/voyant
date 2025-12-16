"""
Forecasting Primitives

Wraps Prophet for Time Series Forecasting.
Implements Roadmap Tier 3 & Phase 3 Items.
Adheres to Vibe Coding Rules: Uses Prophet if available, handles deps.
"""
import logging
import pandas as pd
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False

from voyant.core.errors import AnalysisError

logger = logging.getLogger(__name__)

class ForecastPrimitives:
    """
    Time Series Forecasting operations.
    """
    
    def __init__(self):
        if not PROPHET_AVAILABLE:
            logger.warning("Prophet not found. Forecasting primitives will fail.")

    def forecast_prophet(self, 
                         dates: List[str], 
                         values: List[float], 
                         periods: int = 30,
                         freq: str = 'D') -> Dict[str, Any]:
        """
        Generate forecast using Facebook Prophet.
        """
        if not PROPHET_AVAILABLE:
            raise AnalysisError("VYNT-7010", "Prophet library not installed.")

        if len(dates) != len(values):
            raise AnalysisError("VYNT-7011", "Dates and values length mismatch")
            
        try:
            # Prepare DataFrame for Prophet (ds, y)
            df = pd.DataFrame({'ds': dates, 'y': values})
            df['ds'] = pd.to_datetime(df['ds'])
            
            # Configure & Fit
            m = Prophet()
            m.fit(df)
            
            # Forecast
            future = m.make_future_dataframe(periods=periods, freq=freq)
            forecast = m.predict(future)
            
            # Extract results
            result_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
            
            return {
                "method": "prophet",
                "forecast_dates": result_df['ds'].dt.strftime('%Y-%m-%d').tolist(),
                "forecast_values": result_df['yhat'].tolist(),
                "lower_bound": result_df['yhat_lower'].tolist(),
                "upper_bound": result_df['yhat_upper'].tolist(),
                "components": {
                   # Prophet components if needed later
                }
            }
            
        except Exception as e:
            logger.error(f"Prophet forecast failed: {e}")
            raise AnalysisError("VYNT-7012", f"Forecasting Error: {e}")
