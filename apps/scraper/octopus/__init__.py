"""
OCTOPUS — Multi-Arm Autonomous Web Intelligence Engine.

Eight discrete scraping strategies unified under a single dispatcher.
All arms enforce SSRF protection and emit Kafka telemetry.

Usage:
    from apps.scraper.octopus import OctopusDispatcher, OctopusRequest

    request = OctopusRequest(url="https://example.com", arm="static", tenant_id="t1")
    result = await OctopusDispatcher().dispatch(request)
"""

from apps.scraper.octopus.dispatcher import OctopusDispatcher
from apps.scraper.octopus.schemas import (
    BrowserAction,
    OctopusARM,
    OctopusRequest,
    OctopusResult,
)

__all__ = [
    "OctopusDispatcher",
    "OctopusRequest",
    "OctopusResult",
    "OctopusARM",
    "BrowserAction",
]
