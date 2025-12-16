"""
Verification Script for Operational Presets

Tests Anomaly Detection and Sentiment Analysis primitives.
"""
import logging
import sys
import os
import random

# Add project root to path
sys.path.append(os.getcwd())

from voyant.core.ml_primitives import MLPrimitives
from voyant.core.nlp_primitives import NLPPrimitives

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_ops")

def test_anomaly_detection():
    logger.info("Testing Anomaly Detection...")
    ml = MLPrimitives()
    
    # Generate mock data with outliers
    data = []
    # Normal data (N=100)
    for _ in range(100):
        data.append({"val": random.gauss(50, 5)})
    # Anomalies (N=5)
    for _ in range(5):
        data.append({"val": random.gauss(200, 10)}) # Huge values
        
    try:
        result = ml.detect_anomalies(data, contamination=0.05)
        logger.info(f"Anomaly Count: {result['anomaly_count']} / {result['total_records']}")
        logger.info(f"Anomalies: {result['anomalies']}")
    except Exception as e:
        logger.error(f"Anomaly Detection Failed: {e}")

def test_sentiment():
    logger.info("Testing Sentiment Analysis...")
    nlp = NLPPrimitives()
    
    texts = [
        "I love this product! It's amazing.",
        "This is terrible, I hate it.",
        "It is okay, nothing special."
    ]
    
    try:
        results = nlp.analyze_sentiment(texts)
        for r in results:
            logger.info(f"Text: {r['text_snippet']} -> {r['sentiment']} (Compound: {r['compound']})")
    except Exception as e:
        logger.error(f"Sentiment Analysis Failed: {e}")

if __name__ == "__main__":
    test_anomaly_detection()
    test_sentiment()
