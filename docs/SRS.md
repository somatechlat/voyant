# Voyant v3.0.0 Software Requirements Specification (SRS)

Document ID: VOYANT-SRS-3.0.0
Status: Canonical
Date: 2025-12-17

## 1. Introduction
### 1.1 Purpose
This document defines the functional and non-functional requirements of Voyant v3.0.0 as implemented in the current codebase. It is the single canonical specification for system behavior, interfaces, and operational constraints.

### 1.2 Scope
Voyant is an autonomous data intelligence service that exposes data discovery, ingestion, profiling, quality checks, analytics, and artifact access via REST APIs and MCP tools. The system integrates with external services (Temporal, Kafka, Trino, MinIO, DataHub, Keycloak, Lago) and runs as a containerized stack.

### 1.3 Definitions and Abbreviations
- API: Application Programming Interface
- MCP: Model Context Protocol (JSON-RPC 2.0)
- PII: Personally Identifiable Information
- Temporal: Workflow orchestration engine
- Trino: SQL query engine
- MinIO: S3-compatible object storage
- DataHub: Metadata governance platform
- SomaAgentHub: Orchestration and policy hub (gateway, orchestrator, identity, memory).
- SomaAgent01: Agent operating system (Django) with tool registry and MCP clients.
- Apache Iceberg: Lakehouse table format with versioned datasets
- Apache Flink: Stream processing engine
- Apache Ranger: Data access policy enforcement
- Apache Atlas: Metadata and lineage governance
- Apache SkyWalking: APM and distributed tracing
- Apache NiFi: Visual dataflow ingestion and routing
- Apache Superset: BI and data exploration
- Apache Druid: Real-time OLAP datastore
- Apache Pinot: Low-latency OLAP datastore
- Apache Tika: Document content extraction

### 1.4 Document Conventions
- The word "shall" denotes a mandatory requirement.
- Statements in present tense describe current implementation behavior.

### 1.5 Exclusions
- Roadmap, vision, and future work are intentionally excluded from this SRS.

## 2. Overall Description
### 2.1 Product Perspective
Voyant is a Django (Ninja) service with an optional MCP server. It orchestrates workflows via Temporal, executes SQL via Trino, stores artifacts in MinIO, and integrates with external systems for metadata and billing. Voyant can be registered as a tool provider for SomaAgentHub and SomaAgent01, receiving upstream context and publishing analysis outputs back into the Soma stack.

### 2.2 Product Functions
- Provide REST API endpoints for health, source discovery, job execution, SQL query, artifacts, presets, discovery catalog, governance, and semantic search.
- Provide MCP tools for data operations.
- Orchestrate workflows using Temporal activities and workflows.
- Provide a one-call analyze endpoint for end-to-end agent workflows.
- Support plugin-based analyzers and generators.
- Emit Kafka events and validate event schemas.
- Provide multi-tenant request scoping.
- Integrate with Keycloak for optional authentication.
- Support secrets backends (env, k8s, vault, file, in-memory).
- Apply CORS middleware with configurable origins.
- Integrate with SomaAgentHub (gateway, orchestrator, policy, memory) for agent session execution.
- Expose MCP tool metadata for SomaAgent01 tool registry and tool invocation flows.
- Provide lakehouse storage using Apache Iceberg.
- Provide streaming analytics using Apache Flink.
- Provide data access policy enforcement using Apache Ranger.
- Provide metadata governance using Apache Atlas.
- Provide distributed tracing and APM using Apache SkyWalking.
- Provide ingestion routing and transformation using Apache NiFi.
- Provide BI visualization via Apache Superset.
- Provide low-latency OLAP via Apache Druid and Apache Pinot.
- Provide document extraction via Apache Tika.

### 2.3 User Classes
- Operators: deploy and monitor the stack.
- Analysts: run profiling, quality, and analytics jobs.
- Integrators: connect data sources and consume artifacts via APIs or MCP.

### 2.4 Operating Environment
- Python 3.11+ runtime.
- Docker Compose or Kubernetes deployment.
- External services: PostgreSQL, Redis, Kafka, Temporal, Trino, MinIO, DataHub, Keycloak, Lago.

### 2.5 Constraints
- SQL execution uses Trino only; non-SELECT statements are rejected.
- Profiling uses lightweight pandas summaries rather than full ydata-profiling.
- The quality job endpoint records a job but does not start a workflow in the current implementation.
- Streaming analytics require Kafka topics and Flink job deployment.

