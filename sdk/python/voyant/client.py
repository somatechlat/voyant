"""
Voyant Python SDK Client — Full API client wrapping httpx.

Auto-generated pattern from OpenAPI spec. Covers all major API areas:
sources, jobs, sql, governance, scraper, ontology, ml, auth, capsules,
search, intent, llm, admin, ingestion, discovery.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator
from urllib.parse import urlencode, urljoin

import httpx

logger = logging.getLogger(__name__)

__all__ = ["VoyantClient"]

# Default timeout for API calls (seconds).
_DEFAULT_TIMEOUT = 60.0


class VoyantAPIError(Exception):
    """Raised when the Voyant API returns an error response."""

    def __init__(
        self,
        message: str,
        status_code: int = 0,
        error_code: str = "",
        detail: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail


class _Resource:
    """Base class for API resource namespaces."""

    def __init__(self, client: VoyantClient) -> None:
        self._client = client

    @property
    def _http(self) -> httpx.Client:
        return self._client._http


# ===================================================================
# Sources
# ===================================================================


class SourcesResource(_Resource):
    """Manage data sources (connectors)."""

    def list(self, *, limit: int = 100, offset: int = 0) -> list[dict]:
        """List all data sources."""
        return self._client._get("/v1/sources", params={"limit": limit, "offset": offset})

    def get(self, source_id: str) -> dict:
        """Get a single source by ID."""
        return self._client._get(f"/v1/sources/{source_id}")

    def create(
        self,
        *,
        name: str,
        source_type: str,
        connection_config: dict,
        credentials: dict | None = None,
        sync_schedule: str | None = None,
    ) -> dict:
        """Create a new data source."""
        body: dict[str, Any] = {
            "name": name,
            "source_type": source_type,
            "connection_config": connection_config,
        }
        if credentials:
            body["credentials"] = credentials
        if sync_schedule:
            body["sync_schedule"] = sync_schedule
        return self._client._post("/v1/sources", json=body)

    def update(self, source_id: str, **kwargs: Any) -> dict:
        """Update an existing source."""
        return self._client._put(f"/v1/sources/{source_id}", json=kwargs)

    def delete(self, source_id: str) -> dict:
        """Delete a source."""
        return self._client._delete(f"/v1/sources/{source_id}")

    def discover(self, hint: str) -> dict:
        """Discover source type from a hint string."""
        return self._client._post("/v1/sources/discover", json={"hint": hint})

    def connect(
        self,
        *,
        source_id: str,
        source_definition_id: str,
        connection_config: dict,
        destination_config: dict | None = None,
    ) -> dict:
        """Provision an Airbyte source connector."""
        body: dict[str, Any] = {
            "source_id": source_id,
            "source_definition_id": source_definition_id,
            "connection_config": connection_config,
        }
        if destination_config:
            body["destination_config"] = destination_config
        return self._client._post("/v1/ingestion/connect", json=body)


# ===================================================================
# Jobs
# ===================================================================


class JobsResource(_Resource):
    """Manage async data jobs (ingest, profile, quality, analyze)."""

    def list(
        self,
        *,
        status: str | None = None,
        job_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List jobs with optional filters."""
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status
        if job_type:
            params["job_type"] = job_type
        return self._client._get("/v1/jobs", params=params)

    def get(self, job_id: str) -> dict:
        """Get job details."""
        return self._client._get(f"/v1/jobs/{job_id}")

    def cancel(self, job_id: str) -> dict:
        """Cancel a running job."""
        return self._client._post(f"/v1/jobs/{job_id}/cancel")

    def ingest(self, *, source_id: str, tables: list[str] | None = None, mode: str = "full") -> dict:
        """Start a data ingestion job."""
        body: dict[str, Any] = {"source_id": source_id, "mode": mode}
        if tables:
            body["tables"] = tables
        return self._client._post("/v1/jobs/ingest", json=body)

    def profile(self, *, source_id: str, table: str | None = None, sample_size: int = 10000) -> dict:
        """Run data profiling."""
        body: dict[str, Any] = {"source_id": source_id, "sample_size": sample_size}
        if table:
            body["table"] = table
        return self._client._post("/v1/jobs/profile", json=body)

    def quality(self, *, source_id: str, table: str | None = None, checks: list[str] | None = None) -> dict:
        """Run data quality checks."""
        body: dict[str, Any] = {"source_id": source_id}
        if table:
            body["table"] = table
        if checks:
            body["checks"] = checks
        return self._client._post("/v1/jobs/quality", json=body)

    def analyze(
        self,
        *,
        source_id: str | None = None,
        table: str | None = None,
        tables: list[str] | None = None,
        analyzers: list[str] | None = None,
        kpis: list[dict] | None = None,
        sample_size: int = 10000,
        profile: bool = True,
        run_analyzers: bool = True,
        generate_artifacts: bool = True,
    ) -> dict:
        """Run a full analysis job."""
        body: dict[str, Any] = {
            "sample_size": sample_size,
            "profile": profile,
            "run_analyzers": run_analyzers,
            "generate_artifacts": generate_artifacts,
        }
        if source_id:
            body["source_id"] = source_id
        if table:
            body["table"] = table
        if tables:
            body["tables"] = tables
        if analyzers:
            body["analyzers"] = analyzers
        if kpis:
            body["kpis"] = kpis
        return self._client._post("/v1/analyze", json=body)


