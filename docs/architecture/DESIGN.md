# Voyant v3 Architecture and Design

Document ID: VOYANT-DESIGN-3.0.0
Status: Draft for execution
Date: 2025-12-17

## 1. Design Goals
- Agent-first workflow: discover -> connect -> ingest -> analyze -> artifact in one call.
- Durability: all sources, jobs, and artifacts persist across restarts.
- Traceability: every artifact is linked to source, job, and dataset version.
- Observability: unified metrics, logs, traces across API and workflows.
- Governance: contracts, lineage, and policy enforcement built-in.
- Extensibility: plugin registry for analyzers and generators.
- Soma stack integration: accept upstream context and publish results into Soma memory and orchestration.

## 2. Target Architecture Overview

+-----------------------------------------------------------+
| SomaAgent01 (Django) - Tool Registry / MCP Clients         |
+-----------------------------------------------------------+
| SomaAgentHub - Gateway / Orchestrator / Policy / Memory    |
+-----------------------------------------------------------+
| Voyant Interfaces: MCP tools (JSON-RPC) + REST API         |
+------------------------+----------------------------------+
|      Control Plane     |   AuthN/AuthZ   |  API Gateway    |
|  Tenant, Versioning    |   Keycloak      |  Rate Limits    |
+------------------------+-----------------+-----------------+
|          Orchestration / Workflow Layer (Temporal)         |
+-----------------------------------------------------------+
| Ingestion    | Analysis    | Predict     | Governance      |
| Airbyte/NiFi | Plugins     | ML/Stats    | Contracts/Atlas |
+-----------------------------------------------------------+
| Storage & Query  | Artifacts     | OLAP            | Search |
| Iceberg/Trino    | MinIO         | Druid/Pinot     | Vector |
+-----------------------------------------------------------+
| Observability: Metrics, Logs, Traces (SkyWalking, Kafka)   |
+-----------------------------------------------------------+

### 2.1 Soma Stack Integration
- SomaAgentHub Gateway routes sessions to Orchestrator, which selects Voyant as a tool provider.
- Voyant receives session/tenant/user context and trace headers from Gateway/Orchestrator.
- Policy checks are evaluated via SomaAgentHub Policy Engine before ingest/analyze.
- Analysis summaries and key artifacts are written to SomaAgentHub Memory Gateway for recall.
- Job status updates are pushed back to Orchestrator for session state alignment.

## 3. Component Responsibilities

### 3.1 API Layer
- Django Ninja REST endpoints for core workflows and metadata.
- MCP server for agent tool invocation.
- Middleware for request ID, tenant scoping, API version negotiation.
- Soma context propagation (`X-Soma-Session-ID`, `X-User-ID`, `traceparent`) for upstream orchestration.

### 3.2 Orchestration Layer
- Temporal workflows for ingest, analyze, predict, and operational workflows.
- Activities for ingestion, profiling, quality, KPI, charts, narrative.

### 3.3 Ingestion Layer
- Airbyte for connector provisioning and batch sync.
- NiFi for managed flow-based ingestion.
- Direct file ingestion into DuckDB and Iceberg.
- Tika/unstructured for document parsing.

### 3.4 Storage and Query
- Iceberg as the lakehouse storage layer.
- Trino as the SQL execution engine over Iceberg.
- MinIO as artifact storage.
- Optional Druid/Pinot for low-latency OLAP.

### 3.5 Analytics and Prediction
- KPI SQL execution via Trino.
- Profiling via adaptive sampling and pandas or ydata-profiling.
- Quality and drift via Evidently or rule-based checks.
- ML/Stats: regression, forecasting, anomaly detection.
- Plugin registry to manage analyzers and generators.

### 3.6 Governance and Security
- Data contracts and schema validation pre-ingest/analyze.
- Lineage graph persisted and published to Atlas/DataHub.
- Policy enforcement via Apache Ranger.
- Auth via Keycloak; tenant enforcement in queries and artifacts.

### 3.7 Observability
- Structured logging with correlation IDs.
- Unified metrics endpoint and standard naming.
- Distributed tracing via SkyWalking.
- Kafka events with schema validation.

### 3.8 Soma Integration Layer
- Policy Engine client for sensitive action gating.
- Memory Gateway client for summary and artifact pointers.
- Orchestrator callback publisher for job/session updates.

## 4. Primary Data Flows

### 4.1 Agent One-Call Analyze
1) Agent calls MCP `voyant.analyze`.
2) API creates job record and triggers Temporal analyze workflow.
3) Workflow runs: ingest/normalize -> profile -> quality -> KPI -> charts -> narrative.
4) Artifacts stored in MinIO; manifest returned to agent.
5) Events emitted to Kafka; traces emitted to SkyWalking.

### 4.2 Streaming KPI Flow
1) Kafka topic receives streaming events.
2) Flink pipeline computes KPIs and anomalies.
3) Results written to Iceberg and optional Druid/Pinot.
4) Alerts emitted via Kafka with schema validation.

### 4.3 Governance Flow
1) Contracts validated pre-ingest/analyze.
2) Lineage recorded for source -> table -> job -> artifact.
3) Metadata published to Atlas/DataHub.

### 4.4 Soma Stack Orchestration Flow
1) SomaAgentHub Gateway starts a session and routes to Orchestrator.
2) Orchestrator selects Voyant and calls `/v1/analyze` with session headers.
3) Voyant requests a policy decision before high-risk actions.
4) Workflow runs and stores artifacts; summary is pushed to Memory Gateway.
5) Voyant publishes status updates back to Orchestrator for session continuity.

## 5. Data Model (Target)
- Source: id, tenant_id, type, config, status, external_ids
- Job: id, tenant_id, type, state, progress, timestamps, soma_session_id
- Artifact: id, job_id, type, path, size, created_at
- Contract: name, version, schema, sensitivity
- Lineage: edges between sources, tables, jobs, artifacts

## 6. Non-Functional Design
- Performance: adaptive sampling, query limits, OLAP offload.
- Reliability: circuit breakers and retries for external services.
- Security: tenant isolation, policy enforcement, audit logs.
- Maintainability: modular workflows and plugin registry.

## 7. Deployment Topology
- Core services: API, MCP, Temporal, Kafka, Redis, Postgres, Trino, MinIO.
- Apache extensions: Iceberg catalog, Ranger, Atlas, SkyWalking, NiFi, Superset, Druid/Pinot, Tika.
- Each component deploys as its own container/service.
- Soma stack co-deploy: Gateway, Orchestrator, Policy Engine, Identity, Memory Gateway (service-to-service auth).

## 8. Open Implementation Steps
- Align with `docs/TASKS.md` for execution order and milestones.
