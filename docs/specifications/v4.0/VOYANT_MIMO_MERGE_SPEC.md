# Voyant v4.0 × MIMO SRS — Merge Specification

**Document ID:** VOYANT-MERGE-SPEC-4.0.0
**Version:** 1.0.0
**Date:** 2026-09-09
**Standard:** ISO/IEC/IEEE 29148:2018
**Status:** Draft for Review
**Supersedes:** Nothing (new document)

---

## 1. Purpose

This document maps every requirement from the MIMO SRS (SRS-PLTR-2026-001, 3,495 lines, 10 modules, 200+ FRs) to the Voyant v4.0 codebase, identifies gaps, and defines a merge plan. The goal is to achieve full Palantir-class functionality while preserving Voyant's unique advantages (MCP, Intent Engine, Scraping, Capsules).

---

## 2. Merge Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | Voyant architecture wins on conflict | Monolith > microservices for v4.0 scope |
| 2 | MIMO requirements fill Voyant gaps | Where Voyant has no equivalent, adopt MIMO's requirement |
| 3 | Voyant improvements over MIMO are preserved | MCP, Intent Engine, Scraping, Capsules |
| 4 | No React, no Java, no Spark, no Neo4j | ADR-001, ADR-004 are binding |
| 5 | Every merged requirement gets a Voyant SRS ID | Traceability to VOYANT-SRS-4.0.0 |

---

## 3. Module-by-Module Merge Map

### 3.1 M1 Voyant Connect — Data Integration & Connectors

**MIMO:** 15 FRs, 5 screens (Source Catalog, Connection Detail, New Connection Wizard, Ingestion Monitor, Schema Browser)

| MIMO FR | Description | Voyant Status | Merge Decision | Voyant Action |
|---------|-------------|---------------|----------------|---------------|
| FR-1.4.1.1 | Database connections (Postgres, MySQL, Oracle, SQL Server, SQLite, MongoDB, Cassandra, DynamoDB, Snowflake, BigQuery, Redshift, Databricks) | **Partial** — Airbyte client only | MERGE | Add native connectors for Postgres, MySQL, SQLite via Django ORM; others via Airbyte |
| FR-1.4.1.2 | Cloud storage (S3, Azure Blob, GCS, MinIO) | **Partial** — MinIO + S3 | MERGE | Add Azure Blob + GCS connectors |
| FR-1.4.1.3 | Streaming (Kafka, Kinesis, Event Hubs, Pub/Sub) | **Partial** — Kafka only | MERGE | Add Kinesis + Event Hubs + Pub/Sub connectors |
| FR-1.4.1.4 | REST API connections (API Key, OAuth2, Basic, Bearer, Custom) | **Partial** — basic HTTP | MERGE | Add auth method selector |
| FR-1.4.1.5 | File sources (CSV, JSON, XML, Parquet, Excel) | **Done** | KEEP | Already works |
| FR-1.4.1.6 | AES-256 credential encryption | **Done** — Vault | KEEP | Vault handles this |
| FR-1.4.1.7 | Test connection before save | **Partial** | MERGE | Add test-connection endpoint |
| FR-1.4.1.8 | Edit connection settings | **Done** | KEEP | Already works |
| FR-1.4.1.9 | Delete connection with confirmation | **Done** | KEEP | Already works |
| FR-1.4.1.10 | Connection pooling | **Partial** | MERGE | Add configurable pool size |
| FR-1.4.1.11 | SSH tunneling | **Missing** | MERGE (P1) | Add SSH tunnel support |
| FR-1.4.1.12 | VPN/Private Link | **Missing** | DEFER V4.1 | Not needed for v4.0 |
| FR-1.4.2.1 | Auto-discover tables/collections/files | **Partial** | MERGE | Enhance discovery |
| FR-1.4.2.2 | Extract schema (columns, types, PKs, FKs) | **Partial** | MERGE | Add FK discovery |
| FR-1.4.2.3 | Preview 100 rows | **Missing** | MERGE | Add preview endpoint |
| FR-1.4.2.4 | Select datasets for ingestion | **Done** | KEEP | Already works |
| FR-1.4.2.5 | Custom SQL as source | **Done** | KEEP | Already works |
| FR-1.4.2.6 | File path patterns (glob) | **Missing** | MERGE | Add glob support |
| FR-1.4.2.7 | Schema re-discovery | **Missing** | MERGE | Add re-discovery endpoint |
| FR-1.4.3.1 | Full ingestion | **Done** | KEEP | Already works |
| FR-1.4.3.2 | Incremental ingestion (watermark) | **Partial** | MERGE | Add watermark column config |
| FR-1.4.3.3 | CDC (logical replication, binlog, change streams) | **Missing** | MERGE (P1) | Add CDC connector |
| FR-1.4.3.4 | Audit trail per job | **Done** | KEEP | AuditLog exists |
| FR-1.4.3.5 | Retry policies | **Done** — Temporal | KEEP | Temporal handles retry |
| FR-1.4.3.6 | Parallel ingestion | **Done** — Temporal | KEEP | Temporal handles parallelism |
| FR-1.4.3.7 | Scheduled ingestion (cron) | **Partial** | MERGE | Add cron scheduling |
| FR-1.4.3.8 | Event-driven ingestion (file arrival) | **Missing** | MERGE (P1) | Add file watcher |
| FR-1.4.3.9 | Streaming ingestion (Kafka) | **Partial** | MERGE | Enhance Kafka consumer |
| FR-1.4.3.10 | Schema evolution | **Missing** | MERGE | Add schema evolution rules |
| FR-1.4.3.11 | Data type mapping | **Missing** | MERGE | Add type mapping config |
| FR-1.4.3.12 | Data validation rules | **Partial** | MERGE | Add validation framework |
| FR-1.4.3.13 | Quarantine failed records | **Missing** | MERGE | Add error dataset |
| FR-1.4.3.14 | Real-time metrics | **Partial** | MERGE | Add Prometheus metrics |
| FR-1.4.3.15 | Backpressure (streaming) | **Missing** | MERGE (P1) | Add backpressure |