### 2.6 Assumptions and Dependencies
- External services are reachable and configured via environment variables.
- Kafka and Temporal are optional but required for full event and workflow features.
- SomaAgentHub services are reachable when Soma integration is enabled.

## 3. Functional Requirements
### FR-1: API Service
- FR-1.1 The system shall expose REST endpoints via Django Ninja (Django).
- FR-1.2 The system shall include API version negotiation middleware and return X-API-Version.
- FR-1.3 The system shall add request IDs to responses.

### FR-2: Health and Status
- FR-2.1 The system shall provide `/health`, `/ready`, `/healthz`, `/readyz`, and `/status` endpoints.
- FR-2.2 `/ready` shall check DuckDB connectivity, R engine availability, Temporal connectivity, and circuit breaker state.

### FR-3: Source Discovery and Management
- FR-3.1 The system shall expose `/v1/sources/discover` to classify hints into source types.
- FR-3.2 The system shall provide CRUD-like source endpoints backed by PostgreSQL for the current tenant.

### FR-4: Job Management
- FR-4.1 The system shall expose `/v1/jobs/ingest`, `/v1/jobs/profile`, and `/v1/jobs/quality`.
- FR-4.2 Ingest and profile jobs shall trigger Temporal workflows.
- FR-4.3 Job records shall be stored in PostgreSQL for the current tenant.
- FR-4.4 The quality job endpoint shall return a queued job record without workflow execution.
- FR-4.5 The system shall provide a one-call analyze endpoint for end-to-end analysis.

### FR-5: Preset Workflows
- FR-5.1 The system shall expose `/v1/presets` endpoints for preset listing, retrieval, and execution.
- FR-5.2 Preset execution shall create a queued job record in PostgreSQL.

### FR-6: SQL Execution
- FR-6.1 The system shall expose `/v1/sql/query`, `/v1/sql/tables`, and `/v1/sql/tables/{table}/columns`.
- FR-6.2 SQL execution shall validate allowed statement types (SELECT, WITH, SHOW, DESCRIBE, EXPLAIN) and apply a LIMIT when missing.
- FR-6.3 SQL execution shall use Trino.

### FR-7: Artifacts
- FR-7.1 The system shall list artifacts stored in MinIO via `/v1/artifacts/{job_id}`.
- FR-7.2 The system shall provide presigned URL retrieval for artifacts and direct streaming download.

### FR-8: Discovery Catalog
- FR-8.1 The system shall allow registration and listing of service definitions via `/v1/discovery` endpoints.
- FR-8.2 The system shall parse OpenAPI specs when spec URLs are provided.

### FR-9: Governance (DataHub)
- FR-9.1 The system shall expose `/v1/governance/search` and `/v1/governance/lineage/{urn}`.
- FR-9.2 The system shall query DataHub GraphQL for search and lineage data.

### FR-10: Semantic Search
- FR-10.1 The system shall expose `/v1/search/query` and `/v1/search/index` for vector search.
- FR-10.2 The system shall embed text and query a vector store backend.
- FR-10.3 The vector store shall be an in-memory index with optional file persistence.

### FR-11: MCP Server
- FR-11.1 The system shall expose an MCP server implementing JSON-RPC 2.0 tools:
  - `voyant.discover`, `voyant.connect`, `voyant.ingest`, `voyant.profile`, `voyant.quality`, `voyant.analyze`, `voyant.kpi`, `voyant.status`, `voyant.artifact`, `voyant.sql`, `voyant.search`, `voyant.lineage`.
- FR-11.2 The MCP server shall proxy requests to the REST API.

### FR-12: Workflow Orchestration
- FR-12.1 The system shall implement Temporal workflows for ingest, profile, and analyze operations.
- FR-12.2 The system shall implement operational workflows for anomaly detection, sentiment, quality fixes, and forecasting.

### FR-13: Activities and Analytics
- FR-13.1 The system shall implement ingest, profile, analysis, generation, and operational activities.
- FR-13.2 Profiling shall use adaptive sampling and pandas summaries.
- FR-13.3 Analysis activities shall run registered analyzer plugins.

### FR-14: Plugin Registry
- FR-14.1 The system shall provide a registry for analyzer and generator plugins with metadata.
- FR-14.2 The system shall support core vs. optional plugin execution semantics.

### FR-15: Ingestion Utilities
- FR-15.1 The system shall provide an Airbyte client for sync operations.
- FR-15.2 The system shall provide direct file ingestion into DuckDB.
- FR-15.3 The system shall support unstructured document parsing using `unstructured`.