# ===================================================================
# Artifacts
# ===================================================================


class ArtifactsResource(_Resource):
    """Retrieve job artifacts."""

    def list(self, job_id: str) -> list[dict]:
        """List artifacts for a job."""
        return self._client._get(f"/v1/artifacts/{job_id}")

    def download(self, job_id: str, artifact_type: str) -> bytes:
        """Download an artifact as raw bytes."""
        resp = self._client._http.get(
            f"{self._client._base_url}/v1/artifacts/{job_id}/{artifact_type}/download",
            headers=self._client._headers(),
        )
        resp.raise_for_status()
        return resp.content


# ===================================================================
# SQL
# ===================================================================


class SQLResource(_Resource):
    """Execute SQL queries and explore tables."""

    def tables(self) -> list[dict]:
        """List available tables."""
        return self._client._get("/v1/sql/tables")

    def columns(self, table: str) -> list[dict]:
        """List columns for a table."""
        return self._client._get(f"/v1/sql/tables/{table}/columns")

    def query(self, sql: str, *, max_rows: int = 1000) -> dict:
        """Execute a SQL query."""
        return self._client._post("/v1/sql/query", json={"sql": sql, "max_rows": max_rows})


# ===================================================================
# Ontology
# ===================================================================


class OntologyResource(_Resource):
    """Manage the type system: object types, properties, links, actions, functions."""

    # Object Types
    def list_types(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ontology/types", params={"limit": limit})

    def get_type(self, type_id: str) -> dict:
        return self._client._get(f"/v1/ontology/types/{type_id}")

    def create_type(self, *, name: str, description: str = "", properties: list[dict] | None = None) -> dict:
        body: dict[str, Any] = {"name": name, "description": description}
        if properties:
            body["properties"] = properties
        return self._client._post("/v1/ontology/types", json=body)

    def update_type(self, type_id: str, **kwargs: Any) -> dict:
        return self._client._put(f"/v1/ontology/types/{type_id}", json=kwargs)

    def delete_type(self, type_id: str) -> dict:
        return self._client._delete(f"/v1/ontology/types/{type_id}")

    # Objects
    def list_objects(self, *, type_id: str | None = None, limit: int = 100) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if type_id:
            params["object_type_id"] = type_id
        return self._client._get("/v1/ontology/objects", params=params)

    def get_object(self, object_id: str) -> dict:
        return self._client._get(f"/v1/ontology/objects/{object_id}")

    def create_object(self, *, object_type_id: str, properties: dict | None = None) -> dict:
        body: dict[str, Any] = {"object_type_id": object_type_id}
        if properties:
            body["properties"] = properties
        return self._client._post("/v1/ontology/objects", json=body)

    def update_object(self, object_id: str, **kwargs: Any) -> dict:
        return self._client._put(f"/v1/ontology/objects/{object_id}", json=kwargs)

    def delete_object(self, object_id: str) -> dict:
        return self._client._delete(f"/v1/ontology/objects/{object_id}")

    def batch_create(self, *, object_type_id: str, items: list[dict]) -> dict:
        return self._client._post(
            "/v1/ontology/objects/batch",
            json={"object_type_id": object_type_id, "items": items},
        )

    def upsert_object(self, *, object_type_id: str, properties: dict) -> dict:
        return self._client._post(
            "/v1/ontology/objects/upsert",
            json={"object_type_id": object_type_id, "properties": properties},
        )

    def traverse(self, object_id: str, *, depth: int = 2, link_types: list[str] | None = None) -> dict:
        body: dict[str, Any] = {"depth": depth}
        if link_types:
            body["link_types"] = link_types
        return self._client._post(f"/v1/ontology/objects/{object_id}/traverse", json=body)

    # Links
    def list_links(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ontology/links", params={"limit": limit})

    def create_link(
        self,
        *,
        link_type_id: str,
        source_object_id: str,
        target_object_id: str,
        properties: dict | None = None,
    ) -> dict:
        body: dict[str, Any] = {
            "link_type_id": link_type_id,
            "source_object_id": source_object_id,
            "target_object_id": target_object_id,
        }
        if properties:
            body["properties"] = properties
        return self._client._post("/v1/ontology/links", json=body)

    def delete_link(self, link_id: str) -> dict:
        return self._client._delete(f"/v1/ontology/links/{link_id}")

    # Link Types
    def list_link_types(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ontology/link-types", params={"limit": limit})

    def create_link_type(
        self,
        *,
        name: str,
        source_object_type_id: str,
        target_object_type_id: str,
        cardinality: str = "one_to_many",
        description: str = "",
    ) -> dict:
        return self._client._post("/v1/ontology/link-types", json={
            "name": name,
            "source_object_type_id": source_object_type_id,
            "target_object_type_id": target_object_type_id,
            "cardinality": cardinality,
            "description": description,
        })

    # Actions
    def list_actions(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ontology/actions", params={"limit": limit})

    def create_action(self, *, name: str, description: str = "", **kwargs: Any) -> dict:
        body: dict[str, Any] = {"name": name, "description": description, **kwargs}
        return self._client._post("/v1/ontology/actions", json=body)

    # Functions
    def list_functions(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ontology/functions", params={"limit": limit})

    def create_function(self, *, name: str, description: str = "", **kwargs: Any) -> dict:
        body: dict[str, Any] = {"name": name, "description": description, **kwargs}
        return self._client._post("/v1/ontology/functions", json=body)

    # Interfaces
    def list_interfaces(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ontology/interfaces", params={"limit": limit})

    def create_interface(self, *, name: str, description: str = "", **kwargs: Any) -> dict:
        body: dict[str, Any] = {"name": name, "description": description, **kwargs}
        return self._client._post("/v1/ontology/interfaces", json=body)


# ===================================================================
# Scraper
# ===================================================================


class ScraperResource(_Resource):
    """Web scraping operations: fetch, extract, OCR, PDF, transcription."""

    def start_scrape(
        self,
        *,
        urls: list[str],
        selectors: dict | None = None,
        options: dict | None = None,
    ) -> dict:
        """Start a new web scraping job."""
        body: dict[str, Any] = {"urls": urls}
        if selectors:
            body["selectors"] = selectors
        if options:
            body["options"] = options
        return self._client._post("/v1/scrape/start", json=body)

    def get_status(self, job_id: str) -> dict:
        """Get scrape job status."""
        return self._client._get(f"/v1/scrape/status/{job_id}")

    def get_result(self, job_id: str) -> dict:
        """Get scrape job results and artifacts."""
        return self._client._get(f"/v1/scrape/result/{job_id}")

    def cancel_scrape(self, job_id: str) -> dict:
        """Cancel a scrape job."""
        return self._client._post("/v1/scrape/cancel", json={"job_id": job_id})

    def get_metrics(self, job_id: str) -> dict:
        """Get scrape job metrics."""
        return self._client._get(f"/v1/scrape/metrics/{job_id}")

    def fetch(
        self,
        *,
        url: str,
        engine: str = "playwright",
        wait_for: str | None = None,
        scroll: bool = False,
        timeout: int = 30,
        wait_until: str | None = None,
        settle_ms: int | None = None,
        block_resources: bool | None = None,
        capture_json: bool = False,
    ) -> dict:
        """Fetch a single web page."""
        body: dict[str, Any] = {"url": url, "engine": engine, "scroll": scroll, "timeout": timeout}
        if wait_for:
            body["wait_for"] = wait_for
        if wait_until:
            body["wait_until"] = wait_until
        if settle_ms is not None:
            body["settle_ms"] = settle_ms
        if block_resources is not None:
            body["block_resources"] = block_resources
        if capture_json:
            body["capture_json"] = capture_json
        return self._client._post("/v1/scrape/fetch", json=body)

    def extract(self, *, html: str, selectors: dict[str, Any]) -> dict:
        """Extract data from HTML using CSS/XPath selectors."""
        return self._client._post("/v1/scrape/extract", json={"html": html, "selectors": selectors})

    def ocr(self, *, image_url: str, language: str = "spa+eng") -> dict:
        """Run OCR on an image."""
        return self._client._post("/v1/scrape/ocr", json={"image_url": image_url, "language": language})

    def parse_pdf(self, *, pdf_url: str, extract_tables: bool = False) -> dict:
        """Parse a PDF document."""
        return self._client._post(
            "/v1/scrape/parse_pdf",
            json={"pdf_url": pdf_url, "extract_tables": extract_tables},
        )

    def transcribe(self, *, media_url: str, language: str = "es") -> dict:
        """Transcribe audio/media."""
        return self._client._post(
            "/v1/scrape/transcribe",
            json={"media_url": media_url, "language": language},
        )

    def deep_archive(
        self,
        *,
        url: str,
        target_dir: str,
        interaction_selectors: list[str] | None = None,
        download_patterns: list[str] | None = None,
        wait_settle_ms: int = 2000,
        timeout_ms: int = 60000,
    ) -> dict:
        """Deep archival scrape with interaction and download patterns."""
        body: dict[str, Any] = {
            "url": url,
            "target_dir": target_dir,
            "wait_settle_ms": wait_settle_ms,
            "timeout_ms": timeout_ms,
        }
        if interaction_selectors:
            body["interaction_selectors"] = interaction_selectors
        if download_patterns:
            body["download_patterns"] = download_patterns
        return self._client._post("/v1/scrape/deep_archive", json=body)

    def captcha_status(self) -> dict:
        """Check CAPTCHA solver configuration status."""
        return self._client._get("/v1/scrape/captcha/status")

    def captcha_test(
        self,
        *,
        captcha_type: str = "recaptcha_v2",
        site_key: str,
        page_url: str,
        action: str | None = None,
    ) -> dict:
        """Test the CAPTCHA solver."""
        body: dict[str, Any] = {
            "captcha_type": captcha_type,
            "site_key": site_key,
            "page_url": page_url,
        }
        if action:
            body["action"] = action
        return self._client._post("/v1/scrape/captcha/test", json=body)

    def health(self) -> dict:
        """Scraper health check."""
        return self._client._get("/v1/scrape/health")

    # v2 Scraper resources
    def list_workflows(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/scraper/v2/workflows", params={"limit": limit})

    def list_proxies(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/scraper/v2/proxies", params={"limit": limit})

    def list_schedules(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/scraper/v2/schedules", params={"limit": limit})

    def list_runs(self, *, task_id: str | None = None, limit: int = 100) -> list[dict]:
        params: dict[str, Any] = {"limit": limit}
        if task_id:
            params["task_id"] = task_id
        return self._client._get("/v1/scraper/v2/runs", params=params)

    def list_fingerprints(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/scraper/v2/fingerprints", params={"limit": limit})

    def generate_fingerprint(self) -> dict:
        return self._client._post("/v1/scraper/v2/fingerprints/generate")


# ===================================================================
# ML Platform
# ===================================================================


class MLResource(_Resource):
    """ML platform: models, experiments, agents, endpoints."""

    def list_models(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ml/models", params={"limit": limit})

    def get_model(self, model_id: str) -> dict:
        return self._client._get(f"/v1/ml/models/{model_id}")

    def create_model(self, *, name: str, description: str = "", **kwargs: Any) -> dict:
        body: dict[str, Any] = {"name": name, "description": description, **kwargs}
        return self._client._post("/v1/ml/models", json=body)

    def create_model_version(self, model_id: str, **kwargs: Any) -> dict:
        return self._client._post(f"/v1/ml/models/{model_id}/versions", json=kwargs)

    def set_model_stage(self, version_id: str, stage: str) -> dict:
        return self._client._put(f"/v1/ml/model-versions/{version_id}/stage", json={"stage": stage})

    def list_experiments(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ml/experiments", params={"limit": limit})

    def get_experiment(self, experiment_id: str) -> dict:
        return self._client._get(f"/v1/ml/experiments/{experiment_id}")

    def create_experiment(self, *, name: str, **kwargs: Any) -> dict:
        body: dict[str, Any] = {"name": name, **kwargs}
        return self._client._post("/v1/ml/experiments", json=body)

    def create_run(self, experiment_id: str, **kwargs: Any) -> dict:
        return self._client._post(f"/v1/ml/experiments/{experiment_id}/runs", json=kwargs)

    def log_metrics(self, run_id: str, metrics: dict) -> dict:
        return self._client._put(f"/v1/ml/runs/{run_id}/metrics", json=metrics)

    def list_agents(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ml/agents", params={"limit": limit})

    def get_agent(self, agent_id: str) -> dict:
        return self._client._get(f"/v1/ml/agents/{agent_id}")

    def create_agent(self, *, name: str, **kwargs: Any) -> dict:
        body: dict[str, Any] = {"name": name, **kwargs}
        return self._client._post("/v1/ml/agents", json=body)

    def update_agent(self, agent_id: str, **kwargs: Any) -> dict:
        return self._client._put(f"/v1/ml/agents/{agent_id}", json=kwargs)

    def delete_agent(self, agent_id: str) -> dict:
        return self._client._delete(f"/v1/ml/agents/{agent_id}")

    def list_endpoints(self, *, limit: int = 100) -> list[dict]:
        return self._client._get("/v1/ml/endpoints", params={"limit": limit})

    def create_endpoint(self, **kwargs: Any) -> dict:
        return self._client._post("/v1/ml/endpoints", json=kwargs)


# ===================================================================
# Governance
# ===================================================================


class GovernanceResource(_Resource):
    """Data governance: lineage, schemas, quotas, policies, classifications."""

    def search(self, query: str, *, limit: int = 20) -> list[dict]:
        """Search governed datasets."""
        return self._client._get("/v1/governance/search", params={"q": query, "limit": limit})

    def lineage(self, urn: str) -> dict:
        """Get data lineage graph for a dataset URN."""
        return self._client._get(f"/v1/governance/lineage/{urn}")

    def schema(self, urn: str) -> dict:
        """Get schema for a dataset URN."""
        return self._client._get(f"/v1/governance/schema/{urn}")

    def list_classifications(self) -> list[dict]:
        return self._client._get("/v1/governance/classifications")

    def create_classification(self, **kwargs: Any) -> dict:
        return self._client._post("/v1/governance/classifications", json=kwargs)

    def list_column_masks(self) -> list[dict]:
        return self._client._get("/v1/governance/column-masks")

    def create_column_mask(self, **kwargs: Any) -> dict:
        return self._client._post("/v1/governance/column-masks", json=kwargs)

    def list_row_security_policies(self) -> list[dict]:
        return self._client._get("/v1/governance/row-security-policies")

    def create_row_security_policy(self, **kwargs: Any) -> dict:
        return self._client._post("/v1/governance/row-security-policies", json=kwargs)

    def quota_tiers(self) -> list[dict]:
        return self._client._get("/v1/governance/quotas/tiers")

    def quota_usage(self) -> dict:
        return self._client._get("/v1/governance/quotas/usage")

    def quota_limits(self) -> dict:
        return self._client._get("/v1/governance/quotas/limits")

    def set_quota_tier(self, *, tenant_id: str, tier: str) -> dict:
        return self._client._post(
            "/v1/governance/quotas/set-tier",
            json={"tenant_id": tenant_id, "tier": tier},
        )


# ===================================================================
# Auth
# ===================================================================


class AuthResource(_Resource):
    """Authentication: login, logout, refresh, current user."""

    def login(self, *, username: str, password: str) -> dict:
        """Authenticate and get tokens."""
        return self._client._post(
            "/v1/auth/login",
            json={"username": username, "password": password},
        )

    def logout(self) -> dict:
        """Invalidate current session."""
        return self._client._post("/v1/auth/logout")

    def refresh(self, refresh_token: str) -> dict:
        """Refresh an access token."""
        return self._client._post("/v1/auth/refresh", json={"refresh_token": refresh_token})

    def me(self) -> dict:
        """Get current user info."""
        return self._client._get("/v1/auth/me")

    def token(self, **kwargs: Any) -> dict:
        """Get a token (OAuth2-compatible)."""
        return self._client._post("/v1/auth/token", json=kwargs)


# ===================================================================
# Search (Vector / Full-Text)
# ===================================================================


class SearchResource(_Resource):
    """Vector and full-text search."""

    def index(self, *, text: str, item_id: str | None = None, metadata: dict | None = None) -> dict:
        body: dict[str, Any] = {"text": text}
        if item_id:
            body["item_id"] = item_id
        if metadata:
            body["metadata"] = metadata
        return self._client._post("/v1/search/index", json=body)

    def query(self, *, query: str, limit: int = 10, **kwargs: Any) -> dict:
        body: dict[str, Any] = {"query": query, "limit": limit, **kwargs}
        return self._client._post("/v1/search/query", json=body)

    def get_item(self, item_id: str) -> dict:
        return self._client._get(f"/v1/search/{item_id}")

    def delete_item(self, item_id: str) -> dict:
        return self._client._delete(f"/v1/search/{item_id}")


# ===================================================================
# Intent Engine
# ===================================================================


class IntentResource(_Resource):
    """Natural language intent engine."""

    def query(self, *, text: str, context: dict | None = None) -> dict:
        body: dict[str, Any] = {"text": text}
        if context:
            body["context"] = context
        return self._client._post("/v1/intent/intent/query", json=body)

    def execute(self, *, text: str, context: dict | None = None) -> dict:
        body: dict[str, Any] = {"text": text}
        if context:
            body["context"] = context
        return self._client._post("/v1/intent/intent/execute", json=body)

    def config(self) -> dict:
        return self._client._get("/v1/intent/intent/config")

    def update_config(self, **kwargs: Any) -> dict:
        return self._client._put("/v1/intent/intent/config", json=kwargs)

    def cache_stats(self) -> dict:
        return self._client._get("/v1/intent/intent/cache/stats")

    def cache_clear(self) -> dict:
        return self._client._post("/v1/intent/intent/cache/clear")


# ===================================================================
# Capsules
# ===================================================================


class CapsulesResource(_Resource):
    """Intelligence Recipes / Capsules lifecycle."""

    def registry(self) -> list[dict]:
        return self._client._get("/v1/capsules/registry")

    def get_capsule(self, capsule_id: str) -> dict:
        return self._client._get(f"/v1/capsules/registry/{capsule_id}")

    def create(self, *, name: str, **kwargs: Any) -> dict:
        body: dict[str, Any] = {"name": name, **kwargs}
        return self._client._post("/v1/capsules/create", json=body)

    def install(self, *, capsule_id: str, parameter_overrides: dict | None = None) -> dict:
        body: dict[str, Any] = {"capsule_id": capsule_id}
        if parameter_overrides:
            body["parameter_overrides"] = parameter_overrides
        return self._client._post("/v1/capsules/install", json=body)

    def installed(self) -> list[dict]:
        return self._client._get("/v1/capsules/installed")

    def run(self, *, installation_id: str, parameter_values: dict | None = None) -> dict:
        body: dict[str, Any] = {"installation_id": installation_id}
        if parameter_values:
            body["parameter_values"] = parameter_values
        return self._client._post("/v1/capsules/run", json=body)

    def uninstall(self, installation_id: str) -> dict:
        return self._client._delete(f"/v1/capsules/installed/{installation_id}")


# ===================================================================
# Discovery
# ===================================================================


class DiscoveryResource(_Resource):
    """Service discovery and scanning."""

    def list_services(self) -> list[dict]:
        return self._client._get("/v1/discovery/services")

    def get_service(self, name: str) -> dict:
        return self._client._get(f"/v1/discovery/services/{name}")

    def create_service(self, **kwargs: Any) -> dict:
        return self._client._post("/v1/discovery/services", json=kwargs)

    def scan(self, **kwargs: Any) -> dict:
        return self._client._post("/v1/discovery/scan", json=kwargs)


# ===================================================================
# Admin
# ===================================================================


class AdminResource(_Resource):
    """Admin panel: dashboard, settings, audit, tenants."""

    def dashboard(self) -> dict:
        return self._client._get("/v1/admin/dashboard")

    def list_tenants(self) -> list[dict]:
        return self._client._get("/v1/admin/tenants")

    def settings(self) -> dict:
        return self._client._get("/v1/admin/settings")

    def update_setting(self, key: str, value: Any) -> dict:
        return self._client._put(f"/v1/admin/settings/{key}", json={"value": value})

    def audit_log(self, *, limit: int = 50) -> list[dict]:
        return self._client._get("/v1/admin/audit", params={"limit": limit})

    def list_admin_jobs(self, *, limit: int = 50) -> list[dict]:
        return self._client._get("/v1/admin/jobs", params={"limit": limit})

    def get_admin_job(self, job_id: str) -> dict:
        return self._client._get(f"/v1/admin/jobs/{job_id}")

    def cancel_admin_job(self, job_id: str) -> dict:
        return self._client._post(f"/v1/admin/jobs/{job_id}/cancel")

    def sql_execute(self, sql: str) -> dict:
        return self._client._post("/v1/admin/sql/execute", json={"sql": sql})

    def sql_tables(self) -> list[dict]:
        return self._client._get("/v1/admin/sql/tables")


# ===================================================================
# Pagination Helper
# ===================================================================


def _paginate(
    resource: _Resource,
    path: str,
    *,
    params: dict | None = None,
    page_size: int = 100,
    max_pages: int = 100,
) -> Iterator[dict]:
    """Generic pagination helper. Yields items across pages."""
    offset = 0
    for _ in range(max_pages):
        p = dict(params or {})
        p["limit"] = page_size
        p["offset"] = offset
        items = resource._client._get(path, params=p)
        if not items:
            break
        yield from items
        if len(items) < page_size:
            break
        offset += page_size


# ===================================================================
# Main Client
# ===================================================================


class VoyantClient:
    """
    Voyant API client.

    Args:
        base_url: Base URL of the Voyant API (e.g. ``http://localhost:8000``).
        token: Bearer token for authentication.
        timeout: Default HTTP timeout in seconds.
        tenant_id: Optional tenant ID (sent as ``X-Tenant-ID`` header).

    Example::

        client = VoyantClient(
            base_url="http://localhost:8000",
            token="your-bearer-token",
        )
        sources = client.sources.list()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        token: str = "",
        timeout: float = _DEFAULT_TIMEOUT,
        tenant_id: str = "",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._tenant_id = tenant_id
        self._http = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
        )

        # Resource namespaces
        self.sources = SourcesResource(self)
        self.jobs = JobsResource(self)
        self.artifacts = ArtifactsResource(self)
        self.sql = SQLResource(self)
        self.ontology = OntologyResource(self)
        self.scraper = ScraperResource(self)
        self.ml = MLResource(self)
        self.governance = GovernanceResource(self)
        self.auth = AuthResource(self)
        self.search = SearchResource(self)
        self.intent = IntentResource(self)
        self.capsules = CapsulesResource(self)
        self.discovery = DiscoveryResource(self)
        self.admin = AdminResource(self)

    def _headers(self) -> dict[str, str]:
        """Build request headers."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        if self._tenant_id:
            headers["X-Tenant-ID"] = self._tenant_id
        return headers

    def _handle_response(self, resp: httpx.Response) -> Any:
        """Handle API response, raising errors for non-2xx status codes."""
        if resp.status_code >= 400:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise VoyantAPIError(
                message=f"API error {resp.status_code}: {detail}",
                status_code=resp.status_code,
                detail=detail,
            )
        if resp.status_code == 204:
            return None
        return resp.json()

    def _get(self, path: str, *, params: dict | None = None) -> Any:
        resp = self._http.get(path, headers=self._headers(), params=params)
        return self._handle_response(resp)

    def _post(self, path: str, *, json: dict | None = None) -> Any:
        resp = self._http.post(path, headers=self._headers(), json=json)
        return self._handle_response(resp)

    def _put(self, path: str, *, json: dict | None = None) -> Any:
        resp = self._http.put(path, headers=self._headers(), json=json)
        return self._handle_response(resp)

    def _patch(self, path: str, *, json: dict | None = None) -> Any:
        resp = self._http.patch(path, headers=self._headers(), json=json)
        return self._handle_response(resp)

    def _delete(self, path: str) -> Any:
        resp = self._http.delete(path, headers=self._headers())
        return self._handle_response(resp)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._http.close()

    def __enter__(self) -> VoyantClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def health(self) -> dict:
        """Check API health."""
        resp = self._http.get("/health")
        resp.raise_for_status()
        return resp.json()