**M1 Voyant Connect Summary:** 15 FRs → 8 Done, 7 Merge, 1 Partial, 2 Deferred

---

### 3.2 M2 Voyant Pipeline — Data Pipeline / ETL Engine

**MIMO:** 22 FRs, 6 screens (Pipeline Dashboard, Visual Editor, Runs History, Run Detail, Code Editor, Lineage Browser)

| MIMO FR | Description | Voyant Status | Merge Decision | Voyant Action |
|---------|-------------|---------------|----------------|---------------|
| FR-2.4.1.1 | Create pipelines as DAGs | **Done** | KEEP | Pipeline model exists |
| FR-2.4.1.2 | Visual + code editing | **Missing** | MERGE | Build DAG canvas in Lit |
| FR-2.4.1.3 | DAG cycle validation | **Missing** | MERGE | Add cycle detection |
| FR-2.4.1.4 | Transform types (Filter, Map, Join, Aggregate, Sort, Dedup, Flatten, Pivot, Union, Custom) | **Missing** | MERGE | Add transform engine |
| FR-2.4.1.5 | Schema compatibility validation | **Missing** | MERGE | Add schema validation |
| FR-2.4.1.6 | Parameterized pipelines | **Partial** | MERGE | Enhance with runtime params |
| FR-2.4.1.7 | Version control (history, diff, rollback) | **Missing** | MERGE | Add version tracking |
| FR-2.4.1.8 | Branching pipelines | **Missing** | DEFER V4.1 | Complex, low priority |
| FR-2.4.1.9 | Sub-pipelines | **Missing** | DEFER V4.1 | Complex, low priority |
| FR-2.4.2.1 | Apache Spark compute | **N/A** | REJECT | Use Trino + DuckDB |
| FR-2.4.2.2 | Python, PySpark, SQL, Scala transforms | **Partial** | MERGE | Python + SQL transforms |
| FR-2.4.2.3 | SDK for transforms | **Missing** | MERGE | Create transform SDK |
| FR-2.4.2.4 | UDFs | **Missing** | MERGE | Add UDF support |
| FR-2.4.2.5 | Parallel transforms | **Done** — Temporal | KEEP | Temporal handles this |
| FR-2.4.2.6 | Test with sample | **Missing** | MERGE | Add sample mode |
| FR-2.4.2.7 | Schema inference | **Missing** | MERGE (P1) | Add schema inference |
| FR-2.4.2.8 | Checkpointing | **Done** — Temporal | KEEP | Temporal handles checkpointing |
| FR-2.4.2.9 | Caching intermediate results | **Missing** | MERGE (P1) | Add result caching |
| FR-2.4.3.1 | Cron scheduling | **Done** — Temporal | KEEP | Temporal handles cron |
| FR-2.4.3.2 | Fixed interval scheduling | **Done** — Temporal | KEEP | Temporal handles intervals |
| FR-2.4.3.3 | Event-driven triggers | **Partial** | MERGE | Add event triggers |
| FR-2.4.3.4 | Manual Run Now | **Done** | KEEP | Already works |
| FR-2.4.3.5 | SLA monitoring | **Missing** | MERGE | Add SLA alerts |
| FR-2.4.3.6 | Pipeline dependencies | **Missing** | MERGE | Add dependency chains |
| FR-2.4.3.7 | Retry policies | **Done** — Temporal | KEEP | Temporal handles retry |
| FR-2.4.3.8 | Concurrent execution limits | **Missing** | MERGE | Add concurrency config |
| FR-2.4.4.1 | Auto lineage graph | **Partial** | MERGE | Enhance lineage tracking |
| FR-2.4.4.2 | Column-level lineage | **Missing** | MERGE (P1) | Add column lineage |
| FR-2.4.4.3 | Lineage API | **Partial** | MERGE | Enhance lineage API |
| FR-2.4.4.4 | Lineage metadata | **Missing** | MERGE | Add metadata to lineage |
| FR-2.4.4.5 | Visual lineage browser | **Missing** | MERGE | Build lineage view |

