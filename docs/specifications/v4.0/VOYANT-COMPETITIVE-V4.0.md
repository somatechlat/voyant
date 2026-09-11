# Voyant v4.0.0 — Competitive Analysis

**Document ID:** VOYANT-COMPETITIVE-4.0.0
**Version:** 1.0.0
**Date:** 2026-09-11
**Status:** Active

This document consolidates three prior analyses into a single reference:
- PALANTIR_FEATURE_MAP.md (Palantir feature comparison, 339 lines)
- VOYANT_COMPETITIVE_BENCHMARK.md (3-way benchmark, 1,046 lines)
- VOYANT_USER_JOURNEYS.md (40 user journeys, 2,796 lines)

---


## Part 1: Palantir Feature Map

# Voyant v4.0 — Complete Palantir Feature Map & Gap Analysis

**Date:** 2026-09-05
**Purpose:** Every Palantir Foundry tool → what Voyant has → what needs building

---

## How to Read This

- **HAS** = Fully implemented in code, tested, working
- **PARTIAL** = Partially implemented, needs enhancement
- **SRS** = Specified in SRS but not yet built
- **MISSING** = Not in code, not in SRS — needs design + build

---

## 1. ONTOLOGY ENGINE (Palantir's Core)

### 1.1 Object & Link Types

| Palantir Feature | Voyant Status | Code Location | Gap |
|-----------------|---------------|---------------|-----|
| Object Types (name, description, properties) | **HAS** | `ontology/models.py:23` ObjectType | — |
| 11 Property Types (string/int/float/bool/date/timestamp/enum/array/map/struct/geopoint) | **HAS** | `ontology/models.py:68` PropertyType enum | — |
| Required Properties | **HAS** | `ontology/models.py:109` required field | — |
| Default Values | **HAS** | `ontology/models.py:113` default_value | — |
| Validation Rules (regex/min/max/enum/custom) | **HAS** | `ontology/models.py:118` validation_rules JSONB | — |
| Schema Versioning | **HAS** | `ontology/models.py:40` version field | — |
| Soft Deletion | **HAS** | `ontology/models.py:44` deleted_at | — |
| Link Types with Cardinality (1:1, 1:N, M:N) | **HAS** | `ontology/models.py:208` LinkType | — |
| Link Instances | **HAS** | `ontology/models.py:285` Link | — |
| Object CRUD | **HAS** | `ontology/services.py` ObjectTypeService | — |
| Object Batch Create (1000+) | **HAS** | `ontology/services.py:297` batch_create | — |
| Object Upsert | **HAS** | `ontology/services.py:323` upsert | — |
| Optimistic Concurrency | **HAS** | `ontology/models.py:168` version field | — |
| Multi-hop Traversal (up to 10 hops) | **HAS** | `ontology/services.py:506` traverse | — |
| **Interfaces (Polymorphic Types)** | **SRS** | — | ONT-F-018 |
| **Struct Types (Nested Composites)** | **SRS** | — | ONT-F-020 |
| **Shared Properties (Reusable)** | **SRS** | — | ONT-F-021 |
| **Value Types (Domain Constraints)** | **SRS** | — | ONT-F-022 |
| **Type Classes (Metadata Classification)** | **MISSING** | — | Needs design |
| **Render Hints (UI Config)** | **MISSING** | — | Needs design |
| **Status Definitions (Lifecycle)** | **MISSING** | — | Needs design |
| **Object Type Groups** | **SRS** | — | ONT-F-036 |

### 1.2 Action Types (Palantir's "Kinetics")

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Action Types (CRUD operations)** | **SRS** | ONT-F-026 |
| **Action Parameters (types, defaults, validation)** | **SRS** | ONT-F-026 |
| **Action Rules (pre/post conditions)** | **SRS** | ONT-F-026 |
| **Action Side Effects (notifications, webhooks)** | **SRS** | ONT-F-026 |
| **Action Undo/Revert** | **MISSING** | Needs design |
| **Action Permissions (read/write auth)** | **MISSING** | Needs design |
| **Action Logging (audit trail)** | **HAS** | `core/models.py` AuditLog |
| **Batched Action Execution** | **MISSING** | Needs design |
| **Function-Backed Actions** | **SRS** | ONT-F-029 |
| **Action Metrics** | **MISSING** | Needs design |

### 1.3 Functions (Business Logic)

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Python Functions on Objects** | **SRS** | ONT-F-029 |
| **TypeScript Functions** | **MISSING** | Needs design |
| **Function Versioning** | **MISSING** | Needs design |
| **Function Monitoring** | **MISSING** | Needs design |
| **Function Permissions** | **MISSING** | Needs design |
| **Streaming Functions** | **MISSING** | Needs design |
| **Query Functions (API Gateway)** | **MISSING** | Needs design |
| **Unit Testing for Functions** | **MISSING** | Needs design |

### 1.4 Ontology Services

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Object Set Service (query/filter/aggregate)** | **PARTIAL** | Basic ORM only — need high-scale |
| **Subscription Service (real-time notifications)** | **SRS** | ONT-F-032 |
| **Indexing Service (full-text + semantic)** | **PARTIAL** | Milvus exists, need full-text |
| **Materialization Service (pre-computed views)** | **MISSING** | Needs design |
| **Scenario Engine (what-if analysis)** | **MISSING** | Needs design |
| **Write Architecture (atomic transactions)** | **HAS** | Django transactions |
| **Ontology Branching (git-like)** | **MISSING** | Needs design |

### 1.5 Ontology UI Tools

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Object Explorer (search, filter, pivot, compare)** | **PARTIAL** | Admin dashboard has table view only |
| **Object Views (full, panel, configured)** | **MISSING** | Needs React build |
| **Object Monitors (condition-based alerts)** | **MISSING** | Needs design |
| **Vertex (graph visualization)** | **MISSING** | Needs Sigma.js/D3 |
| **Machinery (process mining)** | **MISSING** | Needs design |
| **Map templates** | **MISSING** | Needs design |
| **Dynamic Scheduling (Gantt, calendar)** | **MISSING** | Needs design |
| **Time Series (events, alerts, derived)** | **MISSING** | Needs design |
| **Ontology Manager (browse, edit, branch)** | **PARTIAL** | Admin has basic CRUD |

---

## 2. DATA ENGINEERING (Palantir Pipeline Builder)

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Visual DAG Pipeline Builder** | **SRS** | DATA-F-012 |
| **Batch Pipelines** | **PARTIAL** | Temporal workflows exist |
| **Streaming Pipelines (Flink)** | **PARTIAL** | `streaming/` stub |
| **Incremental Pipelines** | **MISSING** | Needs design |
| **200+ Data Connectors** | **PARTIAL** | Airbyte client only |
| **Dataset Branching (git-like)** | **MISSING** | Needs design |
| **Data Expectations (quality checks)** | **PARTIAL** | Great Expectations integration |
| **Data Lineage** | **PARTIAL** | DataHub client |
| **SQL Studio** | **HAS** | `sql/api.py` Trino client |
| **Time Travel (dataset snapshots)** | **MISSING** | Needs Iceberg integration |
| **Geospatial Transforms** | **MISSING** | Needs design |
| **LLM Transforms in Pipeline** | **MISSING** | Needs design |
| **Pipeline Parameters** | **MISSING** | Needs design |
| **Subgraphs (reusable blocks)** | **MISSING** | Needs design |
| **Schedules** | **PARTIAL** | Temporal scheduling |

---

## 3. AI/ML PLATFORM (Palantir AIP)

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Model Connectivity (LLM integration)** | **PARTIAL** | MCP tools connect to models |
| **Agent Bricks (build/evaluate agents)** | **PARTIAL** | Capsule system |
| **Agent Evaluation (AI judge)** | **SRS** | ML-F-007 |
| **Experiment Tracking** | **SRS** | ML-F-001 |
| **Model Registry** | **SRS** | ML-F-003 |
| **Model Serving (real-time + batch)** | **SRS** | ML-F-004 |
| **Feature Store** | **MISSING** | Needs design |
| **AutoML** | **MISSING** | Needs design |
| **LLM Fine-Tuning** | **MISSING** | Needs design |
| **Semantic Search (RAG)** | **PARTIAL** | Milvus + embeddings exist |
| **Document Intelligence** | **PARTIAL** | PDF/OCR/transcription exist |

---

## 4. APPLICATIONS (Palantir Workshop + Quiver)

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **Workshop (low-code app builder)** | **MISSING** | Needs React builder |
| **Quiver (analytical notebooks)** | **MISSING** | Needs design |
| **Object Views (configurable UI)** | **MISSING** | Needs React components |
| **Dashboard Builder** | **PARTIAL** | 13 Lit admin pages exist |
| **Comment on Objects** | **MISSING** | Needs design |
| **Media Rendering (images, PDFs)** | **PARTIAL** | PDF/OCR exist |
| **Marketplace (data sharing)** | **MISSING** | Needs design |

---

## 5. SECURITY & GOVERNANCE

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **RBAC (roles + permissions)** | **HAS** | SpiceDB + Keycloak |
| **Row-Level Security** | **SRS** | GOV-F-003 |
| **Column-Level Masking** | **SRS** | GOV-F-004 |
| **Object Security Policies** | **MISSING** | Needs design |
| **Markings (data classification)** | **MISSING** | Needs design |
| **Audit Logging** | **HAS** | AuditLog model |
| **Data Lineage** | **PARTIAL** | DataHub client |
| **Multi-Tenant Isolation** | **HAS** | TenantModel + RBACManager |
| **SSO/SAML** | **HAS** | Keycloak |
| **Encryption (at-rest, in-transit)** | **PARTIAL** | TLS for connections, Vault for secrets |

---

## 6. DEVELOPER TOOLCHAIN

| Palantir Feature | Voyant Status | Gap |
|-----------------|---------------|-----|
| **REST API (OpenAPI 3.1)** | **HAS** | 66 endpoints via Django Ninja |
| **MCP Tools** | **HAS** | 46 tools |
| **OSDK (TypeScript + Python)** | **SRS** | API-F-003 |
| **CLI** | **SRS** | API-F-005 |
| **Code Repositories** | **MISSING** | Git integration for notebooks |
| **Unit Testing Framework** | **HAS** | pytest, 2,203 tests |
| **CI/CD (Asset Bundles)** | **MISSING** | Needs design |

---

## 7. WHAT VOYANT HAS THAT PALANTIR DOESN'T

| Feature | Voyant Advantage |
|---------|-----------------|
| **MCP Protocol (46 tools)** | Palantir has zero MCP support |
| **Agent-First Design** | Purpose-built for AI agent orchestration |
| **Web Scraping Engine (8,471 LOC)** | Deep research, browser automation, OCR — Palantir has nothing |
| **Capsule System (2,550 LOC)** | Portable plugin architecture with Ed25519 signing |
| **Self-Hosted (Docker)** | Full control, no vendor lock-in |
| **Open Source (Apache 2.0)** | Community-driven, extensible, auditable |
| **Temporal Workflows (17)** | Durable, replayable orchestration |
| **Lightweight (20 containers)** | vs Palantir's massive infrastructure |

---

## 8. BUILD PRIORITY — What to Build First

### Phase 1 (Weeks 1–6): Ontology Engine Completion
**Why:** This is Palantir's core differentiator. Voyant has the foundation (5 models, CRUD, traversal). Need to add the "kinetics."

Build:
1. `Interface` model + API (polymorphic types)
2. `StructType` model + API (nested composites)
3. `SharedProperty` model + API (reusable properties)
4. `ValueType` model + API (domain constraints)
5. `ActionType` model + API (operations with params, rules, side effects)
6. `Function` model + API (Python business logic on objects)
7. `TypeClass` model (metadata classification)
8. `RenderHint` model (UI rendering config)
9. `StatusDefinition` model (lifecycle statuses)
10. Object Set Service (high-scale query/filter/aggregate)
11. Subscription Service (Redis Pub/Sub for real-time)
12. Ontology Explorer UI (React: table, grid, graph views)

### Phase 2 (Weeks 1–8, parallel): Scraper Octopus
**Why:** Voyant's unique advantage — Palantir/Databricks have nothing.

Build:
1. Template engine + 50 templates
2. Task CRUD + scheduling
3. CAPTCHA solver integration
4. IP rotation + residential proxies
5. Browser fingerprint randomizer
6. Visual workflow builder
7. Export engine (JSON/CSV/XLSX/XML/DB)
8. 13 MCP tools
9. CLI tool

### Phase 3 (Weeks 7–12): ML Platform
**Why:** Databricks' core advantage. Voyant has sklearn primitives only.

Build:
1. Experiment tracking API (MLflow-compatible)
2. Model registry with versioning
3. Model serving endpoints (real-time + batch)
4. Agent definition model
5. Agent evaluation framework
6. Feature Store (basic)

### Phase 4 (Weeks 9–14): Visual Builders
**Why:** Palantir's Workshop/Quiver are their app layer.

Build:
1. Object Explorer (React: search, filter, pivot, compare)
2. Object Views (configurable full/panel views)
3. Action Builder (visual parameter configuration)
4. Function Editor (Monaco code editor)
5. Pipeline Builder (React Flow DAG editor)
6. Graph View (Sigma.js force-directed)
7. Dashboard Builder (chart/table/widget)

### Phase 5 (Weeks 15–20): Governance & Polish
Build:
1. Row-level security filters
2. Column-level masking
3. Object security policies
4. Data markings/classification
5. Scenario Engine (what-if analysis)
6. Ontology branching (git-like)
7. CLI + SDK (auto-generated from OpenAPI)
8. WebSocket API for real-time

### Phase 6 (Weeks 21–24): Enterprise
Build:
1. Kafka event integration
2. GDPR compliance
3. Performance optimization (1M+ objects, 10K users)
4. ISO documentation finalization
5. Load testing
6. Release preparation

---

## 9. EFFORT SUMMARY

| Domain | Requirements | Done | To Build | Weeks |
|--------|-------------|------|----------|-------|
| Ontology Engine | 35 | 15 | 20 | 6 |
| Scraper Octopus | 30 | 6 | 24 | 8 |
| ML Platform | 12 | 0 | 12 | 6 |
| Visual Builders | 15 | 1 | 14 | 6 |
| Governance | 12 | 4 | 8 | 6 |
| Enterprise | 10 | 2 | 8 | 4 |
| **TOTAL** | **114** | **28** | **86** | **24** |

**Team:** 3–4 engineers, 24 weeks, 6 parallel phases.

---

## 10. FILES TO CREATE/MODIFY

### New Django Apps
| App | Purpose | Models | Priority |
|-----|---------|--------|----------|
| `apps/ontology/` (enhance) | Full Palantir-grade ontology | +10 models | P0 |
| `apps/ml_platform/` | MLflow-compatible ML | 6 models | P1 |
| `apps/agent_platform/` | Agent lifecycle | 4 models | P1 |
| `apps/scraper_octopus/` | Octoparse-grade scraping | 9 models | P0 |
| `apps/dashboard_builder/` | Custom dashboards | 3 models | P2 |

### New Frontend (React)
| Component | Purpose | Priority |
|-----------|---------|----------|
| Ontology Explorer | Search, filter, pivot, compare objects | P0 |
| Object Type Builder | Visual schema designer | P0 |
| Action Builder | Visual action configuration | P1 |
| Function Editor | Monaco code editor | P1 |
| Pipeline Builder | React Flow DAG editor | P1 |
| Graph View | Sigma.js force-directed | P1 |
| Dashboard Builder | Chart/table/widget | P2 |
| Scraper Visual Builder | Workflow editor | P0 |

### New API Endpoints (Target: 120+)
| Router | Current | Target | New |
|--------|---------|--------|-----|
| ontology | 5 | 35 | +30 |
| scraper | 11 | 21 | +10 |
| ml_platform | 0 | 12 | +12 |
| agent_platform | 0 | 8 | +8 |
| governance | 7 | 12 | +5 |
| admin_panel | 28 | 28 | 0 |
| **TOTAL** | **66** | **120+** | **+54** |

### New MCP Tools (Target: 80+)
| Category | Current | Target | New |
|----------|---------|--------|-----|
| Ontology | 0 | 15 | +15 |
| Scraper | 7 | 13 | +6 |
| ML | 0 | 8 | +8 |
| Agent | 0 | 5 | +5 |
| Governance | 5 | 8 | +3 |
| Existing | 34 | 34 | 0 |
| **TOTAL** | **46** | **83+** | **+37** |

---

## Part 2: Competitive Benchmark

# Voyant v4.0 — Deep Competitive Benchmark
## Palantir Foundry vs Databricks vs Voyant

**Document ID:** VOYANT-CB-4.0.0
**Version:** 1.0.0
**Date:** 2026-09-05
**Status:** Draft for Review
**Author:** Voyant Engineering
**Sources:** Palantir Foundry docs, Databricks product pages, MLflow docs, internal SRS/SAD/Feature Map, code inspection of `apps/ontology/models.py`, `apps/ml_platform/models.py`, `apps/mcp/tools_*.py`

---

## 1. Executive Summary

### 1.1 Three-Way Comparison Table (25 Dimensions)

| Dimension | Palantir Foundry | Databricks | Voyant v4.0 | Winner |
|-----------|-----------------|------------|-------------|--------|
| **Deployment** | SaaS only (Palantir-hosted) | SaaS (AWS/Azure/GCP) | Self-hosted Docker/K8s | **Voyant** (full control) |
| **Source Code** | Proprietary closed-source | Mixed (Spark open, platform closed) | Apache 2.0 open source | **Voyant** (audit, extend, fork) |
| **Voyant Catalog (M3)** | Full (Object Types, Actions, Functions, OSS) | None (Genie Ontology is semantic layer only) | Full (10 models, Actions, Functions, MCP) | **Voyant** = Palantir |
| **Data Ingestion** | 200+ connectors, Pipeline Builder | Lakeflow (DLT), Auto Loader, 200+ connectors | Airbyte + NiFi + Temporal | **Databricks** |
| **SQL Engine** | Pipeline Builder SQL transforms | Photon + Spark SQL (10–100x faster) | Trino + Spark SQL | **Databricks** |
| **Storage Format** | Proprietary datasets | Delta Lake (ACID, time travel, open) | Apache Iceberg on MinIO | **Databricks** (maturity) |
| **Voyant ML (M6)** | AIP model connectivity, Agent Bricks | MLflow (experiments, registry, serving, AutoML) | MLflow-compatible (models built, 8 new models) | **Databricks** |
| **Voyant Agent (M7)** | AIP chat, code execution | Agent Bricks (build/evaluate/deploy) | Intent Engine + 67 MCP tools + Capsules | **Voyant** (agent-native) |
| **MCP Protocol** | Zero support | Zero support (proprietary gateway) | 67 tools, native MCP server | **Voyant** (unique) |
| **NL→Execution** | AIP chat (LLM interprets) | Genie (text-to-SQL, LLM interprets) | Intent Engine (LLM proposes, code executes) | **Voyant** (deterministic) |
| **Voyant Scrape (M8)** | None | None | Octopus (8,471 LOC, 8 browser arms) | **Voyant** (unique) |
| **Voyant Shield (M9)** | Object security, markings, audit | Unity Catalog (RLS, column masking, lineage) | SpiceDB RBAC + RLS + masking + DataHub | **Databricks** (maturity) |
| **Data Lineage** | Built-in lineage | Automated column-level lineage | DataHub client (partial) | **Databricks** |
| **Real-time** | Subscription Service (WebSocket) | Structured Streaming, Auto Loader | Kafka + Flink (stub), Redis Pub/Sub | **Databricks** |
| **Visualization** | Workshop (low-code app builder) | Dashboards, Notebooks | Lit 3 admin (13 views) | **Palantir** |
| **Notebooks** | Quiver (analytical notebooks) | Databricks Notebooks (collaborative) | None | **Databricks** |
| **Data Quality** | Built-in expectations | Lakeflow expectations + monitoring | Great Expectations + Evidently | **Databricks** |
| **Multi-Cloud** | AWS + Azure (limited GCP) | AWS + Azure + GCP | Docker (any infra) | **Databricks** |
| **Pricing** | $1M+ annual contracts | Pay-per-DBU (~$0.07–$0.40/DBU) | Self-hosted (infra cost only) | **Voyant** |
| **Time to Value** | 3–6 months (Forward Deployed Engineers) | Days (serverless), weeks (custom) | Hours (Docker compose up) | **Voyant** |
| **Agent Evaluation** | Limited (AIP eval) | Agent Evaluation (AI judges) | AgentDefinition + AgentEvaluation models | **Databricks** (depth) |
| **Capsule System** | None | None | Ed25519-signed plugins (2,550 LOC) | **Voyant** (unique) |
| **Temporal Durability** | Proprietary orchestration | Workflow orchestration (Airflow/DLT) | Temporal.io (25+ workflows, replayable) | **Voyant** (durability) |
| **Graph Traversal** | Limited (link traversal in OSS) | None native | Multi-hop traversal (up to 10 hops) | **Voyant** |
| **Container Count** | Massive infra (proprietary) | Managed (cloud-native) | 20 containers | **Voyant** (lightweight) |

### 1.2 Summary Scorecard

| Category | Palantir | Databricks | Voyant |
|----------|----------|------------|--------|
| Data Engineering (M2, M4) | 8/10 | 10/10 | 6/10 |
| Ontology/Semantics (M3) | 10/10 | 4/10 | 8/10 |
| ML/AI Platform (M6) | 7/10 | 10/10 | 3/10 |
| Agent Platform (M7) | 6/10 | 7/10 | 9/10 |
| Governance (M9) | 8/10 | 9/10 | 6/10 |
| UI/UX | 8/10 | 7/10 | 4/10 |
| Developer Experience (M12) | 6/10 | 7/10 | 8/10 |
| Self-Hosted / Sovereignty | 0/10 | 0/10 | 10/10 |
| Agent-Native (MCP) (M7) | 0/10 | 0/10 | 10/10 |
| Web Data Extraction (M8) | 0/10 | 0/10 | 10/10 |
| **Overall** | **53/100** | **54/100** | **74/100** |

> **Key Insight:** Voyant's score is inflated by unique capabilities (MCP, scraping, self-hosted). In raw feature parity with Palantir/Databricks, Voyant is ~37% complete. But the 37% includes the most differentiated features competitors cannot replicate without rearchitecting.

---

## 2. Architecture Comparison

### 2.1 Palantir Foundry Architecture

```
┌─────────────────────────────────────────────┐
│ LAYER: APPLICATIONS                          │
│ Workshop (low-code) · Quiver (notebooks)     │
│ Object Explorer · Vertex (graph) · Maps      │
├──────────────────────────────────────────────┤
│ LAYER: ONTOLOGY                              │
│ Object Types · Properties · Links            │
│ Actions · Functions · Object Set Service     │
│ Subscription Service · Scenario Engine       │
├──────────────────────────────────────────────┤
│ LAYER: MODEL BUILDING                        │
│ Model Connectivity · AIP · Agent Bricks      │
│ Foundry Agent · Code Repositories            │
├──────────────────────────────────────────────┤
│ LAYER: PIPELINE                              │
│ Pipeline Builder (visual DAG)                │
│ Batch · Streaming (Flink) · Incremental      │
│ 200+ Connectors · Quality Checks             │
├──────────────────────────────────────────────┤
│ LAYER: STORAGE                               │
│ Datasets (proprietary format)                │
│ Dataset Branching · Time Travel · Lineage    │
├──────────────────────────────────────────────┤
│ LAYER: SECURITY                              │
│ RBAC · Object Security · Markings            │
│ Audit · SSO/SAML · Encryption                │
└──────────────────────────────────────────────┘
```

**Key architectural decisions:**
- Proprietary dataset format (not open — lock-in)
- Ontology is THE central abstraction (everything maps to objects/links)
- Pipeline Builder is the data engineering UI (not code-first)
- Closed-source, SaaS-only (you never see the code)
- AIP is the AI layer (added 2023, evolving rapidly)

### 2.2 Databricks Lakehouse Architecture

```
┌─────────────────────────────────────────────┐
│ LAYER: APPLICATIONS                          │
│ Genie One (AI Assistant) · Dashboards        │
│ Notebooks · Databricks Apps · BI Tools       │
├──────────────────────────────────────────────┤
│ LAYER: AI/ML                                 │
│ Agent Bricks · Model Serving · MLflow        │
│ AI Search · Unity AI Gateway · Doc Intel     │
│ Model Training · Fine-Tuning · AutoML        │
├──────────────────────────────────────────────┤
│ LAYER: GOVERNANCE                            │
│ Unity Catalog · Unity AI Gateway             │
│ Business Semantics · Column-level Lineage    │
│ Attribute-based Access Control · Monitoring  │
├──────────────────────────────────────────────┤
│ LAYER: DATA ENGINEERING                      │
│ Lakeflow (DLT) · Auto Loader                 │
│ Workflow Orchestration · Job Scheduling       │
│ Incremental Processing · CDC                 │
├──────────────────────────────────────────────┤
│ LAYER: COMPUTE                               │
│ Photon Engine (C++) · Apache Spark           │
│ Serverless Compute · GPU Clusters            │
├──────────────────────────────────────────────┤
│ LAYER: STORAGE                               │
│ Delta Lake (open format, ACID)               │
│ Apache Iceberg · Hudi · Parquet support      │
│ Managed Tables (auto-optimization)           │
└──────────────────────────────────────────────┘
```

**Key architectural decisions:**
- Open formats (Delta Lake, Iceberg, Parquet) — data is portable
- Unity Catalog as single governance plane for data AND AI
- Genie Ontology learns from usage (user-modeled + inferred semantics)
- Agent Bricks for multi-framework agent development
- Serverless compute with instant-start capability
- Lakebase (Postgres) for transactional + operational workloads

### 2.3 Voyant v4.0 Architecture

