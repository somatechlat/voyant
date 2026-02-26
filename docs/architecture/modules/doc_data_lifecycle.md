# Voyant Documentation: Data Lifecycle (`apps/discovery`, `apps/ingestion`, `apps/governance`)

## 1. Overview
This module group manages the lifecycle of external data coming into the Voyant system. It covers finding data (Discovery), bringing it in (Ingestion), and tracking/controlling its usage (Governance).

## 2. File-by-File Breakdown

### `apps/discovery/api.py`
Provides tools for discovering, registering, and managing external data sources and API services.
*   **Sources Router (`/sources`):**
    *   `/discover`: Takes a "hint" (like a connection string or URL) and uses `detect_source_type` to evaluate the source type, properties, suggested connector, and a confidence score.
    *   `POST /` & `GET /`: Standard CRUD for `Source` objects, securely scoped by `tenant_id`. Stores credentials and connection configurations.
*   **Discovery Router (`/discovery`):**
    *   `/services` (Register & List): Allows agents to register external services by providing a `base_url` or an OpenAPI `spec_url`.
    *   `/scan`: Takes an OpenAPI URL, parses it using `SpecParser`, and returns a preview of available endpoints.

### `apps/ingestion/api.py`
Responsible for triggering and managing long-running data sync jobs using Temporal.
*   **Trigger (`POST /ingest`):** Takes a `source_id`, `mode` (full/incremental), and an optional list of `tables`. Validates that the `Source` exists under the current `tenant_id`. It then dispatches an `IngestDataWorkflow` to the Temporal cluster queue (`temporal_task_queue`).
*   **Tracking (`GET /jobs`, `GET /jobs/{job_id}`):** Lists and retrieves the status of ingestion jobs (e.g., PENDING, QUEUED, RUNNING, FAILED).
*   **Cancellation (`POST /jobs/{job_id}/cancel`):** Connects to the Temporal client to send a cancellation signal to the running workflow handle, terminating the ingestion process safely.

### `apps/governance/api.py`
The control plane for managing API quotas, tracking data lineage, and retrieving schema metadata. Integrates heavily with a backend DataHub GraphQL API.
*   **Search & Lineage (`/search`, `/lineage/{urn}`):** Uses `httpx` to send GraphQL queries to `settings.datahub_gms_url`. Retrieves upstream and downstream dependencies for datasets (nodes and edges), which is critical for understanding data provenance.
*   **Schema (`/schema/{urn}`):** Retrieves precise field schemas (name, type, nullable, description) from DataHub.
*   **Quotas (`/quotas`):** Retrieves and manages tenant quotas using `apps.core.lib.tenant_quotas`.
    *   Exposes detailed metrics: Jobs executed vs. limit, storage GB used vs. limit, active sources vs. limit.

## 3. Integration Patterns
*   **Temporal Integration:** The Ingestion API does not perform data movement itself. It is a strictly asynchronous trigger that passes parameters to an `IngestDataWorkflow` runner.
*   **DataHub Integration:** Governance acts as a proxy to a DataHub GraphQL service to fetch enterprise lineage and schema information.
*   **Authentication & Multi-Tenancy:** All endpoints in these modules are protected by `auth_guard` (via Ninja) and enforce strict `tenant_id` filtering.