### FR-16: Security and Authentication
- FR-16.1 The system shall include a Keycloak-based JWT authentication module.
- FR-16.2 The system shall support multi-tenant scoping via `X-Tenant-ID` header.

### FR-17: Secrets Management
- FR-17.1 The system shall provide pluggable secret backends (env, k8s, vault, file, in-memory).
- FR-17.2 File secrets shall optionally use Fernet encryption when a key is provided.

### FR-18: Events
- FR-18.1 The system shall emit Kafka events using a typed event schema registry.
- FR-18.2 The system shall validate payloads before emission.

### FR-19: Billing
- FR-19.1 The system shall provide a Lago billing client for usage events and customer/subscription operations.

### FR-20: Lakehouse Storage (Apache Iceberg)
- FR-20.1 The system shall store analytical tables in Apache Iceberg.
- FR-20.2 The system shall maintain versioned table snapshots for reproducibility.

### FR-21: Streaming Analytics (Apache Flink)
- FR-21.1 The system shall support streaming ingestion pipelines for Kafka topics.
- FR-21.2 The system shall compute continuous KPIs and anomaly detection on streams.

### FR-22: Policy Enforcement (Apache Ranger)
- FR-22.1 The system shall enforce data access policies at query time.
- FR-22.2 The system shall log policy decisions for auditability.

### FR-23: Governance (Apache Atlas)
- FR-23.1 The system shall publish metadata and lineage to Apache Atlas.
- FR-23.2 The system shall map Voyant sources and artifacts to Atlas entities.

### FR-24: Observability (Apache SkyWalking)
- FR-24.1 The system shall emit distributed traces to Apache SkyWalking.
- FR-24.2 The system shall correlate traces with job and tenant identifiers.

### FR-25: Ingestion Routing (Apache NiFi)
- FR-25.1 The system shall support NiFi-based ingestion pipelines for external sources.
- FR-25.2 The system shall register NiFi flows as managed sources.

### FR-26: BI Access (Apache Superset)
- FR-26.1 The system shall expose curated datasets for Superset dashboards.
- FR-26.2 The system shall publish artifact links for Superset consumption.

### FR-27: OLAP Stores (Apache Druid and Pinot)
- FR-27.1 The system shall support optional export of curated data to Druid and Pinot.
- FR-27.2 The system shall expose low-latency query endpoints for OLAP workloads.

### FR-28: Document Extraction (Apache Tika)
- FR-28.1 The system shall parse documents with Apache Tika when configured.
- FR-28.2 The system shall store extracted text with provenance metadata.

### FR-29: Soma Stack Integration (SomaAgentHub + SomaAgent01)
- FR-29.1 The system shall accept upstream context headers from SomaAgentHub (tenant, user, session, trace).
- FR-29.2 The system shall validate or delegate identity tokens issued by SomaAgentHub identity services.
- FR-29.3 The system shall request policy decisions from SomaAgentHub Policy Engine for sensitive actions.
- FR-29.4 The system shall publish job status updates to SomaAgentHub Orchestrator when configured.
- FR-29.5 The system shall persist analysis summaries and artifacts to SomaAgentHub Memory Gateway when configured.
- FR-29.6 The system shall expose MCP tool metadata suitable for SomaAgent01 tool registry ingestion.

## 4. External Interfaces
### 4.1 REST API
Base path: `/v1` for most endpoints.
Key endpoints:
- Health: `/health`, `/ready`, `/healthz`, `/readyz`, `/status`
- Sources: `/v1/sources`, `/v1/sources/discover`
- Jobs: `/v1/jobs/ingest`, `/v1/jobs/profile`, `/v1/jobs/quality`
- Jobs (detail): `/v1/jobs/{job_id}`
- Analyze: `/v1/analyze`
- Presets: `/v1/presets`
- SQL: `/v1/sql/query`, `/v1/sql/tables`, `/v1/sql/tables/{table}/columns`
- Artifacts: `/v1/artifacts/{job_id}`, `/v1/artifacts/{job_id}/{artifact_type}`
- Discovery: `/v1/discovery/services`, `/v1/discovery/scan`
- Governance: `/v1/governance/search`, `/v1/governance/lineage/{urn}`
- Search: `/v1/search/query`, `/v1/search/index`

### 4.2 MCP Interface
JSON-RPC 2.0 tools over HTTP/stdio via `voyant.mcp.server`.