```
┌─────────────────────────────────────────────┐
│ LAYER 1: CONSUMERS                           │
│ AI Agents (MCP) · Humans (Dashboard)         │
│ Systems (Kafka) · CLI (planned)              │
├──────────────────────────────────────────────┤
│ LAYER 2: GATEWAY                             │
│ Apache APISIX (rate limit, auth, TLS)        │
├──────────────────────────────────────────────┤
│ LAYER 3: API                                 │
│ Django 5 + Django Ninja (120+ REST)          │
│ django-mcp (67 MCP tools)                    │
│ WebSocket (real-time subscriptions)          │
├──────────────────────────────────────────────┤
│ LAYER 4: INTENT ENGINE                       │
│ Query Intent · Pipeline Intent · Scraper     │
│ LLM Router · Ontology Cache                  │
│ Output: Structured JSON execution plans      │
├──────────────────────────────────────────────┤
│ LAYER 5: DOMAIN SERVICES                     │
│ Ontology · Data Intel · Scraper · ML         │
│ Voyant Agent (M7) · Shield (M9) · Capsules   │
│ Search Engine                                │
├──────────────────────────────────────────────┤
│ LAYER 6: ORCHESTRATION                       │
│ Temporal.io (25+ workflows, self-healing)    │
├──────────────────────────────────────────────┤
│ LAYER 7: DATA                                │
│ PostgreSQL · Iceberg · Kafka · Flink         │
│ Spark · Milvus · Elasticsearch · Redis       │
│ MinIO · DuckDB                               │
├──────────────────────────────────────────────┤
│ LAYER 8: GOVERNANCE                          │
│ Ranger (data RBAC) · SpiceDB (app RBAC)      │
│ Atlas (meta) · Vault · Keycloak · AuditLog   │
├──────────────────────────────────────────────┤
│ LAYER 9: OBSERVABILITY                       │
│ Prometheus · Grafana · SkyWalking            │
└──────────────────────────────────────────────┘
```

### 2.4 Side-by-Side Architecture Comparison

| Layer | Palantir | Databricks | Voyant | Voyant Advantage |
|-------|----------|------------|--------|-----------------|
| **Gateway** | Proprietary | Cloud-native | Apache APISIX | Open source, pluggable |
| **API** | REST (proprietary) | REST + SDKs (proprietary) | Django Ninja + MCP | **MCP protocol** — agents talk natively |
| **Intent/Translation (M7)** | AIP chat (LLM interprets) | Genie (LLM interprets) | Intent Engine (LLM proposes, code executes) | **Deterministic execution** — no hallucinated queries |
| **Orchestration** | Proprietary | Databricks Jobs / DLT | Temporal.io | **Replayable**, durable, self-healing |
| **Storage** | Proprietary datasets | Delta Lake (open) | Iceberg on MinIO | Open format, S3-compatible |
| **Governance** | Object security | Unity Catalog | SpiceDB + Ranger + DataHub | Granular Zanzibar-style auth |
| **Compute** | Managed | Photon + Spark serverless | Trino + Spark (self-managed) | Full control over compute |
| **AI/ML (M6)** | AIP | MLflow + Agent Bricks | MLflow-compatible + Intent Engine | Agent-native, MCP-connected |

### 2.5 What Voyant Does Differently (and WHY It's Better)

1. **Agent-Native Architecture** — Palantir and Databricks bolt agents onto existing platforms. Voyant was built with agents as the primary consumer. Every feature is MCP-callable from day one.

2. **Deterministic Execution** — Palantir AIP and Databricks Genie let the LLM generate SQL/code that executes directly. If the LLM hallucinates, the wrong query runs. Voyant's Intent Engine: LLM proposes a structured plan → Plan Validator checks against schema → Plan Executor runs deterministic code. **The LLM never touches production data.**

3. **Self-Hosted Sovereignty** — Both competitors are SaaS-only. Voyant runs on your hardware, your cloud, your air-gapped network. Full data sovereignty.

4. **Lightweight** — Voyant runs in 20 Docker containers vs Palantir/Databricks requiring massive infrastructure. A single `docker compose up` gets you a working platform.

5. **Apache-First** — Every layer uses Apache projects (Iceberg, Spark, Flink, NiFi, Ranger, Atlas, APISIX, SkyWalking). No proprietary lock-in at any layer.

---

## 3. Voyant Catalog (M3) — Ontology Engine Deep Dive

### 3.1 Palantir Ontology Architecture

Palantir's ontology is their core differentiator — the "operating system for the enterprise."

**Core Concepts:**
- **Object Types** — Schema definitions (e.g., "Customer", "Order", "Sensor")
- **Properties** — 11 data types (string, int, float, boolean, date, timestamp, enum, array, map, struct, geopoint)
- **Links** — Relationships between objects with cardinality (1:1, 1:N, M:N)
- **Actions** — Operations on objects with parameters, pre-conditions, side effects, undo
- **Functions** — Python/TypeScript business logic attached to objects/actions
- **Object Set Service** — High-scale query, filter, aggregate on object collections
- **Subscription Service** — Real-time change notifications (WebSocket-based)
- **Interfaces** — Polymorphic type abstractions (like Java interfaces)
- **Struct Types** — Nested composite types
- **Shared Properties** — Reusable property definitions across types
- **Value Types** — Domain constraints with versioning
- **Scenario Engine** — What-if analysis with branching/merging
- **Ontology Branching** — Git-like versioning for schema changes

### 3.2 Feature-by-Feature Ontology Comparison (35+ rows)

| Feature | Palantir | Voyant v4.0 | Voyant Advantage | Code Reference |
|---------|----------|-------------|-----------------|----------------|
| Object Types | Full (proprietary) | **HAS** — `ObjectType` model | Open schema, MCP-accessible | `ontology/models.py:23` |
| 11 Property Types | Full | **HAS** — `PropertyType` enum (11 types) | Identical coverage | `ontology/models.py:68` |
| Required Properties | Full | **HAS** — `required` field | — | `ontology/models.py:109` |
| Default Values | Full | **HAS** — `default_value` JSONB | — | `ontology/models.py:113` |
| Validation Rules | Full | **HAS** — `validation_rules` JSONB (regex/min/max/enum/custom) | JSON-native validation | `ontology/models.py:118` |
| Schema Versioning | Full | **HAS** — `version` auto-increment | — | `ontology/models.py:40` |
| Soft Deletion | Full | **HAS** — `deleted_at` with referential integrity | — | `ontology/models.py:44` |
| Link Types | Full | **HAS** — `LinkType` with cardinality enum | — | `ontology/models.py:208` |
| Link Cardinality | 1:1, 1:N, M:N | **HAS** — `Cardinality` enum | — | `ontology/models.py:200` |
| Link Properties | Full | **HAS** — `properties_schema` JSONB | — | `ontology/models.py:243` |
| Object CRUD | Full | **HAS** — `ObjectService` | — | `ontology/services.py` |
| Batch Create (1000+) | Full | **HAS** — `batch_create()` | — | `ontology/services.py:297` |
| Upsert | Full | **HAS** — `upsert()` by unique key | — | `ontology/services.py:323` |
| Optimistic Concurrency | Full | **HAS** — `version` field on Object | — | `ontology/models.py:168` |
| Multi-hop Traversal | Up to 10 hops | **HAS** — `LinkService.traverse()` | MCP-callable (`voyant.ontology.traverse`) | `ontology/services.py:506` |
| **Interfaces** | Full | **HAS** — `Interface` model with M2M | **Agent can query via MCP** | `ontology/models.py:351` |
| **Struct Types** | Full | **HAS** — `StructType` model | — | `ontology/models.py:410` |
| **Shared Properties** | Full | **HAS** — `SharedProperty` model with M2M | — | `ontology/models.py:451` |
| **Value Types** | Full | **HAS** — `ValueType` model with constraints | — | `ontology/models.py:499` |
| **Action Types** | Full (proprietary) | **HAS** — `ActionType` model (params, rules, side effects, undo) | **Open, auditable, MCP-executable** | `ontology/models.py:546` |
| **Action Execution** | Proprietary | **HAS** — `ActionExecutor` with validation, pre/post conditions, audit | Full undo support via `ActionExecution` | `ontology/action_executor.py` |
| **Functions** | Full (Python/TS) | **HAS** — `Function` model (Python + TS) | Sandboxed subprocess execution | `ontology/models.py:646` |
| **Function Runner** | Proprietary | **HAS** — `FunctionRunner` with timeout, memory limits | Subprocess isolation, schema validation | `ontology/function_runner.py` |
| **Object Set Service** | High-scale | **PARTIAL** — Basic ORM queries | Need: Redis caching, aggregation pipeline | — |
| **Subscription Service** | Real-time WS | **SRS** — ONT-F-032 | Will use Redis Pub/Sub + WebSocket | — |
| **Scenario Engine** | What-if branching | **MISSING** | Planned: Git-like branching | — |
| **Ontology Branching** | Git-like | **MISSING** | Planned: Version branches | — |
| **Type Classes** | Metadata classification | **MISSING** | — | — |
| **Render Hints** | UI config per type | **MISSING** | — | — |
| **Status Definitions** | Lifecycle states | **MISSING** | — | — |
| **Object Type Groups** | Organization | **SRS** — ONT-F-036 | — | — |
| **MCP Tools for Ontology** | Zero | **HAS** — 14 tools | **UNIQUE — agents can CRUD ontology via MCP** | `mcp/tools_ontology.py` |
| **Self-Hosted** | No (SaaS only) | **HAS** — Docker | Full data sovereignty | — |
| **Open Schema** | No (proprietary) | **HAS** — PostgreSQL + JSONB | Inspect, audit, extend | — |
| **Action Audit Trail** | Proprietary | **HAS** — `ActionExecution` model with `previous_values` | Full undo history | `action_executor.py:33` |

### 3.3 Exact Improvements Voyant Catalog (M3) Makes Over Palantir Ontology

| Improvement | Description | Why It Matters |
|------------|-------------|---------------|
| **MCP Access** | 14 MCP tools (`voyant.ontology.types.*`, `voyant.ontology.objects.*`, `voyant.ontology.links.*`, `voyant.ontology.traverse`, `voyant.ontology.interfaces.list`, `voyant.ontology.actions.execute`, `voyant.ontology.functions.run`) | Palantir has ZERO MCP support. AI agents cannot natively interact with Palantir ontology. Voyant agents can create types, write objects, traverse graphs, execute actions — all via standardized MCP protocol. |
| **Self-Hosted** | Runs on Docker, any infrastructure | Palantir requires $1M+ annual contracts and Palantir Forward Deployed Engineers on-site. Voyant: `docker compose up`. |
| **Open Schema** | PostgreSQL + JSONB storage, inspectable | Palantir's dataset format is proprietary. Voyant's ontology is stored in standard PostgreSQL — you can query it directly, back it up, migrate it. |
| **Agent-Native Design** | Every ontology operation is MCP-callable | Palantir was designed for humans first, agents second. Voyant was designed for agents first, humans second. |
| **Function Sandboxing** | Subprocess isolation with timeout + memory limits (`function_runner.py`) | Voyant runs user functions in isolated subprocesses with strict resource limits. Palantir's function execution details are opaque. |
| **Temporal Durability** | All ontology mutations can be wrapped in Temporal workflows | Actions can be made durable and replayable via Temporal. Palantir has no equivalent durable execution layer. |

---

## 4. Voyant Analyze (M5) — Data Intelligence Comparison

### 4.1 Three-Way Data Stack

| Capability | Palantir Foundry | Databricks | Voyant v4.0 |
|-----------|-----------------|------------|-------------|
| **Compute Engine** | Managed (proprietary) | Photon (C++) + Spark SQL | Trino + Spark SQL |
| **Storage Format** | Proprietary datasets | Delta Lake (ACID, time travel) | Apache Iceberg on MinIO |
| **Ingestion** | 200+ connectors, Pipeline Builder | Lakeflow (DLT), Auto Loader, 200+ connectors | Airbyte (200+ connectors), NiFi |
| **SQL** | SQL Studio (proprietary) | Databricks SQL (Photon-accelerated) | Trino SQL (via `tools_core.py:181`) |
| **Data Quality** | Built-in expectations | Lakeflow expectations + quality monitoring | Great Expectations + Evidently |
| **Data Lineage** | Built-in | Automated column-level lineage | DataHub client (`tools_catalog.py:43`) |
| **Streaming** | Flink (managed) | Structured Streaming, Auto Loader | Kafka + Flink (stub) |
| **Pipeline Builder** | Visual DAG (Pipeline Builder) | Lakeflow declarative pipelines | Temporal workflows (code-first) |
| **Time Travel** | Dataset snapshots | Delta Lake time travel (24/7) | Iceberg snapshots (planned) |
| **NL→SQL** | AIP chat | Genie (text-to-SQL) | Intent Engine (NL→plan→Trino SQL) |
| **MCP Data Tools** | None | None | `voyant.sql`, `voyant.ingest`, `voyant.profile`, `voyant.quality`, `voyant.analyze`, `voyant.kpi`, `voyant.lineage` |

### 4.2 Data Engineering: What Voyant Analyze (M5) Improves

| Improvement | Technical Approach | Why It's Better |
|------------|-------------------|-----------------|
| **Agent-First Data Ops** | Every data operation is an MCP tool. An AI agent can discover sources, ingest data, profile quality, run SQL, check lineage — all via MCP protocol. | Neither Palantir nor Databricks allow AI agents to manage data pipelines natively. Their agents can query data, but not orchestrate ingestion/quality/lineage. |
| **Temporal Durability** | All pipelines run as Temporal workflows with replay, retry, timeout. | If a Databricks job fails mid-run, you restart. If a Temporal workflow fails, it automatically resumes from the last completed step. |
| **MCP Lineage Tool** | `voyant.lineage(urn, direction, depth)` — agents can traverse upstream/downstream lineage graphs via MCP. | Neither competitor exposes lineage as a programmatic API for agents. |
| **KPI Template Engine** | `voyant.kpi_templates.*` — pre-built SQL templates for common KPIs, agents can list, get, render. | Neither competitor has agent-callable KPI templates. |

### 4.3 Databricks-Specific Gaps Voyant Must Close

| Databricks Feature | Voyant Gap | Improvement Strategy |
|-------------------|------------|---------------------|
| **Photon Engine** | Trino is 10–100x slower on analytical queries | Phase 3: Deploy Spark with Photon-compatible optimizations; long-term: evaluate DuckDB for small queries, Spark for large |
| **Auto Loader** | No incremental file ingestion | Build: Temporal workflow watching MinIO/S3 for new files, auto-ingest |
| **Serverless Compute** | Manual container scaling | Phase 6: K8s HPA based on queue depth, or serverless Spark on K8s |
| **Managed Tables** | No auto-optimization | Build: Compaction + Z-ordering scheduled workflows on Iceberg tables |
| **Business Semantics** | No semantic layer | Phase 5: Ontology → semantic layer mapping (object types = business entities) |

---

## 5. Voyant ML (M6) — ML/AI Platform Deep Dive

### 5.1 Databricks MLflow: Full Feature Map

| MLflow Feature | Databricks Implementation | Voyant v4.0 Status |
|---------------|--------------------------|-------------------|
| **Experiment Tracking** | Experiments + Runs (params, metrics, artifacts) | **HAS** — `Experiment`, `Run`, `RunArtifact` models (`ml_platform/models.py:15-94`) |
| **Model Registry** | Registered models + versions + stages (none/staging/production/archived) | **HAS** — `RegisteredModel`, `ModelVersion` models (`ml_platform/models.py:97-144`) |
| **Model Serving** | Real-time endpoints + batch inference + GPU | **HAS** — `ModelEndpoint` model (`ml_platform/models.py:147-176`) |
| **MLflow-Compatible API** | Native (built by Databricks creators) | **SRS** — ML-F-005: Will implement `/api/2.0/mlflow/*` endpoints |
| **AutoML** | Built-in (classification, regression, forecasting) | **MISSING** — No AutoML engine |
| **Feature Store** | Centralized feature engineering + serving | **MISSING** — No feature store |
| **LLM Fine-Tuning** | Mosaic AI Training (open-source LLMs) | **MISSING** — No fine-tuning |
| **MLflow Tracing** | GenAI tracing (LLM call logging) | **MISSING** — No tracing |
| **MLflow Evaluate** | AI judges, custom metrics, human feedback | **SRS** — ML-F-007: Agent evaluation with AI judge |
| **Collaborative Notebooks** | PySpark, SQL, R, Scala | **MISSING** — No notebook environment |
| **GPU Clusters** | Multi-GPU training | **MISSING** — CPU-only |

### 5.2 Palantir AIP: Feature Map

| AIP Feature | Palantir Implementation | Voyant v4.0 Status |
|------------|------------------------|-------------------|
| **Model Connectivity** | Connect any LLM (OpenAI, Anthropic, etc.) | **PARTIAL** — MCP tools connect models |
| **Agent Bricks** | Build agents with tools, evaluate, deploy | **PARTIAL** — `AgentDefinition` + `AgentEvaluation` models |
| **AIP Chat** | Chat with your data (NL→query) | **PARTIAL** — Intent Engine (NL→plan→execute) |
| **Code Execution** | Execute Python/SQL in sandbox | **HAS** — `FunctionRunner` (subprocess sandbox) |
| **Evaluation** | AI-powered evaluation | **SRS** — ML-F-007 |
| **Ontology Integration** | Agents operate on ontology objects | **HAS** — 14 ontology MCP tools |
| **Application Studio** | Build AI-powered apps | **MISSING** — No app builder |

### 5.3 Voyant ML (M6): What's Built vs Planned

| Model | Status | Description |
|-------|--------|-------------|
| `Experiment` | **BUILT** | MLflow-compatible experiment tracking |
| `Run` | **BUILT** | Individual runs with params, metrics, artifacts |
| `RunArtifact` | **BUILT** | File artifacts (model, dataset, image, metric, log) |
| `RegisteredModel` | **BUILT** | Model registry with naming |
| `ModelVersion` | **BUILT** | Versioned models with staging pipeline (none→staging→production→archived) |
| `ModelEndpoint` | **BUILT** | Serving endpoints with invocation tracking |
| `AgentDefinition` | **BUILT** | Agent config: system_prompt, model, tools, guardrails |
| `AgentEvaluation` | **BUILT** | AI-judge evaluation with test cases, scores, pass rates |

### 5.4 Exact ML Improvements Voyant ML (M6) Makes

| Improvement | Technical Approach | Why It's Better |
|------------|-------------------|-----------------|
| **Agent Evaluation (not just model evaluation)** | `AgentDefinition` + `AgentEvaluation` models evaluate entire agent pipelines — prompt + model + tools + guardrails — not just individual model outputs. | Databricks evaluates models. Voyant evaluates agents. An agent is more than a model — it's the full system. |
| **MCP-Connected ML** | Every ML operation will be an MCP tool: `voyant.ml.experiment.create`, `voyant.ml.run.log`, `voyant.ml.model.deploy`. | Neither Palantir nor Databricks allow AI agents to manage ML experiments programmatically. |
| **Capsule-Deployed Models** | Models can be packaged as capsules (Ed25519-signed) for portable, auditable deployment. | Neither competitor has signed, portable model deployment. |
| **Intent Engine for ML** | "Train a random forest on the sales data, predict Q4 revenue" → Intent Engine generates structured ML plan → deterministic execution. | No competitor translates NL directly into structured ML training plans with schema validation. |
| **Guardrails in AgentDefinition** | `guardrails` field: `max_queries_per_session`, `blocked_tables`, `require_approval`. | Databricks has Unity AI Gateway guardrails. Voyant has per-agent guardrails at the definition level. |

---

## 6. Voyant Agent (M7) — Agent Platform Comparison

### 6.1 Three-Way Agent Comparison

| Capability | Databricks Agent Bricks | Palantir AIP | Voyant |
|-----------|------------------------|-------------|--------|
| **Agent Definition** | Code-based (Python, LangChain, etc.) | AIP config | `AgentDefinition` model (prompt + model + tools + guardrails) |
| **Tool System** | Unity Catalog Functions (proprietary) | Proprietary tools | **MCP Protocol (67 tools)** |
| **NL Interface** | Genie (text-to-SQL) | AIP Chat | **Intent Engine** (NL→structured plan→deterministic execution) |
| **Evaluation** | AI judges + human feedback | Limited | `AgentEvaluation` model (test cases, AI judge, scores) |
| **Governance** | Unity AI Gateway | Object security | SpiceDB + Ranger + per-agent guardrails |
| **Multi-Model** | Any model via Agent Bricks | Model connectivity | Model-agnostic (LLM Router) |
| **Deployment** | Model Serving endpoints | AIP deployment | ModelEndpoint + Capsule system |
| **Code Execution** | Databricks notebooks | AIP Code Workspaces | `FunctionRunner` (sandboxed subprocess) |
| **Data Access** | Via SQL/Unity Catalog | Via ontology | Via MCP tools (SQL, ontology, scraper, search) |
| **Deterministic Execution** | No (LLM generates code directly) | No (LLM generates code directly) | **Yes** (LLM proposes plan, code executes) |

### 6.2 Why Voyant Agent (M7) Is Superior

**1. MCP Protocol (Unique)**
```
Palantir/Databricks: Agent → Proprietary API → Platform → Result
Voyant:              Agent → MCP Protocol → 67 Standardized Tools → Result
```
MCP is an open, standardized protocol. Any MCP-compatible agent (Claude, GPT, Gemini, open-source) can connect to Voyant and use all 67 tools. Palantir and Databricks lock agents into proprietary APIs.

**2. Deterministic Execution (Unique)**
```
Databricks Genie:  User: "Show me sales in June" → LLM generates SQL → SQL executes
                   Risk: LLM hallucinates wrong table/column → wrong query runs

Voyant Intent:     User: "Show me sales in June" → LLM generates plan →
                   Plan Validator checks against ontology schema →
                   Plan Executor runs validated code → Result
                   Safety: LLM NEVER touches production data directly
```

**3. 67 MCP Tools (Comprehensive)**
| Category | Tools | Examples |
|----------|-------|---------|
| Core Operations | 11 | `voyant.discover`, `voyant.connect`, `voyant.ingest`, `voyant.sql`, `voyant.search` |
| Catalog/Management | 23 | `voyant.lineage`, `voyant.sources.*`, `voyant.jobs.*`, `voyant.kpi_templates.*`, `voyant.discovery.*` |
| Governance | 7 | `voyant.governance.*`, `voyant.quotas.*` |
| Ontology | 14 | `voyant.ontology.types.*`, `voyant.ontology.objects.*`, `voyant.ontology.links.*`, `voyant.ontology.actions.execute`, `voyant.ontology.functions.run` |
| Vector/Search | 2 | `voyant.vector.search`, `voyant.vector.index` |
| Scraper | 7+ | `scrape.fetch`, `scrape.extract`, `scrape.ocr`, `scrape.parse_pdf`, `scrape.transcribe` |
| **Total** | **67** | **83+ targeted for v4.0** |

**4. Capsule System (Unique)**
- Portable, Ed25519-signed agent plugins
- Each capsule bundles: tools + prompts + guardrails + dependencies
- Verified before execution — tamper-proof
- Neither Palantir nor Databricks has anything equivalent

**5. Intent Engine (Unique)**
- 6-stage pipeline: Classify → Schema Resolve → Plan Generate → Plan Validate → Execute → Format
- LLM is only used in stage 3 (Plan Generator)
- Stages 4-6 are pure deterministic code
- Plans are cached for reuse (same intent = cached plan)

---

## 7. Voyant Shield (M9) — Governance Comparison

### 7.1 Three-Way Governance

| Capability | Databricks Unity Catalog | Palantir | Voyant |
|-----------|-------------------------|----------|--------|
| **Authentication** | SSO, SAML, OAuth | SSO, SAML | Keycloak (SSO, SAML, OAuth, OIDC) |
| **App-Level RBAC** | Unity Catalog permissions | Object security policies | SpiceDB (Zanzibar model) |
| **Data-Level RBAC** | Attribute-based access control | Object-level permissions | Apache Ranger (row/column policies) |
| **Row-Level Security** | Dynamic views + RLS policies | Object security | Ranger RLS filters (SRS GOV-F-003) |
| **Column Masking** | Built-in column masking | N/A | Ranger column masking (SRS GOV-F-004) |
| **Audit Logging** | Unity Catalog audit logs | Full audit trail | `AuditLog` model + SkyWalking |
| **Data Lineage** | Automated column-level lineage | Built-in lineage | DataHub client (partial) |
| **Data Classification** | AI-powered auto-classification | Markings system | SRS: Planned |
| **Secrets** | Databricks Secrets | Proprietary | HashiCorp Vault |
| **Agent Governance** | Unity AI Gateway (access, spend, observability) | Object security | Per-agent guardrails in `AgentDefinition` |
| **Multi-Tenancy** | Workspace isolation | Organization isolation | `TenantModel` on every model |
| **Encryption** | At-rest + in-transit | At-rest + in-transit | TLS in-transit, Vault for secrets |

### 7.2 Governance Improvements Voyant Shield (M9) Makes

| Improvement | Description | Why It's Better |
|------------|-------------|-----------------|
| **Agent-Level Governance** | `AgentDefinition.guardrails`: `max_queries_per_session`, `blocked_tables`, `require_approval`. SpiceDB checks which agents can access which resources. | Databricks has Unity AI Gateway at the platform level. Voyant has guardrails at the individual agent definition level — more granular. |
| **Intent Engine Trust Boundary** | The Intent Engine's Plan Validator is a governance checkpoint. Every LLM-generated plan is validated against ontology schema and permissions BEFORE execution. | Neither Palantir nor Databricks validate LLM output before execution. |
| **Zanzibar-Style Auth** | SpiceDB implements Google's Zanzibar authorization model (the same model that powers Google's internal permissions). | More expressive than Databricks' role-based permissions. Supports complex relationships like "manager of team X can access data of team X's members." |
| **Dual-Layer RBAC** | App-level (SpiceDB) + Data-level (Ranger). Separation of concerns. | Databricks conflates app and data governance in Unity Catalog. Voyant separates them for defense-in-depth. |

---

## 8. Voyant Scrape (M8) — Scraper Comparison (vs Octoparse + Bright Data)

### 8.1 Feature Comparison

| Feature | Octoparse | Bright Data | Voyant Octopus |
|---------|-----------|------------|----------------|
| **No-Code Visual Builder** | Full (drag-and-drop) | Full (visual editor) | SRS: Planned (React builder) |
| **Template Library** | 600+ templates | 100+ templates | SRS: 50 templates Phase 1, 200+ Phase 5 |
| **Browser Automation** | Full | Full | **HAS** — 8 browser arms (static, dynamic, crawl, document, OCR, transcribe, evasion, archive) |
| **Anti-Bot** | Full | Enterprise-grade | Partial (user-agent rotation, fingerprint, curl-cffi, camoufox) |
| **CAPTCHA Solving** | AI-powered | AI-powered | SRS: Planned (reCAPTCHA, hCaptcha, Turnstile) |
| **IP Rotation** | Residential proxies | 72M+ residential IPs | SRS: Planned (BrightData/SmartProxy/Oxylabs integration) |
| **Deep Research** | None | None | **UNIQUE** — `deep_research_workflow.py` with query generation, multi-source synthesis |
| **OCR** | None | Limited | **HAS** — Tesseract OCR (`arm_ocr`) |
| **PDF Parsing** | None | Limited | **HAS** — pdfplumber (`pdf_parser.py`) |
| **Audio Transcription** | None | None | **HAS** — Transcription arm (`arm_transcribe`) |
| **MCP Integration** | None | None | **UNIQUE** — 7 MCP tools (`scrape.*`) |
| **Ontology Integration** | None | None | **UNIQUE** — Scrape → auto-create ontology objects |
| **Temporal Durability** | None | None | **UNIQUE** — Scrape jobs as Temporal workflows (replayable, self-healing) |
| **Self-Hosted** | No | No | **YES** — Docker |
| **Open Source** | No | No | **YES** — Apache 2.0 |
| **Content Extraction** | Basic | Basic | **5-strategy chain**: trafilatura → readability → newspaper → crawl4ai → fallback |
| **Evasion Techniques** | Basic | Advanced | Partial: User-agent rotation, fingerprint randomization, curl-cffi TLS, Camoufox browser |

