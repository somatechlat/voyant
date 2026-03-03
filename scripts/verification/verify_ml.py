"""
Verification Script for ML & Forecasting

Tests the Scikit-Learn and Prophet integration.
"""

import logging

# Add project root to path
import os
import random
import sys
from datetime import datetime, timedelta

sys.path.append(os.getcwd())

from apps.analysis.lib.forecast_primitives import ForecastPrimitives
from apps.analysis.lib.ml_primitives import MLPrimitives

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_ml")


def test_kmeans():
    logger.info("Testing K-Means...")
    ml = MLPrimitives()

    # Generate synthetic data for deterministic-style verification
    data = []
    # Cluster 1
    for _ in range(10):
        data.append({"x": random.gauss(0, 0.5), "y": random.gauss(0, 0.5)})
    # Cluster 2
    for _ in range(10):
        data.append({"x": random.gauss(5, 0.5), "y": random.gauss(5, 0.5)})

    try:
        result = ml.cluster_kmeans(data, n_clusters=2)
        logger.info(f"K-Means Result: {len(result['clusters'])} labels assigned.")
        logger.info(f"Silhouette Score: {result.get('silhouette_score')}")
    except Exception as e:
        logger.error(f"K-Means Failed: {e}")


def test_prophet():
    logger.info("Testing Prophet...")
    fc = ForecastPrimitives()

    # Generate synthetic time series
    dates = []
    values = []
    base = datetime.now()
    for i in range(60):
        d = base - timedelta(days=60 - i)
        dates.append(d.strftime("%Y-%m-%d"))
        # Linear trend + noise
        values.append(i * 1.5 + random.gauss(0, 2))

    try:
        result = fc.forecast_prophet(dates, values, periods=7)
        logger.info(f"Forecast Generated: {len(result['forecast_values'])} points.")
        logger.info(f"Next 3 values: {result['forecast_values'][:3]}")
    except Exception as e:
        logger.error(f"Prophet Failed: {e}")


if __name__ == "__main__":
    logger.info("Starting ML Verification...")
    test_kmeans()
    test_prophet()
    logger.info("Verification Complete.")