### 4.3 Messaging
Kafka topics (default):
- `voyant.jobs`, `voyant.quality.alerts`, `voyant.lineage`, `voyant.billing.events`, `voyant.audit`.

### 4.4 Storage
- MinIO bucket: `artifacts` for artifact objects.
- DuckDB file for local profiling and ingestion utilities.
- Iceberg tables stored in object storage for analytical datasets.
- Druid and Pinot clusters for low-latency OLAP (optional).

### 4.5 Headers and Versioning
- Request header `X-Request-ID` may be provided; otherwise a UUID is generated and echoed in responses.
- Request header `X-Tenant-ID` scopes tenant context (default: `default`).
- API version negotiation uses `Accept: application/vnd.voyant.vN+json` or `X-API-Version: vN`.

### 4.6 Soma Stack Integration Interfaces
Inbound from SomaAgentHub:
- Context headers: `X-Tenant-ID`, `X-User-ID`, `X-Soma-Session-ID`, `X-Request-ID`, `traceparent`.
- Auth header: `Authorization: Bearer <token>` (issued by identity service).
Outbound to SomaAgentHub (configurable base URLs):
- Policy Engine: `POST /v1/evaluate` with tenant/user/session metadata.
- Memory Gateway: `POST /v1/remember`, `POST /v1/rag/retrieve` for summary storage and recall.
- Orchestrator: `/v1/sessions/*` for session updates when required.
Outbound to SomaAgent01:
- MCP tool registration and tool invocation through SomaAgent01 tool registry and MCP client settings.

## 5. Data Requirements
- Job and source records are stored in PostgreSQL via Django ORM.
- Job records may include upstream `soma_session_id` when provided.
- Artifacts are stored in MinIO and referenced by object keys.
- Iceberg tables store curated datasets with snapshot metadata.
- Stream outputs may be persisted to Iceberg, Druid, or Pinot.
- Soma memory entries store analysis summaries keyed by tenant/session/job when configured.

## 6. Security Requirements
- JWT validation via Keycloak with JWKS retrieval.
- Tenant scoping via `X-Tenant-ID` header.
- SQL validation to reject mutating statements.
- Secrets must not be logged and should be retrieved via configured backend.
- Service-to-service requests from SomaAgentHub shall use validated identity tokens or mTLS.

## 7. Observability Requirements
- Structured logging with correlation and workflow context is provided in core utilities.
- Prometheus metrics are exposed via a separate server in the worker (`voyant_*` metrics).
- A metrics mode subsystem exists but is not wired to an HTTP endpoint in the API.
- Distributed tracing shall be exported to Apache SkyWalking when configured.
- Trace context from SomaAgentHub shall be propagated when present.

## 8. Quality Requirements (ISO/IEC 25010)
### 8.1 Performance Efficiency
- Health endpoints should respond quickly and avoid heavy operations.
- SQL queries are limited to a maximum row count.
- Profiling uses adaptive sampling to avoid full-table scans on large datasets.

### 8.2 Reliability
- Circuit breakers shall protect external service calls in ingestion and analysis clients.
- Temporal workflows shall use retry policies for transient failures.

### 8.3 Availability and Recoverability
- Readiness endpoints shall report dependency status for routing decisions.
- Artifact retrieval shall return a 503 status if object storage is unavailable.

### 8.4 Security
- See Section 6 for authentication, tenant isolation, and secrets handling.

### 8.5 Maintainability
- Plugin registration and metadata shall allow new analyzers or generators without API changes.
- Workflow activities shall be modular and reusable.

### 8.6 Portability
- The system shall run in Docker Compose and Kubernetes environments.

### 8.7 Usability and Operability
- API responses shall include request and version headers for traceability.
- Structured logs shall include correlation or workflow context when available.

### 8.8 Compatibility and Interoperability
- REST and MCP interfaces shall operate independently.
- Kafka event payloads shall validate against registered schemas.

## 9. Deployment Requirements
- Docker Compose stack includes API, MCP server, Temporal, Kafka, Redis, Postgres, MinIO, Trino, DataHub, Keycloak, Lago, and worker.
- Environment variables configure all service endpoints and credentials.
- Production deployment shall include Apache Iceberg, Ranger, Atlas, SkyWalking, NiFi, Superset, and optional Druid/Pinot clusters.
- When deployed with the Soma stack, Voyant shall run behind SomaAgentHub Gateway/Orchestrator with service-to-service auth.

## 10. Limitations
- No API-level metrics endpoint is implemented in the Django application.
- Health endpoints bypass API version negotiation.
- Soma stack integration endpoints are not wired in the current implementation.