### 8.2 Voyant Scrape (M8) Unique Advantages (No Competitor Has These)

1. **Deep Research Pipeline** — Multi-step research workflow: generate queries → search multiple engines → fetch + extract → synthesize results. No web scraping tool has integrated deep research.

2. **MCP Integration** — 7 MCP tools let AI agents orchestrate scraping: `scrape.fetch`, `scrape.extract`, `scrape.ocr`, `scrape.parse_pdf`, `scrape.transcribe`, `scrape.deep_archive`, `voyant.research.run/status`.

3. **Ontology Integration** — Scraped data can automatically create ontology objects. Scrape a product page → create a `Product` ontology object with structured properties. No competitor connects scraping to a semantic data model.

4. **5-Strategy Content Extraction** — `content_extractor.py` chains 5 extractors: trafilatura → readability → newspaper → crawl4ai → raw fallback. Each fallback is tried if the previous one fails. This is more resilient than any competitor's single-strategy extraction.

---

## 9. UI/UX Comparison

### 9.1 Application Layer

| UI Component | Palantir Workshop | Databricks | Voyant v4.0 |
|-------------|------------------|------------|-------------|
| **App Builder** | Workshop (low-code, ontology-connected) | Databricks Apps (serverless) | SRS: Visual builders (Phase 4) |
| **Notebooks** | Quiver (analytical) | Databricks Notebooks (Py/SQL/R/Scala) | **MISSING** |
| **Object Explorer** | Full (search, filter, pivot, compare) | N/A (no ontology) | SRS: React Explorer (Phase 4) |
| **Graph View** | Vertex (force-directed) | N/A | SRS: Sigma.js graph (Phase 4) |
| **SQL Editor** | SQL Studio | Databricks SQL Editor | **HAS** — `voyant.sql` MCP tool (agent-accessible) |
| **Dashboard** | Configurable views | Dashboards (built-in BI) | 13 Lit admin views |
| **Map View** | Map templates | N/A | SRS: Planned |
| **Data Pipeline Builder** | Visual DAG (Pipeline Builder) | Lakeflow visual builder | SRS: React Flow DAG editor |
| **NL Interface** | AIP Chat | Genie One (AI Assistant) | Intent Engine (backend) + SRS: Chat UI |

### 9.2 What Voyant Improves for Each

| Component | Voyant's Improvement Strategy |
|----------|------------------------------|
| **Object Explorer** | React + TanStack Table + Sigma.js. Not just table view — grid, map, graph. Plus: every explorer action is MCP-callable, so agents can explore too. |
| **SQL Editor** | Agent-accessible via `voyant.sql` MCP tool. SQL isn't just for humans — agents can execute, review, and iterate on queries. |
| **Dashboard Builder** | Chart.js/Apache ECharts integration. Widgets are ontology-aware (show object data). |
| **Pipeline Builder** | React Flow DAG editor. Pipelines execute as Temporal workflows — durable, replayable, self-healing. Palantir's Pipeline Builder has no durable execution. |
| **NL Interface** | Intent Engine (backend) + Chat UI. Unlike Genie/AIP Chat, the Intent Engine validates plans before execution. |

### 9.3 Palantir Foundry — Screen-by-Screen Comparison

Palantir has 5 products: **Foundry** (data + ontology + analytics), **Gotham** (intelligence/military), **AIP** (AI platform), **Workshop** (app builder), **Quiver** (notebooks). Below is every major screen and how Voyant maps to it.

#### 9.3.1 Ontology Manager Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Browse Object Types** | Table view with search across all types | `voyant.ontology.types.list` MCP tool + admin dashboard | **HAS** (MCP) / **SRS** (React UI) | Agent-callable via MCP; Palantir has no agent API for this |
| **Edit Type — Properties Tab** | Edit property definitions (name, type, required, default, validation) | `voyant.ontology.types.get` returns full property definitions; CRUD via REST | **HAS** (API + MCP) | Open schema in PostgreSQL; agents can read/write property defs |
| **Edit Type — Links Tab** | View/edit link types connected to this object type | LinkType model with FK to ObjectType; `voyant.ontology.links.*` tools | **HAS** (API + MCP) | Agents can programmatically manage relationships |
| **Edit Type — Actions Tab** | View/edit action types on this object type | ActionType model with FK to ObjectType; `voyant.ontology.actions.execute` | **HAS** (API + MCP) | ActionExecutor with full undo support and audit trail |
| **Edit Type — Functions Tab** | View/edit Python/TS functions attached to type | Function model with FK to ObjectType; `voyant.ontology.functions.run` | **HAS** (API + MCP) | Sandboxed subprocess with timeout + memory limits |
| **Create New Type Wizard** | Step-by-step: name → properties → links → review | REST API + MCP `voyant.ontology.types.create` (with properties list) | **HAS** (API) / **SRS** (React wizard) | Single API call creates type + properties; agent-driven creation |
| **Type Hierarchy Tree** | Visual inheritance view of type hierarchy | Interface model with M2M implementing_types | **PARTIAL** (model exists, no tree UI) | Interfaces are MCP-queryable; agents can discover type relationships |
| **Schema Diff Viewer** | Compare version changes | ObjectType.version field tracks changes | **PARTIAL** (version tracking, no diff UI) | SRS: Visual diff viewer in Phase 4 |

**What Voyant does BETTER on every Ontology Manager screen:**
- Every operation is MCP-callable (14 ontology tools). Palantir's Ontology Manager is human-only UI.
- Open PostgreSQL schema — direct SQL access to ontology metadata. Palantir's is opaque.
- ActionExecutor records full `previous_values` for undo — more transparent than Palantir's proprietary undo.

#### 9.3.2 Object Explorer Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Search Bar** | Semantic + full-text search across all objects | Milvus vector search + Elasticsearch full-text; `voyant.search` + `voyant.vector.search` MCP tools | **PARTIAL** (backend exists, no React search bar) | Dual search: vector (semantic) + Elasticsearch (full-text). Agent-callable. |
| **Filter Builder** | Visual: field → operator → value with AND/OR groups | ORM filters in ObjectService; SRS: React filter builder | **PARTIAL** (API-level filtering, no visual builder) | SRS Phase 4: React visual filter builder with condition groups |
| **Pivot Table View** | Row/column configuration on object properties | SRS: Pivot component | **SRS** (Phase 4) | Will use Apache ECharts pivot; also agent-callable via MCP |
| **Compare View** | Side-by-side object comparison | SRS: Compare component | **SRS** (Phase 4) | Agents can compare objects programmatically via `voyant.ontology.objects.get` |
| **Export (CSV, JSON)** | Export filtered results | ObjectService.list → serialize → download | **HAS** (API-level) | MCP agents can export data programmatically; add JSONL streaming |

**What Voyant does BETTER on Object Explorer:**
- **Agent-accessible search**: `voyant.search` and `voyant.vector.search` let AI agents search the ontology. Palantir has zero agent API for object exploration.
- **Dual vector + text search**: Milvus dense vectors + Elasticsearch sparse. More resilient than Palantir's single search.
- **MCP export**: Agents can list objects, filter, and export — all programmatically. No human needed.

#### 9.3.3 Object Detail Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Properties Panel** | View/edit object properties | `voyant.ontology.objects.get` returns full properties; update via `voyant.ontology.objects.update` | **HAS** (API + MCP) | Optimistic concurrency via version field; agents can read/write |
| **Relationships Panel** | Graph of connected objects (outgoing + incoming links) | `voyant.ontology.objects.get` returns `outgoing_links` + `incoming_links`; `voyant.ontology.traverse` for multi-hop | **HAS** (API + MCP) | Up to 10-hop traversal via MCP — deeper than Palantir's default view |
| **Actions Panel** | Execute operations on this object | `voyant.ontology.actions.execute` MCP tool | **HAS** (API + MCP) | Full undo support via ActionExecution model; audit trail with previous_values |
| **Timeline Panel** | History of changes to this object | AuditLog model + ActionExecution history | **PARTIAL** (audit exists, no timeline UI) | SRS Phase 4: Visual timeline; data is already captured |
| **Comments Panel** | Collaborative annotations on objects | **MISSING** | **SRS** (Phase 5) | Will use Django comments framework; agent-callable via MCP |

**What Voyant does BETTER on Object Detail:**
- **Deep traversal**: `voyant.ontology.traverse` supports up to 10 hops with direction control (outgoing/incoming/both). Palantir's UI typically shows 1-2 hops.
- **Action undo**: Every action execution records `previous_values`. Full revert capability. More transparent than Palantir.
- **Agent interaction**: Every detail panel action is MCP-callable. An AI agent can view, edit, execute actions, traverse links — all programmatically.

#### 9.3.4 Pipeline Builder Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **DAG Canvas** | Drag nodes, connect edges (visual pipeline editor) | SRS: React Flow DAG editor; Temporal workflows as backend | **SRS** (Phase 4, React Flow) | Pipelines execute as Temporal workflows — durable, replayable, self-healing |
| **Node Types** | Source, Transform, Filter, Aggregate, Join, Output | Temporal activities; Airbyte for source; Spark/Trino for transform | **PARTIAL** (backend exists, no visual nodes) | Code-first pipelines via Temporal are more debuggable than visual-only |
| **Node Configuration** | Configure each node (connection, transform logic) | Django admin config; SRS: visual config panels | **SRS** (Phase 4) | JSON-configured nodes; version-controlled |
| **Run History** | Status, duration, logs per pipeline run | Temporal UI (built-in at port 45089); Job model | **HAS** (Temporal UI) | Temporal UI is superior — shows every workflow step, replay capability |
| **Schedule Configuration** | Cron-based scheduling | Temporal schedules; ScrapeSchedule model for scraper | **HAS** (Temporal) | Durable scheduling — survives restarts; exactly-once execution |
| **Parameter Templates** | Reusable pipeline configurations | SRS: Pipeline parameters | **SRS** | Will support JSON parameter schemas with validation |

**What Voyant does BETTER on Pipeline Builder:**
- **Temporal Durability**: Every pipeline is a Temporal workflow. If any step fails, Temporal automatically retries from the failed step. Palantir's Pipeline Builder has no durable execution — if a job fails, you restart from scratch.
- **Temporal UI**: Built-in workflow visualization at port 45089 shows every step, its status, duration, and logs. Replay capability for debugging.
- **Code-first option**: Developers can write pipelines as Python Temporal workflows instead of using a visual builder. More powerful for complex logic.

#### 9.3.5 Workshop (App Builder) Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Component Palette** | Tables, forms, charts, maps, text widgets | SRS: React component library | **SRS** (Phase 4) | Components will be ontology-aware + MCP-callable |
| **Drag-Drop Layout** | Visual layout editor | SRS: React drag-drop builder | **SRS** (Phase 4) | Lit 3 + Tailwind (current); React (planned) |
| **Data Binding** | Connect components to ontology objects | Ontology API integration | **SRS** (Phase 4) | MCP tools let agents create and configure apps programmatically |
| **Action Configuration** | What happens on click/submit | ActionType + ActionExecutor | **HAS** (backend) | Full undo support; side effects are logged |
| **Preview Mode** | Preview app before publishing | SRS: Live preview | **SRS** (Phase 4) | Hot-reload with Vite |
| **Publish to Marketplace** | Share apps across organization | SRS: Capsule distribution | **PARTIAL** (capsule system exists, no marketplace UI) | Ed25519-signed capsules for auditable distribution |

**What Voyant does BETTER on Workshop:**
- **Agent-created apps**: Via MCP, agents can programmatically create and configure Workshop-equivalent apps. Palantir's Workshop is human-only.
- **Capsule distribution**: Apps can be packaged as Ed25519-signed capsules for tamper-proof distribution. Palantir's marketplace has no signing.
- **Dual access**: Every Workshop action has a corresponding MCP tool. Users can interact via UI OR agents can interact via MCP.

#### 9.3.6 Quiver (Notebooks) Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Cell Editor** | Code, markdown, SQL, visualization cells | **MISSING** — No notebook environment | **SRS** (Phase 6: Jupyter integration) | Will embed JupyterHub; agent-accessible via MCP |
| **Collaborative Editing** | Multiple users edit simultaneously | **MISSING** | **SRS** (Phase 6) | JupyterHub supports real-time collaboration |
| **Kernel Management** | Python, R, SQL kernels | **MISSING** | **SRS** (Phase 6) | Jupyter kernels; MCP tool for programmatic execution |
| **Output Rendering** | Tables, charts, maps | **MISSING** | **SRS** (Phase 6) | Will use Apache ECharts for inline visualization |
| **Version History** | Track notebook changes | **MISSING** | **SRS** (Phase 6) | Git integration for notebooks |

**What Voyant WILL do BETTER on Notebooks:**
- **Agent-executable cells**: MCP tools to create, execute, and read notebook cells. Agents can write and run analysis code in notebooks.
- **FunctionRunner**: Voyant's `FunctionRunner` already provides sandboxed Python/TS execution with timeout and memory limits. This becomes the notebook kernel execution engine.
- **Intent Engine integration**: "Run this analysis in a notebook" → Intent Engine generates cell sequence → deterministic execution.

#### 9.3.7 AIP (AI Platform) Screens

| Palantir Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|----------------|-------------|-------------------|--------|-----------------|
| **Model Connectivity** | Configure LLM providers (OpenAI, Anthropic, etc.) | LLM Router in Intent Engine; model_provider field in AgentDefinition | **HAS** (backend) | Model-agnostic; supports any OpenAI-compatible provider |
| **Logic Studio** | Build AI workflows | Intent Engine (backend) + SRS: visual workflow builder | **PARTIAL** (Intent Engine, no visual builder) | Deterministic execution: LLM proposes, code executes |
| **Agent Builder** | Define agents with tools + guardrails | `AgentDefinition` model (system_prompt, model, tools, guardrails) | **HAS** (model) | 67 MCP tools as agent tools; per-agent guardrails |
| **Evaluation Framework** | Test cases + scoring | `AgentEvaluation` model (test_cases, AI judge, scores) | **HAS** (model) | AI-judge evaluation with per-test-case scoring |
| **Deployment Management** | Deploy agents to production | `ModelEndpoint` model + Capsule system | **HAS** (models) | Ed25519-signed capsule deployment; MCP-callable |
| **Monitoring Dashboard** | Agent performance metrics | Prometheus + Grafana + SkyWalking | **HAS** (observability stack) | Full distributed tracing via SkyWalking |

**What Voyant does BETTER on AIP:**
- **Deterministic execution**: Voyant's Intent Engine validates LLM plans against schema before execution. Palantir's AIP lets LLM-generated code execute directly.
- **67 MCP tools**: Voyant agents have access to 67 standardized tools. Palantir's tools are proprietary and less numerous.
- **Capsule deployment**: Agent deployments are Ed25519-signed for tamper-proof distribution.
- **Agent-level guardrails**: Per-agent `guardrails` field in AgentDefinition. More granular than Palantir's platform-level controls.

---

### 9.4 Databricks — Screen-by-Screen Comparison

Databricks has 15 products. Below is every major screen and how Voyant maps to it.

#### 9.4.1 Workspace Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **File Browser** | Browse notebooks, libraries, models, experiments | Django admin panel (13 views); SRS: React file browser | **PARTIAL** (admin panel) | Self-hosted: files are on your own MinIO; no cloud lock-in |
| **Notebook Editor** | Cells: code, markdown, SQL, visualization | **MISSING** — No notebook | **SRS** (Phase 6: Jupyter) | Will embed JupyterHub with MCP integration |
| **Collaboration** | Shared notebooks, comments | **MISSING** | **SRS** (Phase 6) | Agent collaboration: agents can share artifacts via MCP |
| **Version Control** | Git integration | **MISSING** | **SRS** (Phase 6) | Git-native: all config is version-controlled |
| **Cluster Management** | Start/stop/configure compute clusters | Docker container management; K8s (planned) | **PARTIAL** (manual Docker) | `docker compose up` — simpler than Databricks cluster management |
| **Job Scheduler** | Cron-based job scheduling | Temporal scheduling (built-in) | **HAS** (Temporal) | Durable scheduling with replay — survives restarts |

#### 9.4.2 SQL Editor Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Monaco Editor** | SQL editor with autocomplete | SRS: Monaco-based SQL editor | **SRS** (Phase 4) | Agents can also write SQL via `voyant.sql` MCP tool |
| **Schema Browser** | Catalogs → schemas → tables → columns tree | `voyant.tables.list` + `voyant.tables.columns` MCP tools | **HAS** (MCP) | Agent-callable: agents can browse schemas programmatically |
| **Query Results Table** | Tabular query results | `voyant.sql` returns columns + rows + row_count + truncated flag | **HAS** (MCP) | JSON-native results; agents can process results immediately |
| **Visualization from Results** | Chart from query data | SRS: ECharts visualization | **SRS** (Phase 4) | MCP tools let agents create visualizations programmatically |
| **Query History** | List of past queries | SRS: Query history model | **SRS** | Agent-accessible: agents can review past queries |
| **Saved Queries** | Persist named queries | SRS: Saved query model | **SRS** | MCP tool: `voyant.queries.save` (planned) |
| **SQL AI Assistant (Genie)** | NL → SQL generation | Intent Engine: NL → structured plan → SQL | **HAS** (Intent Engine) | Deterministic: plan is validated before SQL execution. Genie generates SQL directly — risk of hallucinated queries. |

**What Voyant does BETTER on SQL Editor:**
- **Agent-native SQL**: `voyant.sql` MCP tool lets any AI agent execute SQL queries. Databricks SQL Editor is human-only.
- **Deterministic NL→SQL**: Intent Engine generates a structured plan that is validated against the ontology schema before execution. Databricks Genie generates SQL directly from NL — no validation, hallucination risk.
- **Schema browsing for agents**: `voyant.tables.list` and `voyant.tables.columns` let agents discover data structures. No competitor exposes schema browsing as an agent API.

#### 9.4.3 Dashboard Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Widget Palette** | Chart, table, text, filter, image widgets | SRS: Widget library (ECharts + TanStack Table) | **SRS** (Phase 4/5) | Widgets are ontology-aware; show real-time object data |
| **Drag-Drop Layout** | Arrange widgets on canvas | SRS: React grid layout | **SRS** (Phase 5) | Agent-created dashboards via MCP (planned) |
| **Data Source Binding** | Each widget bound to SQL query | Widget → SQL → Trino/Iceberg | **SRS** | MCP tools: agents can configure data sources for widgets |
| **Chart Types** | Line, bar, pie, scatter, heatmap, counter, table | Apache ECharts (planned: 20+ chart types) | **SRS** | ECharts has more chart types than Databricks built-in |
| **Filter Widgets** | Date range, dropdown, multi-select | SRS: Filter components | **SRS** (Phase 5) | Agent-set filters: agents can programmatically configure filters |
| **Auto-Refresh** | Scheduled data refresh | SRS: WebSocket-based refresh | **SRS** | Temporal scheduled refresh (more reliable than polling) |
| **Sharing & Permissions** | Share dashboards with teams | SpiceDB RBAC; SRS: dashboard sharing | **PARTIAL** | Zanzibar-style auth: more granular than Databricks role-based sharing |
| **Embedded Analytics** | Embed dashboards in external apps | SRS: Embeddable components | **SRS** (Phase 6) | Open-source: embed without licensing restrictions |

#### 9.4.4 MLflow Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Experiment List** | Name, tags, run count | `Experiment` model | **HAS** (model) / **SRS** (React UI) | Agent-callable: `voyant.ml.experiment.list` (planned MCP tool) |
| **Run Comparison** | Side-by-side params + metrics | `Run` model with params + metrics JSON | **HAS** (model) | Agents can compare runs programmatically |
| **Run Detail** | Params, metrics, artifacts, tags | `Run` + `RunArtifact` models | **HAS** (models) | MCP tools: agents can log params/metrics/artifacts |
| **Artifact Viewer** | Browse model files, images, data | `RunArtifact` model with storage_path | **HAS** (model) | MinIO-based storage; self-hosted, no vendor lock-in |
| **Model Registration** | Register best model from run | `RegisteredModel` + `ModelVersion` models | **HAS** (models) | Staging pipeline: none → staging → production → archived |
| **Model Registry List** | Model list with versions + stages | `RegisteredModel` + `ModelVersion` | **HAS** (models) | Agent-callable model management |
| **Stage Transitions** | None → Staging → Production → Archived | `ModelVersion.stage` field with choices | **HAS** (model) | Agents can promote/demote models via API |
| **Serving Configuration** | Configure model serving endpoints | `ModelEndpoint` model with config JSON | **HAS** (model) | Self-hosted serving; no per-DBU cost |

**What Voyant does BETTER on MLflow screens:**
- **Agent-managed ML**: Every ML operation will be an MCP tool. Databricks MLflow is human-UI-only.
- **Self-hosted serving**: Model endpoints run on your infrastructure. No per-DBU pricing. No vendor lock-in.
- **Agent evaluation**: `AgentEvaluation` model evaluates entire agent pipelines (prompt + model + tools + guardrails), not just individual model outputs.

#### 9.4.5 Unity Catalog Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Catalog Browser** | 3-level hierarchy (catalog → schema → table) | DataHub metadata; `voyant.governance.schema` MCP tool | **PARTIAL** (DataHub client, no 3-level UI) | Agent-callable schema browsing via MCP |
| **Table Detail** | Schema, sample data, lineage, permissions | `voyant.tables.columns` + `voyant.lineage` + `voyant.governance.schema` | **PARTIAL** (APIs exist, no unified UI) | 3 MCP tools provide table + column + lineage data to agents |
| **Column Security** | Column-level access configuration | Apache Ranger column masking | **SRS** (GOV-F-004) | Dual-layer: Ranger (data) + SpiceDB (app) — defense-in-depth |
| **Row Security** | Row-level security rules | Apache Ranger RLS | **SRS** (GOV-F-003) | Zanzibar-style SpiceDB for app-level + Ranger for data-level |
| **Data Masking** | Mask sensitive columns | Apache Ranger masking policies | **SRS** (GOV-F-004) | Vault for secrets; Ranger for masking — no secrets in platform code |
| **Audit Log** | Track all data access | `AuditLog` model + SkyWalking tracing | **HAS** | Full distributed tracing via SkyWalking — more detailed than UC audit |

#### 9.4.6 Genie (NL BI) Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Chat Interface** | Natural language questions about data | Intent Engine backend + SRS: Chat UI | **PARTIAL** (backend, no chat UI) | Deterministic execution — validated plans, not raw LLM output |
| **NL → SQL** | LLM generates SQL from question | Intent Engine: NL → plan → validated SQL | **HAS** (Intent Engine) | Plan validation catches hallucinated table/column names before execution |
| **Result Visualization** | Auto-chart from query results | SRS: Auto-visualization | **SRS** | Intent Engine can generate visualization specs in the plan |
| **Feedback Loop** | Thumbs up/down on results | SRS: Feedback model | **SRS** | Agent evaluation feedback loop — systematic improvement |
| **Trust Configuration** | Which tables Genie can access | Ontology schema + SpiceDB permissions | **HAS** (RBAC) | Intent Engine validates against ontology — only generates plans for known types |

#### 9.4.7 Lakeflow Pipeline Screens

| Databricks Screen | What It Does | Voyant Equivalent | Status | Voyant Advantage |
|-------------------|-------------|-------------------|--------|-----------------|
| **Pipeline List** | Name, status, last update | Job model + Temporal UI | **HAS** (Temporal UI) | Temporal UI shows step-level detail, replay capability |
| **Pipeline Editor** | Visual DAG or code | SRS: React Flow DAG; Temporal workflows (code) | **PARTIAL** (code-first via Temporal) | Dual: visual builder (planned) + code-first (Temporal workflows) |
| **Quality Expectations** | Data quality rules | Great Expectations integration; `voyant.quality` MCP tool | **PARTIAL** | Agent-callable quality checks: `voyant.quality(source_id, table, checks)` |
| **Monitoring** | Freshness, quality, cost | Prometheus + Grafana; `voyant.status` MCP tool | **HAS** | Agent-callable monitoring: agents can check pipeline status via MCP |

---

### 9.5 User Journey Comparison — Palantir Foundry

#### Journey 1: Data Engineer Integrates New Source

| Step | Palantir Foundry | Voyant | Voyant Advantage |
|------|-----------------|--------|-----------------|
| 1. Navigate to Pipeline Builder | Open Pipeline Builder UI | Open Temporal UI OR call `voyant.connect` MCP tool | Agent can also do this via MCP |
| 2. Create new pipeline | Click "New Pipeline" | Create Temporal workflow OR use Airbyte UI | Code-first option with Temporal |
| 3. Add Source node | Drag Source node → configure connection | `voyant.connect(name, source_type, connection_config)` | Single MCP call; validated connection config |
| 4. Add Transform node | Write SQL transform | Spark/Trino SQL in workflow OR `voyant.sql` MCP tool | Agent can write and test transforms |
| 5. Add Output node | Set destination dataset | MinIO/Iceberg write in workflow | Open format (Iceberg) vs proprietary dataset |
| 6. Run pipeline | Click Run → monitor in Pipeline Builder | `voyant.ingest(source_id)` → Temporal auto-executes | Temporal: durable, replayable, self-healing |
| 7. Data in Ontology | Auto-detected by Foundry | Source detection via `voyant.discover`; auto-profile via `voyant.profile` | Agent can orchestrate the full pipeline |

**Voyant's advantage in this journey:** Steps 1-7 can all be executed by an AI agent via MCP tools. Palantir requires a human at every step. Additionally, Temporal provides durable execution — if any step fails, it resumes from the failed step.

#### Journey 2: Business Analyst Explores Data