**M2 Voyant Pipeline Summary:** 22 FRs → 6 Done, 12 Merge, 2 Deferred, 1 Rejected (Spark), 1 Partial

---

### 3.3 M3 Voyant Catalog — Ontology & Data Catalog

**MIMO:** 20 FRs, 5 screens (Ontology Builder, Object Type Editor, Object Explorer, Data Catalog, Dataset Detail)

| MIMO FR | Description | Voyant Status | Merge Decision | Voyant Action |
|---------|-------------|---------------|----------------|---------------|
| FR-3.4.1.1 | 14 property types | **Done** (11 types) | MERGE | Add Long, Decimal, Binary, Rich Text types |
| FR-3.4.1.2 | Primary key designation | **Partial** | MERGE | Add PK field to ObjectType |
| FR-3.4.1.3 | Backing dataset mapping | **Missing** | MERGE | Add backing_dataset_id to ObjectType |
| FR-3.4.1.4 | Link cardinality | **Done** | KEEP | Already works |
| FR-3.4.1.5 | Composite primary keys | **Missing** | MERGE (P1) | Add composite PK support |
| FR-3.4.1.6 | Object type inheritance | **Partial** — Interface model | MERGE | Enhance Interface to support inheritance |
| FR-3.4.1.7 | Backing dataset schema validation | **Missing** | MERGE | Add schema validation |
| FR-3.4.1.8 | Object type versioning | **Done** | KEEP | Already works |
| FR-3.4.1.9 | Query with filtering, sorting, pagination, link traversal | **Done** | KEEP | Already works |
| FR-3.4.2.1 | Actions (read/write) | **Done** | KEEP | ActionType + ActionExecutor |
| FR-3.4.2.2 | Functions (read-only) | **Done** | KEEP | Function + FunctionRunner |
| FR-3.4.2.3 | Action parameters, output, validation, side effects | **Done** | KEEP | Already works |
| FR-3.4.2.4 | Function parameters, output, code | **Done** | KEEP | Already works |
| FR-3.4.2.5 | Action approval workflows | **Missing** | MERGE | Add approval fields + workflow |
| FR-3.4.2.6 | Action execution logging | **Done** | KEEP | ActionExecution model |
| FR-3.4.2.7 | Action rollback (undo) | **Done** | KEEP | previous_values snapshot |
| FR-3.4.3.1 | Auto-catalog all assets | **Partial** | MERGE | Enhance catalog auto-discovery |
| FR-3.4.3.2 | Full-text search | **Partial** — Milvus | MERGE | Add PostgreSQL full-text |
| FR-3.4.3.3 | Faceted search | **Missing** | MERGE | Add faceted search |
| FR-3.4.3.4 | User-contributed documentation | **Missing** | MERGE | Add documentation model |
| FR-3.4.3.5 | Data quality scores | **Partial** | MERGE | Enhance quality scoring |
| FR-3.4.3.6 | Data classification labels | **Done** | KEEP | DataClassification model |
| FR-3.4.3.7 | Data freshness tracking | **Missing** | MERGE | Add freshness tracking |
| FR-3.4.3.8 | Auto-detect PII columns | **Missing** | MERGE (P1) | Add PII detection |

