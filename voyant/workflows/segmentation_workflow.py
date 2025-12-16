"""
Customer Segmentation Workflow

SEGMENT_CUSTOMERS preset using K-Means clustering.
Adheres to Vibe Coding Rules: Real ML implementation via existing primitives.
"""
from datetime import timedelta
from typing import Any, Dict, List

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from voyant.activities.ml_activities import MLActivities

@workflow.defn
class SegmentCustomersWorkflow:
    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run customer segmentation analysis.
        
        Args:
            params: {
                "data": List[Dict[str, float]] - Customer feature data
                "n_segments": int - Number of segments (default: 3)
            }
        """
        data = params.get("data", [])
        n_segments = params.get("n_segments", 3)
        
        workflow.logger.info(f"Starting SEGMENT_CUSTOMERS: {len(data)} records into {n_segments} segments")
        
        # Clustering Analysis
        result = await workflow.execute_activity(
            MLActivities.cluster_data,
            {
                "data": data,
                "clusters": n_segments
            },
            start_to_close_timeout=timedelta(minutes=10)
        )
        
        # Enrich result with segment profiles
        clusters = result.get("clusters", [])
        segment_profiles = {}
        
        for cluster_id in range(n_segments):
            cluster_members = [data[i] for i, c in enumerate(clusters) if c == cluster_id]
            if cluster_members:
                # Calculate average profile for segment
                avg_profile = {}
                if cluster_members:
                    keys = cluster_members[0].keys()
                    for key in keys:
                        values = [m[key] for m in cluster_members if key in m]
                        avg_profile[key] = sum(values) / len(values) if values else 0
                
                segment_profiles[f"segment_{cluster_id}"] = {
                    "size": len(cluster_members),
                    "percentage": len(cluster_members) / len(data) * 100,
                    "average_profile": avg_profile
                }
        
        return {
            "status": "completed",
            "n_segments": n_segments,
            "total_customers": len(data),
            "silhouette_score": result.get("silhouette_score"),
            "segment_profiles": segment_profiles,
            "cluster_assignments": clusters
        }