| Step | Palantir Foundry | Voyant | Voyant Advantage |
|------|-----------------|--------|-----------------|
| 1. Open Ontology Manager | Browse types in table view | `voyant.ontology.types.list` (agent or admin UI) | Agent can also explore types |
| 2. Search for 'Customer' | Search bar with type-ahead | Full-text + semantic search (Milvus + Elasticsearch) | Dual search strategy — more resilient |
| 3. Click → Object Explorer | Object list with properties | `voyant.ontology.objects.list(type_id)` | Agent-callable object listing |
| 4. Apply filters | Visual filter builder (field → op → value) | ORM filters OR `voyant.ontology.objects.list` with query params | API-level filtering; visual builder in Phase 4 |
| 5. Pivot table | Pivot row/column configuration | SRS: Pivot component (Phase 4) | Will use ECharts pivot; agent-callable |
| 6. Export | CSV/JSON download | API export + MCP agent export | JSON-native; agents can process programmatically |
| 7. Create Workshop dashboard | Build dashboard with Workshop | SRS: Dashboard Builder (Phase 5) | Agent-created dashboards via MCP (planned) |

**Voyant's advantage in this journey:** Steps 1-6 can be performed by an AI agent via MCP tools. An agent can explore data, apply filters, and export results without human intervention. Palantir requires a human analyst at every step.

#### Journey 3: Data Scientist Builds ML Model

| Step | Palantir Foundry | Voyant | Voyant Advantage |
|------|-----------------|--------|-----------------|
| 1. Open Quiver notebook | Cell-based editor | SRS: Jupyter integration (Phase 6) | Agent-executable notebooks via MCP |
| 2. Load data from Ontology | `ontology.load("Customer")` | `voyant.sql` + `voyant.ontology.objects.list` | Agent can load data programmatically |
| 3. Explore with pandas/SQL | Interactive cells | `voyant.sql` for SQL; FunctionRunner for Python | Sandboxed execution with timeout + memory limits |
| 4. Train model | ML code in notebook | MLflow-compatible Experiment + Run models | Agent-managed training via MCP tools |
| 5. Log to MLflow | `mlflow.log_metric()` | `Run.metrics` + `RunArtifact` models | Self-hosted MLflow — no per-DBU cost |
| 6. Register model | Model Registry | `RegisteredModel` + `ModelVersion` | Agent-callable model registration |
| 7. Deploy to serving | Model Serving endpoint | `ModelEndpoint` model | Self-hosted serving; no vendor cost |
| 8. Create AIP agent | AIP Agent Builder | `AgentDefinition` model (prompt + model + tools + guardrails) | 67 MCP tools; per-agent guardrails |

**Voyant's advantage in this journey:** The entire ML workflow can be orchestrated by an AI agent. Steps 1-8 map to MCP tools. Databricks requires a data scientist with notebooks; Voyant lets agents manage the full ML lifecycle.

#### Journey 4: Operations Team Monitors System

| Step | Palantir Foundry | Voyant | Voyant Advantage |
|------|-----------------|--------|-----------------|
| 1. Open Pipeline Operations | Pipeline Operations dashboard | Temporal UI (port 45089) + Grafana (port 3000) | Temporal shows step-level workflow detail |
| 2. Check build history | Build history list | Temporal workflow history + `voyant.jobs.list` MCP tool | Agent-callable: agents can check history |
| 3. Review health alerts | Health monitoring | Prometheus alerts + Grafana dashboards | Industry-standard monitoring stack |
| 4. Check resource usage | Resource metrics | Prometheus + Grafana | Full observability with SkyWalking tracing |
| 5. Drill into failed pipeline | Log viewer | Temporal UI: click workflow → see failed step → see error | Step-level failure visibility + replay capability |
| 6. Fix and rerun | Edit pipeline → rerun | Fix code → deploy → Temporal auto-replays from failed step | Temporal replay: doesn't re-run completed steps |

**Voyant's advantage in this journey:** Temporal's replay capability means failed pipelines resume from the failed step, not from scratch. Operations team can also use `voyant.jobs.list` and `voyant.jobs.cancel` MCP tools for programmatic operations management.

---

### 9.6 User Journey Comparison — Databricks

#### Journey 1: Data Engineer Creates ETL Pipeline

| Step | Databricks | Voyant | Voyant Advantage |
|------|-----------|--------|-----------------|
| 1. Open Lakeflow | Lakeflow UI | Temporal UI + Airbyte UI | Code-first pipelines via Temporal workflows |
| 2. Create new pipeline | Click "New Pipeline" | Define workflow in Python OR use Airbyte connector | Python workflow: more flexible than visual-only |
| 3. Define source | Auto Loader or batch | `voyant.connect` + `voyant.ingest` MCP tools | Agent-callable: agents can set up sources |
| 4. Write transforms | SQL or Python transforms | Spark SQL / Trino SQL in Temporal activities | Agent-managed transforms via `voyant.sql` |
| 5. Add quality expectations | Lakeflow expectations | Great Expectations + `voyant.quality` MCP tool | Agent-callable quality checks |
| 6. Set schedule | Built-in scheduler | Temporal schedules (durable, exactly-once) | Durable scheduling — survives restarts |
| 7. Monitor | Pipeline health dashboard | Temporal UI + Prometheus + Grafana + `voyant.status` MCP | Agent-callable monitoring |

**Voyant's advantage:** Every step is agent-accessible via MCP. Databricks requires a human data engineer. Temporal provides durable execution with step-level replay.

#### Journey 2: Analyst Queries Data

| Step | Databricks | Voyant | Voyant Advantage |
|------|-----------|--------|-----------------|
| 1. Open SQL Editor | Monaco editor + autocomplete | `voyant.sql` MCP tool (agent) + SRS: Monaco editor (human) | Agent AND human can write SQL |
| 2. Browse schema | Unity Catalog tree (catalogs → schemas → tables) | `voyant.tables.list` + `voyant.tables.columns` MCP tools | Agent-callable schema discovery |
| 3. Write query | Manual SQL or Genie NL | Intent Engine (NL→plan→SQL) OR `voyant.sql` (manual) | Deterministic NL→SQL (validated before execution) |
| 4. Run query | Photon-accelerated execution | Trino SQL (medium), Spark SQL (large), DuckDB (small) | Query router: right engine for right query size |
| 5. Create visualization | Built-in chart from results | SRS: ECharts visualization (Phase 4) | ECharts: 20+ chart types, open source |
| 6. Add to dashboard | Dashboard builder | SRS: Dashboard Builder (Phase 5) | Agent-created dashboards |
| 7. Share dashboard | Databricks sharing | SpiceDB permissions + SRS: sharing UI | Zanzibar-style auth: more granular |

**Voyant's advantage:** Agents can query data (`voyant.sql`), browse schema (`voyant.tables.*`), and manage dashboards — all via MCP. Databricks SQL Editor is human-only. Intent Engine provides deterministic NL→SQL with plan validation.

#### Journey 3: Data Scientist Trains Model

| Step | Databricks | Voyant | Voyant Advantage |
|------|-----------|--------|-----------------|
| 1. Create notebook | Workspace → New Notebook | SRS: Jupyter integration | Agent-executable notebooks (planned) |
| 2. Load data | `spark.read.table("delta_table")` | `voyant.sql` MCP tool | Agent-callable data loading |
| 3. Feature engineering | Feature Store | SRS: Feature Store (Phase 5) | MCP tools for feature discovery (planned) |
| 4. Train with MLflow tracking | `mlflow.log_param()`, `mlflow.log_metric()` | Experiment + Run + RunArtifact models | Agent-managed training via MCP tools |
| 5. Compare runs | MLflow comparison UI | API comparison + SRS: React comparison UI | Agent-callable run comparison |
| 6. Register best model | Model Registry | RegisteredModel + ModelVersion | Staging pipeline: none→staging→production→archived |
| 7. Deploy to serving | Model Serving | ModelEndpoint model | Self-hosted serving; no per-DBU cost |
| 8. Monitor endpoint | Serving metrics | Prometheus + Grafana + ModelEndpoint.invocation_count | Built-in invocation tracking + latency metrics |

**Voyant's advantage:** Every ML step maps to an MCP tool or API. Databricks MLflow is human-UI-driven. Voyant's self-hosted model serving has zero per-DBU cost.

#### Journey 4: BI Analyst Builds Dashboard

| Step | Databricks | Voyant | Voyant Advantage |
|------|-----------|--------|-----------------|
| 1. Open Dashboard builder | Dashboard UI | SRS: Dashboard Builder (Phase 5) | Agent-created dashboards via MCP |
| 2. Add SQL widgets | Widget → SQL query → results | Widget → `voyant.sql` → results | Same SQL backend; agent-accessible |
| 3. Configure charts | Chart type + axes + styling | Apache ECharts (open source, 20+ types) | More chart types; open source |
| 4. Add filter widgets | Date range, dropdown | SRS: Filter components | Agent-set filters |
| 5. Arrange layout | Drag-drop grid | SRS: React grid layout | Hot-reload with Vite |
| 6. Auto-refresh | Scheduled refresh | WebSocket + Temporal scheduled refresh | Durable refresh scheduling |
| 7. Publish & share | Databricks sharing | SpiceDB RBAC + public URL | Zanzibar-style auth; embed without licensing |

---

## 10. Developer Experience Comparison

### 10.1 Access Modes

| Access Mode | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| **REST API** | OpenAPI 3.0 | OpenAPI 3.0 | **HAS** — 66 endpoints (Django Ninja, targeting 120+) |
| **MCP Protocol** | None | None | **HAS** — 67 tools (targeting 83+) |
| **Python SDK** | OSDK (Python) | Databricks SDK for Python | **SRS** — OSDK (API-F-003) |
| **TypeScript SDK** | OSDK (TypeScript) | Databricks SDK for JS | **SRS** — OSDK (API-F-003) |
| **CLI** | Foundry CLI | Databricks CLI | **SRS** — CLI (API-F-005) |
| **Webhooks** | Notifications | Job webhooks | **SRS** — Planned |
| **WebSocket** | Subscription Service | N/A | **SRS** — WebSocket API (API-F-004) |
| **Kafka Events** | Event-driven | Event-driven | **SRS** — Kafka integration (API-F-006) |

### 10.2 Developer Experience Advantages

| Advantage | Description |
|----------|-------------|
| **MCP Protocol** | Any AI coding assistant (Claude, Copilot, Cursor) can connect to Voyant via MCP and manage data, ontology, scraping, ML. Neither Palantir nor Databricks support this. |
| **Self-Hosted** | Full control: run on your laptop, your server, your air-gapped network. No vendor approval needed. |
| **Docker Compose** | `docker compose up` and you have a working platform. 20 containers. No cloud account, no sales call. |
| **Apache 2.0** | Read the code. Fork it. Extend it. No proprietary black boxes. |
| **2,203 Tests** | 2,203 test functions across 148 test files. Production-grade quality from day one. |
| **OpenAPI Auto-Generation** | Django Ninja auto-generates OpenAPI 3.1 specs. SDK generation is trivial. |
| **Temporal Workflows** | Every complex operation is a Temporal workflow: durable, replayable, visible in Temporal UI. Developers can debug workflows step-by-step. |

---

## 11. Specific Improvement Strategies

### 11.1 Areas Where Voyant Is Behind

| Area | Competitor | Gap | Strategy to Match | Strategy to Exceed |
|------|-----------|-----|-------------------|-------------------|
| **Photon Performance** | Databricks | 10–100x faster analytical queries | Deploy Spark cluster with Iceberg; tune Trino for small queries | Use DuckDB for embedded analytics (zero-setup, in-process); route small queries to DuckDB, large to Spark |
| **MLflow API Compatibility** | Databricks | ML platform has models but no API | Implement `/api/2.0/mlflow/*` endpoints matching MLflow's REST API | Add MCP tools for every ML operation (agents can manage experiments) |
| **AutoML** | Databricks | No AutoML engine | Phase 5: Basic AutoML using scikit-learn + Optuna for hyperparameter tuning | Intent Engine: "Find the best model for this data" → structured AutoML plan |
| **Feature Store** | Databricks | No centralized features | Phase 5: Simple feature store (computed features in Iceberg tables, cached in Redis) | MCP tools for feature discovery: agents can find and reuse features |
| **Notebooks** | Databricks + Palantir | No notebook environment | Phase 6: Jupyter integration (embed JupyterHub) | Agent-accessible: agents can create and execute notebook cells via MCP |
| **Data Lineage Depth** | Databricks | Column-level lineage, automated | Phase 5: Enhance DataHub integration with column-level lineage | Agent-callable: `voyant.lineage` MCP tool for programmatic lineage traversal |
| **Streaming** | Databricks | Structured Streaming (mature) | Phase 3: Complete Flink integration for streaming pipelines | Temporal workflows for streaming: durable, replayable streaming jobs |
| **Visual Builders** | Palantir | Workshop (mature low-code) | Phase 4: React visual builders for ontology, pipelines, scraping | Every visual action has a corresponding MCP tool (dual UI + agent access) |
| **Multi-Cloud** | Databricks | AWS + Azure + GCP | Phase 6: Terraform modules for each cloud | Self-hosted means ANY cloud, plus on-prem, plus air-gapped — more flexible |
| **Object Security** | Palantir | Per-object access policies | Phase 5: SpiceDB relationships per object type (e.g., `user:alice can_view object:order123`) | Agent-level security: which agents can access which objects, enforced at Intent Engine level |

### 11.2 Specific Technical Approaches

**Photon Performance Gap → Solution:**
```
Current:  Trino → PostgreSQL/MinIO (slow for analytical queries)
Phase 2:  Trino → Iceberg on MinIO (better, still slow for complex aggregations)
Phase 3:  Spark SQL → Iceberg on MinIO (fast, distributed)
Phase 5:  DuckDB for embedded queries <10K rows (<1ms latency, zero setup)
Final:    Query Router: small queries → DuckDB, medium → Trino, large → Spark
```

**MLflow API Compatibility → Solution:**
```python
# Target API endpoints to implement:
POST /api/2.0/mlflow/experiments/create
POST /api/2.0/mlflow/experiments/get
POST /api/2.0/mlflow/runs/create
POST /api/2.0/mlflow/runs/log-metric
POST /api/2.0/mlflow/runs/log-parameter
POST /api/2.0/mlflow/registered-models/create
POST /api/2.0/mlflow/model-versions/create
POST /api/2.0/mlflow/model-versions/transition-stage
POST /api/2.0/mlflow/endpoints/create  # Custom extension
```

**Data Lineage Gap → Solution:**
```
Phase 1: DataHub client (current — entity-level lineage)
Phase 3: Enhance with column-level lineage tracking
Phase 5: Auto-lineage: Airbyte ingestion → automatic DataHub lineage entries
Phase 5: MCP lineage tool: `voyant.lineage(urn, direction, depth)` — already built!
Final:   Intent Engine: "What upstream data affects Q4 revenue?" → lineage traversal plan
```

---

## 12. Benchmark Metrics to Track

### 12.1 Performance Metrics

| Metric | Databricks Target | Palantir Target | Voyant v4.0 Target |
|--------|------------------|----------------|-------------------|
| Simple query latency (p95) | <50ms (Photon) | <100ms | <200ms (Trino), <5ms (DuckDB) |
| Complex aggregation (p95) | <2s | <5s | <5s (Spark SQL) |
| Object CRUD latency (p95) | N/A (no ontology) | <50ms | <50ms (PostgreSQL) |
| Object traversal (3-hop, p95) | N/A | <200ms | <200ms |
| API endpoint latency (p95) | <200ms | <200ms | <200ms |
| MCP tool latency (p95) | N/A | N/A | <500ms |
| Concurrent users | 10,000+ | 5,000+ | 10,000+ (target) |
| Objects per type | 10M+ | 1M+ | 1M+ (target) |
| Pipeline throughput | 1TB/hour | 500GB/hour | 100GB/hour (target) |

### 12.2 Feature Completeness Metrics

| Domain | Current (v3.0) | Target (v4.0 GA) | Palantir Parity | Databricks Parity |
|--------|---------------|------------------|-----------------|-------------------|
| Ontology Engine (M3 Voyant Catalog) | 56% | 90% | 85% | N/A |
| Data Intelligence | 65% | 85% | 70% | 60% |
| ML/AI Platform | 0% | 70% | 60% | 50% |
| Governance | 43% | 80% | 70% | 65% |
| UI/UX | 15% | 60% | 50% | 45% |
| Scraper | 46% | 85% | N/A | N/A |
| API/SDK | 42% | 80% | 70% | 60% |
| **Overall** | **37%** | **78%** | **68%** | **46%** |

### 12.3 Unique Differentiator Metrics (Voyant Only)

| Metric | v3.0 | v4.0 Target | Why It Matters |
|--------|------|-------------|---------------|
| MCP Tools | 46 | 83+ | More tools = more agent capability |
| Temporal Workflows | 17 | 25+ | More durable operations |
| Browser Arms | 8 | 8+ | Web scraping breadth |
| Deep Research Workflows | 1 | 3+ | Research capability depth |
| Capsule Types | 5 | 15+ | Plugin ecosystem breadth |
| Intent Engine Accuracy | N/A | >95% | NL→plan translation quality |
| Agent Evaluation Score | N/A | >0.85 | Agent quality benchmark |
| Docker Container Count | 20 | 30 | Still lightweight |
| Test Functions | 2,203 | 3,500+ | Quality assurance |

### 12.4 Key Competitive Positioning Targets

| Positioning Statement | Target Metric | Timeline |
|----------------------|---------------|----------|
| "Self-hosted Palantir" | Ontology parity 85% | v4.0 GA |
| "Agent-native Databricks" | MCP tools 83+, MLflow API compatible | v4.0 GA |
| "Deterministic AI platform" | Intent Engine >95% accuracy | v4.0 GA |
| "Open-source data intelligence" | Apache 2.0, all layers | Already done |
| "AI agents can manage your data" | 14 ontology MCP tools + 7 scraper MCP tools | v4.0 Phase 1 |
| "The platform AI agents actually use" | 83+ MCP tools covering all domains | v4.0 GA |

---

## Appendix A: Sources

| Source | Type | Date Accessed |
|--------|------|--------------|
| `docs/specifications/v4.0/PALANTIR_FEATURE_MAP.md` | Internal | 2026-09-05 |
| `docs/specifications/v4.0/VOYANT_SRS_V4.md` | Internal | 2026-09-05 |
| `docs/specifications/v4.0/VOYANT_SAD_V4.md` | Internal | 2026-09-05 |
| `docs/specifications/v4.0/VOYANT_SCRAPER_SRS_V4.md` | Internal | 2026-09-05 |
| `apps/ontology/models.py` (754 LOC) | Code | 2026-09-05 |
| `apps/ontology/action_executor.py` (826 LOC) | Code | 2026-09-05 |
| `apps/ontology/function_runner.py` (665 LOC) | Code | 2026-09-05 |
| `apps/ml_platform/models.py` (249 LOC) | Code | 2026-09-05 |
| `apps/mcp/tools_core.py` (200 LOC) | Code | 2026-09-05 |
| `apps/mcp/tools_catalog.py` (408 LOC) | Code | 2026-09-05 |
| `apps/mcp/tools_ontology.py` (386 LOC) | Code | 2026-09-05 |
| Databricks Product Pages (unity-catalog, platform, ai, genie) | Web | 2026-09-05 |
| MLflow Documentation (mlflow.org) | Web | 2026-09-05 |
| Palantir Foundry/AIP pages (palantir.com) | Web | 2026-09-05 |

## Appendix B: Abbreviations

| Abbreviation | Full Form |
|-------------|-----------|
| AIP | Artificial Intelligence Platform (Palantir) |
| DLT | Declarative Pipelines (Databricks Lakeflow) |
| MCP | Model Context Protocol |
| OSS | Object Set Service (Palantir) |
| OSDK | Ontology SDK (Palantir) |
| RLS | Row-Level Security |
| UC | Unity Catalog (Databricks) |

---

**Created:** 2026-09-05
**Author:** Voyant Engineering
**Review cycle:** Monthly
**Next review:** 2026-10-05

---

## Part 3: User Journeys

# Voyant v4.0 — Complete User Journey Map

**Document ID:** VOYANT-UJ-4.0.0
**Version:** 4.0.0-draft
**Date:** 2026-09-05
**Purpose:** Every user journey in Palantir Foundry, Databricks, and how Voyant matches + improves each one
**Status:** Draft for Review

---

## How to Read This Document

Each journey follows this structure:

| Section | Description |
|---------|-------------|
| **Palantir** | Step-by-step in Foundry (screen names, clicks) |
| **Databricks** | Step-by-step in Databricks (screen names, clicks) |
| **Voyant v4.0** | Step-by-step in Voyant (screen names, API calls, MCP tools) |
| **Voyant Improvements** | Where Voyant wins: agent access, MCP, self-hosted, NL |
| **Comparison Table** | Side-by-side feature matrix |

---

## Legend

| Symbol | Meaning |
|--------|---------|
| `→` | Navigate to |
| `[API]` | REST API endpoint |
| `[MCP]` | MCP tool call |
| `[SCREEN]` | UI screen name |
| `[WF]` | Temporal workflow |
| `[AGENT]` | AI agent action |

---

# PART A: DATA ENGINEER JOURNEYS

---

## Journey 1: Register New Data Source (PostgreSQL, S3, API)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Foundry Home** | Click "Connect Data" in left sidebar |
| 2 | **Data Connection Wizard** | Select source type (Database / Cloud Storage / API) |
| 3 | **Connection Config** | Enter: host, port, database, credentials (stored in Foundry Secrets) |
| 4 | **Schema Discovery** | Foundry auto-discovers tables, columns, types |
| 5 | **Preview** | Review discovered schema; select tables to import |
| 6 | **Schedule** | Configure sync frequency (manual / hourly / daily) |
| 7 | **Dataset Created** | Foundry creates backed-up dataset in Foundry Storage |
| 8 | **Pipeline Sync** | Sync pipeline runs via Pipeline Builder |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Explorer** | Click "Create" → "External Data" → "Connection" |
| 2 | **Unity Catalog UI** | Select connector (JDBC / S3 / ADLS / GCS) |
| 3 | **Connection Form** | Enter: host, port, database, auth (Databricks Secrets) |
| 4 | **External Location** | Create external location pointing to S3/ADLS |
| 5 | **External Table** | `CREATE TABLE catalog.schema.table USING ...` or UI form |
| 6 | **Credential Storage** | Credentials stored in Databricks Secrets (backed by Key Vault) |
| 7 | **Unity Catalog** | Table registered in Unity Catalog with ownership + tags |
| 8 | **Auto Loader** (optional) | Configure Auto Loader for incremental ingestion from cloud |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Sources** (`view-sources.ts`) | Click "Add Data Source" button |
| 2 | `[SCREEN]` **Source Type Selector** | Select: PostgreSQL / MySQL / S3 / API / File |
| 3 | `[SCREEN]` **Connection Form** | Enter: name, host, port, database, credentials |
| 4 | `[API]` `POST /ingestion/sources` | Validate connection (triggers Airbyte check) |
| 5 | `[API]` `POST /ingestion/sources/{id}/discover` | Schema discovery via Airbyte connector |
| 6 | `[SCREEN]` **Schema Preview** | Review tables, columns, types; select tables to sync |
| 7 | `[API]` `POST /ingestion/sources/{id}/sync` | Trigger first sync |
| 8 | `[WF]` `DataSyncWorkflow` (Temporal) | Orchestrates: Airbyte pull → Kafka → Flink → Iceberg |
| 9 | `[API]` `GET /ingestion/sources/{id}/status` | Monitor sync progress |
| 10 | `[SCREEN]` **Sources** | Source appears with status "Active", last sync time |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_discovery__register_source → register source
[MCP] mcp__voyant_discovery__discover_schema → discover tables
[MCP] mcp__voyant_discovery__profile_table → profile columns
[MCP] mcp__voyant_discovery__run_profiling → run full profile
```

#### ASCII Wireframe: Sources Screen

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Sources                                    [User ▾]   │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─────────────────────────────────────────────────┐   │
│ Dashboard│ │  Data Sources                     [+ Add Source]│   │
│ Ontology │ ├─────────────────────────────────────────────────┤   │
│ SQL      │ │                                                 │   │
│ Sources  │ │  ┌──────────┐  ┌──────────┐  ┌──────────┐      │   │
│ Scraper  │ │  │PostgreSQL│  │   S3     │  │  API     │      │   │
│ ML       │ │  │ ⚡ Active │  │ ⚡ Active │  │ ⏸ Paused │      │   │
│ Search   │ │  │ Last: 2m │  │ Last: 1h │  │ Last: 3d │      │   │
│ Govern   │ │  │ 12 tables│  │ 4 buckets│  │ 1 endpoint│     │   │
│ Audit    │ │  └──────────┘  └──────────┘  └──────────┘      │   │
│ Capsules │ │                                                 │   │
│          │ │  Sync History ──────────────────────────────    │   │
│          │ │  │ 14:32 │ postgres-prod │ ✅ 12 tables │ 2.3s │   │
│          │ │  │ 14:01 │ s3-warehouse  │ ✅ 4 buckets │ 8.1s │   │
│          │ │  │ 13:45 │ api-orders    │ ⚠️  1 timeout │      │   │
│          │ └─────────────────────────────────────────────────┘   │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| PostgreSQL | ✅ Native | ✅ JDBC | ✅ Airbyte |
| S3/ADLS/GCS | ✅ Native | ✅ Native (Unity) | ✅ Airbyte |
| REST API | ✅ External Dataset | ⚠️ Manual | ✅ Built-in |
| Auto-discovery | ✅ | ✅ | ✅ |
| Secrets Management | ✅ Foundry Secrets | ✅ Databricks Secrets | ✅ HashiCorp Vault |
| Scheduling | ✅ Pipeline Builder | ✅ Jobs/Workflows | ✅ Temporal |
| Incremental Sync | ✅ | ✅ Auto Loader | ✅ Airbyte CDC |
| **Agent-triggered** | ❌ | ❌ | ✅ MCP tools |
| **Self-hosted** | ❌ | ❌ | ✅ Docker |

---

## Journey 2: Create ETL Pipeline (Source → Transform → Validate → Output)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Pipeline Builder** | Click "New Pipeline" → Select type (Batch / Streaming / Incremental) |
| 2 | **DAG Editor** | Drag source dataset onto canvas |
| 3 | **Transform Node** | Add transform: Python, SQL, or visual transform |
| 4 | **Code Editor** | Write transform logic (pandas/PySpark or SQL) |
| 5 | **Quality Node** | Add data expectations (schema checks, null %, range) |
| 6 | **Output Node** | Connect to output dataset |
| 7 | **Schedule** | Set schedule (cron, event-driven, or dependency) |
| 8 | **Run** | Execute pipeline; view DAG execution in real-time |
| 9 | **Monitor** | Pipeline Health dashboard shows success/failure per node |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Workflows** | Click "Create Job" → Add task |
| 2 | **Task Config** | Select type: Notebook / Python / SQL / JAR |
| 3 | **Notebook Editor** | Write transformation in PySpark/SQL notebook |
| 4 | **DLT Pipeline** (alternative) | Create Delta Live Tables pipeline with expectations |
| 5 | **Quality Rules** | Add `@dlt.expect_all()` decorators |
| 6 | **Output** | Write to Delta table in Unity Catalog |
| 7 | **Schedule** | Configure trigger (cron / file arrival / table update) |
| 8 | **Run** | Execute; monitor in "Runs" tab |
| 9 | **Lakeflow Monitor** | View lineage graph, error logs, data quality metrics |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Pipeline Builder** (new React Flow canvas) | Click "New Pipeline" |
| 2 | `[SCREEN]` **DAG Editor** | Drag nodes: Source → Transform → Validate → Output |
| 3 | `[SCREEN]` **Source Node Config** | Select registered data source + tables |
| 4 | `[SCREEN]` **Transform Node** | Choose: Python / SQL / LLM Transform |
| 5 | `[SCREEN]` **Code Editor** (Monaco) | Write transform: `def transform(df): return df[df.amount > 0]` |
| 6 | `[SCREEN]` **Quality Node** | Define expectations: null < 5%, unique keys, range checks |
| 7 | `[SCREEN]` **Output Node** | Select target: Iceberg table / Ontology Object Type / S3 |
| 8 | `[API]` `POST /pipelines` | Save pipeline definition |
| 9 | `[API]` `POST /pipelines/{id}/run` | Execute pipeline |
| 10 | `[WF]` `ETLPipelineWorkflow` (Temporal) | Executes DAG: source pull → transform → validate → write |
| 11 | `[SCREEN]` **Pipeline Monitor** | Real-time DAG view with node status, timings, errors |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_dataintel__create_pipeline → define pipeline
[MCP] mcp__voyant_dataintel__run_pipeline → execute
[MCP] mcp__voyant_dataintel__pipeline_status → check progress
[MCP] mcp__voyant_dataintel__validate_quality → run quality checks
```

