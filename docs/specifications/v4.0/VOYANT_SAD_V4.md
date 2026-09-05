# Voyant v4.0 — System Architecture Document

**Document ID:** VOYANT-SAD-4.0.0
**Version:** 4.0.0-draft
**Date:** 2026-09-05
**Standard:** ISO/IEC/IEEE 42010:2011
**Status:** Draft for Review

---

## 1. System Overview

Voyant v4.0 is an agent-native data intelligence platform. AI agents are the primary users. Humans provide oversight. The system combines Palantir-grade ontology, Databricks-grade data/ML, Octoparse-grade scraping, and a unique intent engine that translates natural language into deterministic execution plans.

---

## 2. Architecture Principles

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | Agent-native | Every feature must be callable by AI agents via MCP tools |
| 2 | Intent-driven | Agents express WHAT. System determines HOW. |
| 3 | LLM translates, code executes | LLMs only in intent layer. Execution is deterministic. |
| 4 | Apache-first | Use Apache projects before building custom |
| 5 | Self-healing | Auto-retry, auto-fix, escalate only if unfixable |
| 6 | Tenant-isolated | Every query filtered by tenant. No cross-tenant leakage. |
| 7 | Fail-closed | Deny by default. Explicit allow only. |
| 8 | Open source | Apache 2.0. No vendor lock-in. |

---

## 3. Layer Architecture

```
┌─────────────────────────────────────────────────────────┐
│ LAYER 1: CONSUMERS                                       │
│ AI Agents (MCP) · Humans (Dashboard) · Systems (Kafka)   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ LAYER 2: GATEWAY                                         │
│ Apache APISIX (rate limit · auth · TLS · routing)        │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ LAYER 3: API                                             │
│ Django 5 + Django Ninja (120+ REST endpoints)            │
│ django-mcp (83+ MCP tools)                               │
│ WebSocket (real-time subscriptions)                      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ LAYER 4: INTENT ENGINE (LLM-Powered)                     │
│ Query Intent · Pipeline Intent · Scraper Intent          │
│ LLM Router (model-agnostic) · Ontology Cache             │
│ Output: Structured JSON execution plans                  │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ LAYER 5: DOMAIN SERVICES                                 │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│ │Ontology │ │ Data    │ │Scraper  │ │   ML    │       │
│ │ Engine  │ │ Intel   │ │Octopus  │ │Platform │       │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐       │
│ │ Agent   │ │Governance│ │Capsule │ │ Search  │       │
│ │Platform │ │ Engine  │ │Runtime │ │ Engine  │       │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ LAYER 6: ORCHESTRATION                                   │
│ Temporal.io (25+ workflows · self-healing · durable)     │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ LAYER 7: DATA                                            │
│ PostgreSQL · Iceberg · Kafka · Flink · Spark · Milvus    │
│ Elasticsearch · Redis · MinIO · DuckDB                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ LAYER 8: GOVERNANCE                                      │
│ Ranger (data RBAC) · SpiceDB (app RBAC) · Atlas (meta)  │
│ Vault (secrets) · Keycloak (auth) · AuditLog             │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ LAYER 9: OBSERVABILITY                                   │
│ Prometheus · Grafana · SkyWalking · Elasticsearch        │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Intent Engine Architecture

```
Agent Request: "Get sales from June, create pie chart"
         │
         ▼