## 11. Verification and Acceptance Criteria
- V-1 Health endpoints return 200 with JSON status payloads.
- V-2 SQL endpoint rejects mutating statements and enforces LIMIT.
- V-3 MCP `tools/list` exposes the Voyant tool set.
- V-4 Artifact retrieval returns a presigned URL when MinIO is available.
- V-5 Kafka event emission validates payloads against registered schemas.
- V-6 Iceberg tables can be queried via Trino.
- V-7 Flink streaming pipeline produces continuous KPIs.
- V-8 Ranger policies deny unauthorized queries.
- V-9 SkyWalking traces show API → workflow → activity chains.
- V-10 Soma policy engine receives evaluate requests for sensitive actions when enabled.
- V-11 Soma memory gateway stores analysis summaries when enabled.

## 12. Requirements Traceability (Code Modules)
| Requirement | Primary Modules |
| --- | --- |
| FR-1 | `voyant_project/urls.py`, `voyant_app/api.py`, `voyant/api/middleware.py` |
| FR-2 | `voyant_project/urls.py` |
| FR-3 | `voyant_app/api.py` |
| FR-4 | `voyant_app/api.py`, `voyant/workflows/ingest_workflow.py`, `voyant/workflows/profile_workflow.py` |
| FR-5 | `voyant_app/api.py` |
| FR-6 | `voyant_app/api.py`, `voyant/core/trino.py` |
| FR-7 | `voyant_app/api.py` |
| FR-8 | `voyant_app/api.py`, `voyant/discovery/spec_parser.py` |
| FR-9 | `voyant_app/api.py` |
| FR-10 | `voyant_app/api.py`, `voyant/core/vector_store.py`, `voyant/core/embeddings.py` |
| FR-11 | `voyant/mcp/server.py` |
| FR-12 | `voyant/workflows/ingest_workflow.py`, `voyant/workflows/profile_workflow.py`, `voyant/workflows/operational_workflows.py` |
| FR-13 | `voyant/activities/ingest_activities.py`, `voyant/activities/profile_activities.py`, `voyant/activities/analysis_activities.py` |
| FR-14 | `voyant/core/plugin_registry.py` |
| FR-15 | `voyant/ingestion/airbyte_client.py`, `voyant/ingestion/direct_utils.py`, `voyant/ingestion/unstructured_utils.py` |
| FR-16 | `voyant/security/auth.py`, `voyant/api/middleware.py` |
| FR-17 | `voyant/security/secrets.py`, `voyant/core/secrets.py` |
| FR-18 | `voyant/core/events.py`, `voyant/core/event_schema.py` |
| FR-19 | `voyant/billing/lago.py` |
| FR-20 | `voyant/core/iceberg.py` (planned), `config/iceberg/*` (planned) |
| FR-21 | `voyant/streaming/*` (planned), `config/flink/*` (planned) |
| FR-22 | `voyant/security/policy.py` (planned), Ranger integration (planned) |
| FR-23 | `voyant/governance/atlas.py` (planned) |
| FR-24 | `voyant/observability/skywalking.py` (planned) |
| FR-25 | `voyant/ingestion/nifi.py` (planned) |
| FR-26 | `voyant/bi/superset.py` (planned) |
| FR-27 | `voyant/olap/druid.py` (planned), `voyant/olap/pinot.py` (planned) |
| FR-28 | `voyant/ingestion/tika.py` (planned) |
| FR-29 | `voyant/api/middleware.py`, `voyant/security/auth.py`, `voyant/core/events.py`, `voyant/integrations/soma.py` (planned) |

## 13. Error Code Traceability
Error codes follow the `VYNT-XXXX` format and are defined in `voyant/core/errors.py` with additional domain-specific errors in analysis and ingestion modules.

| Code Range | Category | Example Usage | Primary Modules |
| --- | --- | --- | --- |
| VYNT-1000–1999 | Validation | Invalid request body, invalid columns | `voyant/core/errors.py`, `voyant/core/stats.py` |
| VYNT-2000–2999 | Resource | Job/artifact/source not found | `voyant/core/errors.py`, API routes |
| VYNT-3000–3999 | Auth/AuthZ | Authentication required, permission errors | `voyant/security/auth.py` |
| VYNT-4000–4999 | Ingestion | File not found, unstructured errors | `voyant/ingestion/direct_utils.py`, `voyant/ingestion/unstructured_utils.py` |
| VYNT-5000–5999 | System/Temporal | Temporal client errors | `voyant/core/temporal_client.py` |
| VYNT-6000–6999 | Stats/R | R engine or stats errors | `voyant/core/r_bridge.py`, `voyant/core/stats_primitives.py` |
| VYNT-7000–7999 | ML/Analytics | ML primitives and forecasting errors | `voyant/core/ml_primitives.py`, `voyant/core/forecast_primitives.py`, `voyant/services/analysis/*` |