#### ASCII Wireframe: Pipeline Builder

```
┌──────────────────────────────────────────────────────────────────┐
│ Pipeline Builder: "Customer ETL"                    [Run] [Save] │
├──────────────────────────────────────────────────────────────────┤
│ ┌────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐  │
│ │Postgres│───→│ Transform│───→│ Validate │───→│ Iceberg Table│  │
│ │Source  │    │ Python   │    │ Quality  │    │ customers    │  │
│ │        │    │          │    │ Checks   │    │              │  │
│ │customers│   │ df=filter│    │ null<5%  │    │ ✅ Ready     │  │
│ │ 12,345 │    │ (amount>0)│   │ unique pk│    │              │  │
│ └────────┘    └──────────┘    └──────────┘    └──────────────┘  │
│                                                                   │
│ ┌─ Node Details ─────────────────────────────────────────────┐   │
│ │ Transform: Python                                          │   │
│ │ ┌──────────────────────────────────────────────────────┐   │   │
│ │ │ def transform(df):                                    │   │   │
│ │ │     df = df[df['amount'] > 0]                         │   │   │
│ │ │     df['total'] = df['amount'] * df['quantity']       │   │   │
│ │ │     return df                                          │   │   │
│ │ └──────────────────────────────────────────────────────┘   │   │
│ │ Last run: 2026-09-05 14:32  │  Rows: 11,892  │  Time: 4.2s│   │
│ └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Visual DAG | ✅ Pipeline Builder | ✅ Lakeflow (DLT) | ✅ React Flow |
| Python Transform | ✅ pandas/PySpark | ✅ PySpark | ✅ pandas/PySpark |
| SQL Transform | ✅ | ✅ | ✅ Trino/Spark SQL |
| **LLM Transform** | ❌ | ❌ | ✅ in-pipeline LLM |
| Quality Checks | ✅ Data Expectations | ✅ DLT Expectations | ✅ Great Expectations |
| Streaming | ✅ Flink | ✅ Structured Streaming | ✅ Flink (stub→full) |
| Incremental | ✅ | ✅ Auto Loader | ✅ Airbyte CDC |
| **Agent-built pipeline** | ❌ | ❌ | ✅ MCP tools |
| Subgraphs | ✅ | ❌ | ✅ (planned) |
| Time Travel | ✅ | ✅ Delta | ✅ Iceberg snapshots |

---

## Journey 3: Monitor Pipeline Health and Fix Failures

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Pipeline Health** | View list of all pipelines with status indicators |
| 2 | **Pipeline Detail** | Click failing pipeline → see DAG with red nodes |
| 3 | **Node Log** | Click failed node → view error log, input/output samples |
| 4 | **Edit Transform** | Fix code in code editor |
| 5 | **Re-run** | Re-run from failed node (incremental re-run) |
| 6 | **Alert** | Configure alert rules (failure, latency, data quality) |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Workflows** | View job list with status badges |
| 2 | **Run Detail** | Click failed run → see task graph |
| 3 | **Task Log** | Click failed task → view Spark UI, driver logs, error trace |
| 4 | **Fix Notebook** | Edit notebook, fix transform |
| 5 | **Re-run** | Re-run failed task or full job |
| 6 | **Alerts** | Configure email/webhook alerts on failure |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Pipeline Monitor** | Dashboard shows all pipelines with status badges |
| 2 | `[SCREEN]` **Pipeline Detail** | Click pipeline → DAG view with per-node status |
| 3 | `[SCREEN]` **Node Log Panel** | Click failed node → error log, data samples, timing |
| 4 | `[API]` `GET /pipelines/{id}/runs/{run_id}` | Get run details with per-node metrics |
| 5 | `[SCREEN]` **Code Editor** | Fix transform code inline |
| 6 | `[API]` `POST /pipelines/{id}/runs/{run_id}/retry` | Re-run from failed node |
| 7 | `[WF]` Temporal retry with backoff | Automatic retry with configurable policy |
| 8 | `[SCREEN]` **Alerts Config** | Set alerts: failure, latency > X, quality < Y% |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_dataintel__pipeline_status → check health
[MCP] mcp__voyant_dataintel__pipeline_logs → get failure logs
[MCP] mcp__voyant_dataintel__retry_pipeline → auto-retry
[AGENT] Agent auto-detects failure → retries → escalates if 3 fails
```

#### Voyant Improvement: Self-Healing Pipelines

```
Pipeline fails
    │
    ▼
Agent detects via workflow signal
    │
    ├── Retry #1 (exponential backoff)
    │   ├── Success → log, continue
    │   └── Fail →
    ├── Retry #2 (fix known issues)
    │   ├── Success → log, continue
    │   └── Fail →
    └── Escalate → notify human + create incident
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Visual Status | ✅ | ✅ | ✅ DAG view |
| Error Logs | ✅ | ✅ Spark UI | ✅ Node logs |
| Incremental Re-run | ✅ | ✅ | ✅ |
| Auto-retry | ⚠️ Basic | ⚠️ Basic | ✅ Temporal policies |
| **Self-healing agent** | ❌ | ❌ | ✅ Agent auto-fix |
| Alert Rules | ✅ | ✅ | ✅ |
| Data Quality Metrics | ✅ | ✅ | ✅ |

---

## Journey 4: Set Up Data Quality Rules

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Health** | Navigate to Data Health dashboard |
| 2 | **Expectations** | Click "Add Expectation" on dataset |
| 3 | **Rule Builder** | Select rule type: Schema / Null % / Range / Uniqueness / Custom |
| 4 | **Configuration** | Set threshold (e.g., null < 5%, unique column) |
| 5 | **Save** | Attach to pipeline; runs on every sync |
| 6 | **Monitor** | Dashboard shows pass/fail rates over time |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **DLT Pipeline** | Open Delta Live Tables pipeline |
| 2 | **Quality Tab** | View existing expectations |
| 3 | **Add Expectation** | `@dlt.expect("valid_email", "email RLIKE '%@%'")` |
| 4 | **Configure** | Choose: warn / drop / fail on violation |
| 5 | **Save** | Pipeline applies on next run |
| 6 | **Monitor** | Quality metrics in pipeline dashboard |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Data Quality** (new view) | Navigate from sidebar → Data Quality |
| 2 | `[API]` `GET /data/quality/rules` | List all quality rules |
| 3 | `[SCREEN]` **Rule Builder** | Select table → Add rule |
| 4 | `[SCREEN]` **Rule Config** | Type: null_check / range / regex / uniqueness / custom_sql |
| 5 | `[API]` `POST /data/quality/rules` | Save rule definition |
| 6 | `[API]` `POST /data/quality/rules/{id}/run` | Execute quality check |
| 7 | `[SCREEN]` **Quality Dashboard** | View pass/fail rates, trend charts |
| 8 | `[WF]` Quality check runs in pipeline | Integrated with ETL pipeline |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_dataintel__create_quality_rule → define rule
[MCP] mcp__voyant_dataintel__run_quality_check → execute check
[MCP] mcp__voyant_dataintel__quality_report → get results
[AGENT] "Add a quality rule: orders.amount must be > 0"
```

