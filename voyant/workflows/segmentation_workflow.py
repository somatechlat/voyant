"""
Customer Segmentation Workflow: Orchestrates Data Clustering Analysis.

This Temporal workflow defines the automated process for performing customer
or data segmentation using clustering algorithms (e.g., K-Means). It delegates
the core clustering logic to specialized ML activities and then enriches
the results by profiling the characteristics of each identified segment.
"""

from datetime import timedelta
from typing import Any, Dict

from temporalio import workflow

# This context manager is necessary to allow importing non-workflow/activity
# modules within the workflow definition. It passes control to the Python
# import system directly, bypassing Temporal's default import handling.
with workflow.unsafe.imports_passed_through():
    from voyant.activities.ml_activities import MLActivities


@workflow.defn
class SegmentCustomersWorkflow:
    """
    Temporal workflow for orchestrating customer or data segmentation analysis.
    """

    @workflow.run
    async def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the customer segmentation analysis workflow.

        This method coordinates data clustering and then enriches the results
        with average profiles for each segment.

        Args:
            params: A dictionary containing the segmentation configuration:
                - `data` (List[Dict[str, float]]): The input feature data for clustering.
                - `n_segments` (int): The desired number of customer segments (default: 3).

        Returns:
            A dictionary containing the segmentation results, including the number
            of segments, total customers, silhouette score, detailed segment profiles,
            and cluster assignments for each data point.
        """
        data = params.get("data", [])
        n_segments = params.get("n_segments", 3)

        workflow.logger.info(
            f"Starting SEGMENT_CUSTOMERS: {len(data)} records into {n_segments} segments."
        )

        # Execute the activity that performs the clustering analysis (e.g., K-Means).
        # This offloads the heavy computation to a dedicated activity worker.
        result = await workflow.execute_activity(
            MLActivities.cluster_data,
            {"data": data, "clusters": n_segments},
            start_to_close_timeout=timedelta(minutes=10),  # Allow up to 10 minutes for clustering.
        )

        # Post-processing: Enrich results with segment profiles for better interpretation.
        clusters = result.get("clusters", [])
        segment_profiles = {}

        # Calculate average profile for each segment.
        for cluster_id in range(n_segments):
            # Identify all data points belonging to the current cluster.
            cluster_members = [
                data[i] for i, c in enumerate(clusters) if c == cluster_id
            ]
            if cluster_members:
                avg_profile = {}
                # For each feature, calculate the average value within the cluster.
                if cluster_members: # Ensure cluster_members is not empty before accessing keys
                    keys = cluster_members[0].keys()
                    for key in keys:
                        values = [m[key] for m in cluster_members if key in m]
                        avg_profile[key] = sum(values) / len(values) if values else 0

                segment_profiles[f"segment_{cluster_id}"] = {
                    "size": len(cluster_members),
                    "percentage": len(cluster_members) / len(data) * 100 if len(data) > 0 else 0,
                    "average_profile": avg_profile,
                }

        workflow.logger.info(f"SEGMENT_CUSTOMERS workflow completed. Found {n_segments} segments.")
        return {
            "status": "completed",
            "n_segments": n_segments,
            "total_customers": len(data),
            "silhouette_score": result.get("silhouette_score"), # A metric for cluster quality.
            "segment_profiles": segment_profiles,
            "cluster_assignments": clusters, # Raw cluster assignment for each data point.
        }