**M3 Voyant Catalog Summary:** 20 FRs → 10 Done, 9 Merge, 1 Partial

---

### 3.4 M4 Voyant Lakehouse — Data Storage & Lakehouse

**MIMO:** 13 FRs, 2 screens (Storage Overview, Version History)

| MIMO FR | Description | Voyant Status | Merge Decision |
|---------|-------------|---------------|----------------|
| FR-4.4.1 | Parquet + Iceberg | **Partial** — Iceberg client exists | MERGE — enhance Iceberg integration |
| FR-4.4.2 | Full version history (time travel) | **Missing** | MERGE — add version tracking model |
| FR-4.4.3 | Query historical versions | **Missing** | MERGE — add time travel API |
| FR-4.4.4 | Schema evolution | **Missing** | MERGE — add schema evolution |
| FR-4.4.5 | Schema compatibility enforcement | **Missing** | MERGE — add compatibility checks |
| FR-4.4.6 | Dataset branching | **Missing** | DEFER V4.1 |
| FR-4.4.7 | Snapshot retention policies | **Missing** | MERGE — add retention config |
| FR-4.4.8 | Dataset statistics | **Partial** | MERGE — enhance stats |
| FR-4.4.9 | Partitioning | **Missing** | MERGE — add partition support |
| FR-4.4.10 | Compaction | **Missing** | MERGE (P1) — add compaction |
| FR-4.4.11 | Compression (Snappy, ZSTD, LZ4) | **Missing** | MERGE (P1) — add compression config |
| FR-4.4.12 | Cross-dataset joins | **Done** — Trino | KEEP |
| FR-4.4.13 | Data markers | **Missing** | MERGE — add DataMarker model |

**M4 Voyant Lakehouse Summary:** 13 FRs → 1 Done, 10 Merge, 1 Partial, 1 Deferred

---

### 3.5 M5 Voyant Analyze — Analytics & Visualization Studio

**MIMO:** 21 FRs, 5 screens (Dashboard Gallery, Dashboard Editor, Query Editor, Pivot Table, Dashboard Viewer)

| MIMO FR | Description | Voyant Status | Merge Decision |
|---------|-------------|---------------|----------------|
| FR-5.4.1.1 | 21 chart types | **Partial** — ECharts supports most | MERGE — add missing chart types |
| FR-5.4.1.2 | Geographic maps | **Missing** | MERGE — add map view |
| FR-5.4.1.3 | Data tables (sort, filter, pagination, resize, reorder, selection, conditional formatting, drill-down) | **Partial** | MERGE — enhance data table |
| FR-5.4.1.4 | Pivot tables | **Missing** | MERGE — build pivot component |
| FR-5.4.1.5 | KPI cards | **Done** | KEEP |
| FR-5.4.1.6 | Custom HTML/Markdown widgets | **Missing** | MERGE — add text widget |
| FR-5.4.2.1 | Responsive 12-column grid | **Missing** | MERGE — add grid layout |
| FR-5.4.2.2 | Global dashboard filters | **Missing** | MERGE — add filter propagation |
| FR-5.4.2.3 | Cross-filtering | **Missing** | MERGE — add filter event bus |
| FR-5.4.2.4 | Drill-down hierarchies | **Missing** | MERGE — add drill-down |
| FR-5.4.2.5 | Dashboard templates | **Missing** | MERGE — add templates |
| FR-5.4.2.6 | Scheduled report delivery | **Missing** | MERGE (P1) — add scheduler |
| FR-5.4.2.7 | Dashboard embedding | **Missing** | MERGE (P1) — add iframe embed |
| FR-5.4.2.8 | Real-time refresh | **Partial** — WebSocket exists | MERGE — wire to dashboard |
| FR-5.4.2.9 | Annotations on data points | **Missing** | MERGE (P1) — add annotations |
| FR-5.4.2.10 | Export PDF/PNG/CSV/Excel | **Missing** | MERGE — add export |
| FR-5.4.3.1 | SQL editor with autocomplete | **Done** — Monaco | KEEP |
| FR-5.4.3.2 | Query any dataset | **Done** — Trino | KEEP |
| FR-5.4.3.3 | Python queries | **Missing** | MERGE (P1) — add Python mode |
| FR-5.4.3.4 | Query result caching | **Missing** | MERGE — add Redis caching |
| FR-5.4.3.5 | Save queries | **Missing** | MERGE — add SavedQuery model |
| FR-5.4.3.6 | Share queries | **Missing** | MERGE — add sharing |
| FR-5.4.3.7 | Auto-suggest visualizations | **Missing** | MERGE (P1) — add auto-viz |
| FR-5.4.3.8 | Query execution stats | **Partial** | MERGE — enhance stats |
| FR-5.4.3.9 | Query timeouts | **Done** | KEEP |