┌──────────────────────────┐
│ 1. INTENT CLASSIFIER     │  Classify: query | pipeline | scrape | analyze
│    (LLM or regex)        │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 2. SCHEMA RESOLVER       │  Load tenant's ontology
│    (PostgreSQL + cache)   │  Find matching ObjectTypes, Properties, Links
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 3. PLAN GENERATOR        │  LLM translates intent + schema → structured plan
│    (LLM API call)        │  Output: JSON array of tool calls
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 4. PLAN VALIDATOR        │  Validate against ontology schema
│    (Deterministic)        │  Check permissions, governance rules
│                           │  Reject if invalid
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 5. PLAN EXECUTOR         │  Execute each step via Temporal workflows
│    (Deterministic)        │  No LLM involved. Pure code.
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ 6. RESULT FORMATTER      │  Structure results for agent consumption
│    (Deterministic)        │  Cache plan for reuse
└──────────────────────────┘
```

---

## 5. Module Map

| Module | App | Models | Endpoints | MCP Tools | Priority |
|--------|-----|--------|-----------|-----------|----------|
| Ontology Engine | `ontology/` | 20 | 35 | 15 | P0 |
| Data Intelligence | `analysis/`, `sql/`, `ingestion/` | 6 | 20 | 10 | P0 |
| Scraper Octopus | `scraper/` | 9 | 21 | 13 | P0 |
| Intent Engine | `intent/` | 3 | 5 | 4 | P0 |
| ML Platform | `ml_platform/` | 6 | 12 | 8 | P1 |
| Agent Platform | `agent_platform/` | 4 | 8 | 5 | P1 |
| Governance | `governance/` | 4 | 12 | 8 | P1 |
| Capsule Runtime | `capsules/` | 0 | 5 | 5 | P1 |
| Search Engine | `search/` | 0 | 4 | 3 | P1 |
| Admin Dashboard | `admin_panel/` | 0 | 28 | 0 | P0 |
| **TOTAL** | | **52+** | **150+** | **71+** | |

---

## 6. Technology Stack

| Layer | Technology | Apache? |
|-------|-----------|---------|
| Backend | Django 5 + Django Ninja | — |
| Frontend | Lit 3 + Vite + Tailwind | — |
| Workflows | Temporal.io | — |
| Metadata DB | PostgreSQL 16 | — |
| Lakehouse | Apache Iceberg on MinIO | Yes |
| SQL | Apache Spark SQL + Trino | Yes |
| Streaming | Apache Flink | Yes |
| Messaging | Apache Kafka | Yes |
| Vector Store | Milvus | — |
| Cache | Redis 7 | — |
| Object Storage | MinIO | — |
| Auth | Keycloak | — |
| App RBAC | SpiceDB | — |
| Data RBAC | Apache Ranger | Yes |
| Metadata | Apache Atlas | Yes |
| Pipelines | Apache NiFi | Yes |
| BI | Apache Superset | Yes |
| Documents | Apache Tika | Yes |
| API Gateway | Apache APISIX | Yes |
| Tracing | Apache SkyWalking | Yes |
| Search | Elasticsearch (Lucene) | Yes |
| Charts | Apache ECharts | Yes |
| ML | MLflow + PySpark | LF/Yes |
| NLP | Apache OpenNLP | Yes |
| Secrets | Vault | — |
| Scraping | Playwright + Scrapy | — |
| Monitoring | Prometheus + Grafana | — |

---

## 7. Docker Services (30)

| # | Service | Port | Purpose |
|---|---------|------|---------|
| 1 | voyant_api | 45000 | Django API + MCP |
| 2 | voyant_worker | 45090 | Temporal worker |
| 3 | voyant_postgres | 45432 | Metadata DB |
| 4 | voyant_redis | 45379 | Cache + Pub/Sub |
| 5 | voyant_kafka | 45092 | Event backbone |
| 6 | voyant_temporal | 45233 | Workflow engine |
| 7 | voyant_temporal_ui | 45089 | Workflow dashboard |
| 8 | voyant_minio | 45900 | Object storage |
| 9 | voyant_vault | 45820 | Secrets |
| 10 | voyant_keycloak | 45180 | Auth (SSO) |
| 11 | voyant_spicedb | 50051 | App RBAC |
| 12 | voyant_iceberg_rest | 8181 | Iceberg catalog |
| 13 | voyant_spark | 7077 | Distributed SQL + ML |
| 14 | voyant_flink_jm | 45082 | Streaming job manager |
| 15 | voyant_flink_tm | — | Streaming task manager |
| 16 | voyant_milvus | 19530 | Vector search |
| 17 | voyant_etcd | 2379 | Milvus backend |
| 18 | voyant_elasticsearch | 45200 | Full-text search |
| 19 | voyant_ranger | 6080 | Data RBAC |
| 20 | voyant_atlas | 21000 | Metadata + lineage |
| 21 | voyant_nifi | 8443 | Pipeline builder |
| 22 | voyant_mlflow | 5000 | ML experiments |
| 23 | voyant_superset | 8088 | BI dashboards |
| 24 | voyant_tika | 9998 | Document parsing |
| 25 | voyant_apisix | 9080 | API gateway |
| 26 | voyant_skywalking_oap | 12800 | Tracing server |
| 27 | voyant_skywalking_ui | 1234 | Tracing dashboard |
| 28 | voyant_searxng | 45088 | Sovereign search |
| 29 | voyant_browserless | 45300 | Headless browser |
| 30 | voyant_dashboard | 3000 | Lit 3 admin UI |

---

## 8. Data Flow

### 8.1 Agent Query Flow
```
Agent → MCP → APISIX → Django → Intent Engine → [LLM] → Plan → Temporal → Trino/Spark → Result → Agent
```

### 8.2 Data Ingestion Flow
```
Source → Airbyte/NiFi → Kafka → Flink → Iceberg → Atlas (lineage) → Ontology (auto-detect)
```

### 8.3 Scraping Flow
```
Agent → MCP → Scraper API → Temporal → Playwright → Content Extractor → Iceberg → Milvus (embeddings)
```

### 8.4 ML Training Flow
```
Agent → MCP → ML API → Temporal → Spark/MLflow → Model Registry → Serving Endpoint
```

---

## 9. Security Architecture

```
Request → APISIX (TLS, rate limit)
       → Keycloak (JWT validation)
       → SpiceDB (app-level RBAC)
       → Ranger (data-level RBAC: row/column security)
       → Django (tenant isolation via RBACManager)
       → AuditLog (every operation logged)
```

---

## 10. Document Revision History

| Version | Date | Changes |
|---------|------|---------|
| 4.0.0-draft | 2026-09-05 | Initial architecture with intent engine, Apache stack, Lit frontend |
