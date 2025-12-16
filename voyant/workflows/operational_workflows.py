"""
Operational Workflows

Workflows for:
- DETECT_ANOMALIES
- ANALYZE_SENTIMENT
"""
from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from voyant.activities.operational_activities import OperationalActivities

@workflow.defn
class DetectAnomaliesWorkflow:
    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run anomaly detection workflow.
        """
        data = params.get("data", [])
        # In a real preset, this would Ingest -> Clean -> Detect.
        # Minimal impl here assumes data passed or loaded via separate activity.
        
        result = await workflow.execute_activity(
            OperationalActivities.detect_anomalies,
            {"data": data, "contamination": params.get("contamination", 0.1)},
            start_to_close_timeout=timedelta(minutes=5)
        )
        return result

@workflow.defn
class AnalyzeSentimentWorkflow:
    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run sentiment analysis workflow.
        """
        texts = params.get("texts", [])
        
        results = await workflow.execute_activity(
            OperationalActivities.analyze_sentiment_batch,
            {"texts": texts},
            start_to_close_timeout=timedelta(minutes=10)
        )
        
        # Calculate aggregate stats
        positive = sum(1 for r in results if r["sentiment"] == "positive")
        negative = sum(1 for r in results if r["sentiment"] == "negative")
        neutral = sum(1 for r in results if r["sentiment"] == "neutral")
        
        return {
            "total": len(results),
            "breakdown": {
                "positive": positive,
                "negative": negative,
                "neutral": neutral
            },
            "details": results
        }