**M5 Voyant Analyze Summary:** 21 FRs → 4 Done, 14 Merge, 2 Partial, 4 Deferred

---

### 3.6 M6 Voyant ML — ML/AI Platform (AIP)

**MIMO:** 25 FRs, 6 screens (ML Workspace, Experiment Tracker, Model Registry, Model Deployment, Feature Store, AI Assistant)

| MIMO FR | Description | Voyant Status | Merge Decision |
|---------|-------------|---------------|----------------|
| FR-6.4.1.1 | Track experiments (params, metrics, artifacts, code version) | **Done** | KEEP |
| FR-6.4.1.2 | Compare runs side-by-side | **Partial** | MERGE — add comparison view |
| FR-6.4.1.3 | Custom metrics | **Done** | KEEP |
| FR-6.4.1.4 | Auto-logging from SDK | **Missing** | MERGE — add auto-log |
| FR-6.4.1.5 | Artifact storage | **Done** — MinIO | KEEP |
| FR-6.4.1.6 | Experiment reproducibility | **Missing** | MERGE (P1) — add dependency capture |
| FR-6.4.2.1 | Register models (name, version, framework, schema, metrics) | **Done** | KEEP |
| FR-6.4.2.2 | Stage transitions (Dev→Staging→Prod→Archived) | **Done** | KEEP |
| FR-6.4.2.3 | Model approval workflows | **Missing** | MERGE — add approval |
| FR-6.4.2.4 | Semantic versioning | **Done** | KEEP |
| FR-6.4.2.5 | Model format conversion | **Missing** | MERGE (P1) — add ONNX export |
| FR-6.4.2.6 | Model lineage | **Missing** | MERGE — add lineage tracking |
| FR-6.4.3.1 | Real-time serving (REST) | **Partial** — model exists, no runtime | MERGE — add inference runtime |
| FR-6.4.3.2 | Batch scoring | **Missing** | MERGE — add batch endpoint |
| FR-6.4.3.3 | Auto-scaling | **Missing** | MERGE (P1) — add scaling |
| FR-6.4.3.4 | A/B testing (traffic splitting) | **Missing** | DEFER V4.1 |
| FR-6.4.3.5 | Canary deployments | **Missing** | DEFER V4.1 |
| FR-6.4.3.6 | Model rollback (<60s) | **Missing** | MERGE — add rollback |
| FR-6.4.3.7 | Shadow deployments | **Missing** | DEFER V4.1 |
| FR-6.4.4.1 | Serving metrics (latency, throughput, error rate) | **Missing** | MERGE — add metrics collection |
| FR-6.4.4.2 | Prediction distribution drift | **Missing** | MERGE — add drift detection |
| FR-6.4.4.3 | Feature drift (KS, PSI) | **Missing** | MERGE — add drift tests |
| FR-6.4.4.4 | Drift alerts | **Missing** | MERGE — add alerting |
| FR-6.4.4.5 | Accuracy tracking over time | **Missing** | MERGE (P1) — add accuracy tracking |
| FR-6.4.4.6 | Alert destinations (email, Slack, webhook) | **Missing** | MERGE — add alert routing |
| FR-6.4.5.1 | Feature store | **Missing** | MERGE — build FeatureGroup + Feature models |
| FR-6.4.5.2 | Online + batch serving | **Missing** | MERGE — add dual serving |
| FR-6.4.5.3 | Point-in-time correct retrieval | **Missing** | MERGE — add PIT logic |
| FR-6.4.5.4 | Feature versioning + lineage | **Missing** | MERGE — add versioning |
| FR-6.4.5.5 | Feature sharing | **Missing** | MERGE (P1) — add sharing |
| FR-6.4.5.6 | Feature statistics | **Missing** | MERGE — add stats computation |
| FR-6.4.6.1 | NL→Ontology queries | **Done** — Intent Engine | KEEP (better than MIMO) |
| FR-6.4.6.2 | Show generated query | **Done** | KEEP |
| FR-6.4.6.3 | Suggested follow-up questions | **Missing** | MERGE — add suggestions |
| FR-6.4.6.4 | Auto-visualization | **Missing** | MERGE — add auto-viz |
| FR-6.4.6.5 | Respect user permissions | **Done** | KEEP |
| FR-6.4.6.6 | Multi-turn dialogue | **Missing** | MERGE — add conversation context |
| FR-6.4.6.7 | Audit logging | **Done** | KEEP |

