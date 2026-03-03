"""
Voyant Scraper — Activities Package.

Re-exports all activity classes by domain and provides a backward-compatible
ScrapeActivities proxy class that delegates to the correct domain class.

Split from scraper/activities.py (Rule 245: 949 lines → 3 files under 320 lines each).

Usage (recommended):
    from apps.scraper.activities import FetchActivities, ParseActivities, StorageActivities

Usage (backward-compatible):
    from apps.scraper.activities import ScrapeActivities
    # Works for all methods: fetch_page, deep_archive, extract_data, process_ocr,
    # transcribe_media, parse_pdf, store_artifact, finalize_job
"""

from apps.scraper.activities.fetch_activities import FetchActivities
from apps.scraper.activities.parse_activities import ParseActivities
from apps.scraper.activities.storage_activities import StorageActivities


class ScrapeActivities(FetchActivities, ParseActivities, StorageActivities):
    """
    Backward-compatible aggregate class providing all scraper activity methods
    from FetchActivities, ParseActivities, and StorageActivities in one object.

    For Temporal workflow activity method references (e.g. ScrapeActivities.fetch_page),
    the name lookup must resolve to the correct decorated @activity.defn function.

    New code should import the specific class directly. This class exists solely
    for backward compatibility with workflow.py, deep_research_workflow.py,
    and any external callers that predate the Rule-245 split.
    """


__all__ = [
    "FetchActivities",
    "ParseActivities",
    "StorageActivities",
    "ScrapeActivities",
]