#### ASCII Wireframe: Data Quality Dashboard

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Data Quality                              [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Quality Overview ────────────────────────────────┐ │
│          │ │  Overall Score: 94.2%  │  Rules: 23  │  Failed: 2 │ │
│          │ └───────────────────────────────────────────────────┘ │
│          │ ┌─ Rules ───────────────────────────────────────────┐ │
│          │ │ Table       │ Rule          │ Status  │ Last Run   │ │
│          │ │ orders      │ null<2%       │ ✅ 0.1% │ 2m ago     │ │
│          │ │ orders      │ amount>0      │ ❌ 3.2% │ 2m ago     │ │
│          │ │ customers   │ unique email  │ ✅ 0.0% │ 1h ago     │ │
│          │ │ products    │ price range   │ ✅ Pass │ 1h ago     │ │
│          │ └──────────────────────────────────────────────────┘ │
│          │ [+ Add Rule]                                          │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Rule Types | ✅ Schema/Null/Range | ✅ DLT Expectations | ✅ Great Expectations |
| Custom Rules | ✅ Python | ✅ SQL expression | ✅ SQL + Python |
| Auto-fix | ❌ | ❌ Drop mode | ⚠️ (planned) |
| Trend Dashboard | ✅ | ✅ | ✅ |
| **Agent-defined rules** | ❌ | ❌ | ✅ NL → rule |
| In-pipeline | ✅ | ✅ Native | ✅ Temporal |

---

## Journey 5: Configure Data Lineage Tracking

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Lineage Graph** | Navigate to dataset → "Lineage" tab |
| 2 | **Auto-detect** | Foundry auto-tracks: source → pipeline → output |
| 3 | **Visual Graph** | Upstream/downstream graph with dataset nodes |
| 4 | **Impact Analysis** | Click "Impact" to see all downstream consumers |
| 5 | **Column Lineage** | Drill into column-level lineage (which source columns map to output) |
| 6 | **Metadata** | Attach tags, descriptions, owners to lineage nodes |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Lineage Explorer** | Navigate: Data Explorer → table → "Lineage" tab |
| 2 | **Unity Catalog** | Auto-captures lineage from Spark SQL |
| 3 | **Visual Graph** | Upstream/downstream graph |
| 4 | **Column Lineage** | Column-level lineage (Unity Catalog Premium) |
| 5 | **Table Explorer** | Search across all tables with lineage |
| 6 | **Tags** | Apply tags for classification, owner, PII |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Lineage View** (new) | Navigate from sidebar → Lineage |
| 2 | `[API]` `GET /data/lineage/{dataset}` | Fetch lineage graph |
| 3 | `[SCREEN]` **Lineage Graph** | Force-directed graph showing upstream/downstream |
| 4 | `[API]` `POST /data/lineage/track` | Register lineage edge (source → transform → output) |
| 5 | `[WF]` Auto-track in pipeline | Every ETL pipeline auto-registers lineage |
| 6 | `[SCREEN]` **Impact Analysis** | Click node → see all downstream consumers |
| 7 | `[SCREEN]` **Column Lineage** | Drill into column-level mappings |
| 8 | Integration | DataHub + Apache Atlas feed lineage metadata |

#### ASCII Wireframe: Lineage Graph

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Data Lineage                             [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Lineage: customers_clean ─────────────────────────┐│
│          │ │                                                    ││
│          │ │  [postgres]    [ETL]     [validate]   [iceberg]    ││
│          │ │  ┌────────┐  ┌──────┐  ┌──────────┐ ┌──────────┐ ││
│          │ │  │ raw    │─→│clean │─→│ quality  │─→│customers │ ││
│          │ │  │custs   │  │      │  │ check    │  │_clean    │ ││
│          │ │  │12,345  │  │filter│  │          │  │          │ ││
│          │ │  └────────┘  └──────┘  └──────────┘ └──────────┘ ││
│          │ │                          └──────────┐              ││
│          │ │                          │ Downstream│              ││
│          │ │                          │ Dashboard │              ││
│          │ │                          │ Report    │              ││
│          │ │                          └──────────┘              ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Auto-tracking | ✅ | ✅ Unity Catalog | ✅ Pipeline + Atlas |
| Visual Graph | ✅ | ✅ | ✅ D3/Sigma.js |
| Column Lineage | ✅ | ✅ Premium | ✅ |
| Impact Analysis | ✅ | ✅ | ✅ |
| Metadata Tags | ✅ | ✅ Tags | ✅ Atlas |
| **Agent-explored** | ❌ | ❌ | ✅ MCP traversal |

---

# PART B: BUSINESS ANALYST JOURNEYS

---

## Journey 6: Explore Ontology (Browse Types, Objects, Relationships)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Object Explorer** | Click "Objects" in sidebar |
| 2 | **Type Browser** | Browse all Object Types with counts |
| 3 | **Object List** | Click type → see all objects with properties |
| 4 | **Search/Filter** | Search by property value; filter by conditions |
| 5 | **Object Detail** | Click object → full view with linked objects |
| 6 | **Graph View** | Click "Graph" → see object relationships visually |
| 7 | **Pivot** | Pivot table view: group by property, aggregate |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Explorer** | Click "Data Explorer" in sidebar |
| 2 | **Catalog Browser** | Browse catalogs → schemas → tables |
| 3 | **Table Detail** | Click table → columns, sample data, lineage |
| 4 | **SQL Query** | Open SQL Editor to query tables |
| 5 | **No native ontology** | Databricks has no ontology concept — tables only |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Ontology Explorer** (`view-ontology.ts`) | Click "Ontology" in sidebar |
| 2 | `[SCREEN]` **Type Browser** | Browse Object Types with property count + instance count |
| 3 | `[API]` `GET /ontology/object-types` | Fetch all types |
| 4 | `[SCREEN]` **Object List** | Click type → see all instances in sortable table |
| 5 | `[API]` `GET /ontology/object-types/{id}/objects` | Fetch instances with pagination |
| 6 | `[SCREEN]` **Filter Builder** | Add property filters |
| 7 | `[SCREEN]` **Object Detail Panel** | Click object → full detail with linked objects |
| 8 | `[SCREEN]` **Graph View** | Force-directed graph of object relationships |
| 9 | `[API]` `GET /ontology/objects/{id}/traverse` | Multi-hop traversal (up to 10 hops) |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ontology__list_object_types → browse types
[MCP] mcp__voyant_ontology__search_objects → NL search
[MCP] mcp__voyant_ontology__traverse_links → multi-hop traversal
[MCP] mcp__voyant_ontology__get_object → detail view
```

#### ASCII Wireframe: Ontology Explorer

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Ontology Explorer                         [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Object Types ──── [Table] [Graph] [Grid] ────────┐│
│          │ │                                                    ││
│          │ │  Type          │ Props │ Instances │ Links          ││
│          │ │  Customer      │  12   │  12,345   │ →Orders        ││
│          │ │  Order         │  8    │  45,678   │ →Products      ││
│          │ │  Product       │  15   │  3,456    │ →Categories    ││
│          │ │  Category      │  4    │  89       │ ←Products      ││
│          │ │  Supplier      │  6    │  234      │ →Products      ││
│          │ │                                                    ││
│          │ │  ┌─ Customer #C-4521 ────────────────────────────┐ ││
│          │ │  │ name: "Acme Corp"                             │ ││
│          │ │  │ email: "info@acme.com"                        │ ││
│          │ │  │ segment: "Enterprise"                         │ ││
│          │ │  │ created: 2024-03-15                           │ ││
│          │ │  │                                               │ ││
│          │ │  │ Linked Objects:                               │ ││
│          │ │  │  ├→ Order #1001 (2026-08-01) $12,500         │ ││
│          │ │  │  ├→ Order #1098 (2026-09-02) $8,300          │ ││
│          │ │  │  └→ Support Ticket #ST-45 (Open)             │ ││
│          │ │  └───────────────────────────────────────────────┘ ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Type Browser | ✅ Object Explorer | ⚠️ Data Explorer (tables) | ✅ Ontology Explorer |
| Object List | ✅ | ⚠️ Table rows | ✅ |
| Relationship Graph | ✅ Vertex | ❌ | ✅ Sigma.js |
| Multi-hop Traversal | ✅ | ❌ | ✅ 10-hop |
| Search/Filter | ✅ Full-text + faceted | ⚠️ SQL only | ✅ Full-text + semantic |
| Pivot | ✅ | ❌ | ✅ (planned) |
| **Agent browsing** | ❌ | ❌ | ✅ MCP tools |
| **NL search** | ❌ | ❌ | ✅ Intent Engine |

---

## Journey 7: Query Data with SQL (Interactive Editor)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **SQL Studio** | Click "SQL" in sidebar |
| 2 | **Editor** | Monaco editor with autocomplete |
| 3 | **Schema Browser** | Browse datasets, columns, types in sidebar |
| 4 | **Run Query** | Execute SQL → results table |
| 5 | **Save as Dataset** | Save result as new backed-up dataset |
| 6 | **Export** | Download as CSV |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **SQL Editor** | Click "SQL Editor" in sidebar |
| 2 | **Editor** | Monaco editor with autocomplete (Unity Catalog aware) |
| 3 | **Catalog Browser** | Browse catalogs, schemas, tables |
| 4 | **Run Query** | Execute on Spark SQL / Photon → results |
| 5 | **Save as View** | Save as view or table |
| 6 | **Visualize** | Built-in chart from results |
| 7 | **Dashboard** | Pin query result to dashboard |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **SQL Studio** (`view-sql.ts`) | Click "SQL" in sidebar |
| 2 | `[SCREEN]` **Monaco Editor** | Write SQL with autocomplete (schema-aware) |
| 3 | `[SCREEN]` **Table Browser** | Left panel: tables, columns, types |
| 4 | `[API]` `POST /sql/query` | Execute SQL (Trino/Spark backend) |
| 5 | `[SCREEN]` **Results Table** | Sortable, paginated results |
| 6 | `[SCREEN]` **Query History** | Last 20 queries with timing |
| 7 | `[API]` `POST /sql/query` (export) | Export as CSV/JSON |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_sql__execute_query → run SQL
[MCP] mcp__voyant_sql__list_tables → browse schema
[MCP] mcp__voyant_sql__describe_table → inspect columns
[AGENT] "Run a query to find all orders over $1000"
```

#### ASCII Wireframe: SQL Studio

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  SQL Studio                                [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│ Tables   │ ┌─ Monaco Editor ───────────────────────────────────┐ │
│  ├ orders│ │ SELECT o.id, c.name, SUM(o.amount) as total       │ │
│  │ ├ id  │ │ FROM orders o                                      │ │
│  │ ├ amt │ │ JOIN customers c ON o.customer_id = c.id           │ │
│  │ └ ... │ │ WHERE o.amount > 1000                              │ │
│  ├ custs │ │ GROUP BY o.id, c.name                              │ │
│  │ ├ id  │ │ ORDER BY total DESC;                               │ │
│  │ ├ name│ └────────────────────────────────────────────────────┘ │
│  │ └ ... │                                            [▶ Run]    │
│  └ prods │ ┌─ Results ─────────────────────────────────────────┐ │
│          │ │ id    │ name       │ total                         │ │
│          │ │ 1001  │ Acme Corp  │ $45,200                       │ │
│          │ │ 1098  │ Globex     │ $32,100                       │ │
│          │ │ 1045  │ Initech    │ $28,750                       │ │
│          │ │ ...   │ ...        │ ...                           │ │
│          │ │ 12 rows │ 0.34s                            [CSV] [JSON]│
│          │ └────────────────────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| SQL Editor | ✅ Monaco | ✅ Monaco | ✅ Monaco |
| Autocomplete | ✅ Dataset-aware | ✅ Catalog-aware | ✅ Schema-aware |
| Multi-engine | ✅ Foundry SQL | ✅ Photon/Spark | ✅ Trino + Spark |
| Save Results | ✅ As dataset | ✅ As view/table | ✅ As Iceberg table |
| Export | ✅ CSV | ✅ CSV/JSON | ✅ CSV/JSON |
| **Agent SQL** | ❌ | ❌ | ✅ MCP `execute_query` |
| **NL → SQL** | ❌ | ⚠️ Genie | ✅ Intent Engine |

---

## Journey 8: Search Data Semantically (NL Question → Results)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Search Bar** | Type natural language in global search bar |
| 2 | **Results** | Returns matching objects, datasets, pipelines |
| 3 | **Filter** | Filter by type, date, owner |
| 4 | **No NL-to-SQL** | Foundry does not convert NL to queries — search only |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Genie** | Open Genie (Natural Language BI) |
| 2 | **Ask Question** | Type: "What were total sales in June?" |
| 3 | **Genie generates SQL** | AI generates SQL query |
| 4 | **Review & Run** | User reviews SQL, approves, runs |
| 5 | **Chart** | Genie returns table + auto-chart |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Search** (`view-search.ts`) | Type NL question in search bar |
| 2 | `[SCREEN]` **Semantic Search** | Full-text + vector search via Milvus + Elasticsearch |
| 3 | `[API]` `GET /search/query?q=...` | Semantic search across ontology |
| 4 | `[SCREEN]` **Query Intent** (Intent Engine) | System classifies: "This is a data query" |
| 5 | `[SCREEN]` **SQL Preview** | Intent Engine generates SQL from NL |
| 6 | `[API]` `POST /sql/query` | Execute generated SQL |
| 7 | `[SCREEN]` **Results** | Table + auto-generated chart |
| 8 | `[SCREEN]` **Refine** | User can refine NL question or edit SQL directly |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_search__semantic_search → search ontology
[MCP] mcp__voyant_sql__execute_query → run generated SQL
[AGENT] "What are the top 10 customers by order volume?"
  → Intent Engine classifies as query
  → Schema Resolver finds Customer, Order types
  → Plan Generator creates SQL
  → Plan Validator checks permissions
  → Plan Executor runs query
  → Result: table + chart
```

#### ASCII Wireframe: Semantic Search

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Search                                   [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │  ┌──────────────────────────────────────────────┐     │
│          │  │ 🔍 What are the top 10 customers by revenue? │     │
│          │  └──────────────────────────────────────────────┘     │
│          │                                                       │
│          │  ┌─ Intent Detected: DATA QUERY ─────────────────┐    │
│          │  │ I found matching types: Customer (12 props),   │    │
│          │  │ Order (8 props). Generating SQL...              │    │
│          │  └────────────────────────────────────────────────┘    │
│          │                                                       │
│          │  ┌─ Generated SQL ───────────────────────────────┐    │
│          │  │ SELECT c.name, SUM(o.amount) as total_revenue │    │
│          │  │ FROM customers c JOIN orders o ON ...          │    │
│          │  │ GROUP BY c.name ORDER BY total_revenue DESC    │    │
│          │  │ LIMIT 10                                 [Edit]│    │
│          │  └────────────────────────────────────────────────┘    │
│          │                                                       │
│          │  ┌─ Results ─────────────────────────────────────┐    │
│          │  │ name         │ total_revenue                   │    │
│          │  │ Acme Corp    │ $452,300                        │    │
│          │  │ Globex Inc   │ $321,800                        │    │
│          │  │ ...          │ ...                             │    │
│          │  │                         [📊 Chart] [📥 Export] │    │
│          │  └────────────────────────────────────────────────┘    │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| NL Search | ✅ Object search | ✅ Genie | ✅ Intent Engine |
| NL → SQL | ❌ | ✅ Genie | ✅ Intent Engine |
| Semantic (vector) | ❌ | ❌ | ✅ Milvus |
| Full-text | ✅ | ⚠️ | ✅ Elasticsearch |
| Auto-chart | ❌ | ✅ | ✅ ECharts |
| Review before run | N/A | ✅ | ✅ |
| **Agent NL** | ❌ | ❌ | ✅ Full MCP |

---

## Journey 9: Build Dashboard (Charts, Tables, Filters)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Workshop** | Click "New Workshop" → select layout |
| 2 | **Widget Library** | Drag: chart, table, map, metric, filter |
| 3 | **Data Binding** | Bind widget to Object Type or dataset |
| 4 | **Configuration** | Configure axes, aggregations, colors |
| 5 | **Filters** | Add interactive filters (dropdown, date range, search) |
| 6 | **Save & Share** | Save workshop; share with team |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Dashboards** | Click "Create" → "Dashboard" |
| 2 | **Add Widget** | Add: visualization, textbox, filter |
| 3 | **SQL Query** | Each widget backed by SQL query |
| 4 | **Chart Config** | Configure chart type, axes, colors |
| 5 | **Filters** | Add parameter filters |
| 6 | **Publish** | Publish dashboard; share via link |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Dashboard Builder** (new) | Click "New Dashboard" |
| 2 | `[SCREEN]` **Layout Editor** | Choose grid layout (2x2, 3x2, custom) |
| 3 | `[SCREEN]` **Widget Library** | Drag: chart (ECharts), table, metric card, map |
| 4 | `[SCREEN]` **Data Binding** | Bind to Object Type, SQL query, or metric |
| 5 | `[SCREEN]` **Chart Config** | Configure: type (bar/line/pie/scatter), axes, colors |
| 6 | `[SCREEN]` **Filter Bar** | Add filters: dropdown, date range, text search |
| 7 | `[API]` `POST /dashboards` | Save dashboard layout + widget configs |
| 8 | `[SCREEN]` **Dashboard View** | Interactive dashboard with real-time data |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_dataintel__create_dashboard → create dashboard
[MCP] mcp__voyant_dataintel__add_widget → add chart/table
[AGENT] "Create a dashboard showing revenue by month with a customer segment filter"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Visual Builder | ✅ Workshop | ✅ Dashboards | ✅ Dashboard Builder |
| Chart Types | ✅ Rich | ✅ Rich | ✅ ECharts (50+ types) |
| Interactive Filters | ✅ | ✅ | ✅ |
| Real-time Data | ✅ | ⚠️ Scheduled | ✅ WebSocket (planned) |
| Map Support | ✅ | ⚠️ | ✅ ECharts Geo |
| **Agent-built** | ❌ | ❌ | ✅ MCP tools |
| **NL → Dashboard** | ❌ | ❌ | ✅ Intent Engine |

---

## Journey 10: Export Data for Reporting

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Object Explorer** or **SQL Studio** | Open dataset or query results |
| 2 | **Export Menu** | Click "Export" → CSV / Excel / PDF |
| 3 | **Options** | Select columns, filters, format |
| 4 | **Download** | Download file |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **SQL Editor** or **Notebook** | Run query |
| 2 | **Export** | Click "Download" on results |
| 3 | **Format** | CSV / TSV / JSON / Excel |
| 4 | **Databricks SQL** | `COPY INTO` for bulk export to S3 |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **SQL Studio** or **Ontology Explorer** | Run query or browse objects |
| 2 | `[SCREEN]` **Export Menu** | Click "Export" on results table |
| 3 | `[SCREEN]` **Format Selector** | Choose: CSV / JSON / XLSX / PDF |
| 4 | `[API]` `POST /export` | Generate export file |
| 5 | `[SCREEN]` **Download** | Download file |
| 6 | `[API]` `POST /export/schedule` | Schedule recurring export |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_sql__execute_query → get data
[MCP] mcp__voyant_dataintel__export_data → export to format
[AGENT] "Export all Q3 orders as Excel with customer names"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| CSV | ✅ | ✅ | ✅ |
| Excel | ✅ | ✅ | ✅ |
| JSON | ✅ | ✅ | ✅ |
| PDF | ✅ | ❌ | ✅ |
| Scheduled Export | ⚠️ | ✅ COPY INTO | ✅ Temporal |
| **Agent export** | ❌ | ❌ | ✅ MCP tools |

---

# PART C: DATA SCIENTIST JOURNEYS

---

## Journey 11: Explore Data in Notebook

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Quiver** | Click "Notebooks" → "New Notebook" |
| 2 | **Cell Editor** | Write Python/SQL/R cells |
| 3 | **Import Data** | `import foundry; ds = foundry.dataset("customers")` |
| 4 | **Explore** | pandas/PySpark analysis with inline charts |
| 5 | **Save** | Save notebook; share with team |
| 6 | **Version** | Notebooks versioned in Foundry Repos |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Workspace** | Click "Create" → "Notebook" |
| 2 | **Language** | Select: Python / SQL / R / Scala |
| 3 | **Cluster** | Attach to compute cluster |
| 4 | **Import Data** | `df = spark.table("catalog.schema.table")` |
| 5 | **Explore** | PySpark/pandas with `%sql` magic, inline charts |
| 6 | **Save** | Auto-saves; version in Repos |
| 7 | **Share** | Share link; collaborate in real-time |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Notebooks** (new) | Click "New Notebook" |
| 2 | `[SCREEN]` **Cell Editor** (Monaco) | Write Python / SQL cells |
| 3 | `[API]` `POST /notebooks/{id}/execute` | Execute cell |
| 4 | `[SCREEN]` **Import Panel** | Browse ontology types or run SQL to load data |
| 5 | `[API]` `GET /ontology/object-types/{id}/objects` | Load objects as DataFrame |
| 6 | `[SCREEN]` **Inline Output** | Tables, charts (ECharts), text output |
| 7 | `[API]` `PUT /notebooks/{id}` | Save notebook |
| 8 | `[SCREEN]` **Version History** | View/restore previous versions |

#### ASCII Wireframe: Notebook

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Notebook: "Customer Analysis"        [Run All] [Save] │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Cell 1 [Python] ─────────────────────────────────┐ │
│ Ontology │ │ import pandas as pd                                │ │
│  ├ Custs │ │ from voyant import ontology                        │ │
│  ├ Orders│ │                                                    │ │
│  └ Prods │ │ df = ontology.objects("Customer").to_dataframe()   │ │
│          │ │ df.head()                                    [▶ Run]│ │
│          │ └────────────────────────────────────────────────────┘ │
│          │ ┌─ Output ──────────────────────────────────────────┐ │
│          │ │    name        segment    revenue   created        │ │
│          │ │ 0  Acme Corp   Enterprise  452300   2024-03-15    │ │
│          │ │ 1  Globex Inc  Mid-Market  321800   2023-11-20    │ │
│          │ │ ...                                                  │ │
│          │ └────────────────────────────────────────────────────┘ │
│          │ ┌─ Cell 2 [Python] ─────────────────────────────────┐ │
│          │ │ df.groupby('segment')['revenue'].sum().plot.bar()  │ │
│          │ └────────────────────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Notebook UI | ✅ Quiver | ✅ Native | ✅ Monaco cells |
| Multi-language | ✅ Py/SQL/R | ✅ Py/SQL/R/Scala | ✅ Py/SQL |
| Collaboration | ⚠️ | ✅ Real-time | ⚠️ (planned) |
| Inline Charts | ✅ | ✅ | ✅ ECharts |
| **Ontology-aware** | ✅ Foundry SDK | ❌ | ✅ Ontology API |
| **Agent-created** | ❌ | ❌ | ✅ MCP tools |
| Version Control | ✅ Repos | ✅ Repos | ✅ Git |

---

## Journey 12: Train ML Model with Experiment Tracking

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **ML Workspace** | Open ML workspace → "New Experiment" |
| 2 | **Configure** | Set: framework (sklearn/PyTorch/TF), compute, dataset |
| 3 | **Training Code** | Write training script in notebook |
| 4 | **Logging** | `foundry.log_metric("accuracy", 0.95)` |
| 5 | **Artifacts** | Upload model artifacts to Foundry Storage |
| 6 | **Compare** | Experiment tracker shows all runs with metrics |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Experiments** | Click "Experiments" → "Create Experiment" |
| 2 | **Notebook** | Write training code with `mlflow.start_run()` |
| 3 | **Autolog** | `mlflow.autolog()` captures params/metrics automatically |
| 4 | **Manual Logging** | `mlflow.log_metric("f1", 0.92)` |
| 5 | **Artifacts** | `mlflow.log_artifact("model.pkl")` |
| 6 | **Compare** | MLflow UI: compare runs, parallel coordinates |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **ML Platform** (new) | Click "Experiments" → "New Experiment" |
| 2 | `[API]` `POST /ml/experiments` | Create experiment (MLflow-compatible) |
| 3 | `[SCREEN]` **Training Config** | Select: framework, compute, dataset |
| 4 | `[API]` `POST /ml/experiments/{id}/runs` | Start run |
| 5 | `[API]` `POST /ml/runs/{id}/log` | Log params, metrics, artifacts |
| 6 | `[WF]` `MLTrainingWorkflow` (Temporal) | Orchestrates: data prep → train → evaluate → log |
| 7 | `[SCREEN]` **Run Comparison** | Table + charts comparing all runs |
| 8 | `[API]` `GET /ml/experiments/{id}/runs` | List all runs |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__create_experiment → create experiment
[MCP] mcp__voyant_ml__start_run → start training run
[MCP] mcp__voyant_ml__log_metric → log metric
[MCP] mcp__voyant_ml__log_artifact → log model
[AGENT] "Train a customer churn model on the orders dataset"
```

#### ASCII Wireframe: Experiment Tracking

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  ML Experiments                           [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Experiment: "Customer Churn Prediction" ──────────┐│
│          │ │ Runs: 12  │  Best F1: 0.92  │  Framework: sklearn  ││
│          │ ├────────────────────────────────────────────────────┤│
│          │ │ Run      │ Accuracy │ F1     │ AUC   │ Status       ││
│          │ │ run-12   │ 0.94     │ 0.92   │ 0.96  │ ✅ Finished  ││
│          │ │ run-11   │ 0.91     │ 0.89   │ 0.93  │ ✅ Finished  ││
│          │ │ run-10   │ 0.88     │ 0.85   │ 0.90  │ ✅ Finished  ││
│          │ │ run-09   │ 0.93     │ 0.91   │ 0.95  │ ✅ Finished  ││
│          │ │ run-08   │ —        │ —      │ —     │ 🔄 Running   ││
│          │ ├────────────────────────────────────────────────────┤│
│          │ │ [Compare Selected]  [Register Best Model]           ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Experiment Tracking | ✅ ML Workspace | ✅ MLflow | ✅ MLflow-compatible |
| Autologging | ⚠️ | ✅ `mlflow.autolog()` | ⚠️ (manual logging) |
| Run Comparison | ✅ | ✅ MLflow UI | ✅ Comparison view |
| Artifact Storage | ✅ Foundry Storage | ✅ MLflow artifacts | ✅ MinIO |
| **Agent training** | ❌ | ❌ | ✅ MCP tools |
| **Self-hosted** | ❌ | ❌ | ✅ Docker |

---

## Journey 13: Compare Model Runs

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Experiment Tracker** | Select multiple runs |
| 2 | **Comparison View** | Parallel coordinates, scatter plots |
| 3 | **Metric Table** | Side-by-side metrics |
| 4 | **Best Run** | System highlights best run per metric |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **MLflow Experiments** | Click experiment → select runs |
| 2 | **Compare** | Click "Compare" button |
| 3 | **Parallel Coordinates** | Visual comparison of hyperparams vs metrics |
| 4 | **Metric Table** | Side-by-side run metrics |
| 5 | **Artifact Diff** | Compare model artifacts |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Run Comparison** | Select runs from experiment detail |
| 2 | `[API]` `GET /ml/runs/compare?ids=run1,run2,...` | Fetch comparison data |
| 3 | `[SCREEN]` **Comparison Table** | Side-by-side params + metrics |
| 4 | `[SCREEN]` **Parallel Coordinates Chart** | ECharts parallel coordinate visualization |
| 5 | `[SCREEN]` **Metric Trend** | Line chart showing metric across runs |
| 6 | `[SCREEN]` **Best Run Highlight** | Auto-highlight best run per metric |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Run Selection | ✅ | ✅ | ✅ |
| Parallel Coordinates | ✅ | ✅ | ✅ ECharts |
| Metric Table | ✅ | ✅ | ✅ |
| Auto-highlight | ⚠️ | ✅ | ✅ |
| **Agent comparison** | ❌ | ❌ | ✅ MCP |

---

## Journey 14: Register and Version Model

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **ML Workspace** | Click best run → "Register Model" |
| 2 | **Model Name** | Enter model name |
| 3 | **Version** | First version is v1 |
| 4 | **Metadata** | Add description, tags |
| 5 | **Model Registry** | Model appears in registry |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **MLflow Run** | Click run → "Register Model" |
| 2 | **Model Registry** | Select/create registered model |
| 3 | **Version Created** | New version auto-created |
| 4 | **Stage** | Set stage: None → Staging → Production → Archived |
| 5 | **Tags** | Add tags, description |
| 6 | **Approval** | Request approval for stage transitions |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Run Detail** | Click run → "Register Model" |
| 2 | `[API]` `POST /ml/models` | Create registered model |
| 3 | `[API]` `POST /ml/models/{id}/versions` | Create version from run |
| 4 | `[SCREEN]` **Model Registry** | Browse all registered models with versions |
| 5 | `[API]` `PATCH /ml/models/{id}/versions/{v}` | Set stage (none → staging → production → archived) |
| 6 | `[SCREEN]` **Version Detail** | View: metrics, artifacts, lineage to run |

#### ASCII Wireframe: Model Registry

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Model Registry                            [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Registered Models ───────────────────────────────┐ │
│          │ │ [+ Register Model]                                 │ │
│          │ │                                                     │ │
│          │ │  Model              │ Versions │ Stage      │ F1    │ │
│          │ │  churn-predictor    │ 5        │ Production │ 0.92  │ │
│          │ │  fraud-detector     │ 3        │ Staging    │ 0.95  │ │
│          │ │  price-optimizer    │ 1        │ None       │ 0.87  │ │
│          │ ├────────────────────────────────────────────────────┤ │
│          │ │ ┌─ churn-predictor Versions ──────────────────────┐│ │
│          │ │ │ v5 │ Production │ F1: 0.92 │ 2026-09-04 [Deploy]││ │
│          │ │ │ v4 │ Staging    │ F1: 0.89 │ 2026-09-02        ││ │
│          │ │ │ v3 │ Archived   │ F1: 0.87 │ 2026-08-28        ││ │
│          │ │ └─────────────────────────────────────────────────┘│ │
│          │ └─────────────────────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Model Registry | ✅ | ✅ MLflow | ✅ MLflow-compatible |
| Versioning | ✅ | ✅ | ✅ |
| Stage Management | ✅ | ✅ (4 stages) | ✅ (4 stages) |
| Approval Workflow | ⚠️ | ✅ | ⚠️ (planned) |
| **Agent register** | ❌ | ❌ | ✅ MCP tools |

---

## Journey 15: Deploy Model to Serving Endpoint

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Model Registry** | Click model → "Deploy" |
| 2 | **Endpoint Config** | Set: compute, scaling, timeout |
| 3 | **Deploy** | Foundry provisions endpoint |
| 4 | **Test** | Send test request via API or UI |
| 5 | **Monitor** | Latency, throughput, error rate |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Model Registry** | Click model version → "Deploy" → "Serving Endpoint" |
| 2 | **Endpoint Config** | Set: compute size, scale-to-zero, timeout |
| 3 | **Deploy** | Databricks provisions GPU/CPU endpoint |
| 4 | **Test** | "Query Endpoint" tab → send test payload |
| 5 | **Traffic** | Configure traffic splitting between versions |
| 6 | **Monitor** | Inference tables, latency, error rate |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Model Detail** | Click model version → "Deploy Endpoint" |
| 2 | `[API]` `POST /ml/endpoints` | Create serving endpoint |
| 3 | `[SCREEN]` **Endpoint Config** | Set: timeout, max batch, replicas |
| 4 | `[API]` `POST /ml/endpoints/{id}/activate` | Activate endpoint |
| 5 | `[SCREEN]` **Test Panel** | Send test payload, view response |
| 6 | `[API]` `POST /ml/endpoints/{id}/predict` | Real-time prediction |
| 7 | `[SCREEN]` **Endpoint Monitor** | Latency, throughput, error rate |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__create_endpoint → deploy model
[MCP] mcp__voyant_ml__predict → call endpoint
[AGENT] "Deploy churn-predictor v5 to production"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| One-click Deploy | ✅ | ✅ | ✅ |
| Auto-scaling | ✅ | ✅ | ⚠️ (planned) |
| Traffic Splitting | ⚠️ | ✅ | ⚠️ (planned) |
| Scale-to-zero | ❌ | ✅ | ⚠️ (planned) |
| **Agent deploy** | ❌ | ❌ | ✅ MCP tools |

---

## Journey 16: Monitor Model Drift

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **ML Monitor** | Navigate to model monitoring dashboard |
| 2 | **Drift Detection** | System compares production vs training distributions |
| 3 | **Alerts** | Configure drift thresholds |
| 4 | **Retrain** | Trigger retrain pipeline when drift detected |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Model Serving** | Click endpoint → "Monitoring" tab |
| 2 | **Inference Tables** | Logs every prediction to Delta table |
| 3 | **Quality Metrics** | Auto-computes: drift, skew, missing values |
| 4 | **Alerts** | Configure alerts on quality metrics |
| 5 | **Retrain** | Databricks can auto-trigger retrain jobs |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Endpoint Monitor** | Navigate to endpoint → "Monitoring" tab |
| 2 | `[API]` `GET /ml/endpoints/{id}/metrics` | Fetch inference metrics |
| 3 | `[SCREEN]` **Drift Dashboard** | Feature distribution comparison (training vs production) |
| 4 | `[API]` `POST /ml/endpoints/{id}/drift-check` | Run drift detection |
| 5 | `[SCREEN]` **Alert Config** | Set drift thresholds (PSI, KS statistic) |
| 6 | `[WF]` Automatic retrain trigger | When drift > threshold → start retrain pipeline |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__endpoint_metrics → check drift
[MCP] mcp__voyant_ml__trigger_retrain → auto-retrain
[AGENT] "Check if churn model is drifting and retrain if needed"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Drift Detection | ✅ | ✅ | ✅ |
| Inference Logging | ✅ | ✅ Inference Tables | ✅ |
| Auto-alerts | ✅ | ✅ | ✅ |
| Auto-retrain | ⚠️ | ✅ | ✅ Temporal |
| **Agent monitoring** | ❌ | ❌ | ✅ MCP tools |

---

# PART D: AI/AGENT ENGINEER JOURNEYS

---

## Journey 17: Define AI Agent (Prompt, Model, Tools, Guardrails)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **AIP Console** | Click "Create Agent" |
| 2 | **Model Selection** | Select LLM (GPT-4, Claude, Llama) |
| 3 | **System Prompt** | Define agent behavior and instructions |
| 4 | **Tools** | Attach tools: ontology read, action, web search |
| 5 | **Guardrails** | Set safety rules: max calls, blocked actions |
| 6 | **Test** | Test in chat interface |
| 7 | **Deploy** | Publish to AIP production |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Agent Bricks** | Click "Create Agent" |
| 2 | **Model** | Select model from Model Serving |
| 3 | **Instructions** | Define agent instructions |
| 4 | **Tools** | Attach: SQL, vector search, web, custom |
| 5 | **Guardrails** | Set safety constraints |
| 6 | **Evaluate** | Run evaluation suite |
| 7 | **Deploy** | Deploy to Model Serving endpoint |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Agent Builder** (new) | Click "Create Agent" |
| 2 | `[API]` `POST /ml/agents` | Create agent definition |
| 3 | `[SCREEN]` **Agent Config** | Set: name, description, system prompt |
| 4 | `[SCREEN]` **Model Selector** | Choose provider (Groq/OpenAI/local) + model |
| 5 | `[SCREEN]` **Tool Selector** | Select MCP tools: voyant.sql, voyant.ontology.*, etc. |
| 6 | `[SCREEN]` **Guardrails Config** | Set: max queries, blocked tables, require approval |
| 7 | `[API]` `PUT /ml/agents/{id}` | Save agent definition |
| 8 | `[SCREEN]` **Test Chat** | Test agent in built-in chat interface |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__create_agent → define agent
[MCP] mcp__voyant_ml__list_agents → browse agents
[MCP] mcp__voyant_ml__update_agent → modify config
[AGENT] "Create an agent that answers sales questions using SQL and ontology"
```

#### ASCII Wireframe: Agent Builder

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Agent Builder                             [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Define Agent ────────────────────────────────────┐ │
│          │ │ Name: [Sales Assistant                        ]    │ │
│          │ │ Model: [Groq ▾] [openai/gpt-oss-120b ▾]           │ │
│          │ │ Temp: [0.1]  Max Tokens: [4096]                    │ │
│          │ │                                                     │ │
│          │ │ System Prompt:                                      │ │
│          │ │ ┌──────────────────────────────────────────────┐   │ │
│          │ │ │ You are a sales data assistant. Answer       │   │ │
│          │ │ │ questions about customers and orders using    │   │ │
│          │ │ │ the available MCP tools. Always explain       │   │ │
│          │ │ │ your reasoning.                               │   │ │
│          │ │ └──────────────────────────────────────────────┘   │ │
│          │ │                                                     │ │
│          │ │ Tools:                                              │ │
│          │ │ ☑ voyant.sql.execute_query                          │ │
│          │ │ ☑ voyant.ontology.list_object_types                 │ │
│          │ │ ☑ voyant.ontology.search_objects                    │ │
│          │ │ ☑ voyant.ontology.traverse_links                    │ │
│          │ │ ☐ voyant.ontology.create_object                     │ │
│          │ │                                                     │ │
│          │ │ Guardrails:                                         │ │
│          │ │ Max queries/session: [50]                            │ │
│          │ │ Blocked tables: [audit_log, credentials]            │ │
│          │ │ Require approval: [No ▾]                            │ │
│          │ │                                           [Save]    │ │
│          │ └─────────────────────────────────────────────────────┘ │
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Agent Definition | ✅ AIP | ✅ Agent Bricks | ✅ Agent Builder |
| Multi-model | ✅ | ✅ | ✅ Groq/OpenAI/local |
| Tool Selection | ✅ Ontology tools | ✅ SQL/Vector/Web | ✅ 80+ MCP tools |
| Guardrails | ✅ | ✅ | ✅ |
| Test Chat | ✅ | ✅ | ✅ |
| **Self-hosted** | ❌ | ❌ | ✅ Docker |
| **Open-source** | ❌ | ❌ | ✅ Apache 2.0 |

---

## Journey 18: Evaluate Agent with Test Cases

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **AIP Evaluation** | Click "Evaluate" on agent |
| 2 | **Test Cases** | Define test cases: input + expected output |
| 3 | **AI Judge** | Select judge model for scoring |
| 4 | **Run** | Execute evaluation suite |
| 5 | **Results** | Per-test scores + overall pass rate |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Agent Evaluation** | Click "Evaluate" on agent |
| 2 | **Test Suite** | Define test cases with expected answers |
| 3 | **AI Judge** | LLM-as-judge scoring |
| 4 | **Run** | Execute evaluation |
| 5 | **Results** | Scores, explanations, failure analysis |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Evaluation** | Click "Evaluate" on agent |
| 2 | `[API]` `POST /ml/agents/{id}/evaluations` | Create evaluation |
| 3 | `[SCREEN]` **Test Case Editor** | Define: input, expected output, expected tools |
| 4 | `[API]` `POST /ml/evaluations/{id}/run` | Run evaluation |
| 5 | `[WF]` `AgentEvaluationWorkflow` (Temporal) | Runs each test case, collects results |
| 6 | `[SCREEN]` **Results Dashboard** | Per-test: score, tool calls, judge notes |
| 7 | `[API]` `GET /ml/evaluations/{id}/results` | Fetch detailed results |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__create_evaluation → define eval
[MCP] mcp__voyant_ml__run_evaluation → execute
[MCP] mcp__voyant_ml__evaluation_results → get scores
[AGENT] "Evaluate the sales agent with these 20 test questions"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Test Cases | ✅ | ✅ | ✅ |
| AI Judge | ✅ | ✅ | ✅ |
| Tool Verification | ⚠️ | ⚠️ | ✅ (check MCP tools used) |
| Detailed Results | ✅ | ✅ | ✅ |
| **Agent self-eval** | ❌ | ❌ | ✅ MCP tools |

---

## Journey 19: Deploy Agent to Production

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **AIP Console** | Click "Deploy" on evaluated agent |
| 2 | **Endpoint** | Agent gets API endpoint |
| 3 | **Monitoring** | Enable monitoring and logging |
| 4 | **Access** | Share endpoint with users/apps |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Model Serving** | Click "Deploy" on agent |
| 2 | **Endpoint** | Agent gets serving endpoint |
| 3 | **Scale** | Configure scaling policy |
| 4 | **Access** | API access via token |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Agent Detail** | Click "Deploy" on agent |
| 2 | `[API]` `POST /ml/agents/{id}/deploy` | Deploy agent |
| 3 | `[WF]` `AgentDeployWorkflow` (Temporal) | Provisions endpoint, registers MCP server |
| 4 | `[SCREEN]` **Agent Endpoint** | Agent accessible via API + MCP |
| 5 | `[API]` `POST /ml/agents/{id}/chat` | Send message to agent |
| 6 | `[SCREEN]` **Production Monitor** | Real-time: messages, latency, tool calls |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| One-click Deploy | ✅ | ✅ | ✅ |
| API Endpoint | ✅ | ✅ | ✅ |
| **MCP Endpoint** | ❌ | ❌ | ✅ Agent-as-MCP |
| Monitoring | ✅ | ✅ | ✅ |
| Scaling | ✅ | ✅ | ⚠️ (planned) |

---

## Journey 20: Monitor Agent Performance

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **AIP Monitor** | Navigate to agent monitoring |
| 2 | **Metrics** | View: calls/hour, latency, error rate |
| 3 | **Conversation Log** | Browse past conversations |
| 4 | **Tool Usage** | Which tools used, frequency |
| 5 | **Cost** | Token usage and cost estimation |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Serving Endpoint** | Click endpoint → "Monitoring" |
| 2 | **Metrics** | Latency, throughput, errors |
| 3 | **Inference Log** | Every request logged |
| 4 | **Cost** | DBU consumption |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Agent Monitor** | Navigate to agent → "Monitoring" tab |
| 2 | `[API]` `GET /ml/agents/{id}/metrics` | Fetch performance metrics |
| 3 | `[SCREEN]` **Metrics Dashboard** | Messages/hour, latency, error rate, cost |
| 4 | `[SCREEN]` **Conversation Browser** | Browse past conversations with tool call details |
| 5 | `[SCREEN]` **Tool Analytics** | Most used tools, avg response time per tool |
| 6 | `[SCREEN]` **Cost Tracker** | Token usage by model, daily/weekly/monthly |
| 7 | `[SCREEN]` **Anomaly Alerts** | Alert on unusual patterns |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_ml__agent_metrics → check performance
[MCP] mcp__voyant_ml__agent_conversations → browse logs
[AGENT] "How is the sales agent performing this week?"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Latency Monitoring | ✅ | ✅ | ✅ |
| Error Tracking | ✅ | ✅ | ✅ |
| Conversation Log | ✅ | ⚠️ Inference tables | ✅ |
| Tool Analytics | ✅ | ❌ | ✅ |
| Cost Tracking | ✅ | ✅ DBU | ✅ Token-based |
| **Agent self-monitor** | ❌ | ❌ | ✅ MCP |

---

## Journey 21: Build and Deploy MCP Tools

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero MCP support |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has zero MCP support |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **MCP Tools** (new) | Navigate to MCP Tools management |
| 2 | `[SCREEN]` **Tool Builder** | Define tool: name, description, input schema |
| 3 | `[SCREEN]` **Function Editor** (Monaco) | Write handler function (Python) |
| 4 | `[API]` `POST /mcp/tools` | Register tool |
| 5 | `[SCREEN]` **Test Panel** | Test tool with sample input |
| 6 | `[API]` `POST /mcp/tools/{id}/deploy` | Deploy to MCP server |
| 7 | `[SCREEN]` **Tool Registry** | Browse all 80+ MCP tools |
| 8 | `[SCREEN]` **Tool Analytics** | Usage stats, latency, error rate |

#### ASCII Wireframe: MCP Tool Builder

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  MCP Tools                                [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ MCP Tool Registry ─── [+ Create Tool] ───────────┐│
│          │ │                                                    ││
│          │ │  Category    │ Tools │ Usage/hr │ Avg Latency      ││
│          │ │  Ontology    │ 15    │ 342      │ 23ms             ││
│          │ │  SQL         │ 3     │ 189      │ 45ms             ││
│          │ │  Scraper     │ 13    │ 67       │ 1.2s             ││
│          │ │  ML          │ 8     │ 23       │ 120ms            ││
│          │ │  Governance  │ 8     │ 56       │ 12ms             ││
│          │ │  Search      │ 3     │ 234      │ 35ms             ││
│          │ │                                                    ││
│          │ │ ┌─ Create Tool ─────────────────────────────────┐  ││
│          │ │ │ Name: [voyant.custom.my_tool             ]     │  ││
│          │ │ │ Description: [Custom analysis tool       ]     │  ││
│          │ │ │ Input Schema:                                  │  ││
│          │ │ │ ┌────────────────────────────────────────┐    │  ││
│          │ │ │ │ {"type": "object", "properties": {     │    │  ││
│          │ │ │ │   "query": {"type": "string"},         │    │  ││
│          │ │ │ │   "limit": {"type": "integer"}         │    │  ││
│          │ │ │ │ }, "required": ["query"]}              │    │  ││
│          │ │ │ └────────────────────────────────────────┘    │  ││
│          │ │ │ Handler:                                      │  ││
│          │ │ │ ┌────────────────────────────────────────┐    │  ││
│          │ │ │ │ def handler(query: str, limit: int=10): │    │  ││
│          │ │ │ │     results = search(query)             │    │  ││
│          │ │ │ │     return results[:limit]               │    │  ││
│          │ │ │ └────────────────────────────────────────┘    │  ││
│          │ │ │                                    [Test] [Deploy]││
│          │ │ └────────────────────────────────────────────────┘  ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| MCP Protocol | ❌ | ❌ | ✅ 80+ tools |
| Visual Tool Builder | ❌ | ❌ | ✅ |
| Function Editor | ❌ | ❌ | ✅ Monaco |
| Tool Analytics | ❌ | ❌ | ✅ |
| Tool Registry | ❌ | ❌ | ✅ |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 22: Create Capsule (Portable Intelligence Recipe)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has no capsule concept |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has no capsule concept |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Capsules** (`view-capsules.ts`) | Click "Create Capsule" |
| 2 | `[SCREEN]` **Capsule Builder** | Define: name, description, version |
| 3 | `[SCREEN]` **Recipe Editor** | Configure steps: agents, tools, workflows, prompts |
| 4 | `[SCREEN]` **Signing** | Ed25519 signature for integrity |
| 5 | `[API]` `POST /capsules` | Create capsule |
| 6 | `[SCREEN]` **Capsule Registry** | Browse, install, share capsules |
| 7 | `[API]` `POST /capsules/{id}/execute` | Run capsule |
| 8 | `[SCREEN]` **Execution Log** | View step-by-step execution |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_capsules__create_capsule → create capsule
[MCP] mcp__voyant_capsules__list_capsules → browse registry
[MCP] mcp__voyant_capsules__execute_capsule → run
[AGENT] "Create a capsule that scrapes competitor prices and generates a report"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Portable Recipes | ❌ | ❌ | ✅ Capsules |
| Signing | ❌ | ❌ | ✅ Ed25519 |
| Agent Composition | ❌ | ❌ | ✅ Multi-agent |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

# PART E: GOVERNANCE OFFICER JOURNEYS

---

## Journey 23: Configure RBAC Policies

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Admin Console** | Navigate to "Access Control" |
| 2 | **Roles** | Create/edit roles (Viewer, Editor, Admin) |
| 3 | **Permissions** | Assign permissions per role (read/write/admin on types) |
| 4 | **Users** | Assign roles to users |
| 5 | **Markings** | Add security markings (classification levels) |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Admin Console** | Navigate to "Access Control" |
| 2 | **Workspace ACLs** | Set permissions on workspace objects |
| 3 | **Unity Catalog** | GRANT/REVOKE on catalogs, schemas, tables |
| 4 | **Service Principals** | Manage service principal access |
| 5 | **Groups** | Create groups, assign to roles |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance** (`view-governance.ts`) | Navigate to Governance |
| 2 | `[API]` `GET /governance/roles` | List all roles |
| 3 | `[SCREEN]` **Role Editor** | Create role: name, description, permissions |
| 4 | `[API]` `POST /governance/roles` | Save role (synced to SpiceDB + Keycloak) |
| 5 | `[SCREEN]` **Permission Matrix** | Grid: roles × resources × actions |
| 6 | `[API]` `POST /governance/assignments` | Assign role to user/group |
| 7 | `[SCREEN]` **User List** | View all users with roles |
| 8 | Keycloak | SSO/SAML/LDAP integration |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Roles | ✅ | ✅ | ✅ |
| Permissions | ✅ Fine-grained | ✅ GRANT/REVOKE | ✅ SpiceDB |
| SSO/SAML | ✅ | ✅ | ✅ Keycloak |
| Markings | ✅ | ❌ | ⚠️ (planned) |
| **Agent RBAC** | ❌ | ❌ | ✅ Per-agent perms |

---

## Journey 24: Set Up Row-Level Security

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Object Security** | Navigate to object type security |
| 2 | **Policy** | Create row-level policy: "Users see only their region's data" |
| 3 | **Conditions** | Define: `user.region == object.region` |
| 4 | **Apply** | Policy enforced on all queries |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Unity Catalog** | `CREATE ROW FILTER` |
| 2 | **Filter Function** | Write SQL function returning boolean |
| 3 | **Apply** | `ALTER TABLE ... SET ROW FILTER` |
| 4 | **Test** | Verify users see only their rows |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance → Row Security** | Navigate to row-level security |
| 2 | `[API]` `GET /governance/row-filters` | List existing filters |
| 3 | `[SCREEN]` **Filter Builder** | Create filter: table, condition, roles |
| 4 | `[API]` `POST /governance/row-filters` | Save filter (registered in Ranger) |
| 5 | `[SCREEN]` **Test Panel** | Test filter as different users |
| 6 | Ranger | Apache Ranger enforces on all queries |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Row Filters | ✅ | ✅ Unity Catalog | ✅ Ranger |
| Visual Builder | ⚠️ | ❌ SQL only | ✅ Filter Builder |
| Test as User | ⚠️ | ❌ | ✅ |
| **Agent filtering** | ❌ | ❌ | ✅ Automatic |

---

## Journey 25: Configure Column-Level Masking

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Security** | Navigate to column masking |
| 2 | **Masking Policy** | Create: "Mask SSN for non-HR roles" |
| 3 | **Rules** | Define masking: hash, partial, null, regex |
| 4 | **Apply** | Policy enforced automatically |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Unity Catalog** | `CREATE COLUMN MASK` |
| 2 | **Mask Function** | Write masking function |
| 3 | **Apply** | `ALTER TABLE ... ALTER COLUMN ... SET MASK` |
| 4 | **Test** | Verify masking works for different roles |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance → Column Masking** | Navigate to column masking |
| 2 | `[API]` `GET /governance/masking-rules` | List existing rules |
| 3 | `[SCREEN]` **Masking Builder** | Create: table, column, mask type, roles exempted |
| 4 | `[API]` `POST /governance/masking-rules` | Save rule (registered in Ranger) |
| 5 | `[SCREEN]` **Preview** | Preview masked vs unmasked data |
| 6 | Ranger | Apache Ranger enforces on all queries |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Column Masking | ✅ | ✅ | ✅ Ranger |
| Mask Types | ✅ Hash/Partial/Null | ✅ Custom functions | ✅ Hash/Partial/Null/Regex |
| Visual Builder | ⚠️ | ❌ | ✅ Masking Builder |
| Preview | ❌ | ❌ | ✅ |

---

## Journey 26: Review Audit Logs

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Admin Console** | Navigate to "Audit Logs" |
| 2 | **Log Viewer** | Search/filter audit entries |
| 3 | **Details** | Click entry: who, what, when, where, result |
| 4 | **Export** | Export logs for compliance |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **System Tables** | Query `system.access.audit` |
| 2 | **Dashboard** | Pre-built audit dashboard |
| 3 | **Search** | SQL queries on audit data |
| 4 | **Export** | Export to Delta table |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Audit** (`view-audit.ts`) | Navigate to Audit in sidebar |
| 2 | `[API]` `GET /governance/audit` | Fetch audit logs |
| 3 | `[SCREEN]` **Audit Log Viewer** | Table: timestamp, user, action, resource, result |
| 4 | `[SCREEN]` **Filters** | Filter by: user, action, resource, date range |
| 5 | `[SCREEN]` **Detail Panel** | Click entry → full details (IP, user agent, changes) |
| 6 | `[API]` `GET /governance/audit/export` | Export as CSV/JSON |

#### ASCII Wireframe: Audit Log

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Audit Log                                 [User ▾]    │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Audit Log ──── [Filter] [Export] ─────────────────┐│
│          │ │                                                    ││
│          │ │  Time       │ User      │ Action      │ Resource   ││
│          │ │  14:32:01   │ john@acme │ CREATE      │ ObjectType ││
│          │ │  14:31:45   │ agent-1   │ QUERY       │ SQL        ││
│          │ │  14:30:12   │ jane@acme │ UPDATE      │ Object     ││
│          │ │  14:29:55   │ agent-2   │ SCRAPE      │ ScrapeJob  ││
│          │ │  14:28:30   │ admin     │ RBAC_CHANGE │ Role       ││
│          │ │                                                    ││
│          │ │ ┌─ Detail: CREATE ObjectType ─────────────────────┐││
│          │ │ │ User: john@acme (IP: 10.0.1.45)                 │││
│          │ │ │ Resource: ObjectType "Supplier"                  │││
│          │ │ │ Changes: {name: "Supplier", properties: [...]}   │││
│          │ │ │ Result: SUCCESS                                  │││
│          │ │ └─────────────────────────────────────────────────┘││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Log Viewer | ✅ | ✅ System Tables | ✅ |
| Search/Filter | ✅ | ✅ SQL | ✅ Visual |
| Detail View | ✅ | ✅ | ✅ |
| Export | ✅ | ✅ | ✅ |
| **Agent audit** | ❌ | ❌ | ✅ Agent actions logged |

---

## Journey 27: Set Up Data Retention Policies

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Admin Console** | Navigate to "Data Retention" |
| 2 | **Policy** | Create: "Delete records older than 7 years" |
| 3 | **Apply** | Apply to datasets |
| 4 | **Monitor** | Track deletions |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Unity Catalog** | Set table properties: `TTL`, `delta.logRetentionDuration` |
| 2 | **VACUUM** | Periodic vacuum of old data |
| 3 | **Policies** | Configure via workspace admin |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance → Retention** | Navigate to retention policies |
| 2 | `[API]` `GET /governance/retention` | List policies |
| 3 | `[SCREEN]` **Policy Builder** | Create: scope (table/object type), duration, action |
| 4 | `[API]` `POST /governance/retention` | Save policy |
| 5 | `[WF]` Retention workflow (Temporal) | Periodic cleanup |
| 6 | `[SCREEN]` **Monitor** | Track deletions, storage reclaimed |

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Retention Policies | ✅ | ✅ TTL/VACUUM | ✅ Temporal |
| Visual Builder | ⚠️ | ❌ | ✅ |
| Auto-cleanup | ✅ | ✅ | ✅ Temporal |
| Audit Trail | ✅ | ⚠️ | ✅ |

---

## Journey 28: GDPR Right-to-Deletion

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Data Request** | Receive GDPR deletion request |
| 2 | **Search** | Find all records for the individual across datasets |
| 3 | **Delete** | Execute deletion across all datasets |
| 4 | **Verify** | Verify deletion complete |
| 5 | **Document** | Generate deletion certificate |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| 1 | **Manual Process** | No native GDPR workflow |
| 2 | **SQL** | `DELETE FROM ... WHERE person_id = ...` |
| 3 | **Delta VACUUM** | Vacuum deleted data |
| 4 | **Audit** | Log deletion in audit log |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Governance → GDPR** | Navigate to GDPR compliance |
| 2 | `[API]` `POST /governance/gdpr/deletion-request` | Create deletion request |
| 3 | `[SCREEN]` **Request Form** | Enter: subject identifier, data scope |
| 4 | `[WF]` `GDPRDeletionWorkflow` (Temporal) | Finds all records across ontology + data |
| 5 | `[SCREEN]` **Progress Tracker** | Track: tables scanned, records found, deleted |
| 6 | `[API]` `GET /governance/gdpr/{id}/status` | Check request status |
| 7 | `[SCREEN]` **Completion Certificate** | Generate deletion certificate |
| 8 | `[SCREEN]` **Audit Log** | Full audit trail of deletion |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_governance__gdpr_deletion → initiate deletion
[MCP] mcp__voyant_governance__gdpr_status → check progress
[AGENT] "Process GDPR deletion for user john@example.com"
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| GDPR Workflow | ⚠️ Manual | ❌ Manual SQL | ✅ Automated |
| Cross-table Scan | ✅ | ❌ | ✅ Ontology-aware |
| Progress Tracking | ❌ | ❌ | ✅ Temporal |
| Certificate | ❌ | ❌ | ✅ |
| **Agent-driven** | ❌ | ❌ | ✅ MCP |

---

# PART F: SCRAPER OPERATOR JOURNEYS

---

## Journey 29: Create Scraping Task (URL + Selectors)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero scraping capability |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has zero scraping capability |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper** (`view-scraper.ts`) | Navigate to Scraper → "Create Task" |
| 2 | `[SCREEN]` **Task Form** | Enter: URLs, CSS/XPath selectors, options |
| 3 | `[API]` `POST /scraper/jobs` | Create scrape job |
| 4 | `[WF]` `ScrapeJobWorkflow` (Temporal) | Executes: fetch → extract → store |
| 5 | `[SCREEN]` **Job Monitor** | Real-time: pages fetched, bytes processed |
| 6 | `[API]` `GET /scraper/jobs/{id}` | Check job status |
| 7 | `[SCREEN]` **Results** | View extracted data |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__create_task → create scrape job
[MCP] mcp__voyant_scraper__get_status → check status
[MCP] mcp__voyant_scraper__get_results → fetch results
[AGENT] "Scrape product prices from https://example.com/products"
```

---

## Journey 30: Use Template Library (Amazon, Google Maps, etc.)

### Palantir Foundry

N/A — No scraping capability.

### Databricks

N/A — No scraping capability.

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Templates** | Browse template library by category |
| 2 | `[SCREEN]` **Category Filter** | Select: E-Commerce / Maps / News / Finance / Jobs |
| 3 | `[SCREEN]` **Template Detail** | View: name, site pattern, selectors, parameters |
| 4 | `[API]` `GET /scraper/templates` | Fetch templates |
| 5 | `[SCREEN]` **Run Template** | Fill in parameters (URL, search term, page count) |
| 6 | `[API]` `POST /scraper/templates/{id}/run` | Execute with parameters |
| 7 | `[SCREEN]` **Results** | View extracted data |

#### ASCII Wireframe: Template Library

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Scraper → Templates                      [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Template Library ─── [All] [E-Commerce] [Maps] ──┐│
│          │ │                [News] [Finance] [Jobs]              ││
│          │ │                                                     ││
│          │ │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐  ││
│          │ │  │ Amazon       │ │ Google Maps  │ │ LinkedIn   │  ││
│          │ │  │ Products     │ │ Places       │ │ Jobs       │  ││
│          │ │  │ 🛒 ecommerce │ │ 🗺 maps      │ │ 💼 jobs    │  ││
│          │ │  │ Used: 1,234  │ │ Used: 890    │ │ Used: 567  │  ││
│          │ │  │ Rate: 94.2%  │ │ Rate: 97.1%  │ │ Rate: 88.5%│  ││
│          │ │  │ [Use]        │ │ [Use]        │ │ [Use]      │  ││
│          │ │  └──────────────┘ └──────────────┘ └────────────┘  ││
│          │ │                                                     ││
│          │ │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐  ││
│          │ │  │ Zillow       │ │ Indeed       │ │ Twitter/X  │  ││
│          │ │  │ Listings     │ │ Jobs         │ │ Posts      │  ││
│          │ │  │ 🏠 realestate│ │ 💼 jobs      │ │ 📱 social  │  ││
│          │ │  │ [Use]        │ │ [Use]        │ │ [Use]      │  ││
│          │ │  └──────────────┘ └──────────────┘ └────────────┘  ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Scraping Engine | ❌ | ❌ | ✅ Playwright + Scrapy |
| Template Library | ❌ | ❌ | ✅ 50+ templates |
| Parameterization | ❌ | ❌ | ✅ |
| Success Tracking | ❌ | ❌ | ✅ |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 31: Build Visual Scraping Workflow

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero scraping capability. No visual web automation builder. |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has zero scraping capability. Users must build custom notebooks with requests/BeautifulSoup. |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Builder** | Click "Visual Workflow Builder" |
| 2 | `[SCREEN]` **Workflow Canvas** | Drag nodes from palette: Navigate → Wait → Extract → Click → Loop |
| 3 | `[SCREEN]` **Node Config** | Configure each node: URL, selector, action, wait time |
| 4 | `[SCREEN]` **Preview** | Run step-by-step with live browser preview (Browserless) |
| 5 | `[API]` `POST /scraper/workflows` | Save workflow definition |
| 6 | `[API]` `POST /scraper/workflows/{id}/run` | Execute full workflow |
| 7 | `[WF]` `ScrapeWorkflowExecution` (Temporal) | Orchestrates: navigate → wait → extract → loop |
| 8 | `[SCREEN]` **Execution Log** | Step-by-step execution with timing and screenshots |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__create_workflow → define workflow steps
[MCP] mcp__voyant_scraper__run_workflow → execute
[MCP] mcp__voyant_scraper__get_workflow_status → monitor
[AGENT] "Build a workflow to crawl all product pages on site X, scroll to load more, extract titles and prices"
```

#### ASCII Wireframe: Visual Scraper Builder

```
┌──────────────────────────────────────────────────────────────────┐
│ Scraper Workflow Builder: "Product Crawler"          [Run] [Save] │
├──────────────────────────────────────────────────────────────────┤
│ ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────────┐ │
│ │Navigate│─→│ Wait   │─→│Extract │─→│Click   │─→│Loop/Next   │ │
│ │URL     │  │2s      │  │CSS     │  │Next    │  │Page        │ │
│ │        │  │        │  │.product│  │Page    │  │Max: 10     │ │
│ │        │  │        │  │-title  │  │Button  │  │            │ │
│ └────────┘  └────────┘  └────────┘  └────────┘  └────────────┘ │
│                                                                   │
│ ┌─ Node Details ─────────────────────────────────────────────┐   │
│ │ Extract: CSS Selector                                      │   │
│ │ Selector: [.product-title]                                 │   │
│ │ Attribute: [text]                                          │   │
│ │ Output: [product_names[]]                                  │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│ ┌─ Live Preview ─────────────────────────────────────────────┐   │
│ │ [Browserless screenshot showing extracted elements          │   │
│ │  highlighted on the page]                                   │   │
│ └────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Visual Workflow | ❌ | ❌ | ✅ React Flow canvas |
| Live Preview | ❌ | ❌ | ✅ Browserless |
| Node Types | ❌ | ❌ | 8 types (Navigate/Wait/Extract/Click/Scroll/Loop/Condition/Export) |
| Reusable Workflows | ❌ | ❌ | ✅ Save & share |
| Agent-built | ❌ | ❌ | ✅ MCP tools |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 32: Configure Anti-Bot (CAPTCHA, Proxy, Fingerprint)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero web scraping or anti-bot capability. Foundry connects only to authorized data sources. |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks has no built-in scraping. Users building scrapers in notebooks have no anti-bot support. |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Anti-Bot** | Navigate to anti-bot configuration panel |
| 2 | `[SCREEN]` **CAPTCHA Solver** | Enable CAPTCHA solving (2Captcha / AntiCaptcha integration) |
| 3 | `[SCREEN]` **Proxy Config** | Configure proxy pool: residential/datacenter, rotation strategy, geo-targeting |
| 4 | `[API]` `PUT /scraper/config/anti-bot` | Save anti-bot configuration |
| 5 | `[SCREEN]` **Fingerprint** | Enable browser fingerprint randomization (canvas, WebGL, fonts, screen) |
| 6 | `[SCREEN]` **Rate Limiting** | Set: requests/second, concurrent sessions, delay between requests |
| 7 | `[SCREEN]` **User-Agent Pool** | Manage rotating user agent strings (100+ pre-loaded) |
| 8 | `[SCREEN]` **Test Panel** | Test anti-bot config against target site |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__configure_anti_bot → set anti-bot config
[MCP] mcp__voyant_scraper__test_anti_bot → verify config works
[AGENT] "Enable residential proxy rotation and CAPTCHA solving for the Amazon scraper"
```

#### ASCII Wireframe: Anti-Bot Configuration

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Scraper → Anti-Bot                       [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Anti-Bot Configuration ───────────────────────────┐│
│          │ │                                                     ││
│          │ │ CAPTCHA Solving:  [☑ Enabled]                       ││
│          │ │   Provider: [2Captcha ▾]  API Key: [••••••••]       ││
│          │ │   Types: ☑ reCAPTCHA ☑ hCaptcha ☑ Cloudflare       ││
│          │ │                                                     ││
│          │ │ Proxy Pool:  [☑ Enabled]                            ││
│          │ │   Type: [Residential ▾]  Rotation: [Per-request ▾]  ││
│          │ │   Providers: [Bright Data ▾] [Oxylabs ▾]            ││
│          │ │   Geo: [US ▾] [EU ▾]  Pool size: [500 IPs]         ││
│          │ │                                                     ││
│          │ │ Fingerprint:  [☑ Enabled]                           ││
│          │ │   Canvas: ☑  WebGL: ☑  Fonts: ☑  Screen: ☑         ││
│          │ │                                                     ││
│          │ │ Rate Limiting:                                      ││
│          │ │   Max req/s: [5]  Delay: [1-3s random]              ││
│          │ │   Concurrent: [3]  Max pages/session: [100]         ││
│          │ │                                                     ││
│          │ │ User-Agent Pool: [127 agents loaded]                ││
│          │ │   Chrome: 45  Firefox: 38  Safari: 22  Edge: 22     ││
│          │ │                                            [Save]   ││
│          │ └─────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| CAPTCHA Solving | ❌ | ❌ | ✅ 2Captcha/AntiCaptcha |
| Proxy Rotation | ❌ | ❌ | ✅ Residential + Datacenter |
| Browser Fingerprint | ❌ | ❌ | ✅ Canvas/WebGL/Fonts/Screen |
| Rate Limiting | ❌ | ❌ | ✅ Per-task configurable |
| User-Agent Rotation | ❌ | ❌ | ✅ 127+ agents |
| Geo-targeting | ❌ | ❌ | ✅ Country-level proxy selection |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 33: Schedule Recurring Scrape

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero scraping capability. Data pipelines can be scheduled, but not web scraping. |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks Jobs can schedule notebooks, but there is no scraping infrastructure. Users would need to build custom solutions. |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Schedule** | Click "Schedule" on task or template |
| 2 | `[SCREEN]` **Schedule Config** | Set: cron expression, timezone, start/end dates |
| 3 | `[SCREEN]` **Advanced Options** | Configure: retry on failure, max retries, notify on completion |
| 4 | `[API]` `POST /scraper/schedules` | Create schedule |
| 5 | `[WF]` Temporal cron schedule | Automatic recurring execution via Temporal |
| 6 | `[SCREEN]` **Schedule List** | View all scheduled scrapes with next run time, status |
| 7 | `[SCREEN]` **Run History** | View past runs with success/failure, duration, artifacts |
| 8 | `[API]` `GET /scraper/schedules/{id}/runs` | Fetch run history |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__schedule_task → create schedule
[MCP] mcp__voyant_scraper__list_schedules → browse schedules
[MCP] mcp__voyant_scraper__schedule_history → view past runs
[AGENT] "Schedule the competitor price scrape to run every 6 hours"
```

#### ASCII Wireframe: Schedule Manager

```
┌──────────────────────────────────────────────────────────────────┐
│ [SIDEBAR]  Scraper → Schedules                      [User ▾]     │
├──────────┬───────────────────────────────────────────────────────┤
│          │ ┌─ Scheduled Scrapes ──── [+ New Schedule] ─────────┐│
│          │ │                                                     ││
│          │ │  Task               │ Cron      │ Next Run │ Status ││
│          │ │  Amazon Products    │ */6 * * * │ 18:00    │ ✅ Active││
│          │ │  Google Maps NYC    │ 0 9 * * 1 │ Mon 9am  │ ✅ Active││
│          │ │  Competitor Prices  │ 0 */2 * * │ 16:00    │ ✅ Active││
│          │ │  Job Listings       │ 0 0 * * * │ Midnight │ ⏸ Paused ││
│          │ │                                                     ││
│          │ ├─ Run History: Amazon Products ──────────────────────┤│
│          │ │  Time      │ Status │ Duration │ Pages │ Artifacts  ││
│          │ │  14:00     │ ✅ OK  │ 2m 34s   │ 45    │ 2,340 rows ││
│          │ │  08:00     │ ✅ OK  │ 2m 12s   │ 45    │ 2,338 rows ││
│          │ │  02:00     │ ⚠️ 3 err│ 3m 01s  │ 42    │ 2,190 rows ││
│          │ └────────────────────────────────────────────────────┘│
└──────────┴───────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| Cron Scheduling | ❌ | ❌ | ✅ Temporal cron |
| Visual Scheduler | ❌ | ❌ | ✅ UI + cron expression |
| Retry on Failure | ❌ | ❌ | ✅ Configurable retries |
| Run History | ❌ | ❌ | ✅ Full audit trail |
| Per-task Schedule | ❌ | ❌ | ✅ Independent schedules |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 34: Export Results (JSON, CSV, XLSX, DB)

### Palantir Foundry

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Palantir has zero scraping capability. Data exports from Foundry are via dataset download, not scraping-specific. |

### Databricks

| Step | Screen | Action |
|------|--------|--------|
| — | N/A | Databricks exports via `COPY INTO` or notebook output, but has no scraping data export pipeline. |

### Voyant v4.0

| Step | Screen | Action |
|------|--------|--------|
| 1 | `[SCREEN]` **Scraper → Results** | View scrape job results with artifact list |
| 2 | `[SCREEN]` **Export Menu** | Click "Export" on job or artifact |
| 3 | `[SCREEN]` **Format Selector** | Choose: JSON / CSV / XLSX / XML / Database (PostgreSQL/Iceberg) |
| 4 | `[API]` `POST /scraper/jobs/{id}/export` | Generate export in selected format |
| 5 | `[SCREEN]` **Download** | Download file or confirm DB write |
| 6 | `[API]` `POST /scraper/jobs/{id}/export/auto` | Configure auto-export on job completion |
| 7 | `[SCREEN]` **Export History** | View past exports with format, size, destination |

#### Agent Path (MCP)

```
[MCP] mcp__voyant_scraper__export_results → export data
[MCP] mcp__voyant_scraper__configure_auto_export → set auto-export
[AGENT] "Export the latest Amazon scrape as XLSX and write to the products Iceberg table"
```

#### ASCII Wireframe: Export Dialog

```
┌──────────────────────────────────────────────────────────────────┐
│ Export Results: Job #scrape-a1b2c3d4                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│ Format:     (●) JSON  ( ) CSV  ( ) XLSX  ( ) XML                │
│                                                                   │
│ Destination: (●) Download  ( ) Database  ( ) S3/MinIO            │
│                                                                   │
│ Options:                                                          │
│   ☑ Include metadata  ☑ Flatten nested JSON  ☐ Compress (gzip)  │
│                                                                   │
│ Preview:                                                          │
│ ┌────────────────────────────────────────────────────────────┐   │
│ │ [{"title": "Widget A", "price": 29.99, "rating": 4.5},    │   │
│ │  {"title": "Widget B", "price": 49.99, "rating": 4.8},    │   │
│ │  ... (2,340 rows total)]                                   │   │
│ └────────────────────────────────────────────────────────────┘   │
│                                                                   │
│ Size estimate: 1.2 MB                            [Export] [Cancel]│
└──────────────────────────────────────────────────────────────────┘
```

### Comparison

| Feature | Palantir | Databricks | Voyant |
|---------|----------|------------|--------|
| JSON | ❌ (no scraping) | ❌ | ✅ |
| CSV | ❌ | ❌ | ✅ |
| XLSX | ❌ | ❌ | ✅ |
| XML | ❌ | ❌ | ✅ |
| Direct DB Write | ❌ | ❌ | ✅ PostgreSQL + Iceberg |
| Auto-export | ❌ | ❌ | ✅ On job completion |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

# PART G: AGENT JOURNEYS (VOYANT-UNIQUE)

These journeys exist **only** in Voyant. Neither Palantir nor Databricks can do them.

---

## Journey 35: Agent Discovers New Data Source → Auto-Creates Ontology Types

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Agent receives instruction: "Onboard the PostgreSQL sales database" |
| 2 | `[MCP]` `mcp__voyant_discovery__register_source` | Register data source |
| 3 | `[MCP]` `mcp__voyant_discovery__discover_schema` | Discover tables, columns, types |
| 4 | `[MCP]` `mcp__voyant_discovery__profile_table` | Profile each table (types, distributions, nulls) |
| 5 | `[AGENT]` | Agent analyzes schema → infers Object Types |
| 6 | `[MCP]` `mcp__voyant_ontology__create_object_type` | Create ObjectType for each table |
| 7 | `[MCP]` `mcp__voyant_ontology__create_property` | Create Properties for each column |
| 8 | `[AGENT]` | Agent infers relationships from FK columns |
| 9 | `[MCP]` `mcp__voyant_ontology__create_link_type` | Create LinkTypes for FK relationships |
| 10 | `[MCP]` `mcp__voyant_ontology__batch_create_objects` | Ingest data as Object instances |
| 11 | `[SCREEN]` **Ontology Explorer** | New types appear automatically |

#### Flow Diagram

```
Agent: "Onboard the sales database"
    │
    ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Register Source │────→│ Discover Schema │────→│ Profile Tables  │
│ (PostgreSQL)    │     │ (12 tables)     │     │ (types, nulls)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
    ┌───────────────────────────────────────────────────┘
    ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Create Object   │────→│ Create          │────→│ Create Link     │
│ Types (12)      │     │ Properties (89) │     │ Types (15)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                                ┌─────────────────┐
                                                │ Batch Ingest    │
                                                │ Objects (45,678)│
                                                └─────────────────┘
```

### Comparison

| Step | Palantir | Databricks | Voyant |
|------|----------|------------|--------|
| Auto-discovery | ⚠️ Manual wizard | ⚠️ Manual | ✅ Agent-driven |
| Auto-ontology | ❌ | ❌ | ✅ Agent creates types |
| Auto-linking | ❌ | ❌ | ✅ Agent infers FK → LinkType |
| **Voyant-unique** | ❌ | ❌ | ✅ Exclusive |

---

## Journey 36: Agent Answers NL Question Using Ontology + SQL

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "What's the average order value by customer segment?" |
| 2 | `[AGENT]` | Intent Engine classifies: DATA_QUERY |
| 3 | `[MCP]` `mcp__voyant_ontology__list_object_types` | Load schema: Customer (segment), Order (amount) |
| 4 | `[MCP]` `mcp__voyant_ontology__search_objects` | Find relevant types |
| 5 | `[AGENT]` | Generate SQL: `SELECT c.segment, AVG(o.amount) FROM ...` |
| 6 | `[MCP]` `mcp__voyant_sql__execute_query` | Execute SQL |
| 7 | `[AGENT]` | Format results with explanation |
| 8 | `[MCP]` `mcp__voyant_sql__list_tables` | (verify table exists) |

#### Full Agent Trace

```
User: "What's the average order value by customer segment?"

Agent Trace:
  1. classify_intent() → DATA_QUERY
  2. list_object_types() → [Customer (12 props), Order (8 props)]
  3. search_objects("segment") → Customer.segment found
  4. search_objects("amount") → Order.amount found
  5. Plan: SQL query with JOIN
  6. validate_plan() → permissions OK
  7. execute_query("SELECT c.segment, AVG(o.amount) ...") →
     ┌──────────────┬────────────┐
     │ segment      │ avg_amount │
     ├──────────────┼────────────┤
     │ Enterprise   │ $12,450    │
     │ Mid-Market   │ $5,230     │
     │ SMB          │ $1,890     │
     └──────────────┴────────────┘
  8. Format response with explanation
```

---

## Journey 37: Agent Traverses Relationships (Multi-Hop)

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "Find all products ordered by Acme Corp's top sales rep" |
| 2 | `[MCP]` `mcp__voyant_ontology__search_objects` | Find Customer "Acme Corp" |
| 3 | `[MCP]` `mcp__voyant_ontology__traverse_links` | Customer → SalesRep (1 hop) |
| 4 | `[MCP]` `mcp__voyant_ontology__traverse_links` | SalesRep → Orders (2 hops) |
| 5 | `[MCP]` `mcp__voyant_ontology__traverse_links` | Orders → Products (3 hops) |
| 6 | `[AGENT]` | Aggregate and format results |

#### Traversal Visualization

```
Customer "Acme Corp"
    │
    ├──[assigned_to]──→ SalesRep "Jane Smith" (top performer)
    │                      │
    │                      ├──[placed]──→ Order #1001
    │                      │                 │
    │                      │                 ├──[contains]──→ Product "Widget A"
    │                      │                 ├──[contains]──→ Product "Widget B"
    │                      │
    │                      ├──[placed]──→ Order #1098
    │                                        │
    │                                        └──[contains]──→ Product "Service Plan"
```

### Comparison

| Capability | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| Graph Traversal | ✅ 10-hop | ❌ | ✅ 10-hop |
| Agent-driven | ❌ | ❌ | ✅ MCP traverse |
| NL query | ❌ | ❌ | ✅ |

---

## Journey 38: Agent Executes Action on Ontology Object

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "Approve order #1001 and notify the customer" |
| 2 | `[MCP]` `mcp__voyant_ontology__get_object` | Fetch Order #1001 |
| 3 | `[AGENT]` | Check: order status is "pending" (pre-condition met) |
| 4 | `[MCP]` `mcp__voyant_ontology__execute_action` | Execute "Approve Order" action |
| 5 | `[AGENT]` | Action side effect: send notification to customer |
| 6 | `[MCP]` `mcp__voyant_ontology__get_object` | Verify order status → "approved" |
| 7 | `[SCREEN]` **Audit Log** | Action logged with full context |

### Comparison

| Capability | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| Action Types | ✅ Kinetics | ❌ | ✅ ActionType |
| Agent-executed | ❌ | ❌ | ✅ MCP |
| Side effects | ✅ | ❌ | ✅ Notifications + webhooks |
| Undo | ✅ | ❌ | ✅ (planned) |

---

## Journey 39: Agent Runs Scraping Task via MCP

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "Scrape the latest product prices from competitor.com" |
| 2 | `[MCP]` `mcp__voyant_scraper__create_task` | Create scrape job with URL + selectors |
| 3 | `[MCP]` `mcp__voyant_scraper__get_status` | Monitor job progress |
| 4 | `[MCP]` `mcp__voyant_scraper__get_results` | Fetch extracted data |
| 5 | `[AGENT]` | Analyze data: "Competitor X has 15 products cheaper than ours" |
| 6 | `[MCP]` `mcp__voyant_scraper__export_results` | Export to Iceberg table |
| 7 | `[MCP]` `mcp__voyant_ontology__batch_create_objects` | Create PriceAlert objects |

### Comparison

| Capability | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| Scraping | ❌ | ❌ | ✅ |
| Agent-triggered | ❌ | ❌ | ✅ MCP |
| Auto-analysis | ❌ | ❌ | ✅ |
| Auto-ontology | ❌ | ❌ | ✅ |

---

## Journey 40: Agent Triggers ML Training Pipeline

### Voyant v4.0

| Step | Actor | Action |
|------|-------|--------|
| 1 | `[AGENT]` | Receives: "Retrain the churn model with the latest data" |
| 2 | `[MCP]` `mcp__voyant_ml__create_experiment` | Create or reuse experiment |
| 3 | `[MCP]` `mcp__voyant_ml__start_run` | Start training run |
| 4 | `[MCP]` `mcp__voyant_sql__execute_query` | Fetch latest training data |
| 5 | `[WF]` `MLTrainingWorkflow` (Temporal) | Execute: data prep → train → evaluate |
| 6 | `[MCP]` `mcp__voyant_ml__log_metric` | Log metrics (accuracy, F1, AUC) |
| 7 | `[AGENT]` | Compare with previous: "New model: F1 0.93 vs old 0.91" |
| 8 | `[MCP]` `mcp__voyant_ml__register_model` | Register new model version |
| 9 | `[MCP]` `mcp__voyant_ml__create_endpoint` | Deploy to production endpoint |
| 10 | `[AGENT]` | "Churn model retrained and deployed. F1 improved 2.2%" |

#### Agent Pipeline Flow

```
Agent: "Retrain churn model"
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Create       │────→│ Fetch Latest │────→│ Start        │
│ Experiment   │     │ Training Data│     │ Training Run │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Deploy to    │←────│ Compare      │←────│ Log          │
│ Endpoint     │     │ vs Previous  │     │ Metrics      │
└──────────────┘     └──────────────┘     └──────────────┘
        │
        ▼
"Churn model deployed. F1: 0.93 (+2.2%)"
```

### Comparison

| Capability | Palantir | Databricks | Voyant |
|------------|----------|------------|--------|
| ML Training | ✅ | ✅ | ✅ MLflow-compatible |
| Agent-triggered | ❌ | ❌ | ✅ MCP |
| Auto-deploy | ❌ | ⚠️ Manual | ✅ Agent-driven |
| Auto-compare | ❌ | ❌ | ✅ |

---

# CROSS-CUTTING ANALYSIS

---

## Journey Coverage Matrix

| # | Journey | Palantir | Databricks | Voyant |
|---|---------|----------|------------|--------|
| 1 | Register Data Source | ✅ | ✅ | ✅ + Agent |
| 2 | Create ETL Pipeline | ✅ | ✅ | ✅ + LLM Transform |
| 3 | Monitor Pipeline | ✅ | ✅ | ✅ + Self-healing |
| 4 | Data Quality | ✅ | ✅ | ✅ + Agent rules |
| 5 | Data Lineage | ✅ | ✅ | ✅ + Agent explored |
| 6 | Explore Ontology | ✅ | ⚠️ Tables only | ✅ + Agent |
| 7 | SQL Editor | ✅ | ✅ | ✅ + Agent SQL |
| 8 | Semantic Search | ⚠️ Objects only | ✅ Genie | ✅ Intent Engine |
| 9 | Build Dashboard | ✅ Workshop | ✅ | ✅ + Agent-built |
| 10 | Export Data | ✅ | ✅ | ✅ + Agent export |
| 11 | Notebook | ✅ Quiver | ✅ | ✅ Ontology-aware |
| 12 | Train ML | ✅ | ✅ MLflow | ✅ + Agent train |
| 13 | Compare Runs | ✅ | ✅ MLflow | ✅ |
| 14 | Register Model | ✅ | ✅ | ✅ + Agent |
| 15 | Deploy Model | ✅ | ✅ | ✅ + Agent deploy |
| 16 | Monitor Drift | ✅ | ✅ | ✅ + Agent monitor |
| 17 | Define Agent | ✅ AIP | ✅ Agent Bricks | ✅ + Open-source |
| 18 | Evaluate Agent | ✅ | ✅ | ✅ |
| 19 | Deploy Agent | ✅ | ✅ | ✅ + MCP endpoint |
| 20 | Monitor Agent | ✅ | ✅ | ✅ |
| 21 | Build MCP Tools | ❌ | ❌ | ✅ **Unique** |
| 22 | Create Capsule | ❌ | ❌ | ✅ **Unique** |
| 23 | Configure RBAC | ✅ | ✅ | ✅ + Agent RBAC |
| 24 | Row-level Security | ✅ | ✅ | ✅ |
| 25 | Column Masking | ✅ | ✅ | ✅ |
| 26 | Audit Logs | ✅ | ✅ | ✅ + Agent audit |
| 27 | Data Retention | ✅ | ✅ | ✅ |
| 28 | GDPR Deletion | ⚠️ | ❌ | ✅ Automated |
| 29 | Create Scrape Task | ❌ | ❌ | ✅ **Unique** |
| 30 | Template Library | ❌ | ❌ | ✅ **Unique** |
| 31 | Visual Scraper | ❌ | ❌ | ✅ **Unique** |
| 32 | Anti-Bot | ❌ | ❌ | ✅ **Unique** |
| 33 | Schedule Scrape | ❌ | ❌ | ✅ **Unique** |
| 34 | Export Scrape | ❌ | ❌ | ✅ **Unique** |
| 35 | Agent Auto-ontology | ❌ | ❌ | ✅ **Unique** |
| 36 | Agent NL Query | ❌ | ❌ | ✅ **Unique** |
| 37 | Agent Multi-hop | ❌ | ❌ | ✅ **Unique** |
| 38 | Agent Actions | ❌ | ❌ | ✅ **Unique** |
| 39 | Agent Scraping | ❌ | ❌ | ✅ **Unique** |
| 40 | Agent ML Pipeline | ❌ | ❌ | ✅ **Unique** |

---

## Voyant Unique Advantages Summary

| Advantage | Journeys | Description |
|-----------|----------|-------------|
| **MCP Protocol (80+ tools)** | All agent journeys | Neither Palantir nor Databricks has MCP support |
| **Agent-First Design** | 35–40 | Every feature callable by AI agents |
| **Web Scraping Engine** | 29–34, 39 | 8,471 LOC — competitors have nothing |
| **Capsule System** | 22 | Portable intelligence recipes with Ed25519 signing |
| **Self-Hosted** | All | Full Docker deployment, no vendor lock-in |
| **Open Source** | All | Apache 2.0, community-driven |
| **Temporal Workflows** | All pipelines | Durable, self-healing orchestration |
| **Intent Engine** | 8, 36 | NL → structured execution plan |
| **GDPR Automation** | 28 | Automated deletion workflow with certificates |
| **4 Access Modes** | All | UI + API + MCP + CLI (planned) |

---

## Per-Role Feature Availability

| Feature | Data Eng | Analyst | Data Sci | Agent Eng | Gov Officer | Scraper Op |
|---------|----------|---------|----------|-----------|-------------|------------|
| Journey 1-5 | ✅ Core | 👁 Read | 👁 Read | 🔧 MCP | 🔒 Audit | — |
| Journey 6-10 | 👁 Read | ✅ Core | 👁 Read | 🔧 MCP | 🔒 Audit | — |
| Journey 11-16 | — | — | ✅ Core | 🔧 MCP | 🔒 Audit | — |
| Journey 17-22 | — | — | — | ✅ Core | 🔒 Audit | — |
| Journey 23-28 | 🔒 Apply | — | — | 🔒 Apply | ✅ Core | — |
| Journey 29-34 | — | — | — | 🔧 MCP | — | ✅ Core |
| Journey 35-40 | — | — | — | ✅ Core | — | — |

---

## API Endpoint Summary by Journey

| Journey Group | Key Endpoints | Count |
|--------------|---------------|-------|
| Data Source (1) | `POST /ingestion/sources`, `POST /ingestion/sources/{id}/discover`, `POST /ingestion/sources/{id}/sync` | 5 |
| Pipeline (2-3) | `POST /pipelines`, `POST /pipelines/{id}/run`, `GET /pipelines/{id}/runs/{run_id}` | 6 |
| Quality (4) | `POST /data/quality/rules`, `POST /data/quality/rules/{id}/run` | 4 |
| Lineage (5) | `GET /data/lineage/{dataset}`, `POST /data/lineage/track` | 3 |
| Ontology (6) | `GET /ontology/object-types`, `GET /ontology/object-types/{id}/objects`, `GET /ontology/objects/{id}/traverse` | 15 |
| SQL (7) | `POST /sql/query`, `GET /sql/tables`, `GET /sql/tables/{id}/describe` | 3 |
| Search (8) | `GET /search/query`, `POST /search/index` | 4 |
| Dashboard (9) | `POST /dashboards`, `PUT /dashboards/{id}` | 4 |
| Export (10) | `POST /export`, `POST /export/schedule` | 3 |
| ML (11-16) | `POST /ml/experiments`, `POST /ml/runs`, `POST /ml/models`, `POST /ml/endpoints` | 12 |
| Agent (17-22) | `POST /ml/agents`, `POST /ml/evaluations`, `POST /mcp/tools`, `POST /capsules` | 12 |
| Governance (23-28) | `GET /governance/roles`, `POST /governance/row-filters`, `GET /governance/audit` | 12 |
| Scraper (29-34) | `POST /scraper/jobs`, `GET /scraper/templates`, `POST /scraper/schedules` | 10 |

---

## MCP Tool Summary by Journey

| Journey Group | Key MCP Tools | Count |
|--------------|---------------|-------|
| Data Source | `mcp__voyant_discovery__register_source`, `discover_schema`, `profile_table`, `run_profiling` | 4 |
| Pipeline | `mcp__voyant_dataintel__create_pipeline`, `run_pipeline`, `pipeline_status`, `validate_quality` | 6 |
| Ontology | `mcp__voyant_ontology__create_object_type`, `search_objects`, `traverse_links`, `execute_action`, `batch_create_objects` | 15 |
| SQL | `mcp__voyant_sql__execute_query`, `list_tables`, `describe_table` | 3 |
| Search | `mcp__voyant_search__semantic_search` | 1 |
| ML | `mcp__voyant_ml__create_experiment`, `start_run`, `log_metric`, `register_model`, `create_endpoint`, `predict` | 8 |
| Agent | `mcp__voyant_ml__create_agent`, `create_evaluation`, `run_evaluation` | 5 |
| Scraper | `mcp__voyant_scraper__create_task`, `get_status`, `get_results`, `export_results`, `use_template` | 7 |
| Governance | `mcp__voyant_governance__audit_logs`, `gdpr_deletion`, `check_permissions` | 5 |

---

## VOYANT-ONLY SCREEN INDEX

All screens unique to Voyant that do not exist in Palantir or Databricks:

| Screen Name | View File | Journeys | Description |
|-------------|-----------|----------|-------------|
| Ontology Explorer | `view-ontology.ts` | 6, 35–38 | Browse types, objects, relationships with graph view |
| SQL Studio | `view-sql.ts` | 7 | Monaco editor with Trino/Spark backend |
| Semantic Search | `view-search.ts` | 8 | NL question → intent → SQL → results |
| Sources | `view-sources.ts` | 1 | Data source registration and monitoring |
| Scraper Templates | `view-scraper.ts` | 29–30 | Template library with 50+ categories |
| Scraper Builder | (new) | 31 | Visual workflow canvas (React Flow) |
| Scraper Anti-Bot | (new) | 32 | CAPTCHA, proxy, fingerprint config |
| Scraper Schedules | (new) | 33 | Recurring scrape management |
| Capsules | `view-capsules.ts` | 22 | Portable intelligence recipes |
| Audit Log | `view-audit.ts` | 26 | Full audit trail with agent actions |
| Governance | `view-governance.ts` | 23–28 | RBAC, RLS, masking, GDPR |
| Pipeline Builder | (new) | 2–3 | Visual DAG editor (React Flow) |
| Pipeline Monitor | (new) | 3 | Real-time DAG execution view |
| Data Quality | (new) | 4 | Quality rules and pass/fail dashboard |
| Data Lineage | (new) | 5 | Force-directed lineage graph |
| Dashboard Builder | (new) | 9 | Chart/table/widget builder (ECharts) |
| ML Experiments | (new) | 12–13 | Experiment tracking with run comparison |
| Model Registry | (new) | 14 | Versioned model management |
| Model Endpoints | (new) | 15–16 | Serving endpoints with monitoring |
| Agent Builder | (new) | 17 | Agent definition with MCP tool selection |
| Agent Evaluation | (new) | 18 | Test cases with AI judge scoring |
| Agent Monitor | (new) | 20 | Performance metrics, conversation browser |
| MCP Tool Builder | (new) | 21 | Visual tool definition + function editor |
| Notebook | (new) | 11 | Python/SQL cells with ontology integration |
| GDPR Compliance | (new) | 28 | Automated deletion workflow |

**Total screens:** 25 (13 existing `view-*.ts` + 12 new)

---

## KEY ARCHITECTURAL DIFFERENTIATORS

### Why Voyant Wins Where Others Can't Compete

#### 1. Agent-Native (Not Agent-Added)

| Aspect | Palantir | Databricks | Voyant |
|--------|----------|------------|--------|
| Design Philosophy | Human-first, agent bolted on | Human-first, agent bolted on | **Agent-first, human overlaid** |
| API for Agents | REST (no MCP) | REST (no MCP) | **REST + MCP (80+ tools)** |
| Agent Can Create Types | ❌ | ❌ | ✅ Via MCP tools |
| Agent Can Traverse Graph | ❌ | ❌ | ✅ 10-hop traversal |
| Agent Can Run Scraping | ❌ | ❌ | ✅ Full scraper access |
| Agent Can Train Models | ❌ | ❌ | ✅ ML pipeline access |

#### 2. Intent Engine (NL → Deterministic Execution)

```
Palantir:  NL → Object Search (limited)
Databricks: NL → Genie SQL (single table focus)
Voyant:    NL → Intent Classification → Schema Resolution → Plan Generation
           → Plan Validation → Deterministic Execution → Formatted Result
```

The Intent Engine is the key differentiator. It:
- Classifies intent (query / pipeline / scrape / analyze)
- Resolves against the full ontology schema
- Generates structured JSON execution plans (not raw SQL)
- Validates against permissions and governance rules
- Executes deterministically (no LLM in execution path)

#### 3. Scraping as a First-Class Platform

Neither Palantir nor Databricks has any scraping capability. Voyant provides:
- Playwright + Scrapy engines
- 50+ pre-built templates
- Visual workflow builder
- Anti-bot suite (CAPTCHA, proxy, fingerprint)
- Temporal-scheduled recurring scrapes
- 7 dedicated MCP tools for agent-driven scraping

#### 4. Capsule System (Portable Intelligence)

Voyant's Capsule system has no equivalent in any competitor:
- Portable recipes combining agents, tools, workflows, and prompts
- Ed25519 cryptographic signing for integrity
- Shareable across teams and deployments
- Agent-composable (agents can create and execute capsules)

#### 5. Self-Hosted + Open Source

| Aspect | Palantir | Databricks | Voyant |
|--------|----------|------------|--------|
| Deployment | Cloud-only (Palantir-managed) | Cloud-only (AWS/Azure/GCP) | **Docker (any infra)** |
| Source Code | Proprietary | Proprietary | **Apache 2.0** |
| Vendor Lock-in | High | High | **Zero** |
| Data Sovereignty | Palantir cloud | Cloud provider | **Your infrastructure** |
| Cost Model | Per-user + compute | Per-DBU | **Self-hosted (fixed infra cost)** |

---

## JOURNEY COMPLETION STATUS

| Phase | Journeys | Status | Notes |
|-------|----------|--------|-------|
| A: Data Engineer | 1–5 | ✅ Complete | All journeys fully documented |
| B: Business Analyst | 6–10 | ✅ Complete | All journeys fully documented |
| C: Data Scientist | 11–16 | ✅ Complete | All journeys fully documented |
| D: AI/Agent Engineer | 17–22 | ✅ Complete | All journeys fully documented |
| E: Governance Officer | 23–28 | ✅ Complete | All journeys fully documented |
| F: Scraper Operator | 29–34 | ✅ Complete | All journeys fully documented |
| G: Agent Journeys | 35–40 | ✅ Complete | All journeys fully documented |

**All 40 journeys documented with:**
- ✅ Step-by-step Palantir walkthrough
- ✅ Step-by-step Databricks walkthrough
- ✅ Step-by-step Voyant v4.0 walkthrough
- ✅ API endpoints (where applicable)
- ✅ MCP tools (where applicable)
- ✅ Comparison tables
- ✅ ASCII wireframes (16 screens)
- ✅ Cross-cutting analysis

---

**Created:** 2026-09-05
**Author:** Voyant Engineering
**Next review:** 2026-09-19
**Total journeys documented:** 40
**Total screens wireframed:** 16
**Total comparison tables:** 45
**Document standard:** ISO/IEC/IEEE 29148:2018 aligned