**M6 Voyant ML Summary:** 25 FRs → 8 Done, 14 Merge, 3 Deferred

---

### 3.7 M10 Voyant Workspace — Collaboration & Workspace

**MIMO:** 10 FRs, 2 screens (Workspace, Notification Center)

| MIMO FR | Description | Voyant Status | Merge Decision |
|---------|-------------|---------------|----------------|
| FR-7.4.1 | Create workspaces | **Missing** | MERGE — new app |
| FR-7.4.2 | Share assets in workspace | **Missing** | MERGE — add sharing |
| FR-7.4.3 | Inline commenting | **Missing** | MERGE — add Comment model |
| FR-7.4.4 | @mention with notification | **Missing** | MERGE — add mentions |
| FR-7.4.5 | Threaded discussions | **Missing** | MERGE (P1) — add threads |
| FR-7.4.6 | Notification center | **Missing** | MERGE — add Notification model + view |
| FR-7.4.7 | Notification channels (email, Slack, Teams) | **Missing** | MERGE (P1) — add channels |
| FR-7.4.8 | Notification preferences | **Missing** | MERGE — add preferences |
| FR-7.4.9 | Activity feed | **Missing** | MERGE — add activity model |
| FR-7.4.10 | Version comments | **Missing** | MERGE (P1) — add version comments |

**M10 Voyant Workspace Summary:** 10 FRs → 0 Done, 8 Merge, 2 Deferred (P1)

---

### 3.8 M9 Voyant Shield — Security, Access Control & Governance

**MIMO:** 20 FRs, 4 screens (User Management, Role Editor, Policy Editor, Audit Log)

| MIMO FR | Description | Voyant Status | Merge Decision |
|---------|-------------|---------------|----------------|
| FR-8.4.1.1 | OAuth 2.0 / OIDC | **Done** — Keycloak | KEEP |
| FR-8.4.1.2 | SAML 2.0 | **Done** — Keycloak | KEEP |
| FR-8.4.1.3 | LDAP/AD | **Done** — Keycloak | KEEP |
| FR-8.4.1.4 | MFA (TOTP, WebAuthn) | **Partial** — Keycloak supports | MERGE — enable MFA |
| FR-8.4.1.5 | API key auth | **Missing** | MERGE — add API key model |
| FR-8.4.1.6 | Session management | **Done** | KEEP |
| FR-8.4.1.7 | Password complexity | **Done** — Keycloak | KEEP |
| FR-8.4.2.1 | RBAC | **Done** — SpiceDB | KEEP |
| FR-8.4.2.2 | ABAC | **Missing** | MERGE — add ABAC policies |
| FR-8.4.2.3 | Resource-level permissions | **Done** | KEEP |
| FR-8.4.2.4 | Column-level security | **Done** — ColumnMask | KEEP |
| FR-8.4.2.5 | Row-level security | **Done** — SecurityPolicy | KEEP |
| FR-8.4.2.6 | Cell-level security | **Missing** | MERGE (P1) — add cell masking |
| FR-8.4.2.7 | Group-based permissions | **Done** | KEEP |
| FR-8.4.2.8 | Deny-overrides evaluation | **Done** — fail-closed | KEEP |
| FR-8.4.3.1 | Audit log (user, timestamp, action, resource, IP, UA) | **Done** — AuditLog | KEEP |
| FR-8.4.3.2 | System event log | **Done** | KEEP |
| FR-8.4.3.3 | Immutable audit logs | **Done** | KEEP |
| FR-8.4.3.4 | Audit retention policies | **Missing** | MERGE — add retention |
| FR-8.4.3.5 | Audit search/filter | **Done** | KEEP |
| FR-8.4.3.6 | Compliance reports (SOC 2, GDPR) | **Partial** — SOC2 doc exists | MERGE — add report generation |
| FR-8.4.3.7 | DSAR (GDPR) | **Done** — GDPR workflow | KEEP |
| FR-8.4.3.8 | Classification enforcement | **Done** | KEEP |
| FR-8.4.4.1 | Data classification labels | **Done** | KEEP |
| FR-8.4.4.2 | Auto-detect PII | **Missing** | MERGE (P1) — add PII detection |
| FR-8.4.4.3 | Data retention policies | **Missing** | MERGE — add retention model |
| FR-8.4.4.4 | Data quality rules + monitoring | **Partial** | MERGE — enhance quality |
| FR-8.4.4.5 | Approval workflows | **Missing** | MERGE — add approval framework |

