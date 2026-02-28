import sys
import uuid

from ninja import NinjaAPI

from apps.analysis.api import analyze_router
from apps.discovery.api import discovery_router, sources_router
from apps.governance.api import governance_router
from apps.scraper.api import scrape_router
from apps.search.api import router as search_router
from apps.sql.api import sql_router
from apps.workflows.api import artifacts_router, jobs_router, presets_router

# Use a unique namespace during testing to avoid NinjaAPI registry collisions
urls_namespace = "v1"
if "pytest" in sys.modules:
    try:
        NinjaAPI._registry.clear()
    except Exception:
        pass
    urls_namespace = f"v1_{uuid.uuid4().hex}"

api = NinjaAPI(
    title="Voyant API",
    description="Autonomous Data Intelligence for AI Agents",
    version="3.0.0",
    urls_namespace=urls_namespace,
)

# Register Routers
api.add_router("/sources", sources_router, tags=["sources"])
api.add_router("/jobs", jobs_router, tags=["jobs"])
api.add_router("/sql", sql_router, tags=["sql"])
api.add_router("/governance", governance_router, tags=["governance"])
api.add_router("/presets", presets_router, tags=["presets"])
api.add_router("/artifacts", artifacts_router, tags=["artifacts"])
api.add_router("/analyze", analyze_router, tags=["analyze"])
api.add_router("/discovery", discovery_router, tags=["discovery"])
api.add_router("/search", search_router, tags=["search"])
api.add_router("/scrape", scrape_router, tags=["scrape"])
