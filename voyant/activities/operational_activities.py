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

logger = logging.getLogger(__name__)

class OperationalActivities:
    def __init__(self):
        self.ml = MLPrimitives()
        self.nlp = NLPPrimitives()
        self.cleaner = DataCleaningPrimitives()

    @activity.defn
    def clean_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean dataset activity.
        """
        data = params.get("data", [])
        strategies = params.get("strategies", {})
        
        activity.logger.info(f"Cleaning {len(data)} records")
        return self.cleaner.clean_dataset(data, strategies)

    @activity.defn
    def detect_anomalies(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect anomalies in data.
        """
        data = params.get("data", [])
        contamination = params.get("contamination", 0.05)
        
        activity.logger.info(f"Detecting anomalies in {len(data)} records")
        return self.ml.detect_anomalies(data, contamination)

    @activity.defn
    def analyze_sentiment_batch(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for a batch of text.
        """
        texts = params.get("texts", [])
        activity.logger.info(f"Analyzing sentiment for {len(texts)} texts")
        return self.nlp.analyze_sentiment(texts)