**M9 Voyant Shield Summary:** 20 FRs → 13 Done, 6 Merge, 1 Partial

---

### 3.9 M11 Voyant Admin — Administration & Operations

**MIMO:** 10 FRs, 3 screens (Admin Dashboard, Compute Resources, System Config)

| MIMO FR | Description | Voyant Status | Merge Decision |
|---------|-------------|---------------|----------------|
| FR-9.4.1 | Real-time health dashboard | **Done** — admin_panel | KEEP |
| FR-9.4.2 | Auto-scaling compute | **Missing** | MERGE (P1) — add scaling policies |
| FR-9.4.3 | Log aggregation | **Partial** — Prometheus/Loki | MERGE — enhance logging |
| FR-9.4.4 | Configurable alerting | **Missing** | MERGE — add alert config |
| FR-9.4.5 | Backup/restore | **Done** — DR runbook | KEEP |
| FR-9.4.6 | Zero-downtime deployments | **Missing** | MERGE (P1) — add rolling deploy |
| FR-9.4.7 | Feature flags | **Missing** | MERGE — add feature flag model |
| FR-9.4.8 | Tenant management | **Done** | KEEP |
| FR-9.4.9 | Usage analytics | **Missing** | MERGE — add usage tracking |
| FR-9.4.10 | Rate limiting per endpoint/user | **Partial** — Intent Engine only | MERGE — add global rate limiting |

**M11 Voyant Admin Summary:** 10 FRs → 4 Done, 5 Merge, 1 Partial

---

### 3.10 M12 Voyant API — API Gateway & SDK

**MIMO:** 12 FRs, 2 screens (API Key Management, API Docs)

| MIMO FR | Description | Voyant Status | Merge Decision |
|---------|-------------|---------------|----------------|
| FR-10.4.1 | RESTful API (OpenAPI 3.1) | **Done** | KEEP |
| FR-10.4.2 | GraphQL API | **Missing** | DEFER V4.1 — REST + MCP sufficient |
| FR-10.4.3 | API versioning (/v1/) | **Done** | KEEP |
| FR-10.4.4 | Cursor-based pagination | **Partial** | MERGE — add cursor pagination |
| FR-10.4.5 | Filtering, sorting, field selection | **Partial** | MERGE — enhance query params |
| FR-10.4.6 | Rate limiting per API key | **Missing** | MERGE — add API key model |
| FR-10.4.7 | Standard HTTP status + structured errors | **Done** | KEEP |
| FR-10.4.8 | Webhook registration | **Missing** | MERGE — add webhook model |
| FR-10.4.9 | SDK (Python, Java, JS, Go) | **Partial** — Python + TS | MERGE — add Go SDK |
| FR-10.4.10 | Interactive API docs | **Done** — OpenAPI | KEEP |
| FR-10.4.11 | CORS configuration | **Done** | KEEP |
| FR-10.4.12 | Request/response compression | **Missing** | MERGE — add gzip middleware |

**M12 Voyant API Summary:** 12 FRs → 6 Done, 4 Merge, 1 Partial, 1 Deferred

---

## 4. Grand Merge Summary

| Module | MIMO FRs | Already Done | To Merge | Deferred | Rejected |
|--------|----------|-------------|----------|----------|----------|
| M1 Voyant Connect | 33 | 8 | 22 | 2 | 0 |
| M2 Voyant Pipeline | 22 | 6 | 12 | 2 | 1 |
| M3 Voyant Catalog | 20 | 10 | 9 | 0 | 0 |
| M4 Voyant Lakehouse | 13 | 1 | 10 | 1 | 0 |
| M5 Voyant Analyze | 21 | 4 | 14 | 0 | 0 |
| M6 Voyant ML | 38 | 8 | 25 | 3 | 0 |
| M10 Voyant Workspace | 10 | 0 | 8 | 2 | 0 |
| M9 Voyant Shield | 26 | 13 | 6 | 0 | 0 |
| M11 Voyant Admin | 10 | 4 | 5 | 0 | 0 |
| M12 Voyant API | 12 | 6 | 4 | 1 | 0 |
| **TOTAL** | **205** | **60** | **115** | **11** | **1** |

