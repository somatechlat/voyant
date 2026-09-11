import sys
import uuid

from ninja import NinjaAPI

from apps.admin_panel.api import admin_router
from apps.analysis.api import analyze_router
from apps.approvals.api import approval_router

# Capsules router — imported lazily to avoid startup coupling
from apps.capsules.api import capsules_router
from apps.core.alerting import get_alerting_router
from apps.core.auth_api import auth_router
from apps.dashboard_builder.api import dashboards_router
from apps.discovery.api import discovery_router, sources_router
from apps.features.api import features_router
from apps.governance.api import governance_router
from apps.ingestion.api import ingestion_router
from apps.intent.api import intent_router
from apps.llm_providers.api import llm_router
from apps.ml_platform.api import ml_router
from apps.ml_platform.mlflow_api import mlflow_router
from apps.notifications.api import notifications_router
from apps.ontology.api import ontology_router
from apps.pipelines.api import pipelines_router
from apps.scraper.api import scrape_router, scraper_v2_router
from apps.scraper.template_api import template_router
from apps.search.api import router as search_router
from apps.sql.api import sql_router

# New feature routers
from apps.streaming.api import streaming_router
from apps.uptp_core.api import uptp_router
from apps.webhooks.api import webhooks_router
from apps.workflows.api import artifacts_router, jobs_router, presets_router
from apps.workspaces.api import workspaces_router

# Use a unique namespace during testing to avoid NinjaAPI registry collisions
urls_namespace = "v1"
if "pytest" in sys.modules:
    try:
        NinjaAPI._registry.clear()  # type: ignore[attr-defined]
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
api.add_router("/scraper", template_router, tags=["scraper-templates"])
api.add_router("/scraper/v2", scraper_v2_router, tags=["scraper-v2"])
api.add_router("/capsules", capsules_router, tags=["capsules"])
api.add_router("/ingestion", ingestion_router, tags=["ingestion"])
api.add_router("/admin", admin_router, tags=["admin"])
api.add_router("/ontology", ontology_router, tags=["ontology"])
api.add_router("/ml", ml_router, tags=["ml"])
api.add_router("/intent", intent_router, tags=["intent"])
api.add_router("/llm", llm_router, tags=["llm-providers"])
api.add_router("/auth", auth_router, tags=["auth"])
api.add_router("/pipelines", pipelines_router, tags=["pipelines"])
api.add_router("/dashboards", dashboards_router, tags=["dashboards"])
api.add_router("/features", features_router, tags=["features"])
api.add_router("/notifications", notifications_router, tags=["notifications"])
api.add_router("/workspaces", workspaces_router, tags=["workspaces"])
api.add_router("/approvals", approval_router, tags=["approvals"])
api.add_router("/webhooks", webhooks_router, tags=["webhooks"])
api.add_router("/streaming", streaming_router, tags=["streaming"])
api.add_router("/uptp", uptp_router, tags=["uptp"])
api.add_router("/alerting", get_alerting_router(), tags=["alerting"])

# ── MLflow-Compatible API (separate URL prefix) ──────────────────────────────
# Mounted at /api/2.0/mlflow/ via voyant_project/urls.py
mlflow_api = NinjaAPI(
    title="Voyant MLflow-Compatible API",
    description="MLflow Tracking Server-compatible REST API for experiment tracking, "
    "run management, and model registry.",
    version="2.0.0",
    urls_namespace=f"mlflow_{urls_namespace}",
)
mlflow_api.add_router("/", mlflow_router, tags=["mlflow"])