## 14. External Dependency Matrix
| Dependency | Purpose | Config Key(s) | Required for Full Functionality |
| --- | --- | --- | --- |
| PostgreSQL | Metadata storage | `DATABASE_URL` | Yes |
| Redis | Cache/session | `REDIS_URL` | Optional |
| Kafka | Event emission | `KAFKA_BOOTSTRAP_SERVERS` | Optional |
| Temporal | Workflow orchestration | `TEMPORAL_HOST`, `TEMPORAL_TASK_QUEUE` | Optional |
| Trino | SQL execution | `TRINO_HOST`, `TRINO_PORT`, `TRINO_CATALOG`, `TRINO_SCHEMA` | Yes (SQL endpoints) |
| MinIO | Artifact storage | `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | Yes (artifacts) |
| DataHub | Governance queries | `DATAHUB_GMS_URL` | Optional |
| Keycloak | Authentication | `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET` | Optional |
| Lago | Billing | `LAGO_API_URL`, `LAGO_API_KEY` | Optional |
| Apache Iceberg | Lakehouse tables | `ICEBERG_CATALOG`, `ICEBERG_WAREHOUSE` | Yes (lakehouse mode) |
| Apache Flink | Streaming analytics | `FLINK_JOBMANAGER_URL` | Optional |
| Apache Ranger | Policy enforcement | `RANGER_ADMIN_URL` | Optional |
| Apache Atlas | Metadata governance | `ATLAS_URL` | Optional |
| Apache SkyWalking | Tracing/APM | `SKYWALKING_OAP_URL` | Optional |
| Apache NiFi | Dataflow ingestion | `NIFI_URL` | Optional |
| Apache Superset | BI dashboards | `SUPERSET_URL` | Optional |
| Apache Druid | OLAP store | `DRUID_BROKER_URL` | Optional |
| Apache Pinot | OLAP store | `PINOT_BROKER_URL` | Optional |
| Apache Tika | Document parsing | `TIKA_URL` | Optional |
| SomaAgentHub Gateway | Upstream entry point | `SOMA_GATEWAY_URL` | Optional |
| SomaAgentHub Orchestrator | Workflow coordination | `SOMA_ORCHESTRATOR_URL` | Optional |
| SomaAgentHub Identity | Token issuance/validation | `SOMA_IDENTITY_URL` | Optional |
| SomaAgentHub Policy Engine | Policy decisions | `SOMA_POLICY_URL` | Optional |
| SomaAgentHub Memory Gateway | Long-term memory | `SOMA_MEMORY_URL` | Optional |

## 15. Appendix: Configuration Summary
Selected environment variables (non-exhaustive):
- `VOYANT_ENV`, `VOYANT_SECRETS_BACKEND`
- `DATABASE_URL`, `REDIS_URL`, `KAFKA_BOOTSTRAP_SERVERS`
- `TRINO_HOST`, `TRINO_PORT`, `TRINO_CATALOG`, `TRINO_SCHEMA`
- `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`
- `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`
- `LAGO_API_URL`, `LAGO_API_KEY`
- Feature flags: `VOYANT_ENABLE_QUALITY`, `VOYANT_ENABLE_BILLING`, `VOYANT_ENABLE_DATAHUB`, `VOYANT_ENABLE_CHARTS`, `VOYANT_ENABLE_NARRATIVE`, `VOYANT_METRICS_MODE`
- `ICEBERG_CATALOG`, `ICEBERG_WAREHOUSE`
- `FLINK_JOBMANAGER_URL`, `RANGER_ADMIN_URL`, `ATLAS_URL`, `SKYWALKING_OAP_URL`
- `NIFI_URL`, `SUPERSET_URL`, `DRUID_BROKER_URL`, `PINOT_BROKER_URL`, `TIKA_URL`
- `SOMA_GATEWAY_URL`, `SOMA_ORCHESTRATOR_URL`, `SOMA_IDENTITY_URL`, `SOMA_POLICY_URL`, `SOMA_MEMORY_URL`