**Completion:** 60/205 already done (29%). 115 to merge (56%). 11 deferred (5%). 1 rejected.

---

## 5. Implementation Priority (Merged with UDP)

### Phase 1 (Weeks 1–4): Foundation + High-Impact Merge

| Item | MIMO FR | Effort | Owner |
|------|---------|--------|-------|
| Feature Store models + API | FR-6.4.5.1..6 | 1wk | Backend |
| Pivot table component | FR-5.4.1.4 | 1wk | Frontend |
| Dashboard cross-filtering | FR-5.4.2.3 | 0.5wk | Frontend |
| Saved queries + sharing | FR-5.4.3.5,6 | 0.5wk | Full-stack |
| API key model + auth | FR-8.4.1.5, FR-10.4.6 | 0.5wk | Backend |
| Webhook registration | FR-10.4.8 | 0.5wk | Backend |
| Notification model + center | FR-7.4.6,7,8 | 1wk | Full-stack |

### Phase 2 (Weeks 5–8): Data Layer Enhancement

| Item | MIMO FR | Effort | Owner |
|------|---------|--------|-------|
| CDC connector (PostgreSQL) | FR-1.4.3.3 | 1wk | Backend |
| Incremental ingestion (watermark) | FR-1.4.3.2 | 0.5wk | Backend |
| Schema evolution | FR-1.4.3.10 | 0.5wk | Backend |
| Pipeline visual DAG editor | FR-2.4.1.2 | 2wk | Frontend |
| Transform engine (Python + SQL) | FR-2.4.1.4 | 1wk | Backend |
| Column-level lineage | FR-2.4.4.2 | 1wk | Backend |
| Time travel UI | FR-4.4.2,3 | 1wk | Frontend |

### Phase 3 (Weeks 9–12): ML + Governance Enhancement

| Item | MIMO FR | Effort | Owner |
|------|---------|--------|-------|
| Model approval workflow | FR-6.4.2.3 | 0.5wk | Backend |
| Drift monitoring (KS, PSI) | FR-6.4.4.2,3 | 1wk | Backend |
| Drift alerts | FR-6.4.4.4,6 | 0.5wk | Backend |
| Model serving runtime | FR-6.4.3.1 | 1wk | Backend |
| ABAC policies | FR-8.4.2.2 | 1wk | Backend |
| Audit retention | FR-8.4.3.4 | 0.5wk | Backend |
| Approval workflows | FR-8.4.4.5 | 1wk | Backend |

### Phase 4 (Weeks 13–16): Polish + Collaboration

| Item | MIMO FR | Effort | Owner |
|------|---------|--------|-------|
| Workspaces | FR-7.4.1,2 | 1wk | Full-stack |
| Comments + @mentions | FR-7.4.3,4 | 1wk | Full-stack |
| Activity feed | FR-7.4.9 | 0.5wk | Backend |
| Dashboard annotations | FR-5.4.2.9 | 0.5wk | Frontend |
| Auto-visualization | FR-5.4.2.7 | 0.5wk | Frontend |
| Feature flags | FR-9.4.7 | 0.5wk | Backend |
| Usage analytics | FR-9.4.9 | 0.5wk | Backend |
| Go SDK | FR-10.4.9 | 1wk | Backend |

---

## 6. What Voyant Keeps That MIMO Doesn't Have

These features are NOT in the MIMO SRS and represent Voyant's competitive advantage:

| Feature | Description | Status |
|---------|-------------|--------|
| **MCP Protocol** | 80 tools for AI agent orchestration | Done |
| **Intent Engine** | NL→structured execution plans (6-stage pipeline) | Done |
| **Web Scraping** | 9-arm Octopus, 51 templates, deep research | Done |
| **Capsule System** | Signed portable intelligence plugins | Done |
| **AI-Native CAPTCHA** | 5-tier hybrid (behavioral+audio+vision+human) | Done |
| **Temporal Workflows** | Durable, replayable, self-healing | Done |
| **Self-Hosted** | Docker Compose, no vendor lock-in | Done |
| **Open Source** | Apache 2.0 | Done |

---

## 7. Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-09-09 | MiMoCode Agent | Initial merge spec: 205 MIMO FRs mapped, 115 merge items identified |
| 1.1.0 | 2026-09-16 | MiMoCode Agent | Module naming standardization: all modules renamed to Voyant [Name] (M1–M16) scheme. Section headers and summary tables updated. |

---

**END OF DOCUMENT**
